"""Las carpetas que merece la pena vigilar, sin que tengas que buscarlas.

Las apps de Apple guardan sus grabaciones en sitios poco amables —contenedores
con nombres de dominio y carpetas con UUID—, pero son justo las que interesan:
lo que grabas con el iPhone aparece ahí solo, por iCloud.
"""

from pathlib import Path

CASA = Path.home()
GRUPOS = CASA / "Library" / "Group Containers"

# clave: (nombre, carpeta, si hay que mirar dentro de subcarpetas, explicación)
CONOCIDAS = {
    "notas_voz": (
        "Notas de voz",
        GRUPOS / "group.com.apple.VoiceMemos.shared" / "Recordings",
        False,
        "Lo que grabas con Notas de Voz, también desde el iPhone o el Apple Watch.",
    ),
    "notas": (
        "Notas",
        GRUPOS / "group.com.apple.notes" / "Accounts",
        True,
        "Los audios que grabas dentro de una nota de la app Notas.",
    ),
    "descargas": (
        "Descargas", CASA / "Downloads", False,
        "Lo que descargas del navegador o te pasan por AirDrop.",
    ),
    "escritorio": (
        "Escritorio", CASA / "Desktop", False,
        "Lo que dejas a mano en el escritorio.",
    ),
}


def disponibles() -> list[tuple[str, str, Path, bool, str]]:
    """Las que existen en este Mac, en orden."""
    return [(clave, nombre, ruta, hondo, nota)
            for clave, (nombre, ruta, hondo, nota) in CONOCIDAS.items() if ruta.is_dir()]


def como_se_llama(carpeta) -> str:
    """El nombre bonito de una carpeta, si es una de las conocidas."""
    ruta = Path(carpeta)
    for nombre, conocida, _, _ in CONOCIDAS.values():
        if ruta == conocida:
            return nombre
    return ruta.name


def hay_que_hondear(carpeta) -> bool:
    """True si esa carpeta guarda los audios dentro de subcarpetas."""
    ruta = Path(carpeta)
    return any(ruta == conocida and hondo for _, conocida, hondo, _ in CONOCIDAS.values())
