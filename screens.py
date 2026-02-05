import tkinter as tk
import configparser
from widgets import *


# Read configuration
config = configparser.ConfigParser()
config.read('config.ini')


class ScreenBase(tk.Frame):
    """Base class for all screens."""
    def __init__(self, master, controller, **kwargs):
        super().__init__(master, **kwargs)
        self.controller = controller
        self.space_edge= config.getint('App', 'space_edge')
        self.space_between = config.getint('App', 'space_between')
        self.width = config.getint('App', 'width') - 2*self.space_edge
        self.height = config.getint('App', 'height') - config.getint("Header Widget", "bar_height")- self.space_edge*2 - self.space_between

        self.place(x=self.space_edge, y=config.getint("Header Widget", "bar_height") + self.space_edge + self.space_between, width=self.width, height=self.height)     

    # Use this to assign a callback (e.g. callback=lamba e: controller.show_screen("Screen2")) to frame and all children
    def make_clickable(self, widget, callback):
        widget.bind("<Button-1>", callback)
        for child in widget.winfo_children():
            self.make_clickable(child, callback)
        


class Screen1(ScreenBase):
    def __init__(self, master, controller):
        super().__init__(master, controller, bg=config.get('Screen1', 'bg_color'))

        # WEATHER WIDET:
        self.weather_widget = WeatherWidet(self, controller, x=self.width - config.getint('Weather Widget', 'width'), y=0)
        self.make_clickable(self.weather_widget, callback=lambda e: controller.show_screen("Screen2"))

        # JOKE FACT WIDGET:
        self.jf_widget = JokeFactWidget(self, controller, x=0, y=0)
        self.make_clickable(self.jf_widget, callback=lambda e: controller.full_screen(self.jf_widget.text, self.jf_widget.icon))
        self.make_clickable(self.jf_widget.rex, callback=lambda e: self.jf_widget.rex.on_tap())

        # CALENDAR WIDGET: 
        self.calendar_widget = CalendarWidet(self, controller, 
                                             x=0, y=self.space_between + config.getint("Weather Widget", "height"),
                                             width=self.width, height=config.getint("Calendar Widget", "height"))
        self.make_clickable(self.calendar_widget, callback=lambda e: controller.show_screen("Screen3"))

        # NEWS WIDGET:
        news_y = self.space_between*2 + config.getint("Weather Widget", "height") + config.getint("Calendar Widget", "height")
        self.news_widget = NewsWidet(self, controller, x=0, y=news_y, width=self.width, height=self.height - news_y)
        self.make_clickable(self.news_widget, callback=lambda e: controller.full_screen(self.news_widget.text))


class Screen2(ScreenBase):
    def __init__(self, master, controller):
        super().__init__(master, controller, bg=config.get('Screen2', 'bg_color'))
        self.rain_widget = RainWidet(self, controller)


class Screen3(ScreenBase):
    def __init__(self, master, controller):
        super().__init__(master, controller, bg=config.get('Screen1', 'bg_color'))
        self.calendar_widget = CalendarWidet(self, controller, x=0, y=0, width=self.width, height=self.height)
        self.make_clickable(self.calendar_widget, callback=lambda e: controller.show_screen("Screen1"))


class FullScreen(ScreenBase):
    def __init__(self, master, controller):
        super().__init__(master, controller, bg=config.get('Screen1', 'bg_color'))
        self.fs_widget = FullScreenWidget(self, controller)
        self.make_clickable(self.fs_widget, callback=lambda e: controller.show_screen("Screen1"))