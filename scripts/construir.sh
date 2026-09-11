#!/bin/bash
# Construye Transcribir.app completa (lleva su propio Python y el motor) y la instala
# en /Applications, con una copia en esta carpeta. Para compartirla: scripts/hacer-dmg.sh
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RAIZ"
PY="$RAIZ/.venv/bin/python"
APP="dist/Transcribir.app"
ID="net.esmexecutive.transcribir"

# no interrumpir una transcripción: mientras trabaja, la app mantiene un caffeinate
P="$(pgrep -f "Transcribir.app/Contents/MacOS/Transcribir" | head -1 || true)"
if [ -n "$P" ] && pgrep -f "caffeinate -i -w $P" >/dev/null; then
    echo "Transcribir está transcribiendo: espera a que termine y vuelve a intentarlo." >&2
    exit 1
fi
/usr/bin/osascript -e "quit app id \"$ID\"" >/dev/null 2>&1 || true
/usr/bin/osascript -e 'quit app id "local.transcribir"' >/dev/null 2>&1 || true

# modelos que hubiera en la carpeta del proyecto: a la de la app (renombrado, sin copiar)
"$PY" -c "import sys; sys.path.insert(0, 'transcribir'); import modelos; modelos.migrar('modelos/hf')"

"$PY" transcribir/make_icon.py
rm -rf build dist
"$PY" setup.py py2app >/dev/null

# mlx y sherpa_onnx se copian enteros, con sus librerías al lado (@loader_path) y, en el
# caso de MLX, con mlx.metallib junto a libmlx.dylib, que es donde lo busca
SITIO="$("$PY" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
DESTINO_LIB="$APP/Contents/Resources/lib/$("$PY" -c 'import sys; print(f"python{sys.version_info[0]}.{sys.version_info[1]}")')"
for PAQUETE in mlx sherpa_onnx; do
    rsync -a --exclude "__pycache__" --exclude "include" --exclude "share" "$SITIO/$PAQUETE" "$DESTINO_LIB/"
done
[ -f "$DESTINO_LIB/mlx/lib/mlx.metallib" ] || { echo "falta mlx.metallib en la app" >&2; exit 1; }

# py2app anota la ruta del Python con que se construyó; es solo informativa y es de esta Mac
/usr/libexec/PlistBuddy -c "Delete :PythonInfoDict:PythonExecutable" "$APP/Contents/Info.plist" 2>/dev/null || true

# firma ad-hoc de dentro hacia fuera y verificación estricta: una firma rota haría que
# macOS dijera "la app está dañada" en otra Mac, en vez del aviso normal
find "$APP/Contents" -type f \( -name "*.so" -o -name "*.dylib" \) -print0 \
    | xargs -0 /usr/bin/codesign --force --sign - 2>/dev/null
/usr/bin/codesign --force --deep --sign - "$APP"
/usr/bin/codesign --verify --deep --strict "$APP"
rm -rf build

for DESTINO in "/Applications/Transcribir.app" "$RAIZ/Transcribir.app"; do
    rm -rf "$DESTINO"
    cp -R "$APP" "$DESTINO"
done
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister \
    -f /Applications/Transcribir.app

# comando `transcribir` y Skill de Claude Code, con el Python de dentro de la app
"$PY" -c "import sys; sys.path.insert(0, 'transcribir'); import agentes; \
print(*agentes.instalar_todo(['/Applications/Transcribir.app/Contents/MacOS/Transcribir', '--cli']), sep='\n')"

du -sh "$APP" | awk '{print "tamaño de la app: "$1}'
echo "Listo: /Applications/Transcribir.app"
