from kivy.config import Config
# Set fullscreen and SPI screen resolution (change if your screen differs)
Config.set('graphics', 'fullscreen', 'auto')
Config.set('graphics', 'width', '480')   # typical 3.5" SPI width
Config.set('graphics', 'height', '320')  # typical 3.5" SPI height
Config.set('graphics', 'show_cursor', '0')  # hide mouse cursor

from kivy.app import App
from kivy.uix.label import Label
from kivy.core.window import Window

# Optional: make background black
Window.clearcolor = (0, 0, 0, 1)

class SPIApp(App):
    def build(self):
        # Centered label
        return Label(text="Hello SPI World!", font_size=50, halign='center', valign='middle')

if __name__ == '__main__':
    SPIApp().run()
