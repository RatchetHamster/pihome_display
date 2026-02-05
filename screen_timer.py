import subprocess
import datetime

class ScreenTimer:
    def __init__(self, root,
                 sleep_start=(0, 0),      # midnight
                 sleep_end=(7, 0),        # 7am
                 night_idle_time=120,     # 2 minutes
                 day_idle_time=600,       # 10 minutes
                 dim_brightness=60,       # percent
                 full_brightness=100,
                 refresh_rate=10):        # 10 seconds

        self.root = root
        self.sleep_start = sleep_start
        self.sleep_end = sleep_end
        self.night_idle_time = night_idle_time
        self.day_idle_time = day_idle_time
        self.dim_brightness = dim_brightness
        self.full_brightness = full_brightness
        self.refresh_rate = refresh_rate

        self.last_activity = datetime.datetime.now()
        self.is_off = False
        self.is_dimmed = False

        # Bind touch/tap events
        root.bind_all("<Button-1>", self.on_touch)

        # Start periodic check
        self.turn_off_default_auto_dim()
        self.check_loop()


    def turn_off_default_auto_dim(self):
        subprocess.run(["xset", "s", "off"])
        subprocess.run(["xset", "s", "noblank"])
        subprocess.run(["xset", "dpms", "0", "0", "0"])

    # ---------------------------
    # Brightness helpers
    # ---------------------------
    def set_brightness(self, percent):
        """Software dimming (no real power saving)."""
        subprocess.run(
            ["xrandr", "--output", "default", "--brightness", str(percent/100)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    def dim_screen(self):
        # Handle edge case where going from off to dim
        if self.is_off:
            self.screen_on()
        self.is_dimmed = True
        self.set_brightness(self.dim_brightness)

    def bright_screen(self):
        if self.is_off:
            self.screen_on()
        self.is_dimmed = False
        self.set_brightness(self.full_brightness)

    def screen_off(self):
        """Real power saving: turn off display output."""
        self.is_off = True
        subprocess.run(["xset", "dpms", "force", "off"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def screen_on(self):
        """Wake display output."""
        self.is_off = False
        subprocess.run(["xset", "dpms", "force", "on"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # ---------------------------
    # Event handling
    # ---------------------------
    def on_touch(self, event):
        self.last_activity = datetime.datetime.now()
        if self.is_off: 
            self.screen_on()
        if self.is_dimmed: 
            self.bright_screen()

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
            if now >= self.last_activity + datetime.timedelta(seconds=self.night_idle_time):
                print("Screen Off")
                self.screen_off()
        else:
            # --- Daytime logic ---
            if now >= self.last_activity + datetime.timedelta(seconds=self.day_idle_time):
                print("Screen Dimmed")
                self.dim_screen()
        
        # Re-run every second
        self.root.after(self.refresh_rate*1000, self.check_loop)
