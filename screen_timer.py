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
                 day_idle_time=600,       # 10 minutes
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

        # Start periodic check
        if not config.getboolean("App","is_test"):
            self.turn_off_default_auto_dim()
        self.check_loop()


    def turn_off_default_auto_dim(self):
        subprocess.run(["xset", "s", "off"])
        subprocess.run(["xset", "s", "noblank"])
        subprocess.run(["xset", "dpms", "0", "0", "0"])

    # ---------------------------
    # Brightness helpers
    # ---------------------------
    def create_overlay(self):
        w = config.getint("App", "width")
        h = config.getint("App", "height")

        # DIM overlay
        self.dim_frame = tk.Frame(self.root)
        self.dim_canvas = tk.Canvas(self.dim_frame, highlightthickness=0)
        self.dim_canvas.pack(fill="both", expand=True)
        self.dim_canvas.create_rectangle(0, 0, w, h, stipple="gray50")

        # OFF overlay
        self.off_frame = tk.Frame(self.root, bg="black")

        self.dim_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.off_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Start hidden
        self.dim_frame.tkraise()
        self.off_frame.lower(self.root.mainframe)

    def dim_screen(self):
        # Handle edge case where going from off to dim
        if self.is_off:
            self.screen_on()
        self.is_dimmed = True
        self.root.attributes("-alpha", 0.5)  # dim entire window

    def screen_off(self):
        """Real power saving: turn off display output."""
        self.is_off = True
        self.is_dimmed = False
        self.root.attributes("-alpha", 0)  # dim entire window
        

    def screen_on(self):
        """Wake display output."""
        self.is_off = False
        self.is_dimmed = False
        self.root.attributes("-alpha", 1)  # dim entire window

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
            if now >= self.last_activity + datetime.timedelta(seconds=self.night_idle_time):
                self.screen_off()
        else:
            # --- Daytime logic ---
            if now >= self.last_activity + datetime.timedelta(seconds=self.day_idle_time):
                self.dim_screen()
        
        # Re-run every second
        self.root.after(self.refresh_rate*1000, self.check_loop)
