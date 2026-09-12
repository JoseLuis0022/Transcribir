"""Los nombres de las notas de voz de Apple, que no están en el nombre del archivo.

Notas de Voz guarda los audios como «20260911 193602.m4a» y el nombre que tú le
pones va aparte, en su base de datos. Aquí se lee (solo lectura) para que la
transcripción se llame igual que la nota, y para enterarse si luego la renombras.
"""

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

CARPETA = (Path.home() / "Library" / "Group Containers"
           / "group.com.apple.VoiceMemos.shared" / "Recordings")
BASE = CARPETA / "CloudRecordings.db"
SIN_NOMBRE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):\d{2}Z?$")  # la fecha que pone Apple
# dónde busca Apple el nombre, de lo más fiel a lo que menos: el título es el que
# cambia al renombrar; la etiqueta se queda con la fecha de cuando se grabó
COLUMNAS = ("ZENCRYPTEDTITLE", "ZCUSTOMLABELFORSORTING", "ZCUSTOMLABEL")
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
    """Si la nota no tiene nombre puesto, Apple deja la fecha en ISO: se hace legible.

    Esa fecha viene en horario universal, así que se pasa a la hora de aquí: una
    nota de las dos de la madrugada no puede llamarse «08.13».
    """
    marca = SIN_NOMBRE.match(etiqueta)
    if marca is None:
        return limpio(etiqueta)
    ano, mes, dia, hora, minuto = (int(g) for g in marca.groups())
    cuando = datetime(ano, mes, dia, hora, minuto, tzinfo=timezone.utc).astimezone()
    return limpio(f"Nota de voz {cuando.day} {MESES[cuando.month - 1]} {cuando.year}, "
                  f"{cuando:%H.%M}")


def titulos() -> dict[str, str]:
    """{nombre de archivo: cómo se llama la nota}. Vacío si no se puede leer."""
    if not BASE.exists():
        return {}
    try:
        con = sqlite3.connect(f"file:{BASE}?mode=ro", uri=True, timeout=1.0)
        try:
            hay = {fila[1] for fila in con.execute("pragma table_info(ZCLOUDRECORDING)")}
            columnas = [c for c in COLUMNAS if c in hay]
            if not columnas:
                return {}
            filas = con.execute(
                f"select ZPATH, {', '.join(columnas)} from ZCLOUDRECORDING "
                "where ZPATH is not null").fetchall()
        finally:
            con.close()
    except sqlite3.Error:
        return {}
    salida = {}
    for fila in filas:
        nombre = next((str(v).strip() for v in fila[1:] if isinstance(v, str) and v.strip()), "")
        if nombre:
            salida[Path(str(fila[0])).name] = _bonito(nombre)
    return salida


def titulo(ruta) -> str | None:
    """Cómo se llama esa nota de voz, o None si no es una o no se pudo leer."""
    ruta = Path(ruta)
    if not es_nota_de_voz(ruta):
        return None
    return titulos().get(ruta.name)
