"""Generates the bundled SYNTHETIC demo dataset (coloured shapes on noisy backgrounds) into sample_data/.
It exists only so the live demo can train end-to-end without uploading photos. Run: python make_sample_data.py"""
import random
from pathlib import Path
from PIL import Image, ImageDraw
random.seed(7); OUT = Path(__file__).parent / "sample_data"; N, S = 24, 128
SHAPES = {"circles": "red", "squares": "blue", "triangles": "green"}
for cls, colour in SHAPES.items():
    d = OUT / cls; d.mkdir(parents=True, exist_ok=True)
    for i in range(N):
        bg = tuple(random.randint(190, 245) for _ in range(3)); im = Image.new("RGB", (S, S), bg); dr = ImageDraw.Draw(im)
        r = random.randint(22, 42); cx, cy = random.randint(r + 4, S - r - 4), random.randint(r + 4, S - r - 4)
        c = {"red": (random.randint(170, 240), random.randint(20, 80), random.randint(20, 80)), "blue": (random.randint(20, 80), random.randint(40, 100), random.randint(170, 240)), "green": (random.randint(20, 80), random.randint(150, 220), random.randint(30, 90))}[colour]
        if cls == "circles": dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c)
        elif cls == "squares": dr.rectangle([cx - r, cy - r, cx + r, cy + r], fill=c)
        else: dr.polygon([(cx, cy - r), (cx - r, cy + r), (cx + r, cy + r)], fill=c)
        for _ in range(60): dr.point((random.randint(0, S - 1), random.randint(0, S - 1)), fill=tuple(random.randint(0, 255) for _ in range(3)))
        im.save(d / f"{cls}_{i:02d}.png")
