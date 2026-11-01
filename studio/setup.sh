#!/usr/bin/env bash
# Installs everything the video studio needs (fresh Linux container).
set -e
cd "$(dirname "$0")"
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq libegl1 libegl-mesa0 libgl1-mesa-dri libgl1 libxkbcommon0 \
  libsm6 libxi6 libxrender1 libxxf86vm1 libxfixes3 ffmpeg >/dev/null 2>&1 || \
  (apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq libegl1 libegl-mesa0 libgl1-mesa-dri \
   libgl1 libxkbcommon0 libsm6 libxi6 libxrender1 libxxf86vm1 libxfixes3 ffmpeg)
pip install -q bpy edge-tts fonttools brotli numpy pillow
if [ ! -f fonts/Montserrat-800.ttf ]; then
  mkdir -p fonts && cd fonts
  for p in montserrat cabin; do npm pack -s @fontsource/$p >/dev/null && tar xzf fontsource-$p-*.tgz && mv package $p && rm fontsource-$p-*.tgz; done
  python3 - <<'EOF'
from fontTools.ttLib import TTFont
for fam, w in [("montserrat", 800), ("montserrat", 700), ("montserrat", 900), ("cabin", 600), ("cabin", 500)]:
    f = TTFont(f"{fam}/files/{fam}-latin-{w}-normal.woff2"); f.flavor = None; f.save(f"{fam.capitalize()}-{w}.ttf")
EOF
  rm -rf montserrat cabin; cd ..
fi
echo "Studio bereit."
