"""Los modelos de Qwen3-ASR en la Mac de cada quien: dónde están y cómo se descargan.

La app carga siempre desde la carpeta local, sin consultar internet. Solo se
conecta para descargar un modelo que falta, una sola vez.
"""

import os
import threading
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
# Descarga HTTP directa: progreso predecible y sin caché de trozos que duplique el espacio.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

CARPETA = Path.home() / "Library" / "Application Support" / "Transcribir" / "Modelos"
CATALOGO = {  # clave: (repositorio, tamaño aproximado en bytes, archivos a bajar o None = todos)
    "alta": ("Qwen/Qwen3-ASR-1.7B", 4_400_000_000, None),
    "rapida": ("Qwen/Qwen3-ASR-0.6B", 1_880_000_000, None),
    "alineador": ("Qwen/Qwen3-ForcedAligner-0.6B", 1_840_000_000, None),
    # separar por persona (Sherpa-ONNX): segmentación de pyannote 3.0 y huellas de voz
    "segmentacion": ("csukuangfj/sherpa-onnx-pyannote-segmentation-3-0", 6_000_000, ["model.onnx"]),
    "voces": ("csukuangfj/speaker-embedding-models", 26_500_000, ["wespeaker_en_voxceleb_resnet34_LM.onnx"]),
}
COMPLETO = ".transcribir-completo"      # se escribe solo cuando la descarga terminó entera


class DescargaCancelada(Exception):
    """Se dejó de esperar una descarga (sigue en segundo plano y se retoma después)."""


class ErrorDescarga(Exception):
    """No se pudo descargar un modelo; el mensaje ya es legible."""


def gb(n: float) -> str:
    """Tamaño legible: "4,4 GB" o, si es pequeño, "26 MB"."""
    if n < 1e9:
        return f"{n / 1e6:.0f} MB"
    return f"{n / 1e9:.1f} GB".replace(".", ",")


def _carpeta(repo: str) -> Path:
    return CARPETA / ("models--" + repo.replace("/", "--"))


def ruta_local(clave: str) -> Path | None:
    """Carpeta del modelo si está completo; None si falta o quedó a medias."""
    snapshots = _carpeta(CATALOGO[clave][0]) / "snapshots"
    if snapshots.is_dir():
        for snap in sorted(snapshots.iterdir()):
            if (snap / COMPLETO).exists():
                return snap
    return None


def _bajado(repo: str) -> int:
    blobs = _carpeta(repo) / "blobs"
    total = 0
    if blobs.is_dir():
        for archivo in blobs.iterdir():
            try:
                total += archivo.stat().st_size
            except OSError:
                pass
    return total


_hilos: dict[str, threading.Thread] = {}
_errores: dict[str, Exception] = {}
_candado = threading.Lock()


def descargar(clave: str, al_progreso=None, cancelado=lambda: False) -> Path:
    """Descarga el modelo si falta y devuelve su carpeta local.

    `al_progreso(bajado, total)` recibe bytes. Aunque varios lo pidan a la vez
    hay una sola descarga por modelo. Cancelar solo deja de esperar.
    """
    ruta = ruta_local(clave)
    if ruta is not None:
        return ruta
    repo, total, _ = CATALOGO[clave]
    with _candado:
        hilo = _hilos.get(clave)
        if hilo is None or not hilo.is_alive():
            _errores.pop(clave, None)
            hilo = threading.Thread(target=_bajar, args=(clave,), daemon=True)
            _hilos[clave] = hilo
            hilo.start()
    while hilo.is_alive():
        hilo.join(0.5)
        if al_progreso is not None:
            al_progreso(min(_bajado(repo), total), total)
        if cancelado():
            raise DescargaCancelada()
    if clave in _errores:
        raise ErrorDescarga(_mensaje(_errores[clave]))
    ruta = ruta_local(clave)
    if ruta is None:
        raise ErrorDescarga("La descarga no se completó. Reintenta.")
    if al_progreso is not None:
        al_progreso(total, total)
    return ruta


def _bajar(clave: str) -> None:
    repo, _, archivos = CATALOGO[clave]
    try:
        from huggingface_hub import snapshot_download

        CARPETA.mkdir(parents=True, exist_ok=True)
        snap = Path(snapshot_download(repo, cache_dir=str(CARPETA), allow_patterns=archivos))
        (snap / COMPLETO).write_text("ok\n")
    except Exception as e:
        _errores[clave] = e


def _mensaje(e: Exception) -> str:
    texto = f"{type(e).__name__}: {e}"
    if "Errno 28" in texto or "No space" in texto:
        return "No hay espacio suficiente en el disco para el modelo."
    if any(p in texto for p in ("Connect", "Timeout", "resolve", "Network", "offline", "SSL")):
        return "Sin conexión: no se pudo descargar el modelo. Revisa internet y reintenta."
    return "No se pudo descargar el modelo: " + (str(e).strip().splitlines() or [type(e).__name__])[0][:120]


def migrar(origen: Path) -> list[Path]:
    """Mueve modelos ya descargados (p. ej. en la carpeta del proyecto) a la de la app.

    En el mismo disco es un renombrado: instantáneo y sin espacio extra.
    """
    origen = Path(origen)
    movidos = []
    if origen.is_dir():
        CARPETA.mkdir(parents=True, exist_ok=True)
        for carpeta in sorted(origen.glob("models--*")):
            destino = CARPETA / carpeta.name
            if not destino.exists():
                carpeta.rename(destino)
                movidos.append(destino)
    for repo, _, _ in CATALOGO.values():
        snapshots = _carpeta(repo) / "snapshots"
        for snap in sorted(snapshots.iterdir()) if snapshots.is_dir() else []:
            if (snap / "config.json").exists() and not (snap / COMPLETO).exists():
                (snap / COMPLETO).write_text("ok\n")
    return movidos
