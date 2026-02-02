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
        self.width = config.getint('App', 'width')
        self.height = config.getint('App', 'height')
        self.space_edge= config.getint('App', 'space_edge')
        self.space_between = config.getint('App', 'space_between')
        self.place(x=0, y=0, width=self.width, height=self.height)

        # Create header widget
        self.header = HeaderWidget(self, controller)

    # Use this to assign a callback (e.g. callback=lamba e: controller.show_screen("Screen2")) to frame and all children
    def make_clickable(self, widget, callback):
        widget.bind("<Button-1>", callback)
        for child in widget.winfo_children():
            self.make_clickable(child, callback)
        


class Screen1(ScreenBase):
    def __init__(self, master, controller):
        super().__init__(master, controller, bg=config.get('Screen1', 'bg_color'))

        # WEATHER WIDET:
        self.weather_widget = WeatherWidet(self, controller,
                                        x=self.width - config.getint('Weather Widget', 'width') - self.space_edge,
                                        y=config.getint('Header Widget', 'bar_height') + self.space_edge + self.space_between)
        self.make_clickable(self.weather_widget, callback=lambda e: controller.show_screen("Screen2"))


        # JOKE FACT WIDGET:
        self.jf_widget = JokeFactWidget(self, controller,
                                        x=self.space_edge,
                                        y=config.getint('Header Widget', 'bar_height') + self.space_edge + self.space_between)
        self.make_clickable(self.jf_widget, callback=lambda e: controller.full_screen(self.jf_widget.text, self.jf_widget.icon))

        # CALENDAR WIDGET: 
        cal_y = config.getint('Header Widget', 'bar_height') + self.space_edge + self.space_between*2 + config.getint("Weather Widget", "height")
        self.calendar_widget = CalendarWidet(self, controller, 
                                             x=self.space_edge, y=cal_y,
                                             width=self.width - 2*self.space_edge, height=config.getint("Calendar Widget", "height"))
        self.make_clickable(self.calendar_widget, callback=lambda e: controller.show_screen("Screen3"))

        # NEWS WIDGET:
        news_y = config.getint('Header Widget', 'bar_height') + self.space_edge + self.space_between*3 + config.getint("Weather Widget", "height") + config.getint("Calendar Widget", "height")
        self.news_widget = NewsWidet(self, controller, 
                                        x=self.space_edge, y=news_y,
                                        width=self.width - 2*self.space_edge, height=self.height - news_y - self.space_edge)
        self.make_clickable(self.news_widget, callback=lambda e: controller.full_screen(self.news_widget.text))


class Screen2(ScreenBase):
    def __init__(self, master, controller):
        super().__init__(master, controller, bg=config.get('Screen2', 'bg_color'))
        self.rain_widget = RainWidet(self, controller)


class Screen3(ScreenBase):
    def __init__(self, master, controller):
        super().__init__(master, controller, bg=config.get('Screen1', 'bg_color'))
        self.calendar_widget = CalendarWidet(self, controller, 
                                             x=self.space_edge, 
                                             y=config.getint('Header Widget', 'bar_height') + self.space_edge + self.space_between,
                                             width=self.width - 2*self.space_edge, height=self.height-config.getint('Header Widget', 'bar_height')-self.space_between-2*self.space_edge)
        self.make_clickable(self.calendar_widget, callback=lambda e: controller.show_screen("Screen1"))


class FullScreen(ScreenBase):
    def __init__(self, master, controller):
        super().__init__(master, controller, bg=config.get('Screen1', 'bg_color'))
        self.fs_widget = FullScreenWidget(self, controller)
        self.make_clickable(self.fs_widget, callback=lambda e: controller.show_screen("Screen1"))