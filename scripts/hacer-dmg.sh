#!/bin/bash
# Empaqueta Transcribir.app en una imagen de disco lista para enviar a alguien.
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RAIZ"
VERSION="$(.venv/bin/python -c "import sys; sys.path.insert(0, 'transcribir'); import identidad; print(identidad.VERSION)")"
STAGE="$(mktemp -d)"
RW="$(mktemp -u).dmg"
DMG="$RAIZ/dist/Transcribir-$VERSION.dmg"
trap 'rm -rf "$STAGE" "$RW"' EXIT

[ -d dist/Transcribir.app ] || ./scripts/construir.sh

cp -R dist/Transcribir.app "$STAGE/"
ln -s /Applications "$STAGE/Applications"
cp transcribir/Transcribir.icns "$STAGE/.VolumeIcon.icns"
cp LEEME-dmg.txt "$STAGE/LÉEME primero.txt"

# imagen editable primero, para poder marcarle el icono al volumen
hdiutil create -volname "Transcribir" -srcfolder "$STAGE" -ov -format UDRW -fs HFS+ "$RW" >/dev/null
hdiutil attach "$RW" -nobrowse -quiet
/usr/bin/SetFile -a C /Volumes/Transcribir 2>/dev/null || true
hdiutil detach /Volumes/Transcribir -quiet

rm -f "$DMG"
hdiutil convert "$RW" -format ULMO -o "$DMG" >/dev/null
echo "listo: $DMG"
du -h "$DMG" | awk '{print "tamaño: "$1}'
