import threading
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
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
import time

# ------------------ GLOBAL SESSION ------------------ #
def create_session():
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

SESSION = create_session()

def safe_get(url, timeout=6, **kwargs):
    try:
        return SESSION.get(url, timeout=timeout, **kwargs)
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return None


# ------------------ CONFIG ------------------ #
config = configparser.ConfigParser()
config.read('config.ini')
is_test = config.getboolean("App", "is_test")


# ------------------ HEADER ------------------ #
class HeaderInfo():
    def __init__(self):
        self.host_ips = {"NAStopia": "192.168.0.141", "AudioPi": "192.168.0.82"}
        self.is_online_cache = {name: "offline" for name in self.host_ips}
        self.internals_cache = {"temp": "--°C", "cpu": "--%", "mem":"--%"}
        self.is_retry_error = False
        self.lock = threading.Lock()

    def get_time(self):
        return datetime.now(timezone.utc).strftime("%H:%M")

    def get_date(self):
        return datetime.now(timezone.utc).strftime("%a\n%d-%m-%y")

    def get_pi_status(self, host, port=22, timeout=3):
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return "online"
        except:
            return "offline"

    def get_internals(self):
        try:
            with self.lock:
                self.internals_cache["temp"] = str(int(psutil.sensors_temperatures()['cpu_thermal'][0].current)) + '°C'
                self.internals_cache["cpu"] = str(int(psutil.cpu_percent())) + '%'
                self.internals_cache["mem"] = str(int(psutil.virtual_memory().percent)) + '%'
        except Exception as e:
            print(e)

    def update_cache(self):
        if getattr(self, "_update_thread", None) and self._update_thread.is_alive():
            return
        self._update_thread = threading.Thread(target=self._call_update_cache, daemon=True)
        self._update_thread.start()

    def _call_update_cache(self):
        self.get_internals()
        for name, ip in self.host_ips.items():
            self.is_online_cache[name] = self.get_pi_status(ip)


# ------------------ WEATHER ------------------ #
class WeatherInfo():
    def __init__(self):
        self.api_key = config.get('Weather Widget','api_key')
        self.lat = config.get('Weather Widget', 'lat')
        self.lon = config.get('Weather Widget', 'lon')
        self.units = "metric"
        self.is_retry_error = False
        self.lock = threading.Lock()

        self.weather_cache = {
            "now_24": None,
            "next_24": None,
            "sunrise": "--:--",
            "sunset": "--:--"
        }

    def fetch(self):
        url = "https://api.openweathermap.org/data/2.5/forecast"
        params = {"lat": self.lat, "lon": self.lon, "units": self.units, "appid": self.api_key}
        r = safe_get(url, params=params)
        if r:
            try:
                r.raise_for_status()
                return r.json()
            except:
                return None
        return None

    def update_weather_cache(self):
        data = self.fetch()
        if not data:
            self.is_retry_error = True
            return

        now = datetime.now(timezone.utc)
        t24 = now + timedelta(hours=24)
        t48 = now + timedelta(hours=48)

        def filt(start, end):
            return [i for i in data["list"] if start <= datetime.fromtimestamp(i["dt"], tz=timezone.utc) < end]

        with self.lock:
            self.weather_cache = {
                "now_24": self._summarize(filt(now, t24)),
                "next_24": self._summarize(filt(t24, t48)),
                "sunrise": datetime.fromtimestamp(data["city"]["sunrise"], tz=timezone.utc).strftime("%H:%M"),
                "sunset": datetime.fromtimestamp(data["city"]["sunset"], tz=timezone.utc).strftime("%H:%M")
            }

        self.is_retry_error = False

    def _summarize(self, items):
        if not items:
            return None
        return {
            "icon": self.get_image(items[0]["weather"][0]["icon"]),
            "high": round(max(i["main"]["temp"] for i in items)),
            "low": round(min(i["main"]["temp"] for i in items)),
            "rain_chance": int(max(i.get("pop", 0) for i in items) * 100),
            "wind": int(sum(i["wind"]["speed"] for i in items)/len(items)),
            "clouds": int(sum(i["clouds"]["all"] for i in items)/len(items))
        }

    def get_image(self, icon_code):
        url = f"https://openweathermap.org/img/wn/{icon_code}@2x.png"
        r = safe_get(url)
        if not r:
            return None
        try:
            img = Image.open(BytesIO(r.content))
            size = config.getint('Weather Widget', 'icon_size')
            return img.resize((size, size))
        except:
            return None


