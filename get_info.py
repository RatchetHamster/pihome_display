import threading
import requests 
from datetime import datetime, timedelta, timezone
import configparser
from PIL import Image, ImageDraw
from io import BytesIO
import math
from icalendar import Calendar
import recurring_ical_events
import feedparser
import socket
import random
import psutil

# Read configuration
config = configparser.ConfigParser()
config.read('config.ini')
is_test = config.getboolean("App", "is_test")


class HeaderInfo():
    def __init__(self):
        self.host_ips = {"NAStopia": "192.168.0.141", "AudioPi": "192.168.0.82"}
        self.is_online_cache = {name: "offline" for name in self.host_ips}
        self.internals_cache = {"temp": "--°C", "cpu": "--%", "mem":"--%"}
        self.is_retry_error = False

    def get_time(self) -> str:
        return datetime.now(timezone.utc).strftime("%H:%M")

    def get_date(self) -> str:
        return datetime.now(timezone.utc).strftime("%a\n%d-%m-%y")

    def get_pi_status(self, host, port=22, timeout=5):
        try:
            host = str(host).strip()
            with socket.create_connection((host, port), timeout=timeout):
                return "online"
        except Exception as e:
            return "offline"
        
    def get_internals(self):
        try:
            self.internals_cache["temp"] = str(int(psutil.sensors_temperatures()['cpu_thermal'][0].current)) + '°C'
            self.internals_cache["cpu"] = str(int(psutil.cpu_percent())) + '%'
            self.internals_cache["mem"] = str(int(psutil.virtual_memory().percent))+ '%'
        except Exception as e:
            print(e)

        
    def update_cache(self):
        if getattr(self, "_update_thread", None) and self._update_thread.is_alive():
            return  # prevent overlapping runs
        
        self._update_thread = threading.Thread(target=self._call_update_cache, daemon=True)
        self._update_thread.start()
    
    def _call_update_cache(self):
        self.get_internals()
        for name, ip in self.host_ips.items():
            self.is_online_cache[name] = self.get_pi_status(ip)


