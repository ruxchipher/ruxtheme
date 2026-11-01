#!/usr/bin/env bash
# ruxtheme installer. Copies the engine, palettes and templates into place and backs up
# anything it will later overwrite. Does not apply a theme and does not need root.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="$HOME/.local/bin"
CFG="$HOME/.config/ruxtheme"
SHARE="$HOME/.local/share/ruxtheme"
EXT="$HOME/.local/share/gnome-shell/extensions"
APPS="$HOME/.local/share/applications"

say() { printf '  \033[2m%s\033[0m\n' "$*"; }
ok()  { printf '  \033[32m%s\033[0m\n' "$*"; }
warn() { printf '  \033[33m%s\033[0m\n' "$*"; }

command -v envsubst >/dev/null || { echo "need gettext (envsubst)" >&2; exit 1; }

printf '\n  \033[1mruxtheme\033[0m\n\n'

mkdir -p "$BIN" "$CFG/palettes" "$CFG/templates" "$CFG/backup" "$SHARE" "$APPS"
install -m755 "$SRC/bin/ruxtheme" "$SRC/bin/ruxtheme-carousel" "$BIN/"
install -m644 "$SRC"/palettes/*.env "$CFG/palettes/"
install -m755 "$SRC/lib/build-icons.sh" "$SHARE/"
install -m644 "$SRC/lib/wallpaper.py" "$SRC/lib/make-wallpaper.py" "$SHARE/"
say "engine -> $BIN, palettes -> $CFG/palettes"

# templates: never clobber ones the user has already customised
for t in "$SRC"/templates/*; do
  d="$CFG/templates/$(basename "$t")"
  if [ -e "$d" ]; then warn "kept your $(basename "$t")"; else install -m644 "$t" "$d"; fi
done
say "templates -> $CFG/templates"

[ -e "$CFG/wallpapers.map" ] || install -m644 "$SRC/wallpapers.map.example" "$CFG/wallpapers.map"
install -m644 "$SRC/share/ruxtheme-carousel.desktop" "$APPS/"

if [ -d "$SRC/extension" ]; then
  mkdir -p "$EXT"
  cp -r "$SRC/extension/"* "$EXT/"
  say "GNOME Shell extension -> $EXT (needs a logout to appear)"
fi

# python bits for the wallpaper pipeline, in a venv so nothing is installed system-wide
if [ ! -x "$SHARE/venv/bin/python" ]; then
  if python -c 'import numpy, PIL' 2>/dev/null; then
    say "numpy and pillow already available"
  else
    say "creating a venv for the wallpaper pipeline"
    python -m venv "$SHARE/venv" && "$SHARE/venv/bin/pip" install --quiet numpy pillow \
      || warn "venv setup failed; wallpaper generation will be skipped"
  fi
fi

printf '\n'
ok "installed"
cat <<'NOTE'

  Next:
    ruxtheme list                   see the themes
    ruxtheme set catppuccin-mocha   apply one

  Your current configs are backed up to ~/.config/ruxtheme/backup/ the first
  time a theme is applied. Optional extras:

    ~/.local/share/ruxtheme/build-icons.sh Papirus-Rux-Dark violet Papirus-Dark
    gsettings set org.gnome.shell enabled-extensions \
      "$(gsettings get org.gnome.shell enabled-extensions | sed "s|]$|, 'ruxtheme@ruxchipher']|")"

NOTE
