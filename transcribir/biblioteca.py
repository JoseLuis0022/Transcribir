"""Catálogo de transcripciones: qué se transcribió, cuándo y dónde quedó el archivo.

Tus archivos son la verdad. El .txt y el .srt viven en tu carpeta y puedes moverlos,
enviarlos o borrarlos; aquí solo se guarda una ficha ligera (~1 KB) con los datos que
la app necesita después: la ruta, un marcador para reencontrar el archivo si cambia de
sitio, la duración, los ajustes y los nombres de las personas. El audio nunca se copia.

    Biblioteca/<id>.json            la ficha
    Biblioteca/<id>.palabras.json   los tiempos por palabra, solo si se calcularon
"""

import base64
import json
import re
import time
import unicodedata
from pathlib import Path

from Foundation import NSURL, NSData

CARPETA = Path.home() / "Library" / "Application Support" / "Transcribir" / "Biblioteca"
ESCRITORIO = Path.home() / "Desktop"
ESQUEMA = 1
LIMITE_BUSQUEDA = 300 * 1024      # no leer archivos enormes al buscar


# ------------------------------------------------------------------ marcadores --
def marcador(ruta) -> str:
    """Marcador del sistema para volver a encontrar el archivo si lo mueves o lo renombras."""
    try:
        url = NSURL.fileURLWithPath_(str(ruta))
        datos = url.bookmarkDataWithOptions_includingResourceValuesForKeys_relativeToURL_error_(
            0, None, None, None)
        if isinstance(datos, tuple):          # (datos, error)
            datos = datos[0]
        return base64.b64encode(datos.bytes().tobytes()).decode("ascii") if datos else ""
    except Exception:
        return ""


def resolver(texto: str):
    """Ruta actual del archivo de un marcador, o None si ya no existe."""
    if not texto:
        return None
    try:
        datos = NSData.dataWithBytes_length_(base64.b64decode(texto), len(base64.b64decode(texto)))
        salida = NSURL.URLByResolvingBookmarkData_options_relativeToURL_bookmarkDataIsStale_error_(
            datos, 0, None, None, None)
        url = salida[0] if isinstance(salida, tuple) else salida
        if url is None or not url.isFileURL():
            return None
        ruta = Path(url.path())
        return ruta if ruta.exists() else None
    except Exception:
        return None


# ----------------------------------------------------------------------- ficha --
def _id(nombre: str) -> str:
    """Identificador legible y ordenable: 20260911-143022-clase-de-historia."""
    base = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-zA-Z0-9]+", "-", base).strip("-").lower()[:40] or "audio"
    return f"{time.strftime('%Y%m%d-%H%M%S')}-{base}"


