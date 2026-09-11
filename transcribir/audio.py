"""Lee audio y video con AVFoundation, el decodificador de macOS: sin ffmpeg."""

from pathlib import Path

import numpy as np
from AVFoundation import (
    AVAssetReader, AVAssetReaderTrackOutput, AVFormatIDKey, AVLinearPCMBitDepthKey,
    AVLinearPCMIsBigEndianKey, AVLinearPCMIsFloatKey, AVLinearPCMIsNonInterleaved,
    AVMediaTypeAudio, AVNumberOfChannelsKey, AVSampleRateKey, AVURLAsset,
)
from CoreMedia import CMBlockBufferCopyDataBytes, CMBlockBufferGetDataLength, CMSampleBufferGetDataBuffer
from Foundation import NSURL

MUESTREO = 16000                 # lo que espera Qwen3-ASR
PCM_LINEAL = 1819304813          # kAudioFormatLinearPCM ('lpcm')
LECTOR_FALLO = 3                 # AVAssetReaderStatusFailed


class AudioIlegible(Exception):
    """El archivo no se pudo leer o no tiene sonido; el mensaje ya es legible."""


def leer(ruta: Path) -> tuple[np.ndarray, float]:
    """Devuelve (muestras float32 mono a 16 kHz, duración en segundos).

    AVFoundation remuestrea y mezcla a un canal. Sirve igual para audio
    (m4a, mp3, wav) que para la pista de sonido de un video (mp4, mov).
    """
    asset = AVURLAsset.URLAssetWithURL_options_(NSURL.fileURLWithPath_(str(ruta)), None)
    pistas = asset.tracksWithMediaType_(AVMediaTypeAudio)
    if not pistas:
        raise AudioIlegible("El archivo no tiene pista de audio")
    lector, error = AVAssetReader.alloc().initWithAsset_error_(asset, None)
    if lector is None:
        raise AudioIlegible("No se pudo leer el archivo: está dañado o no es audio")
    salida = AVAssetReaderTrackOutput.assetReaderTrackOutputWithTrack_outputSettings_(pistas[0], {
        AVFormatIDKey: PCM_LINEAL,
        AVSampleRateKey: MUESTREO,
        AVNumberOfChannelsKey: 1,
        AVLinearPCMBitDepthKey: 32,
        AVLinearPCMIsFloatKey: True,
        AVLinearPCMIsBigEndianKey: False,
        AVLinearPCMIsNonInterleaved: False,
    })
    salida.setAlwaysCopiesSampleData_(False)
    lector.addOutput_(salida)
    if not lector.startReading():
        raise AudioIlegible("No se pudo leer el archivo: está dañado o no es audio")

    trozos = []
    while True:
        muestra = salida.copyNextSampleBuffer()
        if muestra is None:
            break
        bloque = CMSampleBufferGetDataBuffer(muestra)
        if bloque is None:
            continue
        largo = CMBlockBufferGetDataLength(bloque)
        estado, datos = CMBlockBufferCopyDataBytes(bloque, 0, largo, None)
        if estado == 0 and datos:
            trozos.append(bytes(datos))
    if lector.status() == LECTOR_FALLO:
        raise AudioIlegible("No se pudo leer el archivo: está dañado o no es audio")

    muestras = np.frombuffer(b"".join(trozos), dtype=np.float32).copy()
    if not len(muestras):
        raise AudioIlegible("El archivo no tiene sonido")
    return muestras, len(muestras) / MUESTREO
