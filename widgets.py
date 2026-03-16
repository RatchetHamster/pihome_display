import tkinter as tk
from PIL import ImageTk
import configparser
from get_info import *
from rex import Rex

# Read configuration
config = configparser.ConfigParser()
config.read('config.ini')


class WidgetBase(tk.Frame):
    """Base class for all widgets."""
    def __init__(self, master, controller, **kwargs):
        # --- Setup ---
        super().__init__(master, **kwargs)
        self.master = master
        self.controller = controller

        # --- Com props ---
        self.app_font = (config.get('App', 'font'), config.getint('App', 'font_size'), "bold")
        self.app_w = config.getint('App', 'width')
        self.app_h = config.getint('App', 'height')
        self.space_edge= config.getint('App', 'space_edge')
        self.space_between = config.getint('App', 'space_between')

        # --- Update & Screen intervals ---
        self.updatet_norm = 5*60*1000  # (ms) Default - can be overriden
        self.updatet_retry = [0.5*60*1000,2*60*1000]  # (ms) Default  - can be overriden
        self.retry_count = 0
        self.screen_refresh = 15*1000 # (ms) Default - can be overriden

    def update_cache(self, info_class, update_cache_fun_name):
        update_cache_fun_name()

        if info_class.is_retry_error:
            t = self.updatet_retry[self.retry_count]
            self.retry_count = min(self.retry_count+1, len(self.updatet_retry)-1)
            self.after(int(t), lambda: self.update_cache(info_class, update_cache_fun_name))
        else:
            self.retry_count = 0
            self.after(int(self.updatet_norm), lambda: self.update_cache(info_class, update_cache_fun_name))
    
    def update_screen(self, update_fun_name):
        update_fun_name()
        self.after(int(self.screen_refresh), lambda: self.update_screen(update_fun_name))
    

class HeaderWidget(WidgetBase):
    def __init__(self, master, controller):
        # --- Setup ---
        border_w = config.getint('App', 'border')
        super().__init__(master, controller, bg=config.get('Header Widget', 'bg_color'), borderwidth=border_w, relief="groove")

        # --- Pack Iteself --- 
        self.place(x=self.space_edge, y=self.space_edge, width=self.app_w-self.space_edge*2, height=config.getint('Header Widget', 'bar_height'))
        self.pack_propagate(False)

        # --- Properties ---
        self.info = HeaderInfo()
        self.pi_index = -1

        # --- Update intervals (ms) ---
        self.updatet_norm = 2*60*1000   # to update caches
        self.screen_refresh = 10*1000   # to check caches and update screen

        # --- Init --- 
        self.build_ui()
        self.update_cache(self.info, self.info.update_cache)
        self.update_screen(self.update_screen_fun)


    def build_ui(self):
        # Time and date:
        clock_font_size = config.getint('Header Widget', 'font_size_clock')
        date_font_size = config.getint('App', 'font_size') 
        self.clock_label = tk.Label(self, font=(config.get('App', 'font'), clock_font_size),bg=config.get('Header Widget', 'bg_color'))
        self.date_label = tk.Label(self, font=(config.get('App', 'font'), date_font_size),bg=config.get('Header Widget', 'bg_color'))
        self.clock_label.pack(side="right", padx=3)
        self.date_label.pack(side="right")

        # Temp, CPU, Mem: 
        self.tcm_label = tk.Label(self, font=(config.get('App', 'font'), 7),bg=config.get('Header Widget', 'bg_color'))
        self.tcm_label.pack(side="right", padx=10)
        
        # Pi online checks: 
        self.pi_frame = tk.Frame(self, bg=config.get('Header Widget', 'bg_color'))
        self.pi_frame.pack(side="left", fill="both")
        self.dot_label = tk.Label(self.pi_frame, text="⬤", bg=config.get('Header Widget', 'bg_color'), font=self.app_font)
        self.dot_label.pack(side="left", padx=3)
        self.piname_label = tk.Label(self.pi_frame, text="", bg=config.get('Header Widget', 'bg_color'), font=self.app_font)
        self.piname_label.pack(side="left")        


    def update_datetime(self):
        current_time = self.info.get_time()
        current_date = self.info.get_date()
        self.clock_label.config(text=current_time)
        self.date_label.config(text=current_date)


    def update_tcm(self):
        tcm = self.info.internals_cache
        text = f'{tcm["temp"]}\nC:{tcm["cpu"]}\nM:{tcm["mem"]}'
        self.tcm_label.config(text=text)


    def update_pi_check(self):
        self.pi_index += 1
        if self.pi_index > len(self.info.is_online_cache)-1:
            self.pi_index = 0
        name, is_online = list(self.info.is_online_cache.items())[self.pi_index]
        self.piname_label.config(text=name)
        if is_online == "online":
            self.dot_label.config(fg="green")
        else:
            self.dot_label.config(fg="red")

    def update_screen_fun(self):
        self.update_datetime()
        self.update_tcm()
        self.update_pi_check()


