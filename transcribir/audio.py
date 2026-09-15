"""Lee audio y video con AVFoundation, el decodificador de macOS: sin ffmpeg."""

import math
from pathlib import Path

import numpy as np
from AVFoundation import (
    AVAssetReader, AVAssetReaderTrackOutput, AVFormatIDKey, AVLinearPCMBitDepthKey,
    AVLinearPCMIsBigEndianKey, AVLinearPCMIsFloatKey, AVLinearPCMIsNonInterleaved,
    AVMediaTypeAudio, AVNumberOfChannelsKey, AVSampleRateKey, AVURLAsset,
)
from CoreMedia import (
    CMAudioFormatDescriptionGetStreamBasicDescription, CMBlockBufferCopyDataBytes,
    CMBlockBufferGetDataLength, CMSampleBufferGetDataBuffer, CMSampleBufferGetPresentationTimeStamp,
    CMTimeGetSeconds, CMTimeMakeWithSeconds, CMTimeRangeMake, kCMTimePositiveInfinity,
)
from Foundation import NSURL

MUESTREO = 16000                 # lo que espera Qwen3-ASR
PCM_LINEAL = 1819304813          # kAudioFormatLinearPCM ('lpcm')
LECTOR_FALLO = 3                 # AVAssetReaderStatusFailed
SIN_DATOS = -11880               # AVErrorInvalidSampleCursor: ahí ya no hay muestras
MUESTRAS_POR_PAQUETE = 1024      # un paquete AAC; para otros formatos es solo un paso razonable
HUECO_MAXIMO = 0.02              # más de un 2 % sin poder decodificar: el archivo sí está mal
HUECO_TOLERADO = 5.0             # segundos que se aceptan siempre, aunque el audio sea corto

AJUSTES = {
    AVFormatIDKey: PCM_LINEAL,
    AVSampleRateKey: MUESTREO,
    AVNumberOfChannelsKey: 1,
    AVLinearPCMBitDepthKey: 32,
    AVLinearPCMIsFloatKey: True,
    AVLinearPCMIsBigEndianKey: False,
    AVLinearPCMIsNonInterleaved: False,
}


class AudioIlegible(Exception):
    """El archivo no se pudo leer o no tiene sonido; el mensaje ya es legible."""


class _LectorFallido(Exception):
    """AVFoundation dejó de decodificar: (su NSError, hasta qué muestra llegó, código)."""


def leer(ruta: Path) -> tuple[np.ndarray, float, float]:
    """Devuelve (muestras float32 mono a 16 kHz, duración en segundos, segundos que faltan).

    AVFoundation remuestrea y mezcla a un canal. Sirve igual para audio
    (m4a, mp3, wav) que para la pista de sonido de un video (mp4, mov).

    El decodificador AAC de macOS se detiene con paramErr (-50) en los paquetes
    de 4 bytes que dejan Zoom y compañía cuando el micrófono está apagado,
    aunque el archivo esté sano. Cuando pasa, se vuelve a leer desde un paquete
    más adelante y lo saltado queda en silencio, que es lo que había: así las
    marcas de tiempo siguen cuadrando con el video.

    Si el archivo está cortado (la cabecera promete más de lo que hay, como
    una descarga que no terminó), se devuelve lo que sí se pudo leer y cuánto
    falta para lo que dice durar; en un archivo completo, eso último es 0.
    """
    asset = AVURLAsset.URLAssetWithURL_options_(NSURL.fileURLWithPath_(str(ruta)), None)
    pistas = asset.tracksWithMediaType_(AVMediaTypeAudio)
    if not pistas:
        raise AudioIlegible("El archivo no tiene pista de audio")
    pista = pistas[0]
    rango = pista.timeRange()
    inicio_pista = CMTimeGetSeconds(rango.start)
    fin_pista = inicio_pista + CMTimeGetSeconds(rango.duration)
    if not math.isfinite(fin_pista) or fin_pista <= inicio_pista:
        raise AudioIlegible("No se pudo leer el archivo: está dañado o no es audio")
    paso = MUESTRAS_POR_PAQUETE / _muestreo_original(pista)

    # un segundo de holgura: la duración de la pista viene redondeada; lo que sobra se recorta
    muestras = np.zeros(math.ceil((fin_pista - inicio_pista) * MUESTREO) + MUESTREO, dtype=np.float32)
    escrito = 0                      # hasta dónde llega el audio decodificado, en muestras
    saltado = 0.0
    desde = inicio_pista
    cortado = False
    while True:
        try:
            escrito = max(escrito, _decodificar(asset, pista, desde, inicio_pista, muestras))
            break
        except _LectorFallido as error:
            _, llegada, codigo = error.args
            if codigo == SIN_DATOS and not llegada and escrito:
                cortado = True           # archivo cortado: se acabó lo que había
                break
            escrito = max(escrito, llegada)
            siguiente = max(desde, inicio_pista + escrito / MUESTREO) + paso
            saltado += paso
            if siguiente >= fin_pista:
                break
            if saltado > max(HUECO_TOLERADO, HUECO_MAXIMO * (fin_pista - inicio_pista)):
                raise AudioIlegible("No se pudo leer el archivo: está dañado o no es audio") from error
            desde = siguiente

    if not escrito:
        raise AudioIlegible("El archivo no tiene sonido")
    faltan = max(0.0, fin_pista - inicio_pista - escrito / MUESTREO) if cortado else 0.0
    return muestras[:escrito], escrito / MUESTREO, faltan


