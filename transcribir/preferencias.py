"""Preferencias de Transcribir: una sola lista de claves, valores por defecto y opciones.

La app es la única que las escribe; el comando `transcribir` las cambia a través de ella.
"""

from pathlib import Path

from Foundation import NSBundle, NSUserDefaults

from identidad import ID_ANTERIOR, ID_APP

ESCRITORIO = Path.home() / "Desktop"

IDIOMA, PRECISION, VOCABULARIO = "idioma", "precision", "vocabulario"
FORMATO, GUARDAR, CARPETA, AL_TERMINAR = "formato", "guardar", "carpeta", "al_terminar"
PERSONAS, TIEMPOS, RESALTADO = "personas", "tiempos", "resaltado"
TAMANO, PANEL, FUERZA = "tamano_texto", "panel_editor", "fuerza_resaltado"
CERRADOS = "apartados_cerrados"
VIGILAR, CARPETA_VIGILADA = "vigilar", "carpeta_vigilada"
AVISO_CADA, AVISO_COLA, AVISO_ERRORES, AVISO_SONIDO = (
    "avisos_cada_archivo", "avisos_cola", "avisos_errores", "avisos_sonido")

# clave: (valor por defecto, opciones válidas | bool | str)
ESQUEMA = {
    IDIOMA: ("es", ("es", "en", "auto")),
    PRECISION: ("alta", ("alta", "rapida")),
    VOCABULARIO: ("", str),
    FORMATO: ("parrafos", ("parrafos", "tiempos", "srt")),
    PERSONAS: (False, bool),
    TIEMPOS: (False, bool),
    RESALTADO: ("palabra", ("palabra", "fondo")),
    FUERZA: ("fuerte", ("suave", "media", "fuerte")),
    TAMANO: ("15", ("13", "14", "15", "16", "17", "18", "20")),
    PANEL: (True, bool),
    CERRADOS: ("", str),
    GUARDAR: ("carpeta", ("carpeta", "junto")),
    CARPETA: (str(ESCRITORIO), str),
    AL_TERMINAR: ("nada", ("nada", "finder", "abrir")),
    VIGILAR: (False, bool),
    CARPETA_VIGILADA: ("", str),
    AVISO_CADA: (False, bool),
    AVISO_COLA: (True, bool),
    AVISO_ERRORES: (True, bool),
    AVISO_SONIDO: (True, bool),
}

# Opciones de cada trabajo (un agente puede cambiarlas solo para su petición).
DEL_TRABAJO = (IDIOMA, PRECISION, VOCABULARIO, FORMATO, PERSONAS, TIEMPOS, GUARDAR, CARPETA)

ETIQUETAS = {
    IDIOMA: {"es": "Español", "en": "Inglés", "auto": "Detectar automáticamente"},
    PRECISION: {"alta": "Máxima precisión (1.7B)", "rapida": "Rápida (0.6B)"},
    FORMATO: {"parrafos": "Párrafos", "tiempos": "Con marcas de tiempo", "srt": "Subtítulos (.srt)"},
    RESALTADO: {"palabra": "La palabra en negrita", "fondo": "Fondo suave"},
    FUERZA: {"suave": "Suave", "media": "Media", "fuerte": "Fuerte"},
    TAMANO: {t: f"{t} pt" for t in ("13", "14", "15", "16", "17", "18", "20")},
    GUARDAR: {"carpeta": "En la carpeta elegida", "junto": "Junto al archivo original"},
    AL_TERMINAR: {"nada": "No hacer nada", "finder": "Mostrar en Finder", "abrir": "Abrir la transcripción"},
}

# Claves de la primera versión, que se migran una sola vez.
ANTIGUAS = {"carpetaSalida": CARPETA, "avisarCadaArchivo": AVISO_CADA, "avisarCola": AVISO_COLA,
            "avisarErrores": AVISO_ERRORES, "avisarConSonido": AVISO_SONIDO}


def _d():
    return NSUserDefaults.standardUserDefaults()


def en_app() -> bool:
    """True dentro de Transcribir.app (notificaciones y servidor solo existen ahí)."""
    return NSBundle.mainBundle().bundleIdentifier() == ID_APP


BIENVENIDA, HEREDADOS = "bienvenidaHecha", "ajustesHeredados"


def registrar() -> None:
    d = _d()
    if en_app() and not d.boolForKey_(HEREDADOS):
        # una sola vez: los ajustes de la versión de desarrollo, que tenía otro identificador
        anterior = NSUserDefaults.alloc().initWithSuiteName_(ID_ANTERIOR)
        heredados = 0
        for clave in list(ESQUEMA) + list(ANTIGUAS):
            valor = anterior.objectForKey_(clave)
            if valor is not None and d.objectForKey_(clave) is None:
                d.setObject_forKey_(valor, clave)
                heredados += 1
        if heredados:
            d.setBool_forKey_(True, BIENVENIDA)          # ya la usaba: sin bienvenida
        d.setBool_forKey_(True, HEREDADOS)
    for vieja, nueva in ANTIGUAS.items():
        valor = d.objectForKey_(vieja)
        if valor is not None:
            if d.objectForKey_(nueva) is None:
                d.setObject_forKey_(valor, nueva)
            d.removeObjectForKey_(vieja)
    d.registerDefaults_({k: v[0] for k, v in ESQUEMA.items()})


def bienvenida_hecha() -> bool:
    return bool(_d().boolForKey_(BIENVENIDA))


def marcar_bienvenida() -> None:
    _d().setBool_forKey_(True, BIENVENIDA)


def leer(clave):
    defecto, tipo = ESQUEMA[clave]
    if tipo is bool:
        return bool(_d().boolForKey_(clave))
    valor = _d().stringForKey_(clave)
    return str(valor) if valor is not None else defecto


def todas() -> dict:
    return {clave: leer(clave) for clave in ESQUEMA}


def opciones_validas() -> dict:
    return {clave: list(tipo) if isinstance(tipo, tuple) else ("si|no" if tipo is bool else "texto")
            for clave, (_, tipo) in ESQUEMA.items()}


def validar(clave, valor):
    """Devuelve el valor normalizado o lanza ValueError con un mensaje legible."""
    if clave not in ESQUEMA:
        raise ValueError(f"Ajuste desconocido: {clave}. Válidos: {', '.join(ESQUEMA)}")
    _, tipo = ESQUEMA[clave]
    if tipo is bool:
        if isinstance(valor, bool):
            return valor
        texto = str(valor).strip().lower()
        if texto in ("si", "sí", "true", "1", "on"):
            return True
        if texto in ("no", "false", "0", "off"):
            return False
        raise ValueError(f"{clave} acepta: si, no")
    if isinstance(tipo, tuple):
        texto = str(valor).strip().lower()
        if texto not in tipo:
            raise ValueError(f"{clave} acepta: {', '.join(tipo)}")
        return texto
    texto = str(valor).strip()
    if clave in (CARPETA, CARPETA_VIGILADA) and texto:
        ruta = Path(texto).expanduser()
        if not ruta.is_dir():
            raise ValueError(f"No existe la carpeta: {ruta}")
        return str(ruta.resolve())
    return texto


def escribir(clave, valor):
    valor = validar(clave, valor)
    if isinstance(valor, bool):
        _d().setBool_forKey_(valor, clave)
    else:
        _d().setObject_forKey_(valor, clave)
    return valor