# ----- SCREEN 1 ----- #

class WeatherWidet(WidgetBase):
    def __init__(self, master, controller, x, y):
        """x, y,position of TL of the wideget within master frame"""
        # --- Setup ---
        super().__init__(master, controller, bg=master["bg"], borderwidth=2, relief="groove")

        # --- Pack itself --- 
        self.width = config.getint('Weather Widget', 'width')
        self.height = config.getint('Weather Widget', 'height')
        self.place(x=x, y=y, width=self.width, height=self.height)
        self.pack_propagate(False)

        # --- Update intervals [override defaults] ---
        self.updatet_norm = 30*60*1000 
        self.updatet_retry = [1*60*1000,5*60*1000,10*60*1000,15*60*1000,30*60*1000]  # minutes

        # --- Properties ---
        self.weather_info = WeatherInfo()

        # --- Init Methods ---
        self.build_ui()
        self.update_cache(self.weather_info, self.weather_info.update_weather_cache)
        self.update_screen(self.update_screen_fun)

    def build_ui(self):
        """
        [top frame]
        [ L ][ R  ]
        [frm][frm ]

        Top Frame: 
        [Icon, Sun u/d]
        [      T1/T2  ]
        L and R frame: 
        | [24hrs]   | |  [48hrs]    |
        | [High]    | |  [High]     |
        | [Low]     | |  [Low]      |
        | [Rain %]  | |  [Rain %]   |
        | [Wind]    | |  [Wind]     |
        | [Clouds %]| |  [Clouds %] |
        
        """

        self.icon_size = config.getint('Weather Widget', 'icon_size')

        self.top_frame = tk.Frame(self, height=self.icon_size, bg=self.master["bg"])
        self.left_frame = tk.Frame(self, width=int(self.width/2),bg=self.master["bg"])
        self.right_frame = tk.Frame(self, width=int(self.width/2),bg=self.master["bg"])

        self.top_frame.pack(side="top", fill="x")
        self.left_frame.pack(side="left", fill="y")
        self.right_frame.pack(side="left", fill="y")

        self.top_frame.pack_propagate(False)
        self.left_frame.pack_propagate(False)
        self.right_frame.pack_propagate(False)

        # --- Top Frame ---
        icon_img = None
        self.icon_label = tk.Label(self.top_frame, image=icon_img, bg=self.master["bg"])
        self.icon_label.image = icon_img
        self.icon_label.pack(side="left")
        self.sun_ud_label = tk.Label(self.top_frame, text=f"Sun Time", bg=self.master["bg"], font=self.app_font)
        self.sun_ud_label.pack(side="top")
        self.suntime_label = tk.Label(self.top_frame, text=f"↑ --:--\n↓ --:--", bg=self.master["bg"], font=self.app_font)
        self.suntime_label.pack(side="top")

        # --- Left Frame (24h) ---
        big_font = (config.get("App", "font"), 14)
        self.title24_label = tk.Label(self.left_frame, text="24h", bg=self.master["bg"], font=big_font)
        self.title24_label.pack(side="top")
        self.temp24_label = tk.Label(self.left_frame, text="--°/--°", bg=self.master["bg"], font=big_font)
        self.temp24_label.pack(side="top")
        self.rain24_label = tk.Label(self.left_frame, text="☂ --%", bg=self.master["bg"], font=big_font)
        self.rain24_label.pack(side="top")
        self.wind24_label = tk.Label(self.left_frame, text="≋ --m\u2044s", bg=self.master["bg"], font=big_font)
        self.wind24_label.pack(side="top")
        self.clouds24_label = tk.Label(self.left_frame, text="☁ --%", bg=self.master["bg"], font=big_font)
        self.clouds24_label.pack(side="top")

        # --- Right Frame (48hr) ---
        r_color = "gray40"
        self.title48_label = tk.Label(self.right_frame, text="48h", bg=self.master["bg"], fg=r_color, font=big_font)
        self.title48_label.pack(side="top") 
        self.temp48_label = tk.Label(self.right_frame, text="--°/--°", bg=self.master["bg"], fg=r_color, font=big_font)
        self.temp48_label.pack(side="top")   
        self.rain48_label = tk.Label(self.right_frame, text="--%", bg=self.master["bg"], fg=r_color, font=big_font)
        self.rain48_label.pack(side="top")
        self.wind48_label = tk.Label(self.right_frame, text="--m\u2044s", bg=self.master["bg"], fg=r_color, font=big_font)
        self.wind48_label.pack(side="top")
        self.clouds48_label = tk.Label(self.right_frame, text="--%", bg=self.master["bg"], fg=r_color, font=big_font)
        self.clouds48_label.pack(side="top")


    def update_screen_fun(self):
        """This just updates the parameters established in build_ui and cycles every 30 mins"""
        weather_data = self.weather_info.weather_cache
         # --- Top Frame ---
        icon = weather_data["now_24"]["icon"]
        icon = ImageTk.PhotoImage(icon) if icon is not None else None
        self.icon_label.configure(image=icon)
        self.icon_label.image = icon
        self.suntime_label.configure(text=f"↑ {weather_data['sunrise']}\n↓ {weather_data['sunset']}")
        
        # --- Left Frame ---
        self.temp24_label.configure(text=f"{weather_data['now_24']['high']}°/{weather_data['now_24']['low']}°")
        self.rain24_label.configure(text=f"☂ {weather_data['now_24']['rain_chance']}%")
        self.wind24_label.configure(text=f"≋ {weather_data['now_24']['wind']}m\u2044s")
        self.clouds24_label.configure(text=f"☁ {weather_data['now_24']['clouds']}%")
        # --- Right Frame ---
        self.temp48_label.configure(text=f"{weather_data['next_24']['high']}°/{weather_data['next_24']['low']}°")
        self.rain48_label.configure(text=f"{weather_data['next_24']['rain_chance']}%")
        self.wind48_label.configure(text=f"{weather_data['next_24']['wind']}m\u2044s")
        self.clouds48_label.configure(text=f"{weather_data['next_24']['clouds']}%")


