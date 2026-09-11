"""Construye Transcribir.app (modo enlazado: usa el código, el entorno y el modelo de esta carpeta).

Úsalo a través de scripts/construir.sh, que además genera el icono y coloca la app.
"""

from setuptools import setup

setup(
    name="Transcribir",
    app=["transcribir/app.py"],
    options={
        "py2app": {
            "iconfile": "transcribir/Transcribir.icns",
            "plist": {
                "CFBundleName": "Transcribir",
                "CFBundleDisplayName": "Transcribir",
                "CFBundleIdentifier": "local.transcribir",
                "CFBundleShortVersionString": "1.0",
                "LSMinimumSystemVersion": "14.0",
                "NSHighResolutionCapable": True,
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
