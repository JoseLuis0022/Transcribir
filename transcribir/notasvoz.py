"""Los nombres de las notas de voz de Apple, que no están en el nombre del archivo.

Notas de Voz guarda los audios como «20260911 193602.m4a» y el nombre que tú le
pones va aparte, en su base de datos. Aquí se lee (solo lectura) para que la
transcripción se llame igual que la nota, y para enterarse si luego la renombras.
"""

import re
import sqlite3
from pathlib import Path

CARPETA = (Path.home() / "Library" / "Group Containers"
           / "group.com.apple.VoiceMemos.shared" / "Recordings")
BASE = CARPETA / "CloudRecordings.db"
SIN_NOMBRE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z?$")   # la fecha que pone Apple
MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sept", "oct", "nov", "dic")
PROHIBIDOS = str.maketrans({"/": "-", ":": ".", "\n": " ", "\r": " "})


def es_nota_de_voz(ruta) -> bool:
    try:
        return Path(ruta).parent == CARPETA
    except (OSError, ValueError):
        return False


def limpio(titulo: str) -> str:
    """Un nombre que sirva como nombre de archivo."""
    return " ".join(titulo.translate(PROHIBIDOS).split())[:120].strip(" .") or "Nota de voz"


def _bonito(etiqueta: str) -> str:
    """Si la nota no tiene nombre puesto, Apple deja la fecha en ISO: se hace legible."""
    if not SIN_NOMBRE.match(etiqueta):
        return limpio(etiqueta)
    dia = f"{int(etiqueta[8:10])} {MESES[int(etiqueta[5:7]) - 1]} {etiqueta[0:4]}"
    return limpio(f"Nota de voz {dia}, {etiqueta[11:13]}.{etiqueta[14:16]}")


def titulos() -> dict[str, str]:
    """{nombre de archivo: cómo se llama la nota}. Vacío si no se puede leer."""
    if not BASE.exists():
        return {}
    try:
        con = sqlite3.connect(f"file:{BASE}?mode=ro", uri=True, timeout=1.0)
        try:
            filas = con.execute(
                "select ZPATH, ZCUSTOMLABEL from ZCLOUDRECORDING where ZPATH is not null").fetchall()
        finally:
            con.close()
    except sqlite3.Error:
        return {}
    salida = {}
    for ruta, etiqueta in filas:
        if etiqueta:
            salida[Path(str(ruta)).name] = _bonito(str(etiqueta))
    return salida


def titulo(ruta) -> str | None:
    """Cómo se llama esa nota de voz, o None si no es una o no se pudo leer."""
    ruta = Path(ruta)
    if not es_nota_de_voz(ruta):
        return None
    return titulos().get(ruta.name)
