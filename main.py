from kivy.config import Config

# Set fullscreen and SPI screen resolution (adjust if different)
Config.set('graphics', 'fullscreen', 'auto')
Config.set('graphics', 'width', '480')   # SPI screen width
Config.set('graphics', 'height', '320')  # SPI screen height
Config.set('graphics', 'show_cursor', '0')  # hide mouse cursor

from kivy.app import App
from kivy.uix.label import Label

# Import Window AFTER Kivy App is initialized
from kivy.core.window import Window

class SPIApp(App):
    def build(self):
        # Now Window exists
        Window.clearcolor = (0, 0, 0, 1)  # black background

        # Create a centered label
        return Label(
            text="Hello SPI World!",
            font_size=50,
            halign='center',
            valign='middle'
        )

if __name__ == '__main__':
    SPIApp().run()
