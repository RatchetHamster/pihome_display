#!/usr/bin/env python3
from PIL import Image, ImageDraw, ImageFont

WIDTH = 480
HEIGHT = 320

# Create image
img = Image.new("RGB", (WIDTH, HEIGHT), "black")
draw = ImageDraw.Draw(img)

font = ImageFont.load_default()
text = "Hello, world!"

# Measure text (Pillow ≥10)
bbox = draw.textbbox((0, 0), text, font=font)
tw = bbox[2] - bbox[0]
th = bbox[3] - bbox[1]

x = (WIDTH - tw) // 2
y = (HEIGHT - th) // 2

draw.text((x, y), text, fill="white", font=font)

# Convert to RGB565 and write to framebuffer
with open("/dev/fb1", "wb") as fb:
    fb.write(img.tobytes("raw", "RGB;16"))
