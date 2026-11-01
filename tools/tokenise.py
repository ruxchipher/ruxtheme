#!/usr/bin/env python3
"""One-shot: turn Siddique's live Tokyo Night configs into ${ct_*} templates.

Backs up each original to ~/.config/ruxtheme/backup/ before touching anything.
Run once. After this the templates are the source of truth and `ruxtheme` renders them.
"""
import os, re, pathlib, shutil, sys

H = os.path.expanduser("~")
CFG = pathlib.Path(H, ".config/ruxtheme")
TPL, BAK = CFG / "templates", CFG / "backup"

# Tokyo Night hex -> palette token. Chosen so colours that appear together in the
# same file stay visually distinct after the swap.
MAP = {
    "101119": "crust",   "16161e": "mantle",   "1a1b26": "base",
    "1f2335": "view",     "24283b": "surface0", "292e42": "surface1",
    "283457": "surface2", "3b4261": "overlay0", "565f89": "overlay1",
    "a9b1d6": "subtext0", "c0caf5": "text",
    "7aa2f7": "accent",  "7dcfff": "sky",      "bb9af7": "lavender",
    "73daca": "teal",    "9ece6a": "green",    "e0af68": "yellow",
    "ff9e64": "peach",   "f7768e": "red",
    "545c7e": "overlay0", "15161e": "mantle",   "414868": "surface1",
    "ff899d": "red",      "9fe044": "green",    "faba4a": "yellow",
    "8db0ff": "blue",     "c7a9ff": "pink",     "a4daff": "sky",
    "db4b4b": "maroon",
}
KEEP = {"000000", "ffffff"}   # pure shadow / pure white: leave alone

# live path (relative to $HOME)  ->  template filename
TARGETS = {
    ".config/conky/ruxchipher/common.lua":            "conky-common.lua",
    ".config/conky/ruxchipher/hud.lua":               "conky-hud.lua",
    ".config/conky/ruxchipher/lab.lua":               "conky-lab.lua",
    ".config/kitty/current-theme.conf":               "kitty-theme.conf",
    ".config/rofi/config.rasi":                       "rofi-config.rasi",
    ".config/mako/config":                            "mako-config",
    ".config/waybar/style.css":                       "waybar-style.css",
    ".config/hypr/hyprlock.conf":                     "hyprlock.conf",
    ".config/gtk-3.0/gtk.css":                        "gtk3.css",
    ".config/gtk-4.0/gtk.css":                        "gtk4.css",
    ".themes/ruxchipher/gnome-shell/gnome-shell.css": "gnome-shell.css",
    ".config/fish/config.fish":                       "config.fish",
    ".config/fastfetch/config.jsonc":                 "fastfetch.jsonc",
    ".local/share/ruxchipher/startpage/index.html":   "startpage.html",
}

# decimal "r;g;b" triplets used by fastfetch's ANSI colours
DEC, DEC_C = {}, {}
for h, tok in MAP.items():
    r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
    DEC["%d;%d;%d" % (r, g, b)] = tok     # fastfetch ANSI
    DEC_C["%d,%d,%d" % (r, g, b)] = tok   # CSS rgba()

def tokenise(text):
    n = [0]
    # 1. decimal ANSI triplets (fastfetch) - do these first, they're unambiguous
    def dec_sub(m):
        tok = DEC.get(m.group(1))
        if not tok:
            return m.group(0)
        n[0] += 1
        return "38;2;${ct_%s_rgbs}" % tok
    text = re.sub(r"38;2;(\d{1,3};\d{1,3};\d{1,3})", dec_sub, text)

    # 1b. decimal rgb()/rgba(): rgba(122, 162, 247, 0.16) -> rgba(${ct_accent_rgb}, 0.16)
    #     these carry the accent tints in gnome-shell.css and the browser start page.
    def dec_rgba(m):
        key = "%d,%d,%d" % (int(m.group(2)), int(m.group(3)), int(m.group(4)))
        tok = DEC_C.get(key)
        if not tok:
            print("    ! unmapped rgba(%s)" % key, file=sys.stderr)
            return m.group(0)
        n[0] += 1
        return "%s${ct_%s_rgb}%s" % (m.group(1), tok, m.group(5))
    text = re.sub(r"(rgba?\(\s*)(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})(\s*[,)])",
                  dec_rgba, text)

    # 1c. the theme's own name, so rendered headers say what they actually are
    text = text.replace("Tokyo Night", "${ct_label}")

    # 2. bare hex inside rgb()/rgba() (hyprlock): rgba(1a1b26cc) -> rgba(${ct_base_h}cc)
    def bare_sub(m):
        head, hx, tail = m.group(1), m.group(2).lower(), m.group(3)
        tok = MAP.get(hx)
        if not tok:
            return m.group(0)
        n[0] += 1
        return "%s${ct_%s_h}%s%s" % (head, tok, tail, ")")
    text = re.sub(r"(rgba?\()([0-9a-fA-F]{6})([0-9a-fA-F]{0,2})\)", bare_sub, text)

    # 3. #rrggbb, keeping any trailing alpha pair (#1a1b26e6 -> ${ct_base}e6)
    def hex_sub(m):
        hx = m.group(1).lower()
        if hx in KEEP:
            return m.group(0)
        tok = MAP.get(hx)
        if not tok:
            print("    ! unmapped #%s" % hx, file=sys.stderr)
            return m.group(0)
        n[0] += 1
        return "${ct_%s}" % tok
    text = re.sub(r"#([0-9a-fA-F]{6})", hex_sub, text)
    return text, n[0]

TPL.mkdir(parents=True, exist_ok=True)
BAK.mkdir(parents=True, exist_ok=True)
total = 0
for rel, tplname in TARGETS.items():
    src = pathlib.Path(H, rel)
    if not src.exists():
        print("  SKIP (missing) %s" % rel)
        continue
    bak = BAK / rel.replace("/", "__")
    if not bak.exists():
        shutil.copy2(src, bak)
    text, cnt = tokenise(src.read_text())
    (TPL / tplname).write_text(text)
    total += cnt
    print("  %-34s %2d colours -> templates/%s" % (rel.split("/")[-1], cnt, tplname))
print("\n%d colour references tokenised across %d files" % (total, len(list(TPL.iterdir()))))
