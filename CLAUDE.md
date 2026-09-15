# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Transcribir es una app nativa de macOS (Python 3.12 + PyObjC/AppKit) que transcribe audio y video en local con Qwen3-ASR sobre MLX. Todo el proyecto (código, comentarios, commits, releases) está en español.

## Comandos

```sh
.venv/bin/python transcribir/principal.py   # correr desde el código
./scripts/construir.sh                       # compila, BORRA /Applications/Transcribir.app e instala la nueva (+ comando y Skill)
./scripts/hacer-dmg.sh                       # dist/Transcribir-<VERSION>.dmg a partir de dist/Transcribir.app
transcribir ARCHIVO --destino CARPETA        # usar la app instalada desde la terminal
```

- No hay suite de pruebas ni linter: se prueba con scripts sueltos contra `.venv/bin/python` (con `sys.path.insert(0, 'transcribir')`) y con la app instalada.
- `transcribir` necesita **rutas absolutas**: las relativas se resuelven dentro de la app.
- Errores de la app instalada: `~/Library/Logs/Transcribir.log` (el motor escribe ahí el traceback completo; la ventana solo muestra un mensaje corto).

## Arquitectura

- `principal.py` arranca la app, o el comando si recibe `--cli`. El motor (`motor.py`) solo vive dentro de la app: el comando `transcribir` (`cli.py`) le manda trabajos por un socket Unix (`servidor.py`, JSON por líneas) y recibe eventos (`encolado`, `progreso`, `terminado`, `error`, `cancelado`). Ventana y agentes comparten una sola cola; todo pasa por el hilo principal.
- Flujo de una transcripción: `motor._procesar` → `_transcribir` → `_escuchar` (`audio.leer` + Qwen3-ASR) → `formatos` compone el texto → `biblioteca.crear` guarda la ficha JSON → callback `al_terminar` → `app.alTerminar` pinta la fila, emite el evento al CLI y notifica (`avisos.py`).
- `audio.py` lee con AVFoundation (sin ffmpeg) a PCM float32 mono de 16 kHz. El decodificador AAC de macOS se detiene con paramErr (-50) en los paquetes de 4 bytes que dejan Zoom/Meet con el micrófono apagado: `leer` reanuda la lectura y rellena con silencio. Un archivo cortado (`-11880`) se transcribe hasta donde llega y devuelve cuánto falta, que acaba como `ficha["aviso"]`.
- La versión está en `transcribir/identidad.py` (`VERSION`, `COMPILACION`); `setup.py` la lleva al Info.plist.
- Detalles del empaquetado (mlx/sherpa_onnx copiados a mano, firma ad-hoc verificada, exclusiones) en `scripts/construir.sh` y en «Notas técnicas» del README.

## Proceso para publicar una nueva versión

Seguir en este orden. Si un paso falla, no pasar al siguiente.

1. **Verificar el error y lo que se pidió.**
   - Reproducir el problema con el archivo real del usuario y leer `~/Library/Logs/Transcribir.log`.
   - Encontrar la causa real (no la del mensaje de la app) y confirmarla antes de cambiar código.
   - Guardar una copia del módulo que se va a cambiar en el scratchpad para comparar después.
2. **Hacer los cambios** y probarlos desde el código:
   - que el caso que fallaba ya funcione;
   - que lo que ya funcionaba siga igual (p. ej. comparar la salida vieja y la nueva con archivos normales: m4a, mp3, wav, mp4);
   - revisar también los demás archivos parecidos del usuario, no solo el que reportó.
3. **Subir la versión** en `transcribir/identidad.py`: `VERSION` (p. ej. `1.2` → `1.2.1`) y `COMPILACION` +1. Actualizar el nombre del `.dmg` en el README.
4. **Desinstalar, compilar e instalar**: `./scripts/construir.sh`. Cierra la app, borra `/Applications/Transcribir.app` e instala la nueva. Se niega si la app está transcribiendo; en ese caso, esperar.
   - Comprobar: `defaults read /Applications/Transcribir.app/Contents/Info.plist CFBundleShortVersionString` y `codesign --verify --deep --strict /Applications/Transcribir.app`.
5. **Probar con la app instalada** usando `transcribir` con rutas absolutas y `--destino` en el scratchpad (o donde pida el usuario): primero fragmentos cortos que reproduzcan el caso (`ffmpeg -ss … -t … -c copy`) y después el archivo real completo (en segundo plano: una clase de 1 h tarda ~5 min). Revisar el texto obtenido y los avisos.
6. **Si todo funciona, subir el código a GitHub**:
   - rama nueva → commit (mensaje en español: título y explicación de qué cambia para el usuario) → `git merge --ff-only` en `main` → `git push origin main` → borrar la rama;
   - solo código fuente: `dist/`, `Transcribir.app` y `*.dmg` están en `.gitignore`.
7. **Publicar el release**:
   - `./scripts/hacer-dmg.sh` y `hdiutil verify dist/Transcribir-<VERSION>.dmg`;
   - partir de las notas del release anterior (`gh release view v<ANTERIOR> --json body -q .body`), cambiar el nombre del `.dmg` y añadir arriba una sección «Novedades de la <VERSION>» escrita para el usuario final;
   - `gh release create v<VERSION> dist/Transcribir-<VERSION>.dmg --target main --title "Transcribir <VERSION>" --notes-file NOTAS.md`.
8. **Informar al usuario**: qué se arregló, qué pruebas pasaron, enlace del release y lo que quedó pendiente (transcripciones de prueba en su historial, problemas de sus archivos, etc.).