def _escribir(ruta: Path, datos: dict) -> None:
    """Escritura atómica: o queda el archivo entero o queda el anterior."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_suffix(ruta.suffix + ".nuevo")
    temporal.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    temporal.replace(ruta)


def _leer(ruta: Path):
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def crear(origen: Path, salida: Path, opciones: dict, duracion: float, segundos: float,
          cliente=None, personas: int = 0) -> dict:
    """Ficha de una transcripción recién terminada, ya guardada en el catálogo."""
    ficha = {
        "esquema": ESQUEMA,
        "id": _id(origen.stem),
        "creado": time.time(),
        "nombre": origen.name,
        "origen": str(origen),
        "origen_marcador": marcador(origen),
        "salida": str(salida),
        "salida_marcador": marcador(salida),
        "formato": opciones.get("formato", "parrafos"),
        "ajustes": {c: opciones.get(c) for c in ("idioma", "precision", "vocabulario", "personas")},
        "duracion": round(duracion, 2),
        "segundos": round(segundos, 2),
        "cliente": cliente,
        "personas": {},              # "1": "Ana" — los nombres que pongas en el editor
        "cuantas_personas": personas,
        "tiempos": False,            # True cuando hay <id>.palabras.json
    }
    guardar(ficha)
    return ficha


def guardar(ficha: dict) -> None:
    _escribir(CARPETA / f"{ficha['id']}.json", ficha)


def leer(id_ficha: str):
    return _leer(CARPETA / f"{id_ficha}.json")


def todas() -> list[dict]:
    """Todas las fichas, de la más reciente a la más antigua."""
    if not CARPETA.is_dir():
        return []
    fichas = []
    for ruta in CARPETA.glob("*.json"):
        if ruta.name.endswith(".palabras.json"):
            continue
        ficha = _leer(ruta)
        if ficha and ficha.get("id"):
            fichas.append(ficha)
    return sorted(fichas, key=lambda f: f.get("creado", 0), reverse=True)


def olvidar(id_ficha: str) -> None:
    """Quita la entrada del historial. No toca tus archivos."""
    for ruta in (CARPETA / f"{id_ficha}.json", CARPETA / f"{id_ficha}.palabras.json"):
        ruta.unlink(missing_ok=True)


# -------------------------------------------------------------------- archivos --
def ubicar(ficha: dict, clave: str = "salida"):
    """Dónde está hoy el archivo («salida» u «origen»), o None si ya no está.

    Si lo moviste, el marcador lo encuentra y la ficha se corrige sola.
    """
    ruta = Path(ficha.get(clave) or "")
    if ruta.name and ruta.exists():
        return ruta
    encontrada = resolver(ficha.get(f"{clave}_marcador", ""))
    if encontrada is None:
        return None
    ficha[clave] = str(encontrada)
    guardar(ficha)
    return encontrada


def apuntar(ficha: dict, clave: str, ruta: Path) -> None:
    """Fija a mano dónde está el archivo (botón «Ubicar…»)."""
    ficha[clave] = str(ruta)
    ficha[f"{clave}_marcador"] = marcador(ruta)
    guardar(ficha)


def texto(ficha: dict):
    """El contenido del archivo del usuario, que es la transcripción de verdad."""
    ruta = ubicar(ficha)
    if ruta is None:
        return None
    try:
        return ruta.read_text(encoding="utf-8")
    except OSError:
        return None


def escribir_texto(ficha: dict, contenido: str) -> Path:
    """Sobrescribe tu archivo con el texto corregido en el editor."""
    ruta = ubicar(ficha)
    if ruta is None:
        raise FileNotFoundError(ficha.get("salida", ""))
    ruta.write_text(contenido.rstrip("\n") + "\n", encoding="utf-8")
    ficha["editado"] = time.time()
    guardar(ficha)
    return ruta


# --------------------------------------------------------------------- tiempos --
def guardar_palabras(id_ficha: str, palabras: list, personas=None) -> None:
    """Los tiempos por palabra, aparte: solo el editor los lee, y solo cuando hacen falta."""
    ficha = leer(id_ficha)
    _escribir(CARPETA / f"{id_ficha}.palabras.json", {
        "esquema": ESQUEMA,
        "palabras": [[p, round(t0, 3), round(t1, 3)] for p, t0, t1 in palabras],
        "quien": list(personas) if personas else [],
    })
    if ficha is not None:
        ficha["tiempos"] = True
        guardar(ficha)


def palabras(id_ficha: str):
    """[(palabra, inicio, fin, persona|None)] o None si este archivo no tiene tiempos."""
    datos = _leer(CARPETA / f"{id_ficha}.palabras.json")
    if not datos:
        return None
    quien = datos.get("quien") or []
    return [(p, t0, t1, quien[i] if i < len(quien) else None)
            for i, (p, t0, t1) in enumerate(datos.get("palabras", []))]


# -------------------------------------------------------------------- búsqueda --
def buscar(consulta: str, fichas=None) -> list[dict]:
    """Fichas cuyo nombre o texto contienen la consulta, con la línea donde aparece."""
    consulta = consulta.strip().lower()
    if not consulta:
        return list(fichas if fichas is not None else todas())
    salida = []
    for ficha in (fichas if fichas is not None else todas()):
        if consulta in ficha.get("nombre", "").lower():
            salida.append(dict(ficha, coincidencia=""))
            continue
        ruta = ubicar(ficha)
        if ruta is None:
            continue
        try:
            if ruta.stat().st_size > LIMITE_BUSQUEDA:
                contenido = ruta.read_text(encoding="utf-8", errors="ignore")[:LIMITE_BUSQUEDA]
            else:
                contenido = ruta.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        posicion = contenido.lower().find(consulta)
        if posicion >= 0:
            inicio = max(0, posicion - 40)
            trozo = contenido[inicio:posicion + len(consulta) + 60].replace("\n", " ").strip()
            salida.append(dict(ficha, coincidencia=f"…{trozo}…"))
    return salida