class WeatherInfo():
    def __init__(self):
        self.api_key = config.get('Weather Widget','api_key')
        self.lat = config.get('Weather Widget', 'lat')
        self.lon = config.get('Weather Widget', 'lon')
        self.units = "Metric"
        self.weather_cache = {
                "icon": None,
                "high": "--",
                "low": "--",
                "rain_chance": "--",
                "wind": "--",
                "clouds": "--"}
        self.is_retry_error = False  # When true, it should try again sooner than typical update.

    def fetch(self):
        base_url = "https://api.openweathermap.org/data/2.5/forecast"
        params = {"lat": self.lat, "lon": self.lon, "units": self.units, "appid": self.api_key}
        r = requests.get(base_url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    
    def update_weather_cache(self):
        try:
            data = self.fetch()

            now = datetime.now(timezone.utc)
            t24 = now + timedelta(hours=24)
            t48 = now + timedelta(hours=48)

            def in_range(item, start, end):
                t = datetime.fromtimestamp(item["dt"], tz=timezone.utc)
                return start <= t < end

            block_24 = [i for i in data["list"] if in_range(i, now, t24)]
            block_48 = [i for i in data["list"] if in_range(i, t24, t48)]
            self.is_retry_error = False
            self.weather_cache = {    
                "now_24": self._summarize(block_24),
                "next_24": self._summarize(block_48),
                "sunrise": datetime.fromtimestamp(data["city"]["sunrise"], tz=timezone.utc).strftime("%H:%M"),
                "sunset": datetime.fromtimestamp(data["city"]["sunset"], tz=timezone.utc).strftime("%H:%M")}

        except Exception as e:
            print("Weather error:", e)
            self.is_retry_error = True
            return

    def _summarize(self, items):
        if not items:
            return None

        icon_code = items[0]["weather"][0]["icon"]
        temps = [i["main"]["temp"] for i in items]
        winds = [i["wind"]["speed"] for i in items]
        clouds = [i["clouds"]["all"] for i in items]
        pops = [i.get("pop", 0) for i in items]     
       
        return {
            "icon": self.get_image(icon_code=icon_code),
            "high": round(max(temps)),
            "low": round(min(temps)),
            "rain_chance": int(max(pops) * 100),
            "wind": int(sum(winds) / len(winds)),
            "clouds": int(sum(clouds) / len(clouds))}
    
    def get_image(self, icon_code: str):
        icon_url = f"https://openweathermap.org/img/wn/{icon_code}@2x.png"
        try:
            r = requests.get(icon_url)
            r.raise_for_status()
            self.is_retry_error = False
        except Exception as e:
            print("Icon fetch error:", e)
            self.is_retry_error = True
            return None
        img = Image.open(BytesIO(r.content))
        img_size = config.getint('Weather Widget', 'icon_size')
        return img.resize((img_size, img_size), Image.Resampling.LANCZOS) # This was commented out, probs needs a fix: ImageTk.PhotoImage(
    

class RainInfo():

    def __init__(self):
        self.api = "https://api.rainviewer.com/public/weather-maps.json"
        self.tile_url = "https://tilecache.rainviewer.com/v2/radar/{time}/256/{z}/{x}/{y}/2/1_1.png"
        self.lat = config.getfloat('Rain Widget','lat')
        self.lon = config.getfloat('Rain Widget','lon')
        self.px_w = config.getint('Rain Widget','px_w')
        self.px_h = config.getint('Rain Widget','px_h')
        self.max_img_cache = 12 if not is_test else 2
        self.zoom_lvls = [7,5,4] if not is_test else [7,5]
        self.is_retry_error = False # When true, it should try again sooner than typicall update. 

        #Cache: 
        self.base_img_cache = {}  # Base map image cache at different zoom levels {zoom level (int): Image}
        self.image_cache = {}   # Nested dicts; {zoom level (int): {timestamp: Image}}
        for zoom in self.zoom_lvls: 
            self.image_cache[zoom]={}
        
        #Initalisation of the base images and image cache is done by 'update_img_cache' thread, and called by widget

    #--Use this to get images--
    def get_image(self, zoom_index:int, past_index:int):
        """Return cached image for given zoom level index and past frame index.
        0 = most recent frame. 1 would be the frame before that, etc."""
        zoom = self.zoom_lvls[zoom_index]
        try:
            timestamp, img = list(self.image_cache[zoom].items())[-(past_index + 1)]
            return (datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%H:%M"), img)
        except:
            try:
                img = self.crop_to_pos(self.base_img_cache[zoom], self.lat, self.lon, zoom)
                return ("--:--", img)
            except:
                return ("--:--", None)

    #--Calculations--
    def latlon_to_tile(self, lat, lon, zoom):
        """Return fractional tile coordinates (x, y) for given lat/lon and zoom."""
        lat_rad = math.radians(lat)
        n = 2 ** zoom
        x = (lon + 180.0) / 360.0 * n
        y = (1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2.0 * n
        return x, y
    

    def crop_to_pos(self, img, lat, lon, zoom):
        center_x, center_y = self.latlon_to_tile(lat, lon, zoom)
        tile_size = 256
        tiles_x = math.ceil(self.px_w / tile_size) + 2
        tiles_y = math.ceil(self.px_h / tile_size) + 2
        start_x = int(center_x) - tiles_x // 2
        start_y = int(center_y) - tiles_y // 2
        px_center_x = int((center_x - start_x) * tile_size)
        px_center_y = int((center_y - start_y) * tile_size)
        left = px_center_x - self.px_w // 2
        top = px_center_y - self.px_h // 2
        return img.crop((left, top, left + self.px_w, top + self.px_h))

    #--Fetching--
    def get_base_tiles(self, lat, lon, zoom):
        base_tile_url = ("https://cartodb-basemaps-a.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png")
        
        center_x, center_y = self.latlon_to_tile(lat, lon, zoom)
        tile_size = 256
        tiles_x = math.ceil(self.px_w / tile_size) + 2
        tiles_y = math.ceil(self.px_h / tile_size) + 2
        start_x = int(center_x) - tiles_x // 2
        start_y = int(center_y) - tiles_y // 2

        base_img = Image.new("RGBA", (tiles_x * tile_size, tiles_y * tile_size))

        for dx in range(tiles_x):
            for dy in range(tiles_y):
                x = start_x + dx
                y = start_y + dy
                url = base_tile_url.format(z=zoom, x=x, y=y)
                try:
                    r = requests.get(url, timeout=10)
                    r.raise_for_status()
                    tile = Image.open(BytesIO(r.content)).convert("RGBA")
                    base_img.paste(tile, (dx * tile_size, dy * tile_size))
                    self.is_retry_error = False
                except Exception as e:
                    print(f"Rain update error: {e} (line {e.__traceback__.tb_lineno})")
                    self.is_retry_error = True
                    # In case of error, fill with transparent
                    base_img.paste(Image.new("RGBA", (tile_size, tile_size), (0,0,0,0)), (dx * tile_size, dy * tile_size))
        
        # Draw center point:
        draw = ImageDraw.Draw(base_img)
        px = int((center_x - start_x) * tile_size)
        py = int((center_y - start_y) * tile_size)
        radius = 6
        draw.ellipse((px - radius, py - radius, px + radius, py + radius), fill="red", outline="white", width=2)

        return base_img


    def get_region_tiles(self, timestamp, lat, lon, zoom):
        center_x, center_y = self.latlon_to_tile(lat, lon, zoom)
        tile_size = 256
        tiles_x = math.ceil(self.px_w / tile_size) + 2
        tiles_y = math.ceil(self.px_h / tile_size) + 2
        start_x = int(center_x) - tiles_x // 2
        start_y = int(center_y) - tiles_y // 2

        radar_img = Image.new("RGBA", (tiles_x * tile_size, tiles_y * tile_size))
        for dx in range(tiles_x):
            for dy in range(tiles_y):
                x = start_x + dx
                y = start_y + dy
                url = self.tile_url.format(time=timestamp, z=zoom, x=x, y=y)
                try:
                    r = requests.get(url, timeout=10)
                    r.raise_for_status()
                    tile = Image.open(BytesIO(r.content)).convert("RGBA")
                    tile.putalpha(140)  # Set transparency
                    radar_img.paste(tile, (dx * tile_size, dy * tile_size))
                    self.is_retry_error = False
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 404:
                        # Tile not found, fill with transparent
                        radar_img.paste(Image.new("RGBA", (tile_size, tile_size), (0,0,0,0)), (dx * tile_size, dy * tile_size))
                        self.is_retry_error = False
                    else:
                        print(f"Rain update error: {e} (line {e.__traceback__.tb_lineno})")
                        self.is_retry_error = True
                except Exception as e:
                    print(f"Rain update error: {e} (line {e.__traceback__.tb_lineno})")
                    self.is_retry_error = True

        combined = Image.alpha_composite(self.base_img_cache[zoom], radar_img)
        return self.crop_to_pos(combined, self.lat, self.lon, zoom)
    

    #--Cache Management--
    def update_base_tiles(self):
        for zoom in self.zoom_lvls:
            self.base_img_cache[zoom] = self.get_base_tiles(self.lat, self.lon, zoom)


    def update_img_cache(self):
        """This sets up '_call_update_img_cache' as a thread. """
        if getattr(self, "_update_thread", None) and self._update_thread.is_alive():
            return  # prevent overlapping runs
        
        self._update_thread = threading.Thread(target=self._call_update_img_cache, daemon=True)
        self._update_thread.start()


    def _call_update_img_cache(self):
        # On first call update base tiles to allow alpha composite later in this fun:
        if len(self.base_img_cache) == 0:
            self.update_base_tiles()
        
        #Update Img Cache:
        try:    
            data = requests.get(self.api, timeout=10)
            data.raise_for_status()
            self.is_retry_error = False

        except Exception as e:
            print(f"Rain update error: {e} (line {e.__traceback__.tb_lineno})")
            self.is_retry_error = True
            return

        past = data.json()["radar"]["past"][-self.max_img_cache:]
        timestamps = [f["time"] for f in past]
            
        for zoom in self.zoom_lvls:
            for ts in timestamps:
                if ts not in self.image_cache[zoom]:
                    self.image_cache[zoom][ts] = self.get_region_tiles(ts, self.lat, self.lon, zoom)
        
            # Cleanup cache length:
            if len(self.image_cache[zoom]) > self.max_img_cache:
                self.image_cache[zoom] = dict(list(self.image_cache[zoom].items())[-self.max_img_cache:])

            
    #--Debugging--
    def _debug_save_images(self):
        for zoom, ts_dict in self.image_cache.items():
            for ts, img in ts_dict.items():
                img.save(f"rain_zoom{zoom}_{ts}.png")


class CalendarInfo():
    def __init__(self):
        self.ical_urls = {
            "JBC": r"https://calendar.google.com/calendar/ical/jbreezecrow%40gmail.com/private-8db182c878d189a3051c0e34f192ad09/basic.ics",
            "Kid": r"https://calendar.google.com/calendar/ical/9go9bmpr030ibvsot2fdcun1b8%40group.calendar.google.com/private-4cecc62e2dda645ffca7f0168de11ced/basic.ics"}
        self.days_to_cache = 10 if not is_test else 3
        self.cal_cache = {} # a dict with day up to X cached days. Each day has a list dictionarys: 
            # Those dicts are: "calendar", "name", "begin"; where begin is time unless all day in which case "day"
        self.text_cache = "Nothing..."
        self.is_retry_error = False
        #Updating is started and controlled by the widget

    def update_all_cache(self):
        """This sets up as a thread. """
        # Function to call in thread: 
        def update_all():
            self.update_cal_cache()
            self.update_text_cache()
        
        if getattr(self, "_update_thread", None) and self._update_thread.is_alive():
            return  # prevent overlapping runs
        
        self._update_thread = threading.Thread(target=update_all, daemon=True)
        self._update_thread.start()

    def get_calendar(self, url):
        """fetch and parse calendar from URL given"""
        try:
            r = requests.get(url)
            r.raise_for_status()
            self.is_retry_error = False
            return Calendar.from_ical(r.text)
        except Exception as e:
            print("error in get_calendar:", e)
            self.is_retry_error = True
            return None
        
    def update_cal_cache(self):
        today = datetime.now().date()
        end_day = today + timedelta(days=self.days_to_cache - 1)
        self.cal_cache = {}

        start = datetime.now(timezone.utc)
        end = start + timedelta(days=self.days_to_cache)

        for name, url in self.ical_urls.items():
            cal = self.get_calendar(url)
            if cal is None:
                continue

            events = recurring_ical_events.of(cal).between(start, end)

            for event in events:
                dtstart = event.get("DTSTART")
                dtend = event.get("DTEND")
                summary = event.get("SUMMARY")

                if not dtstart or not dtend:
                    continue

                begin_dt = dtstart.dt
                end_dt = dtend.dt

                # Convert date → datetime if all-day
                if not isinstance(begin_dt, datetime):
                    begin_dt = datetime.combine(begin_dt, datetime.min.time(), tzinfo=timezone.utc)
                if not isinstance(end_dt, datetime):
                    end_dt = datetime.combine(end_dt, datetime.min.time(), tzinfo=timezone.utc)

                event_start = begin_dt.date()
                event_end = end_dt.date()
                if not isinstance(dtstart.dt, datetime) and not isinstance(dtend.dt, datetime):
                    event_end = event_end - timedelta(days=1)

                if event_end < today or event_start > end_day:
                    continue

                overlap_start = max(event_start, today)
                overlap_end = min(event_end, end_day)
                current_day = overlap_start

                while current_day <= overlap_end:
                    self.cal_cache.setdefault(current_day, []).append({
                        "calendar": name,
                        "name": str(summary),
                        "begin": (
                            begin_dt.strftime("%H:%M")
                            if isinstance(dtstart.dt, datetime)
                            else "[Day]"
                        ),
                    })
                    current_day += timedelta(days=1)
    
    def update_text_cache(self):
        text_out = ''
        today = datetime.now().date()
        for i in range(self.days_to_cache):
            day = today + timedelta(days=i)
            events = self.cal_cache.get(day, [])
            text_out += day.strftime("%A").upper() + day.strftime("  [%d-%m-%y]\n") # Date line.
            if events:
                # Sort events by time
                for event in events: 
                    if event["begin"]=="00:00":
                        event["begin"] = "[Day]"
                sorted_events = sorted(events, key=lambda x: x['begin'])
                for event in sorted_events:
                    text_out += f'  {event["calendar"]} {event["begin"]}  {event["name"]}\n'
            else:
                text_out += f" (no events)\n"
        self.text_cache = text_out


class NewsInfo():
    def __init__(self):
        self.url = "https://feeds.bbci.co.uk/news/rss.xml"
        self.headline_cache = []
        self.num_headlines_cache = 5 if not is_test else 2
        self.is_retry_error = False


    def update_headline_cache(self):        
        if getattr(self, "_update_thread", None) and self._update_thread.is_alive():
            return  # prevent overlapping runs
        
        self._update_thread = threading.Thread(target=self._call_update_headling, daemon=True)
        self._update_thread.start()


    def _call_update_headling(self):
        try:
            feed = feedparser.parse(self.url)
            self.is_retry_error = False
        except Exception as e:
            print("error in get_calendar:", e)
            self.is_retry_error = True
            return

        for i, entry in enumerate(feed.entries[:self.num_headlines_cache]):
            self.headline_cache.append(f'#{i+1}. {entry.title}')


class JokeFactInfo():
    def __init__(self):
        self.num_of_jokes = 10 if not is_test else 2
        self.num_of_facts = 10 if not is_test else 2
        self.is_retry_error = False
        self.cache = []
    
    def get_joke(self):
        url = "https://official-joke-api.appspot.com/random_joke"
        try:
            r = requests.get(url)
            r.raise_for_status()
            self.is_retry_error = False
        except Exception as e: 
            print(f"Error getting joke: {e}")
            self.is_retry_error = True
            return
        
        joke = r.json()
        return f'{joke.get("setup", "No Setup")} - {joke.get("punchline", "No punchline")}'
    
    def get_fact(self):
        url = "https://uselessfacts.jsph.pl/random.json?language=en"
        try:
            r = requests.get(url)
            r.raise_for_status()
            self.is_retry_error = False
        except Exception as e: 
            print(f"Error getting fact: {e}")
            self.is_retry_error = True

        return f'{r.json().get("text", "No Fact found")}'
    
    def update_cache(self):
        if getattr(self, "_update_thread", None) and self._update_thread.is_alive():
            return  # prevent overlapping runs
        
        self._update_thread = threading.Thread(target=self._call_update_jokefacts, daemon=True)
        self._update_thread.start()
    
    def _call_update_jokefacts(self):
        for _ in range(self.num_of_jokes):
            self.cache.append({"type": "joke", "text": self.get_joke()})
        for _ in range(self.num_of_facts):
            for _ in range(self.num_of_jokes):
                self.cache.append({"type": "fact", "text": self.get_fact()})
        random.shuffle(self.cache)

if __name__ == "__main__":
    # Test Datetime - OK:
    head = HeaderInfo()
    print("Current Time:", head.get_time())
    print("Current Date:", head.get_date())
    #print(f'nas: {head.get_pi_status(head.host_ips["NAStopia"])}')

    # Test Weather - OK:
    #weather_obj = WeatherInfo()
    #weather = weather_obj.get_weather()
    #print("Now 24h:", weather["now_24"])
    #print("Next 24h:", weather["next_24"])
    #print("Sunrise:", weather["sunrise"])
    #print("Sunset:", weather["sunset"])

    # Test Rain - OK:
    #rain = RainInfo()
    #rain._debug_save_images()

    # Test Cal - OK: 
    #cal = CalendarInfo()
    #cal.get_text_schedule()

    # Test Joke Fact: 
    JF = JokeFactInfo()
    print(JF.get_joke())
    print(JF.get_fact())
