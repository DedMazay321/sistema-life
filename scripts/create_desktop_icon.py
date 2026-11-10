from pathlib import Path
from PIL import Image, ImageDraw

output = Path(__file__).resolve().parents[1] / "desktop" / "assets"
output.mkdir(parents=True, exist_ok=True)
size = 256
image = Image.new("RGBA", (size, size), (6, 10, 18, 255))
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((4, 4, 252, 252), radius=48, fill=(8, 17, 30, 255), outline=(34, 67, 94, 255), width=4)
for inset, color, width in ((40, (88, 215, 255, 255), 8), (70, (52, 134, 174, 255), 6)):
    points = [(128, inset), (256 - inset, 128), (128, 256 - inset), (inset, 128)]
    draw.line(points + [points[0]], fill=color, width=width, joint="curve")
draw.polygon([(128, 96), (160, 128), (128, 160), (96, 128)], fill=(88, 215, 255, 255))
image.save(output / "icon.png")
image.save(output / "icon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print(output / "icon.ico")
