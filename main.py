from kivy.app import App
from kivy.uix.label import Label
from kivy.core.window import Window

Window.fullscreen = True
Window.borderless = True

class TestApp(App):
    def build(self):
        return Label(text="HELLO", font_size=40)

TestApp().run()
