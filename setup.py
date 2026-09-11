"""Construye Transcribir.app completa: lleva su propio Python, el motor y los recursos,
así que funciona en cualquier Mac con chip Apple sin instalar nada más.

Úsalo a través de scripts/construir.sh (y scripts/hacer-dmg.sh para compartirla).
"""

import sys
from pathlib import Path

from setuptools import setup

sys.path.insert(0, str(Path(__file__).resolve().parent / "transcribir"))
import identidad  # noqa: E402

MODULOS = ["agentes", "ajustes", "app", "audio", "avisos", "bienvenida", "cli", "formatos",
           "identidad", "interlocutores", "modelos", "motor", "preferencias", "recursos",
           "servidor", "ui", "vigia"]

setup(
    name=identidad.NOMBRE,
    app=["transcribir/principal.py"],
    data_files=["transcribir/glifo-on.png", "transcribir/glifo-off.png"],
    options={
        "py2app": {
            "iconfile": "transcribir/Transcribir.icns",
            "arch": "arm64",
            "includes": MODULOS,
            # paquetes con binarios o datos propios: se copian enteros, fuera del zip
            "packages": ["mlx_qwen3_asr", "numpy", "regex", "certifi", "huggingface_hub",
                         "httpx", "httpcore", "anyio", "h11", "idna",
                         "AVFoundation", "CoreMedia", "UserNotifications", "Quartz"],
            # mlx (sin __init__.py) y sherpa_onnx llevan librerías enlazadas con @rpath que
            # py2app no sabe reubicar: scripts/construir.sh los copia intactos después
            "excludes": ["mlx", "sherpa_onnx", "tkinter", "PySide6", "torch", "pyannote", "hf_xet",
                         "fastapi", "uvicorn",
                         # no se usan dentro de la app (Pillow solo genera el icono) y sus
                         # librerías de Homebrew no se dejan firmar
                         "PIL", "lzma", "_lzma"],
            "plist": {
                "CFBundleName": identidad.NOMBRE,
                "CFBundleDisplayName": identidad.NOMBRE,
                "CFBundleIdentifier": identidad.ID_APP,
                "CFBundleShortVersionString": identidad.VERSION,
                "CFBundleVersion": identidad.COMPILACION,
                "LSMinimumSystemVersion": "14.0",
                "LSArchitecturePriority": ["arm64"],
                "LSApplicationCategoryType": "public.app-category.productivity",
                "NSHighResolutionCapable": True,
                "NSHumanReadableCopyright": identidad.NOMBRE,
                "CFBundleDocumentTypes": [
                    {
                        "CFBundleTypeName": "Audio o video",
                        "CFBundleTypeRole": "Viewer",
                        "LSHandlerRank": "Alternate",
                        "LSItemContentTypes": [
                            "com.apple.m4a-audio",
                            "public.mpeg-4-audio",
                            "public.mpeg-4",
                            "public.mp3",
                            "com.microsoft.waveform-audio",
                            "com.apple.quicktime-movie",
                        ],
                    }
                ],
            },
        }
    },
)
