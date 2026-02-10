import subprocess
import datetime
import tkinter as tk
import configparser

# Read configuration
config = configparser.ConfigParser()
config.read('config.ini')
is_test = config.getboolean("App", "is_test")

class ScreenTimer:
    def __init__(self, root,
                 sleep_start=(0, 0),      # midnight
                 sleep_end=(7, 0),        # 7am
                 night_idle_time=120,     # 2 minutes
                 day_idle_time=2*60*60,   # 2hrs
                 refresh_rate=10):        # 10 seconds

        self.root = root
        self.sleep_start = sleep_start
        self.sleep_end = sleep_end
        self.night_idle_time = night_idle_time
        self.day_idle_time = day_idle_time
        self.refresh_rate = refresh_rate

        self.last_activity = datetime.datetime.now()
        self.is_off = False
        self.is_dimmed = False

        # Bind touch/tap events
        root.bind_all("<Button-1>", self.on_touch)

        # --- Init Methods ---
        if not config.getboolean("App","is_test"):
            self.turn_off_default_auto_dim()
        self.create_overlay()
        self.screen_on()
        self.check_loop()


    def turn_off_default_auto_dim(self):
        subprocess.run(["xset", "s", "off"])
        subprocess.run(["xset", "s", "noblank"])
        subprocess.run(["xset", "dpms", "0", "0", "0"])

    # ---------------------------
    # Brightness helpers
    # ---------------------------
    def create_overlay(self):
        # OFF overlay
        self.off_frame = tk.Frame(self.root, bg="black")
        self.off_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

    def dim_screen(self):
        # Handle edge case where going from off to dim
        if self.is_off:
            self.screen_on()
        self.is_dimmed = True
        # Dim Screen Not implimented

    def screen_off(self):
        """Real power saving: turn off display output."""
        self.is_off = True
        self.is_dimmed = False
        self.off_frame.tkraise()
        

    def screen_on(self):
        """Wake display output."""
        self.is_off = False
        self.is_dimmed = False
        self.off_frame.lower()

    # ---------------------------
    # Event handling
    # ---------------------------
    def on_touch(self, event):
        self.last_activity = datetime.datetime.now()
        if self.is_off or self.is_dimmed: 
            self.screen_on()

    # ---------------------------
    # Time logic
    # ---------------------------
    def is_in_sleep_hours(self, now):
        start = now.replace(hour=self.sleep_start[0], minute=self.sleep_start[1], second=0)
        end = now.replace(hour=self.sleep_end[0], minute=self.sleep_end[1], second=0)

        # Handle ranges that cross midnight
        if start < end:
            return start <= now < end
        else:
            return now >= start or now < end

    # ---------------------------
    # Main loop
    # ---------------------------
    def check_loop(self):
        now = datetime.datetime.now()

        if self.is_in_sleep_hours(now):
            # --- Night Logic ---
            if not self.is_off and now >= self.last_activity + datetime.timedelta(seconds=self.night_idle_time):
                self.screen_off()
        else:
            # --- Daytime logic ---
            if not self.is_dimmed and now >= self.last_activity + datetime.timedelta(seconds=self.day_idle_time):
                self.dim_screen()
        
        # Re-run every second
        self.root.after(int(self.refresh_rate*1000), self.check_loop)
