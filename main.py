import tkinter as tk
import configparser
from screens import *
from screen_timer import ScreenTimer

# Read configuration
config = configparser.ConfigParser()
config.read('config.ini')


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Pihome_display")
        self.app_w = config.getint('App', 'width')
        self.app_h = config.getint('App', 'height')
        self.geometry(f"{self.app_w}x{self.app_h}")
        self.configure(cursor="none")
        self.screen_timer = ScreenTimer(self)

        # Clean Exit: 
        self.protocol("WM_DELETE_WINDOW", self.destroy())

        # Frame for all screens
        self.mainframe = tk.Frame(self, bg=config.get('Screen1', 'bg_color'))
        self.mainframe.pack(fill="both", expand=True)

        # Header on all screens, nothing overlaps it: 
        self.header = HeaderWidget(self, self)

        # Dictionary to hold screens
        self.screens = {}
        screen_classes = (Screen1, Screen2, Screen3, FullScreen)

        for ScreenClass in screen_classes:
            screen_name = ScreenClass.__name__
            frame = ScreenClass(self.mainframe, self)
            self.screens[screen_name] = frame

        self.show_screen("Screen1")

    def show_screen(self, name):
        """Raise the selected screen to the top."""
        frame = self.screens[name]
        self.configure(bg=frame["bg"])
        frame.tkraise()

    def full_screen(self, text, icon=""):
        self.screens["FullScreen"].fs_widget.update_screen(text, icon)
        self.show_screen("FullScreen")
        


if __name__ == "__main__":
    app = App()
    app.mainloop()


