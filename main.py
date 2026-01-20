from PIL import Image, ImageDraw, ImageFont
import os

# Waveshare 3.5" LCD resolution (most models)
WIDTH = 480
HEIGHT = 320

# Create a black image
img = Image.new("RGB", (WIDTH, HEIGHT), "black")
draw = ImageDraw.Draw(img)

# Load default font
font = ImageFont.load_default()

text = "Hello, world!"

# Center the text
text_width, text_height = draw.textsize(text, font=font)
x = (WIDTH - text_width) // 2
y = (HEIGHT - text_height) // 2

# Draw text
draw.text((x, y), text, fill="white", font=font)

# Write directly to framebuffer
with open("/dev/fb1", "wb") as f:
    f.write(img.tobytes())
