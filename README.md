# Transcribir

Convierte audios y videos en texto **en tu Mac y sin internet**. Arrastras los
archivos a la ventana, se encolan y cada uno termina como un `.txt` limpio (o
subtítulos `.srt`) en la carpeta que elijas.

Hecha para macOS con Apple Silicon: interfaz nativa (AppKit vía PyObjC) y el
modelo de código abierto **Qwen3-ASR**, acelerado con MLX en la GPU del chip.

## Qué hace

- **Cola por arrastrar y soltar**: `.m4a`, `.mp4`, `.mp3`, `.wav` y `.mov`, uno
  tras otro, con progreso y opción de **cancelar** el que está en curso.
- **Terminados** con "Mostrar en Finder" y botón para limpiar la lista.
- **Formatos**: párrafos, párrafos con marcas de tiempo `[mm:ss]` o subtítulos
  `.srt` (tiempos por palabra con Qwen3-ForcedAligner).
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
transcribir reunion.m4a --texto        # transcribe, espera e imprime el texto
transcribir clase.mp4 --formato srt    # subtítulos
transcribir *.m4a --no-esperar         # encola y sigue
transcribir estado --json              # cola, progreso, terminados y ajustes
transcribir cancelar --todo
transcribir ajustes idioma auto        # cambia un ajuste (se ve en la app)
transcribir guia                       # la guía completa para agentes
```

Al construir la app se instalan:

- el comando en `~/.local/bin/transcribir`;
- una **Skill de Claude Code** en `~/.claude/skills/transcribir/`, con la que
  Claude Code descubre la app y la usa en cuanto le pides una transcripción.

Para otros agentes, **Ajustes › Agentes › Copiar guía** y pégala en su
`AGENTS.md`.

Por dentro, el comando habla con la app por un socket Unix local
(`~/Library/Application Support/Transcribir/transcribir.sock`). Si la app está
cerrada, la abre en segundo plano sin robar el foco.

## Instalación

Requisitos: Mac con Apple Silicon, macOS 14 o posterior,
[Homebrew](https://brew.sh) con `ffmpeg`, y [uv](https://docs.astral.sh/uv/).

```sh
brew install ffmpeg
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt

# modelos (unos 8 GB en total), dentro del proyecto
export HF_HUB_CACHE="$PWD/modelos/hf"
hf download Qwen/Qwen3-ASR-1.7B
hf download Qwen/Qwen3-ASR-0.6B
hf download Qwen/Qwen3-ForcedAligner-0.6B

./scripts/construir.sh    # Transcribir.app aquí y en /Applications, más el comando y la Skill
```

La app se construye en modo enlazado: usa el código, el entorno y los modelos
de esta carpeta, así que no la muevas después de construir.

## Estructura

```
transcribir/
  app.py           ventana principal y delegado de la app
  ajustes.py       ventana de Ajustes
  motor.py         cola y transcripción (Qwen3-ASR vía mlx-qwen3-asr)
  formatos.py      párrafos, marcas de tiempo y subtítulos .srt
  preferencias.py  claves, valores por defecto y validación de ajustes
  avisos.py        notificaciones del sistema
  vigia.py         carpeta vigilada
  servidor.py      socket local que atiende al comando
  cli.py           el comando `transcribir`
  agentes.py       guía, lanzador del comando y Skill de Claude Code
  ui.py            piezas de interfaz nativas
  make_icon.py     genera el icono y los glifos
scripts/
  construir.sh     construye e instala la app
  aplicar_icono.swift
setup.py           configuración de py2app
```

## Privacidad

Todo ocurre en el Mac. Los modelos se descargan una vez y la app funciona con
`HF_HUB_OFFLINE=1`: ningún audio ni texto sale de la computadora.
