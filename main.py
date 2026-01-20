from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.core.window import Window

# Optional: force landscape for testing
Window.size = (480, 320)


class CalendarWidget(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)

        title = Label(
            text="Upcoming Events",
            size_hint_y=None,
            height=40,
            font_size=18,
        )
        self.add_widget(title)

        scroll = ScrollView()
        events = GridLayout(
            cols=1,
            size_hint_y=None,
            padding=10,
            spacing=10,
        )
        events.bind(minimum_height=events.setter("height"))

        # Placeholder events
        for i in range(5):
            events.add_widget(
                Label(
                    text=f"Event {i+1}\nToday 14:00",
                    size_hint_y=None,
                    height=60,
                    halign="left",
                    valign="middle",
                )
            )

        scroll.add_widget(events)
        self.add_widget(scroll)


class RootLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="horizontal", **kwargs)

        # Left: calendar (50%)
        calendar = CalendarWidget(size_hint_x=0.5)

        # Right: placeholder panel
        right_panel = BoxLayout(size_hint_x=0.5)
        right_panel.add_widget(Label(text="Other UI"))

        self.add_widget(calendar)
        self.add_widget(right_panel)


class TouchCalendarApp(App):
    def build(self):
        return RootLayout()


if __name__ == "__main__":
    TouchCalendarApp().run()
