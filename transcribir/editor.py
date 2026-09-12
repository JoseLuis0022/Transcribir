"""El editor: ver la transcripción, escuchar el audio y corregir el texto.

Lo que se edita aquí es tu archivo, no una copia: al guardar se sobrescribe el .txt
(o el .srt) que está en tu carpeta. Si la transcripción tiene tiempos, la palabra que
suena se resalta y con ⌘-clic saltas a ese momento del audio.
"""

from bisect import bisect_left, bisect_right
from pathlib import Path

import objc
from AppKit import (
    NSApplication, NSBackingStoreBuffered, NSColor, NSCursor, NSFont, NSSavePanel,
    NSScrollView, NSSlider, NSTextView, NSView, NSVisualEffectView, NSWindow, NSWorkspace,
)
from AVFoundation import AVPlayer, AVPlayerItem
from CoreMedia import CMTimeGetSeconds, CMTimeMakeWithSeconds
from Foundation import NSURL, NSMakeRange, NSMakeRect, NSObject

import biblioteca
import exportar
import formatos
import preferencias as pref
import ui

W, H = 760.0, 680.0
PAD = 24.0
CABECERA, PERSONAS_H, TRANSPORTE = 92.0, 40.0, 64.0
TOPE = 30.0                      # aire de los botones de la ventana, que van encima
SALTO = 15.0                     # los segundos que retroceden o adelantan los botones
ESCALA = 600                     # precisión de los tiempos del reproductor
VELOCIDADES = [(0.75, "0,75×"), (1.0, "1×"), (1.25, "1,25×"), (1.5, "1,5×"), (2.0, "2×")]

CMD, OPT = 1 << 20, 1 << 19      # teclas ⌘ y ⌥
ANCHO_FLEX, ALTO_FLEX = 2, 16
PEGADO_ARRIBA, PEGADO_ABAJO = 2 | 8, 2 | 32
FONDO_TEMPORAL = "NSBackgroundColor"
SALIDA = 0.3                     # lo que tarda en apagarse la palabra anterior


COLOR_RESALTE = NSColor.systemPurpleColor()
INVISIBLE = NSFont.systemFontOfSize_(0.01)      # lo que está en el archivo pero no se dibuja
JUSTIFICADO = 3
CABECERA_NOMBRE, CABECERA_HORA, AIRE = 46.0, 26.0, 12.0


def reloj(segundos: float) -> str:
    segundos = max(0, int(segundos))
    if segundos >= 3600:
        return f"{segundos // 3600}:{segundos % 3600 // 60:02d}:{segundos % 60:02d}"
    return f"{segundos // 60}:{segundos % 60:02d}"


def parrafo(cabecera: float):
    """Estilo de un párrafo del editor: justificado y con hueco arriba para su cabecera."""
    p = ui.NSMutableParagraphStyle.alloc().init()
    p.setLineSpacing_(5.0)
    p.setParagraphSpacingBefore_(cabecera)
    p.setAlignment_(JUSTIFICADO)
    return p


class Bloque:
    """Una intervención: dónde está en el archivo, cuándo suena y quién habla."""

    def __init__(self, inicio, fin, desde, hasta, numero, nombre, color):
        self.inicio, self.fin = inicio, fin
        self.desde, self.hasta = desde, hasta
        self.numero, self.nombre, self.color = numero, nombre, color

    @property
    def cabecera(self) -> float:
        if self.nombre:
            return CABECERA_NOMBRE
        return CABECERA_HORA if self.desde is not None else AIRE

    @property
    def cuando(self) -> str:
        if self.desde is None:
            return ""
        if self.hasta is None or self.hasta <= self.desde + 0.6:
            return reloj(self.desde)
        return f"{reloj(self.desde)} – {reloj(self.hasta)}"


