"""Exportar una transcripción a PDF o a Word, sin salir de la app.

El texto sigue siendo el de tu archivo: aquí solo se le da forma de documento
(título, fecha y los nombres de quien habla en negrita) con AppKit, que ya trae
macOS. No hace falta ninguna biblioteca de más.
"""

import time
from pathlib import Path

from AppKit import (
    NSColor, NSDocumentTypeDocumentAttribute, NSFont, NSMutableParagraphStyle,
    NSOfficeOpenXMLTextDocumentType, NSPrintInfo, NSPrintJobDisposition, NSPrintJobSavingURL,
    NSPrintOperation, NSPrintSaveJob, NSTextView,
)
from Foundation import NSURL, NSMakeRange, NSMakeRect, NSMutableAttributedString

import biblioteca
import formatos

FORMATOS = {"pdf": ".pdf", "word": ".docx", "docx": ".docx"}

PAGINA = (612.0, 792.0)          # carta, en puntos
MARGEN = 64.0
MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre")


class ErrorExportar(Exception):
    """No se pudo escribir el documento; el mensaje ya es legible."""


def fecha_larga(cuando: float) -> str:
    t = time.localtime(cuando or time.time())
    return f"{t.tm_mday} de {MESES[t.tm_mon - 1]} de {t.tm_year}"


def _parrafo(espacio_despues=9.0, interlineado=4.0):
    p = NSMutableParagraphStyle.alloc().init()
    p.setParagraphSpacing_(espacio_despues)
    p.setLineSpacing_(interlineado)
    return p


def documento(ficha: dict, contenido: str):
    """El texto con forma de documento: título, fecha y quien habla en negrita."""
    texto = NSMutableAttributedString.alloc().init()

    def poner(cadena, tamano, peso, color, parrafo):
        texto.appendAttributedString_(NSMutableAttributedString.alloc().initWithString_attributes_(
            cadena, {"NSFont": NSFont.systemFontOfSize_weight_(tamano, peso),
                     "NSColor": color, "NSParagraphStyle": parrafo}))

    poner(f"{Path(ficha.get('nombre', 'Transcripción')).stem}\n", 20.0, 0.3,
          NSColor.blackColor(), _parrafo(4.0, 0.0))
    detalle = (f"{formatos.duracion_corta(ficha.get('duracion') or 0)} de audio"
               f" · {fecha_larga(ficha.get('creado'))}")
    poner(f"{detalle}\n\n", 10.0, 0.0, NSColor.grayColor(), _parrafo(14.0, 0.0))

    nombres = list((ficha.get("personas") or {}).values())
    cuerpo = _parrafo()
    for linea in contenido.rstrip("\n").split("\n"):
        if not linea.strip():
            continue
        inicio = texto.length()
        poner(f"{linea}\n", 11.5, 0.0, NSColor.blackColor(), cuerpo)
        marca = formatos.MARCA.match(linea)
        if marca:                                  # «[02:15]» pequeño y gris
            texto.addAttributes_range_(
                {"NSFont": NSFont.systemFontOfSize_(9.5), "NSColor": NSColor.grayColor()},
                NSMakeRange(inicio, marca.end()))
        quien = _quien(linea[marca.end() if marca else 0:], nombres)
        if quien:
            texto.addAttributes_range_(
                {"NSFont": NSFont.systemFontOfSize_weight_(11.5, 0.3)},
                NSMakeRange(inicio + (marca.end() if marca else 0), quien))
    return texto


def _quien(linea: str, nombres) -> int:
    """Cuántos caracteres ocupa el «Ana:» del principio de la línea, si lo hay."""
    encontrado = formatos.QUIEN.match(linea)
    if encontrado:
        return len(encontrado.group().rstrip())
    for nombre in nombres:
        if nombre.strip() and linea.startswith(f"{nombre}:"):
            return len(nombre) + 1
    return 0


def a_word(texto, destino: Path) -> None:
    datos = texto.dataFromRange_documentAttributes_error_(
        NSMakeRange(0, texto.length()),
        {NSDocumentTypeDocumentAttribute: NSOfficeOpenXMLTextDocumentType}, None)
    if isinstance(datos, tuple):
        datos = datos[0]
    if datos is None or not datos.writeToFile_atomically_(str(destino), True):
        raise ErrorExportar("No se pudo escribir el documento de Word")


def a_pdf(texto, destino: Path) -> None:
    """Se imprime a PDF con el mismo motor que usa cualquier app de macOS."""
    ancho = PAGINA[0] - MARGEN * 2
    vista = NSTextView.alloc().initWithFrame_(NSMakeRect(0, 0, ancho, PAGINA[1]))
    vista.textContainer().setLineFragmentPadding_(0.0)
    vista.textStorage().setAttributedString_(texto)
    vista.setBackgroundColor_(NSColor.whiteColor())
    # a la medida del texto: si no, sobra una página en blanco al final
    vista.layoutManager().ensureLayoutForTextContainer_(vista.textContainer())
    alto = vista.layoutManager().usedRectForTextContainer_(vista.textContainer()).size.height
    vista.setFrameSize_((ancho, max(alto + 2, 10.0)))

    info = NSPrintInfo.sharedPrintInfo().copy()
    info.setPaperSize_(PAGINA)
    info.setTopMargin_(MARGEN)
    info.setBottomMargin_(MARGEN)
    info.setLeftMargin_(MARGEN)
    info.setRightMargin_(MARGEN)
    info.setHorizontalPagination_(0)              # ajustar al ancho
    info.dictionary()[NSPrintJobDisposition] = NSPrintSaveJob
    info.dictionary()[NSPrintJobSavingURL] = NSURL.fileURLWithPath_(str(destino))

    operacion = NSPrintOperation.printOperationWithView_printInfo_(vista, info)
    operacion.setShowsPrintPanel_(False)
    operacion.setShowsProgressPanel_(False)
    if not operacion.runOperation():
        raise ErrorExportar("No se pudo crear el PDF")


def exportar(ficha: dict, formato: str, destino: Path) -> Path:
    """Escribe la transcripción en `destino` con el formato pedido."""
    if formato not in FORMATOS:
        raise ErrorExportar(f"Formato desconocido: {formato}. Válidos: pdf, word")
    contenido = biblioteca.texto(ficha)
    if contenido is None:
        raise ErrorExportar("No se encontró el archivo de esa transcripción")
    texto = documento(ficha, contenido)
    destino = destino.with_suffix(FORMATOS[formato])
    destino.parent.mkdir(parents=True, exist_ok=True)
    if formato == "pdf":
        a_pdf(texto, destino)
    else:
        a_word(texto, destino)
    return destino