class CalendarWidet(WidgetBase):
    def __init__(self, master, controller, x, y, width, height):
        """x, y,position of TL of the wideget within master frame"""
        # --- Setup ---
        super().__init__(master, controller, bg=master["bg"], borderwidth=2, relief="groove")

        # --- Pack Iteself ---
        self.place(x=x, y=y, width=width, height=height)
        self.pack_propagate(False)
        
        # --- Update intervals [override defaults] ---
        # None
        
        # --- Properties ---
        self.cal_info = CalendarInfo()

        # --- Init Methods ---
        self.build_ui()
        self.update_cache(self.cal_info, self.cal_info.update_all_cache)
        self.update_screen(self.update_screen_fun)


    def build_ui(self):
        self.cal_text = tk.Label(self, text="", bg=self.master["bg"], font=self.app_font, justify="left", anchor="nw")
        self.cal_text.pack(side="top", fill="both")

    def update_screen_fun(self):
        self.cal_text.config(text=self.cal_info.text_cache)


class NewsWidet(WidgetBase):
    def __init__(self, master, controller, x, y, width, height):
        """x, y,position of TL of the wideget within master frame"""
        # --- Setup ---
        super().__init__(master, controller, bg=master["bg"], borderwidth=2, relief="groove")

        # --- Pack Iteself ---
        self.place(x=x, y=y, width=width, height=height)
        self.pack_propagate(False)
        
        # --- Update intervals [override defaults] ---
        # None
        
        # --- Properties ---
        self.headline_index = -1
        self.icon=None
        self.text="Nothing..."
        self.news_info = NewsInfo()

        # --- Init Methods ---
        self.build_ui()
        self.update_cache(self.news_info, self.news_info.update_headline_cache)
        self.update_screen(self.update_screen_fun)


    def build_ui(self):
        self.news_text = tk.Label(self, text="", bg=self.master["bg"], font=self.app_font, justify="left", anchor="nw", wraplength=self.app_w-4*self.space_edge)
        self.news_text.pack(side="top", fill="both")


    def update_screen_fun(self):
        if len(self.news_info.headline_cache)==0:
            self.text = "Nothing..."
        else:
            self.headline_index += 1
            if self.headline_index >= len(self.news_info.headline_cache):
                self.headline_index = 0
            self.text = self.news_info.headline_cache[self.headline_index]
        self.news_text.config(text=self.text)


