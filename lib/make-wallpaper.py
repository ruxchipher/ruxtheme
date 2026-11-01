"""Turn any photo into a ruxtheme wallpaper.

Scales/crops to 3840x2160, lays a soft scrim where the conky widgets sit so text stays
readable, and composites the Arch logo back at the exact spot left.lua anchors to
(ox=44, oy=484, 750x248 in the 4K image) using the theme's own colours.

  usage: make-wallpaper.py <theme> <source-image> <out.png> [--no-logo] [--scrim N]
"""
import os
import re
import sys

import numpy as np
from PIL import Image, ImageFilter

HOME = os.path.expanduser("~")
W, H = 3840, 2160
LOGO_SRC = os.path.join(HOME, "Pictures/Wallpapers/geology.png")
LOGO_BOX = (440, 720, 1440, 1050)   # logo area inside the 5120x2880 original
LOGO_DX, LOGO_DY = -286, -56

theme, src_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
use_logo = "--no-logo" not in sys.argv
scrim = 0.38
if "--scrim" in sys.argv:
    scrim = float(sys.argv[sys.argv.index("--scrim") + 1])


def load_palette(name):
    path = os.path.join(HOME, ".config/ruxtheme/palettes", name + ".env")
    pal = {}
    for line in open(path):
        m = re.match(r"^(ct_[a-z0-9_]+)='?([^'\n]*)'?$", line.strip())
        if m:
            pal[m.group(1)] = m.group(2)
    return pal


def hexc(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32) / 255


pal = load_palette(theme)
BASE, CRUST = hexc(pal["ct_base"]), hexc(pal["ct_crust"])
CYAN, PURPLE, FG = hexc(pal["ct_sky"]), hexc(pal["ct_lavender"]), hexc(pal["ct_text"])

# ---------------------------------------------------------------- fit to 4K (cover)
im = Image.open(src_path).convert("RGB")
s = max(W / im.width, H / im.height)
im = im.resize((max(W, round(im.width * s)), max(H, round(im.height * s))), Image.LANCZOS)
left, top = (im.width - W) // 2, (im.height - H) // 2
im = im.crop((left, top, left + W, top + H))
img = np.asarray(im, dtype=np.float32) / 255

y, x = np.mgrid[0:H, 0:W].astype(np.float32)
u, v = x / W, y / H


def smoothstep(a, b, t):
    t = np.clip((t - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- scrim for widget areas
# left column (greeting / mission / weather), plus top-right HUD and bottom-right lab widget.
left_col = smoothstep(0.34, 0.0, u)
right_col = smoothstep(0.72, 1.0, u) * (smoothstep(0.30, 0.0, v) + smoothstep(0.66, 1.0, v))
mask = np.clip(left_col * 1.0 + right_col * 0.75, 0, 1) * scrim
img = img * (1 - mask[..., None]) + CRUST * mask[..., None]

# gentle overall tint toward the palette so photos sit in the theme
img = img * 0.93 + BASE * 0.07

# ---------------------------------------------------------------- Arch logo
if use_logo and os.path.exists(LOGO_SRC):
    srcimg = Image.open(LOGO_SRC).convert("L")
    sx = srcimg.width / W
    crop = srcimg.crop(LOGO_BOX).resize(
        (round((LOGO_BOX[2] - LOGO_BOX[0]) / sx), round((LOGO_BOX[3] - LOGO_BOX[1]) / sx)),
        Image.LANCZOS)
    ox = round(LOGO_BOX[0] / sx) + LOGO_DX
    oy = round(LOGO_BOX[1] / sx) + LOGO_DY
    m = np.asarray(crop, dtype=np.float32) / 255
    lmask = np.zeros((H, W), np.float32)
    lmask[oy:oy + m.shape[0], ox:ox + m.shape[1]] = m

    halo = np.asarray(
        Image.fromarray((lmask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(34)),
        dtype=np.float32) / 255
    ha = (halo * 0.5)[..., None]
    img = img * (1 - ha) + CRUST * ha          # darken behind the logo so it always reads

    lt = np.clip((x - ox) / m.shape[1], 0, 1)
    logo_col = CYAN * (1 - lt)[..., None] + PURPLE * lt[..., None]
    logo_col = logo_col * 0.78 + FG * 0.22
    img = img * (1 - lmask[..., None]) + logo_col * lmask[..., None]

img += np.random.default_rng(23).normal(0, 0.004, img.shape).astype(np.float32)
os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), "RGB").save(out_path, optimize=True)
print("saved", out_path)
