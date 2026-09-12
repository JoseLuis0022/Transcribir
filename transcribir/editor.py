"""El editor: ver la transcripción, escuchar el audio y corregir el texto.

Lo que se edita aquí es tu archivo, no una copia: al guardar se sobrescribe el .txt
(o el .srt) que está en tu carpeta. Si la transcripción tiene tiempos, la palabra que
suena se resalta y con ⌘-clic saltas a ese momento del audio.
"""

from bisect import bisect_right
from pathlib import Path

import objc
from AppKit import (
    NSApplication, NSBackingStoreBuffered, NSColor, NSFont, NSSavePanel, NSScrollView,
    NSSlider, NSTextView, NSView, NSVisualEffectView, NSWindow, NSWorkspace,
)
from AVFoundation import AVPlayer, AVPlayerItem
from CoreMedia import CMTimeGetSeconds, CMTimeMakeWithSeconds
from Foundation import NSURL, NSMakeRange, NSMakeRect, NSObject

import biblioteca
import exportar
import formatos
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


def reloj(segundos: float) -> str:
    segundos = max(0, int(segundos))
    if segundos >= 3600:
        return f"{segundos // 3600}:{segundos % 3600 // 60:02d}:{segundos % 60:02d}"
    return f"{segundos // 60}:{segundos % 60:02d}"


# ------------------------------------------------------------------- el texto --
class VistaTexto(NSTextView):
    """El texto de la transcripción: se edita como en cualquier editor, y además
    ⌘-clic en una palabra salta a ese momento y ⌥-espacio reproduce o pausa."""

    def mouseDown_(self, evento):
        if evento.modifierFlags() & CMD and self.dueno.tiene_audio:
            punto = self.convertPoint_fromView_(evento.locationInWindow(), None)
            self.dueno.saltarACaracter(self.characterIndexForInsertionAtPoint_(punto))
            return
        objc.super(VistaTexto, self).mouseDown_(evento)

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
        self.resaltada = None
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
        parrafo = ui.NSMutableParagraphStyle.alloc().init()
        parrafo.setLineSpacing_(5.0)
        parrafo.setParagraphSpacing_(10.0)
        self.texto.setTypingAttributes_({
            "NSFont": NSFont.systemFontOfSize_(14.0),
            "NSColor": NSColor.labelColor(),
            "NSParagraphStyle": parrafo})
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
        gestor = self.texto.layoutManager()
        if self.resaltada is not None and self.resaltada < len(self.mapa):
            antes = self.mapa[self.resaltada]
            gestor.removeTemporaryAttribute_forCharacterRange_(
                FONDO_TEMPORAL, NSMakeRange(antes[0], antes[1] - antes[0]))
        self.resaltada = i
        if i is None:
            return
        inicio, fin, _, _ = self.mapa[i]
        if fin > len(self.contenido()):
            return
        rango = NSMakeRange(inicio, fin - inicio)
        gestor.addTemporaryAttributes_forCharacterRange_(
            {FONDO_TEMPORAL: NSColor.systemPurpleColor().colorWithAlphaComponent_(0.28)}, rango)
        if self.sonando():
            self.texto.scrollRangeToVisible_(rango)

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
        numero = str(sender.tag())
        actual = (self.ficha.get("personas") or {}).get(numero, "")
        nombre = self.dueno.preguntarTexto(
            f"¿Quién es la persona {numero}?",
            "Se cambiará en todo el archivo. Déjalo vacío para volver a «Persona " + numero + "».",
            actual, f"Persona {numero}")
        if nombre is None:
            return
        self.renombrarPersonas({numero: nombre})

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