# ------------------------------------------------------------------- el texto --
class VistaTexto(NSTextView):
    """El texto de la transcripción: se edita como en cualquier editor, y además
    ⌘-clic en una palabra salta a ese momento y ⌥-espacio reproduce o pausa.

    En el margen izquierdo se dibuja la hora de cada intervención, que no está en
    el archivo: es solo de la ventana, y se puede pulsar para escuchar desde ahí.
    """

    def drawViewBackgroundInRect_(self, rect):
        """Encima de cada intervención, quién habla y de qué minuto a qué minuto.

        No está en el archivo: se dibuja aquí, en el hueco que deja el párrafo.
        """
        objc.super(VistaTexto, self).drawViewBackgroundInRect_(rect)
        dueno = getattr(self, "dueno", None)
        if dueno is None:
            return
        arriba, abajo = rect.origin.y, rect.origin.y + rect.size.height
        for bloque in dueno.bloques:
            if not bloque.cabecera:
                continue
            y = dueno.altoDeBloque(bloque)
            if y is None or y + bloque.cabecera < arriba or y > abajo:
                continue
            ancho = self.bounds().size.width
            if bloque.nombre and bloque.numero != dueno.editando():
                ui.attributed(bloque.nombre, 13.5, ui.W_SEMIBOLD, bloque.color,
                              ui.ALIGN_LEFT).drawInRect_(
                    NSMakeRect(0, y - bloque.cabecera + 4, ancho, 18))
            if bloque.cuando:
                ui.attributed(bloque.cuando, 11.0, ui.W_REGULAR, NSColor.secondaryLabelColor(),
                              ui.ALIGN_LEFT).drawInRect_(
                    NSMakeRect(0, y - (23 if bloque.nombre else 19), ancho, 15))

    def mouseDown_(self, evento):
        punto = self.convertPoint_fromView_(evento.locationInWindow(), None)
        if evento.modifierFlags() & CMD and self.dueno.tiene_audio:
            self.dueno.saltarACaracter(self.characterIndexForInsertionAtPoint_(punto))
            return
        bloque, zona = self.dueno.zonaCabecera(punto)
        if zona == "nombre":                       # el nombre se edita aquí mismo
            self.dueno.editarNombre(bloque)
            return
        if zona == "hora" and self.dueno.tiene_audio:
            self.dueno.escucharDesde(bloque.desde)
            return
        objc.super(VistaTexto, self).mouseDown_(evento)

    def resetCursorRects(self):
        """La mano solo donde se puede pulsar: los nombres y las horas."""
        objc.super(VistaTexto, self).resetCursorRects()
        dueno = getattr(self, "dueno", None)
        if dueno is None:
            return
        for bloque in dueno.bloques:
            y = dueno.altoDeBloque(bloque)
            if y is None or not bloque.cabecera:
                continue
            if bloque.nombre:
                self.addCursorRect_cursor_(
                    NSMakeRect(0, y - bloque.cabecera, dueno.anchoNombre(bloque), 20),
                    NSCursor.pointingHandCursor())
            if bloque.cuando:
                self.addCursorRect_cursor_(
                    NSMakeRect(0, y - 24, 120, 16), NSCursor.pointingHandCursor())

    def keyDown_(self, evento):
        if evento.modifierFlags() & OPT and evento.charactersIgnoringModifiers() == " ":
            self.dueno.alternarReproduccion()
            return
        objc.super(VistaTexto, self).keyDown_(evento)


