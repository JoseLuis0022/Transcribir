# Transcribir

Convierte audios y videos en texto **en tu Mac y sin internet**. Arrastras los
archivos a la ventana, se encolan y cada uno termina como un `.txt` limpio (o
subtítulos `.srt`) en la carpeta que elijas.

Hecha para macOS con Apple Silicon: interfaz nativa (AppKit vía PyObjC), el
modelo de código abierto **Qwen3-ASR** acelerado con MLX en la GPU del chip, y
audio leído con AVFoundation. No depende de nada instalado aparte: la app lleva
dentro su propio Python y el motor.

## Instalar

Descarga `Transcribir-1.1.dmg` de
[Releases](https://github.com/JoseLuis0022/Transcribir/releases), ábrelo y
arrastra Transcribir a Aplicaciones. Requiere **macOS 14 o posterior** en un Mac
con **chip Apple**.

La primera vez macOS avisa de que no puede verificar la app (no está firmada con
una cuenta de desarrollador de pago): el `LÉEME primero.txt` del disco explica
cómo abrirla. Después, la bienvenida te deja elegir el modelo y lo descarga una
sola vez (4,4 GB el preciso, 1,9 GB el rápido).

## Qué hace

- **Cola por arrastrar y soltar**: `.m4a`, `.mp4`, `.mp3`, `.wav` y `.mov`, uno
  tras otro, con progreso y opción de **cancelar** el que está en curso.
- **Terminados** con "Mostrar en Finder" y botón para limpiar la lista.
- **Formatos**: párrafos, párrafos con marcas de tiempo `[mm:ss]` o subtítulos
  `.srt` (tiempos por palabra con Qwen3-ForcedAligner).
- **Separar por persona**: marca quién habla («Persona 1:», «Persona 2:») con
  Sherpa-ONNX (segmentación de pyannote 3.0 y huellas de voz WeSpeaker), sin
  cuentas ni PyTorch. Se combina con cualquier formato.
- **Ajustes** (⌘,): idioma (español, inglés o automático), precisión (1.7B o
  rápida 0.6B), vocabulario propio para nombres y siglas, dónde guardar, qué
  hacer al terminar, carpeta vigilada y notificaciones.
- **Carpeta vigilada**: transcribe sola lo que llegue a una carpeta mientras la
  app está abierta.
- **Notificaciones** al terminar, con clic para ver el resultado en Finder.

## 🤖 Para agentes

Transcribir es *agent first*: Claude Code, Codex o cualquier agente con
terminal la usan con el comando `transcribir`, y lo que piden **aparece en la
ventana** con su nombre, para que veas qué están haciendo.

```sh
transcribir reunion.m4a --texto          # transcribe, espera e imprime el texto
transcribir entrevista.m4a --personas    # quién dijo qué
transcribir clase.mp4 --formato srt      # subtítulos
transcribir *.m4a --no-esperar           # encola y sigue
transcribir estado --json                # cola, progreso, terminados y ajustes
transcribir cancelar --todo
transcribir ajustes idioma auto          # cambia un ajuste (se ve en la app)
transcribir guia                         # la guía completa para agentes
```

En la bienvenida (o en **Ajustes › Agentes**) se instalan:

- el comando en `~/.local/bin/transcribir`, que usa el Python de dentro de la
  app (si mueves la app, se pone al día solo al abrirla);
- una **Skill de Claude Code** en `~/.claude/skills/transcribir/`, con la que
  Claude Code descubre la app y la usa en cuanto le pides una transcripción.

Para otros agentes, **Ajustes › Agentes › Copiar guía** y pégala en su
`AGENTS.md`.

Por dentro, el comando habla con la app por un socket Unix local
(`~/Library/Application Support/Transcribir/transcribir.sock`). Si la app está
cerrada, la abre en segundo plano sin robar el foco.

## Privacidad

Todo el procesamiento ocurre en el Mac. La app solo se conecta a internet para
descargar un modelo que falta (de Hugging Face, a
`~/Library/Application Support/Transcribir/Modelos`), y los carga siempre desde
esa carpeta local. Ningún audio ni texto sale de la computadora.

## Desarrollo

Requisitos: Mac con Apple Silicon, macOS 14+ y [uv](https://docs.astral.sh/uv/).

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt sherpa-onnx

.venv/bin/python transcribir/principal.py   # correr desde el código
./scripts/construir.sh                       # app completa en /Applications, más el comando y la Skill
./scripts/hacer-dmg.sh                       # dist/Transcribir-<versión>.dmg para compartir
```

Los modelos se descargan desde la propia app la primera vez (o con
`hf download … --cache-dir ~/Library/Application\ Support/Transcribir/Modelos`).

## Estructura

```
transcribir/
  principal.py     punto de entrada: la app, o el comando con --cli
  app.py           ventana principal y delegado de la app
  bienvenida.py    primera vez: elegir y descargar el modelo, conectar agentes
  ajustes.py       ventana de Ajustes
  motor.py         cola y transcripción (Qwen3-ASR vía mlx-qwen3-asr)
  audio.py         lectura de audio y video con AVFoundation
  modelos.py       dónde viven los modelos y cómo se descargan
  interlocutores.py  separar por persona con Sherpa-ONNX
  formatos.py      párrafos, marcas de tiempo, personas y subtítulos .srt
  preferencias.py  claves, valores por defecto y validación de ajustes
  avisos.py        notificaciones del sistema
  vigia.py         carpeta vigilada
  servidor.py      socket local que atiende al comando
  cli.py           el comando `transcribir`
  agentes.py       guía, lanzador del comando y Skill de Claude Code
  recursos.py      recursos dentro de la app o junto al código
  identidad.py     nombre, versión e identificador
  ui.py            piezas de interfaz nativas
  make_icon.py     genera el icono y los glifos
scripts/
  construir.sh     construye la app completa y la instala
  hacer-dmg.sh     la empaqueta en una imagen de disco
setup.py           configuración de py2app
LEEME-dmg.txt      instrucciones que viajan dentro del DMG
```