def _muestreo_original(pista) -> float:
    try:
        formato = CMAudioFormatDescriptionGetStreamBasicDescription(pista.formatDescriptions()[0])
        if formato is not None and formato.mSampleRate > 0:
            return formato.mSampleRate
    except (IndexError, TypeError):
        pass
    return 44100.0


def _decodificar(asset, pista, desde: float, origen: float, destino: np.ndarray) -> int:
    """Escribe en `destino`, en su sitio según el tiempo, lo que haya de `desde` al final.

    Devuelve hasta qué muestra llegó; si el lector falla, lanza _LectorFallido
    con ese mismo dato.
    """
    lector, _ = AVAssetReader.alloc().initWithAsset_error_(asset, None)
    if lector is None:
        raise AudioIlegible("No se pudo leer el archivo: está dañado o no es audio")
    if desde > origen:               # abierto hasta el final: la duración viene redondeada
        lector.setTimeRange_(CMTimeRangeMake(CMTimeMakeWithSeconds(desde, MUESTREO), kCMTimePositiveInfinity))
    salida = AVAssetReaderTrackOutput.assetReaderTrackOutputWithTrack_outputSettings_(pista, AJUSTES)
    salida.setAlwaysCopiesSampleData_(False)
    lector.addOutput_(salida)
    if not lector.startReading():
        raise _LectorFallido(*_fallo(lector, 0))

    llegada = 0
    while True:
        muestra = salida.copyNextSampleBuffer()
        if muestra is None:
            break
        bloque = CMSampleBufferGetDataBuffer(muestra)
        if bloque is None:
            continue
        largo = CMBlockBufferGetDataLength(bloque)
        estado, datos = CMBlockBufferCopyDataBytes(bloque, 0, largo, None)
        if estado != 0 or not datos:
            continue
        trozo = np.frombuffer(datos, dtype=np.float32)
        tiempo = CMTimeGetSeconds(CMSampleBufferGetPresentationTimeStamp(muestra)) - origen
        pos = max(0, round(tiempo * MUESTREO))
        cabe = min(len(trozo), len(destino) - pos)
        if cabe > 0:
            destino[pos:pos + cabe] = trozo[:cabe]
            llegada = max(llegada, pos + cabe)
    if lector.status() == LECTOR_FALLO:
        raise _LectorFallido(*_fallo(lector, llegada))
    return llegada


def _fallo(lector, llegada: int) -> tuple[str, int, int]:
    error = lector.error()
    return str(error), llegada, error.code() if error is not None else 0
