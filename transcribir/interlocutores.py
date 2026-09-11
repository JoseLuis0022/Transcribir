"""Separar por persona: quién habla cuándo, con Sherpa-ONNX (sin internet ni cuentas).

Segmentación de pyannote 3.0 y huellas de voz WeSpeaker ResNet34, ambas en ONNX.
"""

from pathlib import Path

SEGMENTACION = "model.onnx"
VOCES = "wespeaker_en_voxceleb_resnet34_LM.onnx"
# Distancia entre huellas de voz para darlas por la misma persona. El 0,5 que sugiere
# Sherpa juntaba dos voces distintas; con 0,30-0,35 separa bien un diálogo y no parte
# en dos a quien habla solo, así que va en medio de ese rango.
UMBRAL = 0.33


def turnos(muestras, carpeta_segmentacion: Path, carpeta_voces: Path, revisar=None) -> list[tuple[float, float, int]]:
    """Devuelve [(inicio, fin, persona)] en orden de tiempo; `persona` es un índice.

    `revisar()` se llama mientras avanza y puede lanzar una excepción para cancelar.
    """
    import sherpa_onnx

    config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
            pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(
                model=str(carpeta_segmentacion / SEGMENTACION))),
        embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(carpeta_voces / VOCES)),
        clustering=sherpa_onnx.FastClusteringConfig(num_clusters=-1, threshold=UMBRAL),
        min_duration_on=0.3,
        min_duration_off=0.5,
    )
    if not config.validate():
        raise RuntimeError("No se pudo preparar la separación por persona")
    diarizador = sherpa_onnx.OfflineSpeakerDiarization(config)
    cancelado = []

    def avance(hechos, total):
        try:
            if revisar is not None:
                revisar()
        except Exception as e:           # se relanza fuera del código nativo
            cancelado.append(e)
            return 1                     # distinto de 0: que Sherpa se detenga
        return 0

    resultado = diarizador.process(muestras, callback=avance)
    if cancelado:
        raise cancelado[0]
    return [(s.start, s.end, s.speaker) for s in resultado.sort_by_start_time()]
