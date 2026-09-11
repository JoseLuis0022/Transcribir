#!/bin/bash
# Construye Transcribir.app (modo enlazado: usa el código, el entorno y el modelo
# de esta carpeta) y la deja aquí y en /Applications, con su icono.
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RAIZ"
PY="$RAIZ/.venv/bin/python"

# no interrumpir una transcripción: mientras trabaja, la app mantiene un caffeinate
P="$(pgrep -f "Transcribir.app/Contents/MacOS/Transcribir" || true)"
if [ -n "$P" ] && pgrep -f "caffeinate -i -w $P" >/dev/null; then
    echo "Transcribir está transcribiendo: espera a que termine y vuelve a intentarlo." >&2
    exit 1
fi
/usr/bin/osascript -e 'quit app "Transcribir"' >/dev/null 2>&1 || true

"$PY" transcribir/make_icon.py
rm -rf build dist
"$PY" setup.py py2app -A >/dev/null

# en modo -A el icono del bundle es un enlace: se sustituye por el archivo real
for f in dist/Transcribir.app/Contents/Resources/*.icns; do
    if [ -L "$f" ]; then rm "$f"; cp transcribir/Transcribir.icns "$f"; fi
done

for destino in "$RAIZ/Transcribir.app" "/Applications/Transcribir.app"; do
    rm -rf "$destino"
    cp -R dist/Transcribir.app "$destino"
    touch "$destino"
done
rm -rf build dist

swift scripts/aplicar_icono.swift transcribir/Transcribir.icns \
    "$RAIZ/Transcribir.app" /Applications/Transcribir.app

# comando `transcribir` y Skill de Claude Code: los agentes pueden usarla desde ya
"$PY" -c "import sys; sys.path.insert(0, 'transcribir'); import agentes; print(*agentes.instalar_todo(), sep='\n')"
echo "Listo: $RAIZ/Transcribir.app y /Applications/Transcribir.app"