# ------------------------------------------------------------------ la ventana --
class Editor(NSObject):

    def initWithDueno_ficha_(self, dueno, ficha):
        self = objc.super(Editor, self).init()
        if self is None:
            return None
        contenido = biblioteca.texto(ficha)
        if contenido is None:                 # el archivo se movió o se borró
            return None
        self.dueno = dueno                    # el delegado de la app
        self.ficha = ficha
        self.guardado = contenido             # lo que hay ahora mismo en tu archivo
        self.palabras = biblioteca.palabras(ficha["id"]) or []
        self.mapa, self.inicios = [], []      # [(inicio, fin, desde, hasta)] por palabra
        self.bloques = []                     # cada intervención: dónde, cuándo y de quién
        self.resaltada, self.capa, self.capas = None, None, []
        self.campo_nombre = None
        self.pastilla_oculta = None
        self.sucio = False
        self.arrastrando = False
        self.reproductor = None
        self.vigilante = None
        self.audio = biblioteca.ubicar(ficha, "origen")
        self.tiene_audio = self.audio is not None
        self.construir()
        self.cargar(contenido)
        return self

    @objc.python_method
    def mostrar(self, segundo=None):
        self.ventana.makeKeyAndOrderFront_(None)
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        if segundo is not None and self.reproductor is not None:
            self.buscar(float(segundo))

    # ------------------------------------------------------------- interfaz --
    @objc.python_method
    def construir(self):
        rect = NSMakeRect(0, 0, W, H)
        self.ventana = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, ui.STYLE_TITLED | ui.STYLE_CLOSABLE | ui.STYLE_MINI | ui.STYLE_RESIZABLE
            | ui.STYLE_FULL_CONTENT, NSBackingStoreBuffered, False)
        self.ventana.setTitle_(self.ficha.get("nombre", "Transcripción"))
        self.ventana.setTitleVisibility_(1)          # el nombre se pinta dentro, con su detalle
        self.ventana.setTitlebarAppearsTransparent_(True)
        self.ventana.setMovableByWindowBackground_(True)
        self.ventana.setReleasedWhenClosed_(False)
        self.ventana.setMinSize_((520, 420))
        self.ventana.setDelegate_(self)
        self.ventana.center()

        fondo = NSVisualEffectView.alloc().initWithFrame_(rect)
        fondo.setMaterial_(ui.MATERIAL_UNDER_WINDOW)
        fondo.setBlendingMode_(ui.BLEND_BEHIND_WINDOW)
        fondo.setState_(ui.VFX_ACTIVE)
        fondo.setAutoresizingMask_(ANCHO_FLEX | ALTO_FLEX)
        self.ventana.setContentView_(fondo)

        alto_personas = PERSONAS_H if self.personas() else 0.0
        self.construirCabecera(fondo, alto_personas)
        self.construirTexto(fondo, alto_personas)
        self.construirTransporte(fondo)

    @objc.python_method
    def construirCabecera(self, fondo, alto_personas):
        alto = CABECERA + alto_personas
        barra = NSView.alloc().initWithFrame_(NSMakeRect(0, H - alto, W, alto))
        barra.setAutoresizingMask_(PEGADO_ARRIBA)
        fondo.addSubview_(barra)

        ancho_botones = 104.0 + 6 + 128 + 6 + 80
        arriba = alto - TOPE - 22.0
        ancho_texto = W - PAD * 2 - ancho_botones - 16
        barra.addSubview_(ui.label(self.ficha.get("nombre", ""), 15.0, ui.W_SEMIBOLD,
                                   NSColor.labelColor(), NSMakeRect(PAD, arriba, ancho_texto, 20),
                                   ui.ALIGN_LEFT, truncate=ui.TRUNC_MIDDLE))
        self.detalle = ui.label("", 11.5, ui.W_REGULAR, NSColor.tertiaryLabelColor(),
                                NSMakeRect(PAD, arriba - 19, ancho_texto, 16), ui.ALIGN_LEFT,
                                truncate=ui.TRUNC_MIDDLE)
        barra.addSubview_(self.detalle)

        derecha = NSView.alloc().initWithFrame_(
            NSMakeRect(W - PAD - ancho_botones, arriba - 7, ancho_botones, 28))
        derecha.setAutoresizingMask_(8 | 1)          # pegado a la derecha y arriba
        barra.addSubview_(derecha)
        derecha.addSubview_(ui.menu_button("Exportar…", ["PDF", "Word (.docx)"],
                                           NSMakeRect(0, 0, 104, 28), self, b"exportarComo:"))
        derecha.addSubview_(ui.bezel_button("Mostrar en Finder", NSMakeRect(110, 0, 128, 28),
                                            self, b"mostrarEnFinder:"))
        self.boton_guardar = ui.bezel_button("Guardar", NSMakeRect(244, 0, 80, 28),
                                             self, b"guardarDocumento:")
        self.boton_guardar.setEnabled_(False)
        derecha.addSubview_(self.boton_guardar)

        if alto_personas:
            self.construirPersonas(barra)

    @objc.python_method
    def personas(self):
        """Los números de persona que aparecen en el texto, en orden."""
        cuantas = int(self.ficha.get("cuantas_personas") or 0)
        nombres = self.ficha.get("personas") or {}
        return [str(n) for n in range(1, cuantas + 1)] or sorted(nombres)

    @objc.python_method
    def construirPersonas(self, barra):
        """Una pastilla por persona: se pulsa para ponerle nombre."""
        self.fila_personas = NSView.alloc().initWithFrame_(NSMakeRect(0, 4, W, PERSONAS_H - 8))
        self.fila_personas.setAutoresizingMask_(ANCHO_FLEX)
        barra.addSubview_(self.fila_personas)
        self.pintarPersonas()

    @objc.python_method
    def pintarPersonas(self):
        for vista in list(self.fila_personas.subviews()):
            vista.removeFromSuperview()
        nombres = self.ficha.get("personas") or {}
        colores = [NSColor.systemPurpleColor(), NSColor.systemTealColor(), NSColor.systemOrangeColor(),
                   NSColor.systemPinkColor(), NSColor.systemIndigoColor()]
        x = PAD
        for i, numero in enumerate(self.personas()):
            titulo = (nombres.get(numero) or "").strip() or f"Persona {numero}"
            color = colores[i % len(colores)]
            boton = ui.pill_button(titulo, "person.fill", color, self, b"renombrarPersona:", tag=int(numero))
            boton.setFrameOrigin_((x, 3))
            boton.setToolTip_("Ponle su nombre")
            self.fila_personas.addSubview_(boton)
            x += boton.frame().size.width + 8

    @objc.python_method
    def construirTexto(self, fondo, alto_personas):
        alto = H - CABECERA - alto_personas - TRANSPORTE
        marco = NSMakeRect(PAD, TRANSPORTE, W - PAD * 2, alto)
        scroll = NSScrollView.alloc().initWithFrame_(marco)
        scroll.setHasVerticalScroller_(True)
        scroll.setAutohidesScrollers_(True)
        scroll.setDrawsBackground_(False)
        scroll.setAutoresizingMask_(ANCHO_FLEX | ALTO_FLEX)

        ancho = marco.size.width
        self.texto = VistaTexto.alloc().initWithFrame_(NSMakeRect(0, 0, ancho, alto))
        self.texto.dueno = self
        self.texto.setDelegate_(self)
        self.texto.setWantsLayer_(True)          # la palabra que crece va en una capa encima
        self.texto.setAllowsUndo_(True)
        self.texto.setDrawsBackground_(False)
        self.texto.setRichText_(False)
        self.texto.setMinSize_((0, 0))
        self.texto.setMaxSize_((1e7, 1e7))
        self.texto.setVerticallyResizable_(True)
        self.texto.setHorizontallyResizable_(False)
        self.texto.setAutoresizingMask_(ANCHO_FLEX)
        self.texto.setTextContainerInset_((0, 12))
        self.texto.textContainer().setLineFragmentPadding_(0.0)   # alineado con la cabecera
        self.texto.textContainer().setWidthTracksTextView_(True)
        self.texto.textContainer().setContainerSize_((ancho, 1e7))
        scroll.setDocumentView_(self.texto)
        fondo.addSubview_(scroll)

    @objc.python_method
    def construirTransporte(self, fondo):
        barra = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, W, TRANSPORTE))
        barra.setAutoresizingMask_(PEGADO_ABAJO)
        fondo.addSubview_(barra)
        barra.addSubview_(ui.hairline(NSMakeRect(0, TRANSPORTE - 1, W, 1)))

        if not self.tiene_audio:
            barra.addSubview_(ui.icon_view("waveform.slash", NSMakeRect(PAD, 22, 20, 20),
                                           NSColor.tertiaryLabelColor(), 14.0))
            barra.addSubview_(ui.label(
                "No se encontró el audio original, así que no se puede escuchar.",
                12.0, ui.W_REGULAR, NSColor.tertiaryLabelColor(),
                NSMakeRect(PAD + 30, 23, W - PAD * 2 - 30, 18), ui.ALIGN_LEFT))
            return

        y = 20.0
        self.boton_atras = ui.symbol_button("gobackward.15", NSMakeRect(PAD, y, 24, 24), self,
                                            b"atras:", size=16.0, tooltip="15 s atrás")
        barra.addSubview_(self.boton_atras)
        self.boton_play = ui.symbol_button("play.circle.fill", NSMakeRect(PAD + 32, y - 3, 30, 30), self,
                                           b"reproducir:", size=22.0,
                                           tooltip="Reproducir o pausar (⌥espacio)")
        barra.addSubview_(self.boton_play)
        barra.addSubview_(ui.symbol_button("goforward.15", NSMakeRect(PAD + 70, y, 24, 24), self,
                                           b"adelante:", size=16.0, tooltip="15 s adelante"))

        self.tiempo = ui.label("0:00 / 0:00", 12.0, ui.W_MEDIUM, NSColor.secondaryLabelColor(),
                              NSMakeRect(PAD + 102, y + 4, 96, 16), ui.ALIGN_LEFT)
        barra.addSubview_(self.tiempo)

        ancho_barra = W - (PAD + 206) - (PAD + 160)
        self.barra = NSSlider.alloc().initWithFrame_(NSMakeRect(PAD + 206, y + 2, ancho_barra, 20))
        self.barra.setMinValue_(0.0)
        self.barra.setMaxValue_(max(self.ficha.get("duracion") or 1.0, 1.0))
        self.barra.setTarget_(self)
        self.barra.setAction_(b"mover:")
        self.barra.setAutoresizingMask_(ANCHO_FLEX)
        barra.addSubview_(self.barra)

        derecha = NSView.alloc().initWithFrame_(NSMakeRect(W - PAD - 152, y - 3, 152, 30))
        derecha.setAutoresizingMask_(1 | 8)
        barra.addSubview_(derecha)
        self.velocidad = ui.popup(NSMakeRect(152 - 76, 2, 76, 24), [t for _, t in VELOCIDADES],
                                  self, b"cambiarVelocidad:")
        self.velocidad.selectItemAtIndex_(1)
        self.velocidad.setToolTip_("Velocidad de reproducción")
        derecha.addSubview_(self.velocidad)
        self.boton_tiempos = ui.bezel_button("Activar resaltado", NSMakeRect(0, 1, 140, 26),
                                             self, b"activarResaltado:")
        self.boton_tiempos.setToolTip_(
            "Vuelve a escuchar el audio para saber cuándo suena cada palabra.\n"
            "Tu texto no cambia: se respeta tal como está.")
        derecha.addSubview_(self.boton_tiempos)

    # -------------------------------------------------------------- contenido --
    @objc.python_method
    def cargar(self, contenido):
        """Pone el texto en la ventana con el estilo de lectura y prepara el resaltado."""
        self.texto.setTypingAttributes_({
            "NSFont": NSFont.systemFontOfSize_(14.0),
            "NSColor": NSColor.labelColor(),
            "NSParagraphStyle": parrafo(0.0)})
        self.texto.setString_(contenido)
        almacen = self.texto.textStorage()
        almacen.setAttributes_range_(self.texto.typingAttributes(),
                                     NSMakeRange(0, almacen.length()))
        self.guardado = contenido
        self.marcarSucio(False)
        self.rehacerMapa()
        self.pintarDetalle()
        self.prepararAudio()

    @objc.python_method
    def contenido(self):
        return str(self.texto.string())

    @objc.python_method
    def rehacerMapa(self):
        nombres = list((self.ficha.get("personas") or {}).values())
        self.mapa = formatos.mapear_tiempos(self.contenido(), self.palabras, nombres) if self.palabras else []
        self.inicios = [m[2] for m in self.mapa]
        self.rehacerBloques(nombres)

    @objc.python_method
    def rehacerBloques(self, nombres):
        """Prepara cada intervención: quién habla, de qué minuto a qué minuto y su texto.

        El archivo dice «Ana: Cuéntame…» en una sola línea. Aquí el «Ana:» se
        esconde (queda en el archivo, pero sin tamaño) y se dibuja arriba, con su
        color y su rango de tiempo, como una ficha de conversación.
        """
        contenido = self.contenido()
        colores = ui.COLORES_PERSONA
        arranques = [m[0] for m in self.mapa]
        self.bloques, posicion = [], 0
        almacen = self.texto.textStorage()
        almacen.beginEditing()
        almacen.setAttributes_range_({"NSFont": NSFont.systemFontOfSize_(14.0),
                                      "NSColor": NSColor.labelColor(),
                                      "NSParagraphStyle": parrafo(0.0)},
                                     NSMakeRange(0, almacen.length()))
        for linea in contenido.split("\n"):
            fin = posicion + len(linea)
            if not linea.strip():
                if fin > posicion:              # línea en blanco del archivo: sin altura
                    almacen.addAttribute_value_range_("NSFont", INVISIBLE,
                                                      NSMakeRange(posicion, fin - posicion))
                posicion = fin + 1
                continue

            i = bisect_left(arranques, posicion)
            j = bisect_left(arranques, fin) - 1
            desde = self.mapa[i][2] if i < len(self.mapa) and arranques[i] < fin else None
            hasta = self.mapa[j][3] if desde is not None and 0 <= j < len(self.mapa) else None
            largo, numero = self._quien(linea, nombres)
            bloque = Bloque(posicion, fin, desde, hasta, numero,
                            linea[:largo].rstrip(": ") if largo else "",
                            colores[(int(numero) - 1) % len(colores)] if numero
                            else NSColor.secondaryLabelColor())
            self.bloques.append(bloque)
            if largo:                            # el «Ana:» se dibuja arriba, no en la línea
                almacen.addAttributes_range_({"NSFont": INVISIBLE, "NSColor": NSColor.clearColor()},
                                             NSMakeRange(posicion, min(largo + 1, fin - posicion)))
            almacen.addAttribute_value_range_("NSParagraphStyle", parrafo(bloque.cabecera),
                                              NSMakeRange(posicion, fin - posicion))
            posicion = fin + 1
        almacen.endEditing()
        # TextKit no aplica el hueco superior al primer párrafo: se lo da la vista
        primera = self.bloques[0].cabecera if self.bloques else AIRE
        self.texto.setTextContainerInset_((0, primera + 6))
        self.texto.setNeedsDisplay_(True)
        self.ventana.invalidateCursorRectsForView_(self.texto)

    @objc.python_method
    def altoDeBloque(self, bloque):
        """Dónde empieza a dibujarse el texto de un bloque, en coordenadas de la vista."""
        gestor, contenedor = self.texto.layoutManager(), self.texto.textContainer()
        if bloque.inicio >= len(self.contenido()):
            return None
        glifos = gestor.glyphRangeForCharacterRange_actualCharacterRange_(
            NSMakeRange(bloque.inicio, 1), None)[0]
        marco = gestor.boundingRectForGlyphRange_inTextContainer_(glifos, contenedor)
        return marco.origin.y + self.texto.textContainerOrigin().y

    @objc.python_method
    def editando(self):
        """Qué persona se está renombrando ahora mismo (su nombre no se dibuja)."""
        return self.campo_nombre[1] if self.campo_nombre else None

    @objc.python_method
    def anchoNombre(self, bloque):
        return ui.attributed(bloque.nombre, 13.5, ui.W_SEMIBOLD, bloque.color).size().width + 10

    @objc.python_method
    def zonaCabecera(self, punto):
        """Qué hay bajo el ratón en la cabecera de una intervención: su nombre o su hora."""
        for bloque in self.bloques:
            if not bloque.cabecera:
                continue
            y = self.altoDeBloque(bloque)
            if y is None or not (y - bloque.cabecera <= punto.y <= y - 3):
                continue
            if bloque.nombre and punto.y <= y - bloque.cabecera + 20 \
                    and punto.x <= self.anchoNombre(bloque):
                return bloque, "nombre"
            if bloque.desde is not None and punto.x <= 120:
                return bloque, "hora"
            return None, None
        return None, None

    @objc.python_method
    def escucharDesde(self, segundo):
        if segundo is None:
            return
        self.buscar(segundo)
        if not self.sonando():
            self.alternarReproduccion()

    # --------------------------------------------------- nombre en su sitio --
    @objc.python_method
    def editarNombre(self, bloque):
        """Pulsar el nombre lo convierte en un campo, ahí mismo: sin ventanas ni modales."""
        y = self.altoDeBloque(bloque)
        if y is None:
            return
        self.campoNombre(bloque.numero, bloque.color, self.texto,
                         NSMakeRect(-3, y - bloque.cabecera, max(self.anchoNombre(bloque) + 40, 160), 22),
                         13.5)

    @objc.python_method
    def campoNombre(self, numero, color, vista, marco, tamano):
        self.cerrarCampoNombre()
        if not numero:
            return
        actual = (self.ficha.get("personas") or {}).get(str(numero), "")
        campo = ui.text_field(marco, f"Persona {numero}", self, b"guardarNombre:")
        campo.setFont_(NSFont.systemFontOfSize_weight_(tamano, ui.W_SEMIBOLD))
        campo.setTextColor_(color)
        campo.setStringValue_(actual)
        campo.setDelegate_(self)
        self.campo_nombre = (campo, str(numero))
        self.texto.setNeedsDisplay_(True)
        vista.addSubview_(campo)
        self.ventana.makeFirstResponder_(campo)

    @objc.python_method
    def cerrarCampoNombre(self):
        if getattr(self, "campo_nombre", None) is None:
            return
        campo, _ = self.campo_nombre
        self.campo_nombre = None
        campo.setDelegate_(None)
        campo.removeFromSuperview()
        if getattr(self, "pastilla_oculta", None) is not None:
            self.pastilla_oculta.setHidden_(False)
            self.pastilla_oculta = None
        self.texto.setNeedsDisplay_(True)
        self.ventana.makeFirstResponder_(self.texto)

    def control_textView_doCommandBySelector_(self, control, vista, selector):
        if selector == "cancelOperation:":
            self.cerrarCampoNombre()
            return True
        return False

    def guardarNombre_(self, sender):
        if getattr(self, "campo_nombre", None) is None:
            return
        _, numero = self.campo_nombre
        nombre = sender.stringValue().strip()
        self.cerrarCampoNombre()
        if numero and nombre != (self.ficha.get("personas") or {}).get(numero, ""):
            self.renombrarPersonas({numero: nombre})

    @objc.python_method
    def _quien(self, linea, nombres):
        """(cuántas letras ocupa «Ana:» al principio, qué número de persona es)."""
        marca = formatos.MARCA.match(linea)
        desde = marca.end() if marca else 0
        resto = linea[desde:]
        encontrado = formatos.QUIEN.match(resto)
        if encontrado:
            return desde + len(encontrado.group().rstrip()), encontrado.group().split()[1].rstrip(":")
        nombres_ficha = self.ficha.get("personas") or {}
        for numero, nombre in nombres_ficha.items():
            if nombre.strip() and resto.startswith(f"{nombre}:"):
                return desde + len(nombre) + 1, numero
        for nombre in nombres:
            if nombre.strip() and resto.startswith(f"{nombre}:"):
                return desde + len(nombre) + 1, None
        return 0, None

    @objc.python_method
    def pintarDetalle(self):
        ruta = biblioteca.ubicar(self.ficha)
        partes = [f"{reloj(self.ficha.get('duracion') or 0)} de audio"]
        if ruta is not None:
            partes.append("en el Escritorio" if ruta.parent == biblioteca.ESCRITORIO
                          else f"en «{ruta.parent.name}»")
        if self.palabras and self.tiene_audio:
            partes.append("⌘-clic en una palabra para escucharla")
        elif self.tiene_audio:
            partes.append("sin tiempos todavía")
        self.detalle.setStringValue_(" · ".join(partes))
        self.detalle.setToolTip_(str(ruta) if ruta else "")
        if hasattr(self, "boton_tiempos"):
            self.boton_tiempos.setHidden_(bool(self.palabras))

    @objc.python_method
    def marcarSucio(self, sucio):
        self.sucio = sucio
        self.boton_guardar.setEnabled_(sucio)
        self.ventana.setDocumentEdited_(sucio)

    def textDidChange_(self, notificacion):
        self.marcarSucio(True)
        # rehacer el mapa en cada tecla sería caro en textos largos: se espera a la pausa
        NSObject.cancelPreviousPerformRequestsWithTarget_selector_object_(self, b"volverAMapear:", None)
        self.performSelector_withObject_afterDelay_(b"volverAMapear:", None, 0.6)

    def volverAMapear_(self, _):
        self.rehacerMapa()

    @objc.python_method
    def recargar(self, ficha):
        """La app avisa de que la ficha cambió (por ejemplo, ya tiene tiempos)."""
        self.ficha = ficha
        self.palabras = biblioteca.palabras(ficha["id"]) or []
        self.rehacerMapa()
        self.pintarDetalle()

    # ---------------------------------------------------------------- guardar --
    def guardarDocumento_(self, sender):
        self.guardar()

    @objc.python_method
    def guardar(self):
        """Sobrescribe tu archivo. Lo de deshacer sigue disponible (⌘Z)."""
        if not self.sucio:
            return True
        try:
            biblioteca.escribir_texto(self.ficha, self.contenido())
        except OSError as e:
            self.dueno.alerta("No se pudo guardar", str(e), ["Aceptar"])
            return False
        self.guardado = self.contenido()
        self.marcarSucio(False)
        self.dueno.alGuardarFicha(self.ficha)
        return True

    def windowShouldClose_(self, ventana):
        if not self.sucio:
            return True
        eleccion = self.dueno.alerta(
            f"¿Guardar los cambios en «{self.ficha.get('nombre', '')}»?",
            "Se sobrescribirá tu archivo de texto. Si no los guardas, se pierden.",
            ["Guardar", "Descartar", "Cancelar"])
        if eleccion == 1000:
            return self.guardar()
        if eleccion == 1001:
            self.marcarSucio(False)
            return True
        return False

    def windowWillClose_(self, notificacion):
        self.soltarAudio()
        self.dueno.alCerrarEditor(self.ficha["id"])

    # ------------------------------------------------------------------ audio --
    @objc.python_method
    def prepararAudio(self):
        if not self.tiene_audio or self.reproductor is not None:
            return
        item = AVPlayerItem.playerItemWithURL_(NSURL.fileURLWithPath_(str(self.audio)))
        self.reproductor = AVPlayer.playerWithPlayerItem_(item)
        self.vigilante = self.reproductor.addPeriodicTimeObserverForInterval_queue_usingBlock_(
            CMTimeMakeWithSeconds(0.05, ESCALA), None, self.alSonar)

    @objc.python_method
    def soltarAudio(self):
        if self.reproductor is None:
            return
        self.reproductor.pause()
        if self.vigilante is not None:
            self.reproductor.removeTimeObserver_(self.vigilante)
        self.reproductor, self.vigilante = None, None

    @objc.python_method
    def alSonar(self, tiempo):
        segundo = CMTimeGetSeconds(tiempo)
        if segundo != segundo:                      # NaN mientras carga
            return
        total = self.duracion()
        if not self.arrastrando:
            self.barra.setDoubleValue_(segundo)
        self.tiempo.setStringValue_(f"{reloj(segundo)} / {reloj(total)}")
        self.resaltar(segundo)

    @objc.python_method
    def duracion(self):
        if self.reproductor is not None and self.reproductor.currentItem() is not None:
            total = CMTimeGetSeconds(self.reproductor.currentItem().duration())
            if total == total and total > 0:
                self.barra.setMaxValue_(total)
                return total
        return self.ficha.get("duracion") or 0.0

    @objc.python_method
    def sonando(self):
        return self.reproductor is not None and self.reproductor.rate() > 0

    @objc.python_method
    def alternarReproduccion(self):
        if self.reproductor is None:
            return
        if self.sonando():
            self.reproductor.pause()
        else:
            self.reproductor.setRate_(VELOCIDADES[self.velocidad.indexOfSelectedItem()][0])
        self.boton_play.setImage_(ui.sf("pause.circle.fill" if self.sonando() else "play.circle.fill", 22.0))

    @objc.python_method
    def buscar(self, segundo):
        if self.reproductor is None:
            return
        segundo = max(0.0, min(segundo, self.duracion()))
        self.reproductor.seekToTime_toleranceBefore_toleranceAfter_(
            CMTimeMakeWithSeconds(segundo, ESCALA),
            CMTimeMakeWithSeconds(0.02, ESCALA), CMTimeMakeWithSeconds(0.02, ESCALA))
        self.resaltar(segundo)

    @objc.python_method
    def saltarACaracter(self, posicion):
        """⌘-clic: suena desde la palabra que se ha pulsado."""
        for inicio, fin, desde, _ in self.mapa:
            if inicio <= posicion <= fin:
                self.buscar(desde)
                if not self.sonando():
                    self.alternarReproduccion()
                return

    # -------------------------------------------------------------- resaltado --
    @objc.python_method
    def resaltar(self, segundo):
        """Marca la palabra que suena ahora, sin tocar el texto ni el deshacer."""
        if not self.mapa:
            return
        i = bisect_right(self.inicios, segundo) - 1
        if i < 0 or segundo > self.mapa[i][3] + 0.6:
            i = None
        if i == self.resaltada:
            return
        self.apagarResaltado()
        self.resaltada = i
        if i is None:
            return
        inicio, fin, desde, hasta = self.mapa[i]
        if fin > len(self.contenido()):
            return
        rango = NSMakeRange(inicio, fin - inicio)
        if pref.leer(pref.RESALTADO) == "fondo":
            self.texto.layoutManager().addTemporaryAttributes_forCharacterRange_(
                {FONDO_TEMPORAL: COLOR_RESALTE.colorWithAlphaComponent_(0.28)}, rango)
        else:
            dura = max(hasta - desde, 0.12)
            self.cantarPalabra(rango, max(hasta - segundo, 0.12), (segundo - desde) / dura)
        if self.sonando():
            self.texto.scrollRangeToVisible_(rango)

    @objc.python_method
    def apagarResaltado(self):
        """Deja la palabra anterior como estaba: se apaga poco a poco y su capa se va."""
        if self.resaltada is not None and self.resaltada < len(self.mapa):
            antes = self.mapa[self.resaltada]
            rango = NSMakeRange(antes[0], antes[1] - antes[0])
            gestor = self.texto.layoutManager()
            gestor.removeTemporaryAttribute_forCharacterRange_(FONDO_TEMPORAL, rango)
            gestor.removeTemporaryAttribute_forCharacterRange_("NSColor", rango)
        capa = self.capa
        self.capa = None
        if capa is None:
            return
        capa.removeAllAnimations()
        capa.setOpacity_(0.0)
        capa.addAnimation_forKey_(ui.suave("opacity", 1.0, 0.0, SALIDA), "apagar")
        # y fuera: si se quedaran puestas se irían apilando una encima de otra
        self.performSelector_withObject_afterDelay_(b"limpiarCapas:", None, SALIDA + 0.05)

    def limpiarCapas_(self, _):
        """Quita las capas de palabras que ya no suenan (todas menos la de ahora)."""
        for vieja in list(self.capas):
            if vieja is not self.capa:
                vieja.removeFromSuperlayer()
                self.capas.remove(vieja)

    @objc.python_method
    def cantarPalabra(self, rango, restante, avance):
        """La palabra que suena se pone en negrita de izquierda a derecha, como las
        letras de Apple Music, pero sin crecer.

        Crecer empujaría a la palabra siguiente: las guías de Apple piden que la
        animación no desplace lo que se está leyendo. En Apple Music quien crece es
        el renglón entero, no la palabra suelta.

        Son dos copias de la palabra, la normal y la negrita, con máscaras que se
        complementan: cada punto enseña una o la otra, nunca las dos, así que no se
        ve doble. Van en una capa encima del texto para que el renglón no se mueva
        ni una décima, que es lo que pasaría si se cambiara la letra de verdad.
        """
        gestor, contenedor = self.texto.layoutManager(), self.texto.textContainer()
        glifos = gestor.glyphRangeForCharacterRange_actualCharacterRange_(rango, None)[0]
        marco = gestor.boundingRectForGlyphRange_inTextContainer_(glifos, contenedor)
        origen = self.texto.textContainerOrigin()
        palabra = self.contenido()[rango.location:rango.location + rango.length]
        if not palabra.strip() or marco.size.width <= 0:
            return

        nitidez = self.ventana.backingScaleFactor() or 2.0
        # la caja empieza justo donde la palabra y sobra un poco a la derecha, que es
        # lo que ocupa de más la negrita; así encaja sobre el texto sin moverlo
        ancho, alto = marco.size.width + 12, marco.size.height + 2
        capa = ui.CALayer.layer()
        capa.setBounds_(NSMakeRect(0, 0, ancho, alto))
        capa.setAnchorPoint_((0.0, 0.5))
        capa.setPosition_((marco.origin.x + origen.x,
                           marco.origin.y + origen.y + marco.size.height / 2))

        def letras(peso):
            letra = ui.CATextLayer.layer()
            letra.setContentsScale_(nitidez)
            letra.setAlignmentMode_("left")     # CATextLayer no hace caso al estilo del párrafo
            letra.setString_(ui.attributed(palabra, 14.0, peso, NSColor.labelColor(), ui.ALIGN_LEFT))
            letra.setFrame_(NSMakeRect(0, 0, ancho, alto))
            return letra

        antes, ahora = letras(ui.W_REGULAR), letras(ui.W_SEMIBOLD)
        capa.addSublayer_(antes)
        capa.addSublayer_(ahora)

        # una máscara descubre la negrita y la otra esconde la normal, a la vez
        avance = min(max(avance, 0.0), 1.0)
        antes.setMask_(ui.barrido(ancho, alto, 1.0, invertida=True))
        mascara = ui.barrido(ancho, alto, 1.0)
        ahora.setMask_(mascara)

        # el texto de debajo se tapa: lo que se ve es la capa, que sí puede crecer
        gestor.addTemporaryAttributes_forCharacterRange_({"NSColor": NSColor.clearColor()}, rango)
        self.texto.layer().addSublayer_(capa)
        self.capa = capa
        self.capas.append(capa)
        if ui.poca_animacion():
            return                     # accesibilidad: sin barrido, la negrita y ya
        capa.addAnimation_forKey_(ui.suave("opacity", 0.4, 1.0, 0.18), "aparecer")
        for mascarita in (antes.mask(), mascara):
            mascarita.addAnimation_forKey_(
                ui.suave("locations", ui.paradas(avance), ui.paradas(1.0),
                         max(restante, 0.16), "linear"), "cantar")

    # -------------------------------------------------------------- acciones --
    def reproducir_(self, sender):
        self.alternarReproduccion()

    def atras_(self, sender):
        self.buscar(CMTimeGetSeconds(self.reproductor.currentTime()) - SALTO)

    def adelante_(self, sender):
        self.buscar(CMTimeGetSeconds(self.reproductor.currentTime()) + SALTO)

    def mover_(self, sender):
        self.arrastrando = True
        self.buscar(sender.doubleValue())
        self.arrastrando = False

    def cambiarVelocidad_(self, sender):
        if self.sonando():
            self.reproductor.setRate_(VELOCIDADES[sender.indexOfSelectedItem()][0])

    def activarResaltado_(self, sender):
        if self.dueno.calcularTiempos(self.ficha) is not None:
            self.boton_tiempos.setEnabled_(False)
            self.detalle.setStringValue_("Calculando los tiempos: se está escuchando el audio…")

    def mostrarEnFinder_(self, sender):
        ruta = biblioteca.ubicar(self.ficha)
        if ruta is not None:
            NSWorkspace.sharedWorkspace().activateFileViewerSelectingURLs_(
                [NSURL.fileURLWithPath_(str(ruta))])

    def exportarComo_(self, sender):
        """Exporta a PDF o a Word, preguntando dónde guardarlo."""
        formato = "pdf" if "PDF" in (sender.titleOfSelectedItem() or "") else "word"
        if self.sucio and not self.guardar():
            return
        ruta = biblioteca.ubicar(self.ficha)
        panel = NSSavePanel.savePanel()
        panel.setNameFieldStringValue_((ruta.stem if ruta else "Transcripción")
                                       + exportar.FORMATOS[formato])
        panel.setAllowedFileTypes_([exportar.FORMATOS[formato][1:]])
        panel.setPrompt_("Exportar")
        if panel.runModal() != 1:
            return
        try:
            destino = exportar.exportar(self.ficha, formato, Path(panel.URL().path()))
        except exportar.ErrorExportar as e:
            self.dueno.alerta("No se pudo exportar", str(e), ["Aceptar"])
            return
        NSWorkspace.sharedWorkspace().activateFileViewerSelectingURLs_(
            [NSURL.fileURLWithPath_(str(destino))])

    # --------------------------------------------------------------- personas --
    def renombrarPersona_(self, sender):
        marco = sender.frame()
        self.pastilla_oculta = sender          # la pastilla se aparta: el campo ocupa su sitio
        sender.setHidden_(True)
        self.campoNombre(sender.tag(),
                         ui.COLORES_PERSONA[(sender.tag() - 1) % len(ui.COLORES_PERSONA)],
                         self.fila_personas,
                         NSMakeRect(marco.origin.x, marco.origin.y - 1,
                                    max(marco.size.width + 60, 150), 24), 11.5)

    @objc.python_method
    def renombrarPersonas(self, nombres):
        """Cambia los nombres en el texto que se está viendo y guarda el archivo."""
        if self.sucio and not self.guardar():
            return
        actuales = self.ficha.get("personas") or {}
        nuevo = formatos.renombrar_personas(self.contenido(), nombres, actuales)
        self.ficha["personas"] = {**actuales, **nombres}
        biblioteca.guardar(self.ficha)
        self.texto.setString_("")                 # el cambio no debería poder deshacerse a medias
        self.cargar(nuevo)
        try:
            biblioteca.escribir_texto(self.ficha, nuevo)
        except OSError as e:
            self.dueno.alerta("No se pudo guardar", str(e), ["Aceptar"])
        self.pintarPersonas()
        self.dueno.alGuardarFicha(self.ficha)
