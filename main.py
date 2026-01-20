#!/usr/bin/env python3
from PIL import Image, ImageDraw, ImageFont

WIDTH = 480
HEIGHT = 320

# Create image
img = Image.new("RGB", (WIDTH, HEIGHT), "black")
draw = ImageDraw.Draw(img)

# Font
font = ImageFont.load_default()

text = "Hello, world!"

# Get text bounding box (NEW way)
bbox = draw.textbbox((0, 0), text, font=font)
text_width = bbox[2] - bbox[0]
text_height = bbox[3] - bbox[1]

# Center text
x = (WIDTH - text_width) // 2
y = (HEIGHT - text_height) // 2

# Draw text
draw.text((x, y), text, fill="white", font=font)

# Write to framebuffer
with open("/dev/fb1", "wb") as f:
    f.write(img.tobytes())
