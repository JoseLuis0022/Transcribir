"""Motor de transcripción: procesa la cola en segundo plano con Qwen3-ASR."""

import threading
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from queue import Queue

import audio
import biblioteca
import formatos
import interlocutores
import modelos

IDIOMAS = {"es": "Spanish", "en": "English", "auto": None}
EXTENSIONES = {".m4a", ".mp4", ".mp3", ".wav", ".mov"}
REGISTRO = Path.home() / "Library" / "Logs" / "Transcribir.log"


class Cancelado(Exception):
    """Se canceló el trabajo en curso (desde la ventana o desde un agente)."""


@dataclass
class Trabajo:
    id: int
    origen: Path
    opciones: dict            # idioma, precision, vocabulario, formato, destino
    cliente: str | None = None  # "Claude Code", "Carpeta vigilada"…; None si lo agregó el usuario
    tarea: str = "transcribir"  # o "tiempos": calcular el resaltado de una ficha ya hecha


def ruta_libre(carpeta: Path, nombre: str, extension: str = ".txt") -> Path:
    """nombre.txt, o nombre (2).txt, nombre (3).txt… si ya existe."""
    ruta = carpeta / f"{nombre}{extension}"
    n = 2
    while ruta.exists():
        ruta = carpeta / f"{nombre} ({n}){extension}"
        n += 1
    return ruta


def motivo_legible(e: Exception) -> str:
    if isinstance(e, (audio.AudioIlegible, modelos.ErrorDescarga)):
        return str(e)
    return (str(e).strip().splitlines() or [type(e).__name__])[0][:200]


