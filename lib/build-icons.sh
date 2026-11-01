#!/usr/bin/env bash
# Build a Papirus folder-colour variant into ~/.local/share/icons, by symlinking the
# stock Papirus colour variants. No sudo, no SVG copying: same trick papirus-folders uses.
#   usage: build-icons.sh <theme-name> <folder-colour> <inherits>
set -euo pipefail
NAME="$1"; COLOUR="$2"; INHERITS="$3"
SRC=/usr/share/icons/Papirus
DST="$HOME/.local/share/icons/$NAME"
[ -d "$SRC" ] || { echo "Papirus not installed at $SRC" >&2; exit 1; }

rm -rf "$DST"; mkdir -p "$DST"
n=0
for sizedir in "$SRC"/*/places; do
  size="$(basename "$(dirname "$sizedir")")"
  # only sizes that actually carry the colour variants
  compgen -G "$sizedir/folder-$COLOUR*.svg" >/dev/null || continue
  mkdir -p "$DST/$size/places"
  for f in "$sizedir/folder-$COLOUR"*.svg; do
    b="$(basename "$f")"
    # folder-violet-documents.svg -> folder-documents.svg ; folder-violet.svg -> folder.svg
    t="${b/folder-$COLOUR-/folder-}"; [ "$t" = "$b" ] && t="${b/folder-$COLOUR/folder}"
    ln -sfn "$f" "$DST/$size/places/$t"; n=$((n+1))
  done
done

dirs="$(cd "$DST" && for d in */places; do printf '%s,' "$d"; done | sed 's/,$//')"
cat > "$DST/index.theme" <<EOF
[Icon Theme]
Name=$NAME
Comment=ruxtheme folder colour ($COLOUR), inheriting $INHERITS
Inherits=$INHERITS,hicolor
Example=folder
FollowsColorScheme=true
DesktopDefault=48
DesktopSizes=16,22,24,32,48,64
ToolbarDefault=22
Directories=$dirs
EOF
for d in "$DST"/*/places; do
  size="$(basename "$(dirname "$d")")"; px="${size%%x*}"; px="${px%%@*}"
  cat >> "$DST/index.theme" <<EOF

[$size/places]
Context=Places
Size=$px
Type=Fixed
EOF
done
echo "$NAME: $n folder icons -> $COLOUR, inherits $INHERITS"