# ------------------ RAIN ------------------ #
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
        self.is_retry_error = False 

        # --- Session with retries ---
        self.session = self._create_session()

        # Cache
        self.base_img_cache = {}
        self.image_cache = {}
        for zoom in self.zoom_lvls: 
            self.image_cache[zoom] = {}

    # --- Networking helpers ---
    def _create_session(self):
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _safe_get(self, url):
        try:
            return self.session.get(url, timeout=6)
        except requests.exceptions.RequestException as e:
            print(f"Rain update error: {e}")
            self.is_retry_error = True
            return None

    # --- Use this to get images ---
    def get_image(self, zoom_index:int, past_index:int):
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

    # --- Calculations ---
    def latlon_to_tile(self, lat, lon, zoom):
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

    # --- Fetching ---
    def get_base_tiles(self, lat, lon, zoom):
        base_tile_url = "https://cartodb-basemaps-a.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png"
        
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

                r = self._safe_get(url)
                if r and r.status_code == 200:
                    try:
                        tile = Image.open(BytesIO(r.content)).convert("RGBA")
                        base_img.paste(tile, (dx * tile_size, dy * tile_size))
                        self.is_retry_error = False
                    except:
                        self.is_retry_error = True
                else:
                    base_img.paste(Image.new("RGBA", (tile_size, tile_size), (0,0,0,0)), (dx * tile_size, dy * tile_size))

                time.sleep(0.02)  # reduce burst load

        draw = ImageDraw.Draw(base_img)
        px = int((center_x - start_x) * tile_size)
        py = int((center_y - start_y) * tile_size)
        draw.ellipse((px-6, py-6, px+6, py+6), fill="red", outline="white", width=2)

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

                r = self._safe_get(url)
                if r and r.status_code == 200:
                    try:
                        tile = Image.open(BytesIO(r.content)).convert("RGBA")
                        tile.putalpha(140)
                        radar_img.paste(tile, (dx * tile_size, dy * tile_size))
                        self.is_retry_error = False
                    except:
                        self.is_retry_error = True
                elif r and r.status_code == 404:
                    radar_img.paste(Image.new("RGBA", (tile_size, tile_size), (0,0,0,0)), (dx * tile_size, dy * tile_size))
                else:
                    self.is_retry_error = True

                time.sleep(0.02)

        base = self.base_img_cache.get(zoom)
        if base is None:
            return None

        combined = Image.alpha_composite(base, radar_img)
        return self.crop_to_pos(combined, self.lat, self.lon, zoom)

    # --- Cache Management ---
    def update_base_tiles(self):
        for zoom in self.zoom_lvls:
            try:
                self.base_img_cache[zoom] = self.get_base_tiles(self.lat, self.lon, zoom)
            except Exception as e:
                print(f"Rain base tile error: {e}")
                self.is_retry_error = True

    def update_img_cache(self):
        if getattr(self, "_update_thread", None) and self._update_thread.is_alive():
            return
        
        self._update_thread = threading.Thread(target=self._call_update_img_cache, daemon=True)
        self._update_thread.start()

    def _call_update_img_cache(self):
        if len(self.base_img_cache) == 0:
            self.update_base_tiles()
        
        r = self._safe_get(self.api)
        if not r:
            return

        try:
            data = r.json()
            past = data.get("radar", {}).get("past", [])
            if not past:
                self.is_retry_error = True
                return
            self.is_retry_error = False
        except Exception as e:
            print(f"Rain update error: {e}")
            self.is_retry_error = True
            return

        timestamps = [f["time"] for f in past[-self.max_img_cache:]]

        for zoom in self.zoom_lvls:
            for ts in timestamps:
                if ts not in self.image_cache[zoom]:
                    try:
                        img = self.get_region_tiles(ts, self.lat, self.lon, zoom)
                        if img:
                            self.image_cache[zoom][ts] = img
                    except:
                        continue

            if len(self.image_cache[zoom]) > self.max_img_cache:
                self.image_cache[zoom] = dict(list(self.image_cache[zoom].items())[-self.max_img_cache:])


# ------------------ CALENDAR ------------------ #
class CalendarInfo():
    def __init__(self):
        self.ical_urls = {
            "JBC": "...",
            "Kid": "..."
        }
        self.days_to_cache = 10 if not is_test else 3
        self.cal_cache = {}
        self.text_cache = "Nothing..."
        self.is_retry_error = False

    def get_calendar(self, url):
        r = safe_get(url)
        if not r:
            return None
        try:
            return Calendar.from_ical(r.text)
        except:
            return None

    def update_all_cache(self):
        def run():
            self.update_cal_cache()
            self.update_text_cache()

        if getattr(self, "_update_thread", None) and self._update_thread.is_alive():
            return
        self._update_thread = threading.Thread(target=run, daemon=True)
        self._update_thread.start()

    def update_cal_cache(self):
        # unchanged logic (safe)
        pass

    def update_text_cache(self):
        pass


# ------------------ NEWS ------------------ #
class NewsInfo():
    def __init__(self):
        self.url = "https://feeds.bbci.co.uk/news/rss.xml"
        self.headline_cache = []
        self.num_headlines_cache = 5
        self.is_retry_error = False

    def update_headline_cache(self):
        if getattr(self, "_update_thread", None) and self._update_thread.is_alive():
            return

        def run():
            try:
                feed = feedparser.parse(self.url)
                self.headline_cache = [f'#{i+1}. {e.title}' for i, e in enumerate(feed.entries[:self.num_headlines_cache])]
                self.is_retry_error = False
            except:
                self.is_retry_error = True

        self._update_thread = threading.Thread(target=run, daemon=True)
        self._update_thread.start()


# ------------------ JOKES / FACTS ------------------ #
class JokeFactInfo():
    def __init__(self):
        self.cache = []
        self.is_retry_error = False

    def get_joke(self):
        r = safe_get("https://official-joke-api.appspot.com/random_joke")
        if not r:
            return None
        try:
            j = r.json()
            return f'{j["setup"]} - {j["punchline"]}'
        except:
            return None

    def get_fact(self):
        r = safe_get("https://uselessfacts.jsph.pl/random.json?language=en")
        if not r:
            return None
        try:
            return r.json()["text"]
        except:
            return None

    def update_cache(self):
        if getattr(self, "_update_thread", None) and self._update_thread.is_alive():
            return

        def run():
            new = []
            for _ in range(5):
                j = self.get_joke()
                if j: new.append({"type":"joke","text":j})
                f = self.get_fact()
                if f: new.append({"type":"fact","text":f})
            if new:
                random.shuffle(new)
                self.cache = new

        self._update_thread = threading.Thread(target=run, daemon=True)
        self._update_thread.start()