class Motor(threading.Thread):
    """Transcribe un archivo a la vez.

    Los avisos se entregan con `despachar(funcion, *args)`; en la app los lleva
    al hilo principal. `al_progreso(id, estado, fraccion)` usa -1 para "sin
    porcentaje", `al_terminar(id, ruta, duracion, segundos, ficha)`, `al_fallar(id, motivo)`
    y `al_cancelar(id)`. Si falta un modelo, lo descarga antes de transcribir.
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

    def _modelo(self, t: Trabajo, clave: str) -> Path:
        """Carpeta local del modelo; si falta, lo descarga mostrando el avance."""
        ruta = modelos.ruta_local(clave)
        if ruta is not None:
            return ruta

        def avance(bajado, total):
            self._despachar(self._al_progreso, t.id,
                            f"Descargando el modelo · {modelos.gb(bajado)} de {modelos.gb(total)}",
                            bajado / total if total else -1.0)

        try:
            return modelos.descargar(clave, avance, lambda: t.id in self._cancelados)
        except modelos.DescargaCancelada:
            raise Cancelado()

    def _sesion(self, t: Trabajo, precision: str):
        if precision not in self._sesiones:
            ruta = self._modelo(t, precision)
            self._despachar(self._al_progreso, t.id, "Preparando el modelo…", -1.0)
            from mlx_qwen3_asr import Session

            self._sesiones[precision] = Session(model=str(ruta))
        return self._sesiones[precision]

    def _obtener_alineador(self, t: Trabajo):
        if self._alineador is None:
            ruta = self._modelo(t, "alineador")
            self._despachar(self._al_progreso, t.id, "Preparando el modelo…", -1.0)
            from mlx_qwen3_asr.forced_aligner import ForcedAligner

            self._alineador = ForcedAligner(str(ruta))
        return self._alineador

    def _escuchar(self, t: Trabajo, con_tiempos: bool):
        """Lee el audio y lo pasa por el modelo. Devuelve (resultado, muestras, duración)."""
        sesion = self._sesion(t, t.opciones["precision"])
        alineador = self._obtener_alineador(t) if con_tiempos else None
        self._revisar(t.id)

        muestras, duracion = audio.leer(t.origen)
        self._revisar(t.id)
        self._despachar(self._al_progreso, t.id, "Transcribiendo…", 0.0)

        def al_avanzar(p: dict) -> None:
            self._revisar(t.id)             # cancelar corta aquí, entre fragmentos
            if p.get("event") in ("chunks_prepared", "chunk_completed"):
                self._despachar(self._al_progreso, t.id, "Transcribiendo…", float(p.get("progress", 0.0)))

        resultado = sesion.transcribe(
            muestras, language=IDIOMAS[t.opciones["idioma"]], context=t.opciones["vocabulario"] or "",
            return_timestamps=con_tiempos, forced_aligner=alineador, on_progress=al_avanzar)
        self._revisar(t.id)
        return resultado, muestras, duracion

    def _tiempos(self, t: Trabajo) -> None:
        """Calcula el resaltado de una transcripción que ya existe, sin tocar su texto.

        Vuelve a escuchar el audio para saber cuándo suena cada palabra, pero las
        palabras son las del archivo: si lo corregiste en el editor, se respeta.
        """
        ficha = biblioteca.leer(t.opciones["ficha"])
        if ficha is None:
            raise RuntimeError("Esta transcripción ya no está en el historial")
        contenido = biblioteca.texto(ficha)
        if contenido is None:
            raise RuntimeError("No se encontró la transcripción")
        nombres = list((ficha.get("personas") or {}).values())

        resultado, _, _ = self._escuchar(t, con_tiempos=True)
        palabras = formatos.palabras_con_tiempo(formatos.limpiar(contenido, nombres),
                                                resultado.segments or [])
        if not palabras:
            raise RuntimeError("No se pudieron calcular los tiempos de las palabras")
        biblioteca.guardar_palabras(ficha["id"], palabras)
        self._despachar(self._al_terminar, t.id, str(biblioteca.ubicar(ficha)),
                        ficha.get("duracion", 0.0), 0.0, ficha["id"])

    def _procesar(self, t: Trabajo) -> None:
        self._revisar(t.id)
        if t.tarea == "tiempos":
            return self._tiempos(t)
        op = t.opciones
        por_persona = bool(op.get("personas"))
        con_tiempos = op["formato"] in ("tiempos", "srt") or por_persona or bool(op.get("tiempos"))

        inicio = time.perf_counter()
        resultado, muestras, duracion = self._escuchar(t, con_tiempos)

        palabras = formatos.palabras_con_tiempo(resultado.text, resultado.segments or []) if con_tiempos else []
        if con_tiempos and not palabras:
            raise RuntimeError("No se pudieron calcular los tiempos de las palabras")
        personas = None
        if por_persona:
            segmentacion = self._modelo(t, "segmentacion")
            voces = self._modelo(t, "voces")
            self._despachar(self._al_progreso, t.id, "Separando por persona…", -1.0)
            turnos = interlocutores.turnos(
                muestras, segmentacion, voces, lambda: self._revisar(t.id),
                lambda f: self._despachar(self._al_progreso, t.id, "Separando por persona…", f))
            personas = formatos.asignar_personas(palabras, turnos)

        if op["formato"] == "srt":
            contenido, extension = formatos.a_srt(palabras, personas), ".srt"
        elif personas is not None:
            contenido, extension = formatos.con_personas(palabras, personas, op["formato"] == "tiempos"), ".txt"
        elif op["formato"] == "tiempos":
            contenido, extension = formatos.con_tiempos(palabras), ".txt"
        else:
            contenido, extension = formatos.en_parrafos(resultado.text), ".txt"
        if not contenido.strip():
            raise RuntimeError("No se detectó voz en el archivo")

        carpeta = Path(op["destino"])
        carpeta.mkdir(parents=True, exist_ok=True)
        destino = ruta_libre(carpeta, t.origen.stem, extension)
        destino.write_text(contenido + "\n", encoding="utf-8")

        segundos = time.perf_counter() - inicio
        ficha = biblioteca.crear(t.origen, destino, op, duracion, segundos, t.cliente,
                                 len(set(personas)) if personas else 0)
        if palabras:
            biblioteca.guardar_palabras(ficha["id"], palabras, personas)
        self._despachar(self._al_terminar, t.id, str(destino), duracion, segundos, ficha["id"])
