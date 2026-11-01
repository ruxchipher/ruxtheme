"""ruxtheme wallpaper: flowing contour lines + the Arch logo, in any ruxtheme palette.

Derived from ruxchipher-dotfiles/tools/wallpaper.py, which was hard-coded to Tokyo Night.
This version reads a palette from ~/.config/ruxtheme/palettes/<name>.env, so every theme
gets a matching wallpaper and the desktop can never drift out of sync with the terminal.

  usage: python wallpaper.py <theme-name> <out.png> [logo-source.png]
"""
import os
import re
import sys

import numpy as np
from PIL import Image, ImageFilter

HOME = os.path.expanduser("~")
NAME = sys.argv[1]
OUT = sys.argv[2]
SRC = sys.argv[3] if len(sys.argv) > 3 else os.path.join(HOME, "Pictures/Wallpapers/geology.png")

W, H = 3840, 2160                      # 2x the 1920x1080 screen
LOGO_DY = -56                          # logo sits tight under the greeting widget
LOGO_DX = -286                         # and centred over the 360px widget column
rng = np.random.default_rng(23)        # fixed seed: same art every time, only colours change


# ---------------------------------------------------------------- palette
def load_palette(name):
    path = os.path.join(HOME, ".config/ruxtheme/palettes", name + ".env")
    if not os.path.exists(path):
        sys.exit("no such palette: " + path)
    pal = {}
    for line in open(path):
        m = re.match(r"^(ct_[a-z0-9_]+)='?([^'\n]*)'?$", line.strip())
        if m:
            pal[m.group(1)] = m.group(2)
    return pal


pal = load_palette(NAME)
DARK = pal.get("ct_is_dark", "1") == "1"


def hexc(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32) / 255


BG0, BG1 = hexc(pal["ct_base"]), hexc(pal["ct_crust"])
CYAN = hexc(pal["ct_sky"])             # cool end of the contour gradient
BLUE = hexc(pal["ct_accent"])          # the theme accent, mid gradient
PURPLE = hexc(pal["ct_lavender"])      # warm/light end
FG = hexc(pal["ct_text"])

y, x = np.mgrid[0:H, 0:W].astype(np.float32)
u, v = x / W, y / H


def smoothstep(a, b, t):
    t = np.clip((t - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def noise(cells_x, cells_y):
    """Smooth value noise in [-1, 1]: a small random grid upsampled bicubically in float."""
    small = rng.uniform(-1, 1, (cells_y, cells_x)).astype(np.float32)
    return np.asarray(Image.fromarray(small, "F").resize((W, H), Image.BICUBIC), dtype=np.float32)


# ---------------------------------------------------------------- base
img = BG0 * (1 - (0.6 * u + 0.4 * v))[..., None] + BG1 * (0.6 * u + 0.4 * v)[..., None]


def glow(cx, cy, r, color, strength):
    """Additive on dark themes; on light themes blend toward the colour so it can't blow out."""
    d = np.sqrt(((x - cx) / r) ** 2 + ((y - cy) / r) ** 2)
    a = np.exp(-d * d) * strength
    return a[..., None], color


for cx, cy, r, c, s in (
    (0.20 * W, 0.30 * H, 0.35 * W, CYAN, 0.06),
    (0.92 * W, 0.95 * H, 0.45 * W, PURPLE, 0.09),
    (0.75 * W, 0.05 * H, 0.35 * W, BLUE, 0.05),
):
    a, col = glow(cx, cy, r, c, s if DARK else s * 2.2)
    img = img + a * col if DARK else img * (1 - a) + col * a

# ---------------------------------------------------------------- flowing contours
field = v * 46 + noise(7, 5) * 7.0 + noise(16, 10) * 1.6 + np.sin(u * 9.0 + v * 3.0) * 0.8
gy, gx = np.gradient(field)
grad = np.sqrt(gx * gx + gy * gy) + 1e-6
frac = field - np.floor(field)
dist = np.minimum(frac, 1 - frac) / grad          # distance to nearest isoline, in px
line = np.clip(1.4 - dist, 0, 1)                   # ~1.4px antialiased line

major = (np.floor(field + 0.5).astype(np.int32) % 6 == 0)
weight = np.where(major, 0.7, 0.24)
if not DARK:
    weight = weight * 1.5                          # darker lines need more presence on a light field

# empty on the left, dense from the middle to the right
reveal = smoothstep(0.28, 0.62, u + noise(5, 4) * 0.06)
fade_tb = smoothstep(0.0, 0.08, v) * smoothstep(1.0, 0.92, v)
alpha = line * weight * reveal * fade_tb

t = np.clip((u - 0.3) / 0.7 + noise(6, 4) * 0.25, 0, 1)
col = np.where((t < 0.5)[..., None],
               CYAN * (1 - t * 2)[..., None] + BLUE * (t * 2)[..., None],
               BLUE * (2 - t * 2)[..., None] + PURPLE * (t * 2 - 1)[..., None])
img = img * (1 - alpha[..., None]) + col * alpha[..., None]

# faint grid, strongest around the middle
grid = ((x % 96 < 2) | (y % 96 < 2)).astype(np.float32)
ga = (grid * (0.018 if DARK else 0.05) * smoothstep(0.1, 0.5, u) * fade_tb)[..., None]
img = img + ga * BLUE if DARK else img * (1 - ga) + BLUE * ga

# ---------------------------------------------------------------- Arch logo
src = Image.open(SRC).convert("L")
sx = src.width / W                                 # 5120 -> 3840
box = (440, 720, 1440, 1050)                       # logo area in the 5120x2880 original
crop = src.crop(box).resize(
    (round((box[2] - box[0]) / sx), round((box[3] - box[1]) / sx)), Image.LANCZOS)
ox, oy = round(box[0] / sx) + LOGO_DX, round(box[1] / sx) + LOGO_DY
mask = np.zeros((H, W), np.float32)
m = np.asarray(crop, dtype=np.float32) / 255
mask[oy:oy + m.shape[0], ox:ox + m.shape[1]] = m

halo = np.asarray(
    Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(28)),
    dtype=np.float32) / 255
if DARK:
    img += (halo * 0.55)[..., None] * CYAN * 0.6
else:
    ha = (halo * 0.30)[..., None]
    img = img * (1 - ha) + CYAN * ha

lt = np.clip((x - ox) / m.shape[1], 0, 1)
logo_col = CYAN * (1 - lt)[..., None] + PURPLE * lt[..., None]
logo_col = logo_col * 0.75 + FG * 0.25
img = img * (1 - mask[..., None]) + logo_col * mask[..., None]

# ---------------------------------------------------------------- finish
vig_amt = 0.35 if DARK else 0.14
vig = 1 - vig_amt * smoothstep(
    0.55, 1.15, np.sqrt((u - 0.5) ** 2 * 1.2 + (v - 0.5) ** 2 * 1.6) * 1.6)
img *= vig[..., None]
img += rng.normal(0, 0.006, img.shape).astype(np.float32)   # grain, stops gradient banding

os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), "RGB").save(OUT, optimize=True)
print("saved", OUT)
