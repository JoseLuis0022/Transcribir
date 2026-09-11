"""Motor de transcripción: procesa la cola en segundo plano con Qwen3-ASR."""

import os
import threading
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from queue import Queue

import formatos

PROYECTO = Path(__file__).resolve().parent.parent
MODELOS = {"alta": "Qwen/Qwen3-ASR-1.7B", "rapida": "Qwen/Qwen3-ASR-0.6B"}
ALINEADOR = "Qwen/Qwen3-ForcedAligner-0.6B"
IDIOMAS = {"es": "Spanish", "en": "English", "auto": None}
EXTENSIONES = {".m4a", ".mp4", ".mp3", ".wav", ".mov"}
REGISTRO = Path.home() / "Library" / "Logs" / "Transcribir.log"

# Los modelos viven en la carpeta del proyecto y nunca se consulta internet.
os.environ["HF_HUB_CACHE"] = str(PROYECTO / "modelos" / "hf")
os.environ["HF_HUB_OFFLINE"] = "1"
# La librería llama a `ffmpeg` por nombre, y las apps abiertas desde Finder
# no heredan el PATH de Homebrew.
os.environ["PATH"] = "/opt/homebrew/bin:/usr/local/bin:" + os.environ.get("PATH", "/usr/bin:/bin")


class Cancelado(Exception):
    """Se canceló el trabajo en curso (desde la ventana o desde un agente)."""


@dataclass
class Trabajo:
    id: int
    origen: Path
    opciones: dict            # idioma, precision, vocabulario, formato, destino
    cliente: str | None = None  # "Claude Code", "Carpeta vigilada"…; None si lo agregó el usuario


def ruta_libre(carpeta: Path, nombre: str, extension: str = ".txt") -> Path:
    """nombre.txt, o nombre (2).txt, nombre (3).txt… si ya existe."""
    ruta = carpeta / f"{nombre}{extension}"
    n = 2
    while ruta.exists():
        ruta = carpeta / f"{nombre} ({n}){extension}"
        n += 1
    return ruta


def motivo_legible(e: Exception) -> str:
    if "Failed to load audio" in str(e):
        return "No se pudo leer el audio: archivo dañado o sin sonido"
    return (str(e).strip().splitlines() or [type(e).__name__])[0][:200]


class Motor(threading.Thread):
    """Transcribe un archivo a la vez.

    Los avisos se entregan con `despachar(funcion, *args)`; en la app los lleva
    al hilo principal. `al_progreso(id, estado, fraccion)` usa -1 para "sin
    porcentaje", `al_terminar(id, ruta, duracion, segundos)`, `al_fallar(id, motivo)`
    y `al_cancelar(id)`.
    """

    def __init__(self, al_progreso, al_terminar, al_fallar, al_cancelar, despachar):
        super().__init__(daemon=True)
        self._al_progreso, self._al_terminar = al_progreso, al_terminar
        self._al_fallar, self._al_cancelar = al_fallar, al_cancelar
        self._despachar = despachar
        self._cola: Queue[Trabajo] = Queue()
        self._cancelados: set[int] = set()
        self._sesiones = {}
        self._alineador = None

    def encolar(self, trabajo: Trabajo) -> None:
        self._cola.put(trabajo)

    def cancelar(self, id_trabajo: int) -> None:
        """Vale para uno en espera y para el que está en curso (se detiene en el
        siguiente fragmento de audio, a los pocos segundos)."""
        self._cancelados.add(id_trabajo)

    def run(self) -> None:
        while True:
            trabajo = self._cola.get()
            if trabajo.id in self._cancelados:
                continue                      # se quitó antes de empezar
            try:
                self._procesar(trabajo)
            except Cancelado:
                self._despachar(self._al_cancelar, trabajo.id)
            except Exception as e:
                with REGISTRO.open("a", encoding="utf-8") as log:
                    log.write(f"\n[{time.ctime()}] {trabajo.origen}\n{traceback.format_exc()}")
                self._despachar(self._al_fallar, trabajo.id, motivo_legible(e))

    def _revisar(self, id_trabajo: int) -> None:
        if id_trabajo in self._cancelados:
            raise Cancelado()

    def _sesion(self, precision: str):
        modelo = MODELOS[precision]
        if modelo not in self._sesiones:
            from mlx_qwen3_asr import Session

            self._sesiones[modelo] = Session(model=modelo)
        return self._sesiones[modelo]

    def _obtener_alineador(self):
        if self._alineador is None:
            from mlx_qwen3_asr.forced_aligner import ForcedAligner

            self._alineador = ForcedAligner(ALINEADOR)
        return self._alineador

    def _procesar(self, t: Trabajo) -> None:
        self._revisar(t.id)
        op = t.opciones
        con_tiempos = op["formato"] in ("tiempos", "srt")
        if MODELOS[op["precision"]] not in self._sesiones or (con_tiempos and self._alineador is None):
            self._despachar(self._al_progreso, t.id, "Preparando el modelo…", -1.0)
        sesion = self._sesion(op["precision"])
        alineador = self._obtener_alineador() if con_tiempos else None
        self._revisar(t.id)

        self._despachar(self._al_progreso, t.id, "Transcribiendo…", 0.0)
        duracion = 0.0

        def al_avanzar(p: dict) -> None:
            nonlocal duracion
            self._revisar(t.id)             # cancelar corta aquí, entre fragmentos
            duracion = p.get("audio_duration_sec", duracion)
            if p.get("event") in ("chunks_prepared", "chunk_completed"):
                self._despachar(self._al_progreso, t.id, "Transcribiendo…", float(p.get("progress", 0.0)))

        inicio = time.perf_counter()
        resultado = sesion.transcribe(
            str(t.origen), language=IDIOMAS[op["idioma"]], context=op["vocabulario"] or "",
            return_timestamps=con_tiempos, forced_aligner=alineador, on_progress=al_avanzar)
        self._revisar(t.id)

        if op["formato"] == "srt":
            contenido, extension = formatos.a_srt(resultado.text, resultado.segments or []), ".srt"
        elif op["formato"] == "tiempos":
            contenido, extension = formatos.con_tiempos(resultado.text, resultado.segments or []), ".txt"
        else:
            contenido, extension = formatos.en_parrafos(resultado.text), ".txt"
        if not contenido.strip():
            raise RuntimeError("No se detectó voz en el archivo")

        carpeta = Path(op["destino"])
        carpeta.mkdir(parents=True, exist_ok=True)
        destino = ruta_libre(carpeta, t.origen.stem, extension)
        destino.write_text(contenido + "\n", encoding="utf-8")
        self._despachar(self._al_terminar, t.id, str(destino), duracion, time.perf_counter() - inicio)
