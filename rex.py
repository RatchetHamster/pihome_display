import tkinter as tk
from PIL import Image, ImageTk
import random

class Rex(tk.Label):
    SIZE=90
    def __init__(self, master, **kwargs):
        super().__init__(master, width=self.SIZE, height=self.SIZE, **kwargs)

        # --- Frames ---
        self.sheet = Image.open('rex_sprite_sheet.png')
        self.frames = self._load_frames()
        self.fps = 4

        # --- States ---
        self.state = "idle" 
        self.current_frame = 0
        self.loop_num = 0
        self.after_id = None
        self.set_state("idle")

    # ----- Sprite loading -----
    def _load_frames(self):
        frames = []
        LEFT = 100
        TOP = 80
        RIGHT = 85
        BOTTOM = 105
        img = self.sheet.crop((LEFT, TOP, self.sheet.width - RIGHT, self.sheet.height - BOTTOM))
        row_gap = [0, int(3*self.SIZE/128), int(7*self.SIZE/128), 0]
        img = ImageTk.PhotoImage(img.resize((self.SIZE*4, self.SIZE*4), Image.NEAREST))
        
        for y in range(4):
            for x in range(4):
                frame = tk.PhotoImage()
                frame.tk.call(
                    frame, "copy", img,
                    "-from",
                    x * self.SIZE, y * self.SIZE + row_gap[y],
                    (x + 1) * self.SIZE, y * self.SIZE + row_gap[y] + self.SIZE,
                    "-to", 0, 0)
                frames.append(frame)
        return frames

    # ----- State control -----
    def set_state(self, state):
        # happy, pant, walk, lay_transition, sleep, idle
        if self.after_id:
            self.after_cancel(self.after_id)
            
        self.state = state
        self.current_frame = 0
        if state == "happy":
            self.animate([0, 1], loop=5, on_end="idle")

        elif state == "pant":
            self.animate([3,4], loop=5, on_end="idle")

        elif state == "walk":
            self.animate([6, 7, 8, 9], loop=10, on_end="pant")

        elif state == "lay_transition":
            self.animate([9,10], loop=1, on_end="sleep")

        elif state == "nap":
            self.animate([9,10] + [11]*15 + [10,9], loop=1, on_end="pant")

        elif state == "wake_transition":
            self.animate([11]*2 + [10,9], loop=1, on_end="idle")

        elif state == "sleep":
            self.animate([11])

        elif state == "idle":
            self.pick_idle_behavior()

    def pick_idle_behavior(self):
        self.set_state(random.choice(["pant", "walk", "nap"]))

    def trigger_sleep(self):
        if self.state not in ["lay_transition", "wake_reansition","nap", "sleep"]:
            self.set_state("lay_transition")

    def trigger_wake(self):
        if self.state in ["sleep"]:
            self.set_state("wake_transition")

    # ----------------------------
    # Animation engine
    # ----------------------------
    def animate(self, frame_indices, loop=0, on_end=None):
        # if Loop set to 0, it keeps going until intrup of set_state, otherwise loops the stated number of times

        frame = self.frames[frame_indices[self.current_frame]]
        self.config(image=frame)
        self.image = frame  # prevent GC

        self.current_frame += 1

        if self.current_frame >= len(frame_indices):
            
            if loop==0:
                self.current_frame = 0
            elif self.loop_num<loop-1:
                self.loop_num+=1
                self.current_frame=0
            else:
                self.loop_num=0
                if on_end:
                    self.after_id = self.after(500, lambda: self.set_state(on_end))
                return

        self.after_id = self.after(1000 // self.fps,
                                   lambda: self.animate(frame_indices, loop, on_end))

    # ----------------------------
    # Interaction
    # ----------------------------
    def on_tap(self):
        if self.state in ["sleep", "nap"]:
            self.set_state("wake_transition")
        elif self.state not in ["wake_transition", "nap"]:
            self.set_state("happy")

if __name__ == "__main__":
    root = tk.Tk()    
    rex = Rex(root)
    rex.pack(padx=10, pady=10)
    root.mainloop()