class JokeFactWidget(WidgetBase):
    def __init__(self, master, controller, x, y):
        """x, y,position of TL of the wideget within master frame"""
        # --- Setup ---
        super().__init__(master, controller, bg=master["bg"], borderwidth=2, relief="groove")

        # --- Pack Itself ---
        self.width = int(config.getint('Weather Widget', 'width')-self.space_between*2.75)
        self.height = config.getint('Weather Widget', 'height')
        self.place(x=x, y=y, width=self.width, height=self.height)
        self.pack_propagate(False)
        
        # --- Update intervals [override defaults] ---
        # None
        
        # --- Properties ---
        self.jf_info_index = -1
        self.icon=None
        self.text="Nothing..."
        self.jf_info = JokeFactInfo()

        # --- Init Methods ---
        self.build_ui()
        self.update_cache(self.jf_info, self.jf_info.update_cache)
        self.update_screen(self.update_screen_fun)


    def build_ui(self):
        # ICON INSTED OF REX:
        #icon_img = None
        #self.icon_label = tk.Label(self, image=icon_img, bg=self.master["bg"])
        #self.icon_label.image = icon_img
        #self.icon_label.pack(side="top")
        # REX INSTEAD OF ICON:
        self.rex = Rex(self)
        self.rex.configure(bg=self.master["bg"])
        self.rex.pack(side="top")
        
        self.jf_text = tk.Label(self, text="", bg=self.master["bg"], font=self.app_font, justify="left", anchor="nw", wraplength=self.width-2*self.space_edge)
        self.jf_text.pack(side="top", fill="both")        

    def update_screen_fun(self):
        if len(self.jf_info.cache)==0:
            self.text = "Nothing..."
            self.img = None
        else:
            self.jf_info_index += 1
            if self.jf_info_index >= len(self.jf_info.cache):
                self.jf_info_index = 0
            # ONLY IF ICON USED:
            #if self.jf_info.cache[self.jf_info_index]["type"]=="joke":
            #    img = Image.open("laugh.png")
            #else: 
            #    img = Image.open("ancient-scroll.png")
            #img = img.resize((40,40), Image.LANCZOS)
            #self.icon = ImageTk.PhotoImage(img)
            self.text = self.jf_info.cache[self.jf_info_index]["text"]

        #self.icon_label.configure(image=self.icon)
        #self.icon_label.image = self.icon
        self.jf_text.config(text=self.text)

        #Rex: 
        if hasattr(self.controller, "screen_timer"):
            if self.controller.screen_timer.is_off or self.controller.screen_timer.is_dimmed:
                self.rex.trigger_sleep()
            else:
                self.rex.trigger_wake()

# ----- SCREEN 2 ----- #

