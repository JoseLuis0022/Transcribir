"""Separar por persona: quién habla cuándo, con Sherpa-ONNX (sin internet ni cuentas).

Segmentación de pyannote 3.0 y huellas de voz WeSpeaker ResNet34, ambas en ONNX.

Corre en un proceso aparte (la propia app lanzada con `--separar`): Sherpa no
suelta el intérprete de Python mientras trabaja y, en el mismo proceso, dejaba
la ventana sin responder hasta 17 segundos seguidos.
"""

import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

SEGMENTACION = "model.onnx"
VOCES = "wespeaker_en_voxceleb_resnet34_LM.onnx"
# Distancia entre huellas de voz para darlas por la misma persona. El 0,5 que sugiere
# Sherpa juntaba dos voces distintas; con 0,30-0,35 separa bien un diálogo y no parte
# en dos a quien habla solo, así que va en medio de ese rango.
UMBRAL = 0.33
HILOS = max(1, min(8, (os.cpu_count() or 4) - 2))    # Sherpa usa un solo núcleo si no se le dice


def _ejecutable() -> list[str]:
    """Cómo lanzar el proceso aparte: la propia app, o el Python del proyecto en desarrollo."""
    import recursos

    app = recursos.app()
    if app is not None:
        return [str(app / "Contents" / "MacOS" / "Transcribir")]
    return [sys.executable, str(Path(__file__).resolve().parent / "principal.py")]


def turnos(muestras, carpeta_segmentacion: Path, carpeta_voces: Path, revisar=None,
           al_avanzar=None, cuantas=None) -> list[tuple[float, float, int]]:
    """Devuelve [(inicio, fin, persona)] en orden de tiempo; `persona` es un índice.

    `cuantas` es la pista de cuántas personas hablan: si la sabes, se agrupan las
    voces en ese número exacto y se acierta mucho más que dejándolo a ojo.
    `al_avanzar(fraccion)` recibe el avance; `revisar()` puede lanzar una excepción
    para cancelar, y entonces se detiene el proceso aparte.
    """
    import numpy as np

    with tempfile.TemporaryDirectory() as carpeta:
        audio = Path(carpeta) / "audio.npy"
        np.save(audio, np.asarray(muestras, dtype=np.float32))
        errores = open(Path(carpeta) / "errores.txt", "w+")
        proceso = subprocess.Popen(
            _ejecutable() + ["--separar", str(audio), str(carpeta_segmentacion / SEGMENTACION),
                             str(carpeta_voces / VOCES), str(cuantas or 0)],
            stdout=subprocess.PIPE, stderr=errores, text=True)
        lineas: queue.Queue = queue.Queue()

        def leer():
            for linea in proceso.stdout:
                lineas.put(linea)
            lineas.put(None)

        threading.Thread(target=leer, daemon=True).start()
        resultado = None
        try:
            while True:
                if revisar is not None:
                    revisar()
                try:
                    linea = lineas.get(timeout=0.5)
                except queue.Empty:
                    continue
                if linea is None:
                    break
                tipo, _, dato = linea.strip().partition(" ")
                if tipo == "avance" and al_avanzar is not None:
                    al_avanzar(float(dato))
                elif tipo == "turnos":
                    resultado = json.loads(dato)
        except BaseException:
            proceso.kill()
            proceso.wait()
            raise
        proceso.wait()
        if resultado is None:
            errores.seek(0)
            ultimas = errores.read().strip().splitlines()
            raise RuntimeError("No se pudo separar por persona" + (f": {ultimas[-1][:120]}" if ultimas else ""))
        return [(float(a), float(b), int(p)) for a, b, p in resultado]


def proceso(argumentos: list[str]) -> int:
    """Lo que corre en el proceso aparte: `--separar audio.npy segmentacion.onnx voces.onnx [n]`.

    `n` es cuántas personas hablan, si se sabe; 0 deja que lo decida el agrupador.
    Escribe `avance 0.42` mientras trabaja y, al final, `turnos [[inicio, fin, persona], …]`.
    """
    import numpy as np
    import sherpa_onnx

    audio, segmentacion, voces = argumentos[:3]
    cuantas = int(argumentos[3]) if len(argumentos) > 3 else 0
    config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
            pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(model=segmentacion),
            num_threads=HILOS),
        embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=voces, num_threads=HILOS),
        # con el número de personas se agrupa en ese número exacto y el umbral no
        # pinta nada; sin él, el agrupador decide, y ahí es donde se equivoca
        clustering=sherpa_onnx.FastClusteringConfig(
            num_clusters=cuantas if cuantas > 1 else -1,
            threshold=UMBRAL),
        min_duration_on=0.3,
        min_duration_off=0.5,
    )
    if not config.validate():
        print("configuración de Sherpa inválida", file=sys.stderr)
        return 1

    def avance(hechos, total):
        print(f"avance {hechos / total if total else 0.0:.3f}", flush=True)
        return 0

    resultado = sherpa_onnx.OfflineSpeakerDiarization(config).process(np.load(audio), callback=avance)
    print("turnos " + json.dumps([(s.start, s.end, s.speaker) for s in resultado.sort_by_start_time()]),
          flush=True)
    return 0
