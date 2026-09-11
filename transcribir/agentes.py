"""Lo que Transcribir instala para que los agentes de IA la usen (solo biblioteca estándar)."""

import shlex
from pathlib import Path

COMANDO = Path.home() / ".local" / "bin" / "transcribir"
SKILL = Path.home() / ".claude" / "skills" / "transcribir" / "SKILL.md"

GUIA = """\
Transcribir convierte audio y video (.m4a .mp4 .mp3 .wav .mov) en texto en este
Mac, sin internet (Qwen3-ASR acelerado con MLX). Lo que pidas aparece en la
ventana de la app con tu nombre, para que el usuario vea qué estás haciendo.
Si la app está cerrada, el comando la abre sola en segundo plano.

Comandos:

  transcribir ARCHIVO...               transcribe, espera e imprime la ruta de cada resultado
  transcribir ARCHIVO... --texto       además imprime el texto (para leerlo sin abrir el archivo)
  transcribir ARCHIVO... --json        una línea JSON por evento: encolado, progreso, terminado…
  transcribir ARCHIVO... --no-esperar  encola y devuelve los ids al instante
  transcribir estado [--json]          cola, progreso, terminados y ajustes
  transcribir cancelar ID... | --todo  cancela en espera o en curso
  transcribir ajustes [--json]         ver los ajustes y sus opciones
  transcribir ajustes CLAVE VALOR      cambiar un ajuste (se ve en la app)
  transcribir limpiar                  vacía la lista de terminados (no borra archivos)
  transcribir abrir                    trae la ventana al frente

Opciones solo para esa petición (no cambian los ajustes del usuario):

  --idioma es|en|auto          --formato parrafos|tiempos|srt
  --precision alta|rapida      --vocabulario "Nombres, siglas, términos"
  --personas                   separa por interlocutor: «Persona 1: …», «Persona 2: …»
  --destino CARPETA | --junto  (junto = al lado del archivo original)

Cómo usarla bien:

  · Pasa rutas absolutas. Si el usuario solo dice el nombre, búscalo antes
    (Escritorio, Descargas, Documentos) y confirma si hay varios candidatos.
  · Tarda ~1/6 de la duración con precisión alta (~1/15 con rápida); la primera
    vez de la sesión carga el modelo (~10 s). Si falta un modelo, la app lo
    descarga antes (verás "Descargando el modelo"). Con audios de más de
    20 min usa --no-esperar y consulta `transcribir estado --json`.
  · Si el audio tiene nombres propios o siglas, pásalos con --vocabulario:
    es lo que más mejora la precisión.
  · Para subtítulos usa --formato srt; para citar momentos, --formato tiempos.
  · En reuniones, entrevistas o llamadas usa --personas para saber quién dijo
    qué (se combina con cualquier formato).
  · Los resultados se guardan donde el usuario lo tenga configurado (por
    defecto, el Escritorio); la ruta sale en la salida del comando.
  · No cambies ajustes permanentes (`transcribir ajustes CLAVE VALOR`) salvo
    que el usuario lo pida; usa las opciones de la petición.
  · Códigos de salida: 0 bien, 1 algún archivo falló, 2 la app no está
    disponible, 3 cancelado.
  · Si `transcribir` no está en el PATH, usa ~/.local/bin/transcribir.
"""

SKILL_TEXTO = """\
---
name: transcribir
description: Transcribe audio or video files (m4a, mp4, mp3, wav, mov) to text locally on this Mac with the Transcribir app, as plain text, timestamped paragraphs or SRT subtitles. Use when the user asks to transcribe a recording, meeting, class, interview, voice note or video, wants a transcript or subtitles, asks what was said in a media file, or who said what (speaker separation). Español: transcribir, transcripción, subtítulos, grabación, reunión, clase, nota de voz, qué dijo, quién habló, interlocutores.
allowed-tools: Bash(transcribir *) Bash(~/.local/bin/transcribir *)
---

# Transcribir

{guia}"""


def ejecutable_desarrollo() -> list[str]:
    """En desarrollo, el comando corre con el Python del proyecto."""
    raiz = Path(__file__).resolve().parent.parent
    return [str(raiz / ".venv" / "bin" / "python"), str(raiz / "transcribir" / "cli.py")]


def _lanzador(ejecutable: list[str]) -> str:
    return ("#!/bin/bash\n# Lanzador de Transcribir, generado por la app.\n"
            f'exec {shlex.join(ejecutable)} "$@"\n')


def instalar_comando(ejecutable: list[str]) -> Path:
    """Deja un lanzador en ~/.local/bin, que suele estar en el PATH.

    `ejecutable` es cómo arrancar el comando: dentro de la app,
    ["…/Transcribir.app/Contents/MacOS/Transcribir", "--cli"].
    """
    COMANDO.parent.mkdir(parents=True, exist_ok=True)
    COMANDO.write_text(_lanzador(ejecutable), encoding="utf-8")
    COMANDO.chmod(0o755)
    return COMANDO


def instalar_skill() -> Path:
    """La Skill con la que Claude Code descubre y usa Transcribir por su cuenta."""
    SKILL.parent.mkdir(parents=True, exist_ok=True)
    SKILL.write_text(SKILL_TEXTO.format(guia=GUIA), encoding="utf-8")
    return SKILL


def instalar_todo(ejecutable: list[str]) -> list[Path]:
    return [instalar_comando(ejecutable), instalar_skill()]


def comando_existe() -> bool:
    return COMANDO.exists()


def comando_instalado(ejecutable: list[str]) -> bool:
    try:
        return COMANDO.read_text(encoding="utf-8") == _lanzador(ejecutable)
    except OSError:
        return False


def skill_existe() -> bool:
    return SKILL.exists()


def skill_instalada() -> bool:
    try:
        return SKILL.read_text(encoding="utf-8") == SKILL_TEXTO.format(guia=GUIA)
    except OSError:
        return False