class RainWidet(WidgetBase):
    def __init__(self, master, controller):
        """x, y,position of TL of the wideget within master frame"""
        # --- Setup ---
        super().__init__(master, controller, bg=master["bg"], borderwidth=2, relief="groove")

        # --- Pack Iteself ---
        self.place(x=0, y=0, width=master.width, height=master.height)
        self.pack_propagate(False)
        
        # --- Update intervals (ms) ---
        self.updatet_norm = 30*60*1000  # 30 minutes
        self.updatet_retry = [1*60*1000,5*60*1000,15*60*1000,30*60*1000]  # 5,10,20,30 minutes
        
        # --- Properties ---
        self.rain_info = RainInfo()
        self.zoom_index = 0 # (0 = first zoom level, 1=second etc.)
        self.past_index = 0 # (0=now, 1=1 back in time etc.)
        self.skip_per_click = 3 # Number of frames to move per arrow click

        # --- Init Methods ---
        self.build_ui()
        self.update_cache(self.rain_info, self.rain_info.update_img_cache)
        self.update_screen(self.update_screen_fun)


    def build_ui(self):
        """
        This controler the setout of the weather widget, try and keep labels the same as used in update_weather:
        |   Rain Image   |
        | <<   Home   >> | (buttons x3)
        """
        # Rain image:
        timestamp, rain_img = self.rain_info.get_image(self.zoom_index, self.past_index)
        rain_img = ImageTk.PhotoImage(rain_img) if rain_img is not None else None

        self.rain_canvas = tk.Canvas(self, width=config.getint("Rain Widget", "px_w"), height=config.getint("Rain Widget", "px_h"), highlightthickness=0)
        self.rain_img_id = self.rain_canvas.create_image(0,0, anchor="nw", image=rain_img)
        self.ts_id = self.rain_canvas.create_text(4,4,anchor="nw", text=timestamp, fill="navy", font = (config.get("App","font"),20, "bold"))
        self.rain_canvas.pack(side="top")

        self.master.make_clickable(self.rain_canvas, callback=self.zoom_click)

        # Buttons: 
        self.controls = tk.Frame(self)
        self.controls.pack(side="bottom", fill="both")
        
        self.btn_prev = tk.Button(self.controls, text="◀", command=self.press_L, font = (config.get("App","font"),20))
        self.btn_home = tk.Button(self.controls, text="O", command=self.home_click, font = (config.get("App","font"),20, "bold"))
        self.btn_next = tk.Button(self.controls, text="▶", command=self.press_R, font = (config.get("App","font"),20))
        
        self.btn_prev.pack(side="left", expand=True, fill="both")
        self.btn_home.pack(side="left", expand=True, fill="both")
        self.btn_next.pack(side="left", expand=True, fill="both")

    # --- Clicks --- 
    def press_L(self):
        self.past_index += self.skip_per_click
        self.btn_next.config(fg="black")
        if self.past_index > len(self.rain_info.image_cache[self.rain_info.zoom_lvls[self.zoom_index]])-1:
            self.past_index -= self.skip_per_click
            return            
        self.update_screen_fun()
        
    def press_R(self):
        self.past_index -= self.skip_per_click
        if self.past_index < 0:
            self.past_index += self.skip_per_click
            return            
        self.update_screen_fun()
    
    def zoom_click(self, event=None):
        self.past_index = 0
        self.zoom_index += 1
        if self.zoom_index > len(self.rain_info.zoom_lvls)-1:
            self.zoom_index = 0
        self.past_index = 0
        self.update_screen_fun()
    
    def home_click(self):
        self.zoom_index = 0
        self.past_index = 0
        self.controller.show_screen("Screen1")
        self.update_screen_fun()

    def update_screen_fun(self):
        timestamp, rain_img = self.rain_info.get_image(self.zoom_index, self.past_index)
        rain_img = ImageTk.PhotoImage(rain_img) if rain_img is not None else None
        
        self.rain_canvas.itemconfig(self.rain_img_id, image=rain_img)
        self.rain_canvas.image = rain_img  # keep reference, or image disappears
        self.rain_canvas.itemconfig(self.ts_id, text=timestamp)      


# ----- SCREEN 3----- #
#See screen 1 calendar widget


# ----- FULLSCREEN TEXT ---- #
class FullScreenWidget(WidgetBase):
    def __init__(self, master, controller):
            """x, y,position of TL of the wideget within master frame"""
            # --- Setup ---
            super().__init__(master, controller, bg=master["bg"], borderwidth=2, relief="groove")

            # --- Pack Itself ---
            self.width = master.width
            self.height = master.height
            self.place(x=0, y=0, width=self.width, height=self.height)
            self.pack_propagate(False)
            
            # --- Init Methods ---
            self.build_ui()
            self.update_screen()


    def build_ui(self):       
        icon_img = None
        self.icon_label = tk.Label(self, image=icon_img, bg=self.master["bg"])
        self.icon_label.image = icon_img
        self.icon_label.pack(side="top")

        self.fs_text = tk.Label(self, text="", bg=self.master["bg"], font=self.app_font, justify="left", anchor="nw", wraplength=self.width)
        self.fs_text.pack(side="top", fill="both", expand=True)  

    def update_screen(self, text=None, icon=""): #Re-define
        self.icon_label.configure(image=icon)
        self.icon_label.image = icon

        if text=="" or text==None:
            text="Nothing..."
        self.fs_text.config(text=text)


