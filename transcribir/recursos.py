"""Dónde están los recursos: dentro de Transcribir.app o junto al código en desarrollo."""

from pathlib import Path

from Foundation import NSBundle

from identidad import ID_APP


def empaquetada() -> bool:
    return NSBundle.mainBundle().bundleIdentifier() == ID_APP


def ruta(nombre: str) -> Path:
    if empaquetada():
        return Path(NSBundle.mainBundle().resourcePath()) / nombre
    return Path(__file__).resolve().parent / nombre


def app() -> Path | None:
    """La Transcribir.app que está corriendo (None en desarrollo)."""
    return Path(NSBundle.mainBundle().bundlePath()) if empaquetada() else None
