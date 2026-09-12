"""El editor: ver la transcripción, escuchar el audio y corregir el texto.

Lo que se edita aquí es tu archivo, no una copia: al guardar se sobrescribe el .txt
(o el .srt) que está en tu carpeta. Si la transcripción tiene tiempos, la palabra que
suena se resalta y con ⌘ + clic saltas a ese momento del audio.
"""

from bisect import bisect_left, bisect_right
from pathlib import Path

import objc
from AppKit import (
    NSApplication, NSBackingStoreBuffered, NSButton, NSColor, NSCursor, NSFont, NSSavePanel,
    NSScrollView, NSSearchToolbarItem, NSSlider, NSSplitViewController, NSSplitViewItem,
    NSTextView, NSToolbar, NSToolbarItem, NSView, NSViewController, NSWindow, NSWorkspace,
)
from AVFoundation import AVPlayer, AVPlayerItem
from CoreMedia import CMTimeGetSeconds, CMTimeMakeWithSeconds
from Foundation import NSURL, NSMakeRange, NSMakeRect, NSObject

import biblioteca
import exportar
import formatos
import preferencias as pref
import ui

W, H = 980.0, 700.0
PANEL_W = 272.0                  # el inspector de la derecha
PAD = 20.0
TRANSPORTE = 52.0                # la barra del reproductor
SALTO = 15.0                     # los segundos que retroceden o adelantan los botones
ESCALA = 600                     # precisión de los tiempos del reproductor
VELOCIDADES = [(0.75, "0,75×"), (1.0, "1×"), (1.25, "1,25×"), (1.5, "1,5×"), (2.0, "2×")]

CMD, OPT = 1 << 20, 1 << 19      # teclas ⌘ y ⌥
ANCHO_FLEX, ALTO_FLEX = 2, 16
PEGADO_ABAJO = 2 | 32
SOLO_ICONOS, UNIFICADA = 2, 3    # NSToolbarDisplayModeIconOnly, NSWindowToolbarStyleUnified
ESPACIO_FLEXIBLE = "NSToolbarFlexibleSpaceItem"
INSPECTOR = "NSToolbarToggleInspectorItem"
FONDO_TEMPORAL = "NSBackgroundColor"
ANTICIPO = 0.10                  # la siguiente entra antes de que acabe la anterior
SOLTAR_BLOQUE = 0.55             # lo que tarda en apagarse la intervención anterior
# el peso de la letra de la palabra dicha (0 es normal, 0,4 negrita)
PESOS = {"suave": 0.23, "media": 0.3, "fuerte": 0.4}
LETRA, INTERLETRA = "NSFont", "NSKern"


COLOR_RESALTE = NSColor.systemPurpleColor()
INVISIBLE = NSFont.systemFontOfSize_(0.01)      # lo que está en el archivo pero no se dibuja
AIRE = 40.0
TAMANOS = (12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0)     # los del ajuste
COLUMNA = 540.0                  # ~70 caracteres por línea, que es lo cómodo de leer


def reloj(segundos: float) -> str:
    segundos = max(0, int(segundos))
    if segundos >= 3600:
        return f"{segundos // 3600}:{segundos % 3600 // 60:02d}:{segundos % 60:02d}"
    return f"{segundos // 60}:{segundos % 60:02d}"


def parrafo(cabecera: float):
    """Estilo de un párrafo del editor, con el hueco de arriba para su cabecera.

    Alineado a la izquierda: justificar en una sola columna abre ríos de espacio
    entre palabras y se lee como un fallo de composición.
    """
    p = ui.NSMutableParagraphStyle.alloc().init()
    p.setLineHeightMultiple_(1.35)
    p.setParagraphSpacingBefore_(cabecera)
    p.setAlignment_(ui.ALIGN_LEFT)
    return p


class Bloque:
    """Una intervención: dónde está en el archivo, cuándo suena y quién habla.

    `tamano` es el del nombre, que va atado al del texto: quien habla siempre se
    lee un punto más grande que lo que dice.
    """

    def __init__(self, inicio, fin, desde, hasta, numero, nombre, color, tamano=15.0, texto=None):
        self.inicio, self.fin = inicio, fin
        self.texto = inicio if texto is None else texto   # después del «Ana: » escondido
        self.desde, self.hasta = desde, hasta
        self.numero, self.nombre, self.color = numero, nombre, color
        self.tamano = tamano

    @property
    def hora_tamano(self) -> float:
        return max(self.tamano - 6.0, 10.0)

    @property
    def cabecera(self) -> float:
        if self.nombre:
            return self.tamano + 16.0
        return self.tamano + 14.0 if self.desde is not None else AIRE

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
    ⌘ + clic en una palabra salta a ese momento y ⌥ + espacio reproduce o pausa.

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
            izquierda = self.textContainerOrigin().x
            ancho = self.bounds().size.width - izquierda
            # el renglón de la cabecera, encima del párrafo
            alto = y - bloque.tamano - 8
            x = izquierda
            escrito = dueno.comoSeLlama(bloque)
            if escrito and bloque.numero != dueno.editandoEnElTexto():
                nombre = ui.attributed(escrito, bloque.tamano, ui.W_SEMIBOLD, bloque.color,
                                       ui.ALIGN_LEFT)
                nombre.drawInRect_(NSMakeRect(x, alto, ancho, bloque.tamano + 5))
                x += nombre.size().width + 9
            if bloque.cuando:
                ui.cifras(bloque.cuando, bloque.hora_tamano, NSColor.tertiaryLabelColor(),
                          ui.W_REGULAR).drawInRect_(
                    NSMakeRect(x, alto + 3, ancho - x, bloque.hora_tamano + 4))

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
            izquierda = self.textContainerOrigin().x
            if bloque.nombre:
                self.addCursorRect_cursor_(
                    NSMakeRect(izquierda, y - bloque.cabecera, dueno.anchoNombre(bloque), 20),
                    NSCursor.pointingHandCursor())
            if bloque.cuando:
                self.addCursorRect_cursor_(
                    NSMakeRect(izquierda, y - 24, 120, 16), NSCursor.pointingHandCursor())

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
        self.resaltada, self.cambio = None, 0.0
        self.bloque_activo, self.anterior = None, None
        self.pintadas = {}                    # qué trozos están marcados ahora
        self.lectura = float(pref.leer(pref.TAMANO))
        self.campo_nombre = None
        self.oculto = None
        self.filas_persona = {}
        self.encontrado, self.cual = [], -1
        self.anchos = {}
        self.veloz = 1
        self.ver_panel = bool(pref.leer(pref.PANEL))
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
        """La ventana la reparte el sistema: barra de herramientas arriba, el texto
        y el inspector en una división, y el reproductor abajo."""
        rect = NSMakeRect(0, 0, W, H)
        self.ventana = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, ui.STYLE_TITLED | ui.STYLE_CLOSABLE | ui.STYLE_MINI | ui.STYLE_RESIZABLE,
            NSBackingStoreBuffered, False)
        self.ventana.setTitle_(self.ficha.get("nombre", "Transcripción"))
        self.ventana.setReleasedWhenClosed_(False)
        self.ventana.setMinSize_((680, 460))
        self.ventana.setDelegate_(self)
        self.ventana.center()

        self.vc_texto = NSViewController.alloc().init()
        self.vc_texto.setView_(self.construirTexto())
        self.vc_panel = NSViewController.alloc().init()
        self.vc_panel.setView_(self.construirPanel())

        self.division = NSSplitViewController.alloc().init()
        self.division.addSplitViewItem_(
            NSSplitViewItem.splitViewItemWithViewController_(self.vc_texto))
        hacer_inspector = getattr(NSSplitViewItem, "inspectorWithViewController_", None)
        self.item_panel = (hacer_inspector(self.vc_panel) if hacer_inspector
                           else NSSplitViewItem.sidebarWithViewController_(self.vc_panel))
        self.item_panel.setMinimumThickness_(PANEL_W - 20)
        self.item_panel.setMaximumThickness_(PANEL_W + 60)
        self.item_panel.setCollapsed_(not self.ver_panel)
        self.division.addSplitViewItem_(self.item_panel)

        raiz = NSViewController.alloc().init()
        marco = NSView.alloc().initWithFrame_(rect)
        raiz.setView_(marco)
        raiz.addChildViewController_(self.division)
        self.division.view().setFrame_(NSMakeRect(0, TRANSPORTE, W, H - TRANSPORTE))
        self.division.view().setAutoresizingMask_(ANCHO_FLEX | ALTO_FLEX)
        marco.addSubview_(self.division.view())
        self.construirTransporte(marco)
        self.ventana.setContentViewController_(raiz)
        self.construirBarra()
        self.pintarDetalle()

    # ------------------------------------------------- barra de herramientas --
    @objc.python_method
    def construirBarra(self):
        barra = NSToolbar.alloc().initWithIdentifier_("transcripcion")
        barra.setDelegate_(self)
        barra.setDisplayMode_(SOLO_ICONOS)
        barra.setAllowsUserCustomization_(False)
        self.ventana.setToolbar_(barra)
        if hasattr(self.ventana, "setToolbarStyle_"):
            self.ventana.setToolbarStyle_(UNIFICADA)

    @objc.python_method
    def piezas(self):
        return [ESPACIO_FLEXIBLE, "exportar", "finder", "buscar", INSPECTOR]

    def toolbarDefaultItemIdentifiers_(self, barra):
        return self.piezas()

    def toolbarAllowedItemIdentifiers_(self, barra):
        return self.piezas()

    def toolbar_itemForItemIdentifier_willBeInsertedIntoToolbar_(self, barra, cual, insertar):
        if cual == "buscar":
            item = NSSearchToolbarItem.alloc().initWithItemIdentifier_(cual)
            item.setResignsFirstResponderWithCancel_(True)
            self.buscador = item.searchField()
            self.buscador.setPlaceholderString_("Buscar")
            self.buscador.setDelegate_(self)
            self.buscador.setTarget_(self)
            self.buscador.setAction_(b"buscarSiguiente:")
            return item
        if cual in ("exportar", "finder"):
            simbolo, titulo, accion, ayuda = {
                "exportar": ("square.and.arrow.up", "Exportar", b"menuExportar:",
                             "Exportar a PDF o a Word"),
                "finder": ("folder", "Finder", b"mostrarEnFinder:", "Mostrar en Finder"),
            }[cual]
            item = NSToolbarItem.alloc().initWithItemIdentifier_(cual)
            item.setLabel_(titulo)
            item.setToolTip_(ayuda)
            item.setImage_(ui.sf(simbolo, 16.0))
            item.setTarget_(self)
            item.setAction_(accion)
            if hasattr(item, "setBordered_"):
                item.setBordered_(True)
            return item
        return None                      # los del sistema los pone AppKit

    def alternarPanel_(self, sender):
        """Por si el sistema no trae el botón de inspector (macOS anterior)."""
        self.item_panel.animator().setCollapsed_(not self.item_panel.isCollapsed())

    @objc.python_method
    def personas(self):
        """Los números de persona que aparecen en el texto, en orden."""
        cuantas = int(self.ficha.get("cuantas_personas") or 0)
        nombres = self.ficha.get("personas") or {}
        return [str(n) for n in range(1, cuantas + 1)] or sorted(nombres)

    # ------------------------------------------------------------------ panel --
    @objc.python_method
    def construirPanel(self):
        """El inspector: quién habla y qué es este archivo."""
        self.panel = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, PANEL_W, H - TRANSPORTE))
        self.dentro_panel = ui.VistaVolteada.alloc().initWithFrame_(self.panel.bounds())
        self.dentro_panel.setAutoresizingMask_(ANCHO_FLEX | ALTO_FLEX)
        self.panel.addSubview_(self.dentro_panel)
        self.pintarPanel()
        return self.panel

    @objc.python_method
    def pintarPanel(self):
        caja = self.dentro_panel
        for vista in list(caja.subviews()):
            vista.removeFromSuperview()
        ancho = caja.frame().size.width
        margen, eje = 20.0, 92.0                  # el eje donde se juntan etiqueta y valor
        util = ancho - margen * 2
        y = [18.0]                                # de arriba hacia abajo (vista volteada)

        def titulo(texto, primero=False):
            if not primero:
                y[0] += 14
                caja.addSubview_(ui.hairline(NSMakeRect(margen, y[0], util, 1)))
                y[0] += 16
            caja.addSubview_(ui.section_title(texto, NSMakeRect(margen, y[0], util, 16)))
            y[0] += 22

        def control(etiqueta, vista, alto=22.0):
            """Una fila del panel con su control a la derecha del mismo eje."""
            caja.addSubview_(ui.label(etiqueta, 11.0, ui.W_REGULAR, NSColor.secondaryLabelColor(),
                                      NSMakeRect(margen, y[0] + (alto - 15) / 2 + 1,
                                                 eje - margen - 8, 15), ui.ALIGN_RIGHT))
            vista.setFrame_(NSMakeRect(eje - 4, y[0], ancho - eje - margen + 4, alto))
            caja.addSubview_(vista)
            y[0] += alto + 6

        def dato(etiqueta, valor):
            caja.addSubview_(ui.label(etiqueta, 11.0, ui.W_REGULAR, NSColor.secondaryLabelColor(),
                                      NSMakeRect(margen, y[0] + 2, eje - margen - 8, 15),
                                      ui.ALIGN_RIGHT))
            caja.addSubview_(ui.label(valor, 11.0, ui.W_REGULAR, NSColor.labelColor(),
                                      NSMakeRect(eje, y[0] + 2, ancho - eje - margen, 15),
                                      ui.ALIGN_LEFT, truncate=ui.TRUNC_MIDDLE))
            y[0] += 20

        nombres = self.ficha.get("personas") or {}
        quienes = self.personas()
        self.filas_persona = {}
        if quienes:
            titulo("PERSONAS", primero=True)
            for i, numero in enumerate(quienes):
                color = ui.COLORES_PERSONA[i % len(ui.COLORES_PERSONA)]
                fila = NSView.alloc().initWithFrame_(NSMakeRect(margen, y[0], util, 24))
                caja.addSubview_(fila)
                fila.addSubview_(ui.rounded(NSMakeRect(0, 7, 10, 10), 5.0, fill=color,
                                            clase=ui.Decorativa))
                fila.addSubview_(ui.label((nombres.get(numero) or "").strip() or f"Persona {numero}",
                                          13.0, ui.W_REGULAR, NSColor.labelColor(),
                                          NSMakeRect(20, 3, util - 44, 17), ui.ALIGN_LEFT,
                                          truncate=ui.TRUNC_TAIL))
                fila.addSubview_(ui.etiqueta_cifras(numero, 11.0, NSColor.tertiaryLabelColor(),
                                                    NSMakeRect(util - 20, 3, 20, 16),
                                                    ui.ALIGN_RIGHT))
                boton = NSButton.alloc().initWithFrame_(NSMakeRect(margen, y[0], util, 24))
                boton.setBordered_(False)
                boton.setTitle_("")
                boton.setTarget_(self)
                boton.setAction_(b"renombrarPersona:")
                boton.setTag_(int(numero))
                boton.setToolTip_("Ponle su nombre")
                caja.addSubview_(boton)
                self.filas_persona[numero] = (fila, boton)
                y[0] += 24

        ruta = biblioteca.ubicar(self.ficha)
        ajustes = self.ficha.get("ajustes") or {}
        titulo("DETALLES", primero=not quienes)
        dato("Duración", reloj(self.ficha.get("duracion") or 0))
        dato("Fecha", exportar.fecha_corta(self.ficha.get("creado")))
        dato("Idioma", {"es": "Español", "en": "Inglés"}.get(ajustes.get("idioma"), "Automático"))
        dato("Precisión", "Máxima" if ajustes.get("precision") == "alta" else "Rápida")
        dato("Formato", {"parrafos": "Párrafos", "tiempos": "Con tiempos",
                         "srt": "Subtítulos"}.get(self.ficha.get("formato"), "Párrafos"))
        if ruta is not None:
            dato("Carpeta", "Escritorio" if ruta.parent == biblioteca.ESCRITORIO else ruta.parent.name)
        if self.ficha.get("cliente"):
            dato("Lo pidió", self.ficha["cliente"])

        titulo("RESALTADO")
        if self.tiene_audio:
            tipos = [pref.ETIQUETAS[pref.RESALTADO][c] for c in ("palabra", "fondo")]
            menu_tipo = ui.popup(NSMakeRect(0, 0, 10, 22), tipos, self, b"elegirResaltado:")
            menu_tipo.setControlSize_(1)
            menu_tipo.selectItemAtIndex_(0 if pref.leer(pref.RESALTADO) == "palabra" else 1)
            control("Marca", menu_tipo)

            fuerzas = [pref.ETIQUETAS[pref.FUERZA][c] for c in ("suave", "media", "fuerte")]
            menu_fuerza = ui.popup(NSMakeRect(0, 0, 10, 22), fuerzas, self, b"elegirFuerza:")
            menu_fuerza.setControlSize_(1)
            menu_fuerza.selectItemAtIndex_(
                ("suave", "media", "fuerte").index(pref.leer(pref.FUERZA)))
            control("Fuerza", menu_fuerza)
            y[0] += 6

        if not self.palabras and self.tiene_audio:
            self.boton_tiempos = ui.bezel_button("Calcular los tiempos",
                                                 NSMakeRect(margen, y[0], util, 24),
                                                 self, b"activarResaltado:", size=11.5)
            self.boton_tiempos.setToolTip_(
                "Vuelve a escuchar el audio para saber cuándo suena cada palabra.\n"
                "Tu texto no cambia: se respeta tal como está.")
            caja.addSubview_(self.boton_tiempos)
            y[0] += 30
            caja.addSubview_(ui.label("Esta transcripción no guardó cuándo suena cada palabra.",
                                      11.0, ui.W_REGULAR, NSColor.tertiaryLabelColor(),
                                      NSMakeRect(margen, y[0], util, 30), ui.ALIGN_LEFT))
        elif self.palabras and self.tiene_audio:
            caja.addSubview_(ui.label("⌘ + clic en una palabra para escucharla desde ahí.",
                                      11.0, ui.W_REGULAR, NSColor.tertiaryLabelColor(),
                                      NSMakeRect(margen, y[0], util, 30), ui.ALIGN_LEFT))

    # ------------------------------------------------------------------ texto --
    @objc.python_method
    def construirTexto(self):
        marco = NSMakeRect(0, 0, W - PANEL_W, H - TRANSPORTE)
        fondo = NSView.alloc().initWithFrame_(marco)
        fondo.setWantsLayer_(True)
        fondo.layer().setBackgroundColor_(NSColor.textBackgroundColor().CGColor())

        self.scroll = scroll = NSScrollView.alloc().initWithFrame_(marco)
        scroll.setHasVerticalScroller_(True)
        scroll.setAutohidesScrollers_(True)
        scroll.setDrawsBackground_(False)
        scroll.setAutoresizingMask_(ANCHO_FLEX | ALTO_FLEX)

        ancho = marco.size.width
        self.texto = VistaTexto.alloc().initWithFrame_(NSMakeRect(0, 0, ancho, marco.size.height))
        self.texto.dueno = self
        self.texto.setDelegate_(self)
        self.texto.setWantsLayer_(True)
        self.texto.setAllowsUndo_(True)
        self.texto.setDrawsBackground_(False)
        self.texto.setRichText_(False)
        self.texto.setMinSize_((0, 0))
        self.texto.setMaxSize_((1e7, 1e7))
        self.texto.setVerticallyResizable_(True)
        self.texto.setHorizontallyResizable_(False)
        self.texto.setAutoresizingMask_(ANCHO_FLEX)
        self.texto.setTextContainerInset_((0, AIRE))
        self.texto.textContainer().setLineFragmentPadding_(0.0)
        self.texto.textContainer().setWidthTracksTextView_(True)
        self.texto.textContainer().setContainerSize_((ancho, 1e7))
        scroll.setDocumentView_(self.texto)
        fondo.addSubview_(scroll)
        return fondo

    # ------------------------------------------------------------ reproductor --
    @objc.python_method
    def construirTransporte(self, marco):
        barra = ui.material(NSMakeRect(0, 0, W, TRANSPORTE), ui.MATERIAL_BARRA)
        barra.setAutoresizingMask_(PEGADO_ABAJO)
        marco.addSubview_(barra)
        barra.addSubview_(ui.hairline(NSMakeRect(0, TRANSPORTE - 1, W, 1)))
        medio = (TRANSPORTE - 28) / 2

        if not self.tiene_audio:
            barra.addSubview_(ui.icon_view("waveform.slash", NSMakeRect(PAD, medio + 5, 18, 18),
                                           NSColor.tertiaryLabelColor(), 13.0))
            barra.addSubview_(ui.label("No se encontró el audio original, así que no se puede escuchar.",
                                       11.5, ui.W_REGULAR, NSColor.tertiaryLabelColor(),
                                       NSMakeRect(PAD + 26, medio + 7, W - PAD * 2 - 26, 16),
                                       ui.ALIGN_LEFT))
            return

        def boton(simbolo, accion, ayuda, x, tamano=16.0):
            b = ui.symbol_button(simbolo, NSMakeRect(x, medio, 28, 28), self, accion,
                                 tooltip=ayuda, size=tamano, tint=NSColor.labelColor())
            barra.addSubview_(b)
            return b

        x = PAD
        boton("gobackward.15", b"atras:", "15 s atrás", x)
        self.boton_play = boton("play.fill", b"reproducir:", "Reproducir o pausar (⌥ + espacio)",
                                x + 32, 22.0)
        boton("goforward.15", b"adelante:", "15 s adelante", x + 64)

        # [botones] 16 [ahora] 8 [barra] 8 [total] 16 [velocidad]
        reloj_w, veloz_w = 44.0, 56.0
        self.tiempo = ui.label("0:00", 11.0, ui.W_REGULAR, NSColor.secondaryLabelColor(),
                               NSMakeRect(PAD + 92 + 16, medio + 7, reloj_w, 15), ui.ALIGN_RIGHT)
        barra.addSubview_(self.tiempo)

        self.velocidad = ui.popup(NSMakeRect(W - PAD - veloz_w, medio + 2, veloz_w, 22),
                                  [t for _, t in VELOCIDADES], self, b"cambiarVelocidad:")
        self.velocidad.setBordered_(False)
        self.velocidad.setControlSize_(1)
        self.velocidad.selectItemAtIndex_(1)
        self.velocidad.setToolTip_("Velocidad de reproducción")
        self.velocidad.setAutoresizingMask_(1)
        barra.addSubview_(self.velocidad)

        derecha = W - PAD - veloz_w - 16
        self.total = ui.label("0:00", 11.0, ui.W_REGULAR, NSColor.secondaryLabelColor(),
                              NSMakeRect(derecha - reloj_w, medio + 7, reloj_w, 15), ui.ALIGN_LEFT)
        self.total.setAutoresizingMask_(1)
        barra.addSubview_(self.total)

        izquierda = PAD + 92 + 16 + reloj_w + 8
        self.barra = NSSlider.alloc().initWithFrame_(
            NSMakeRect(izquierda, medio + 4, derecha - reloj_w - 8 - izquierda, 20))
        self.barra.setControlSize_(1)
        self.barra.setMinValue_(0.0)
        self.barra.setMaxValue_(max(self.ficha.get("duracion") or 1.0, 1.0))
        self.barra.setTarget_(self)
        self.barra.setAction_(b"mover:")
        self.barra.setAutoresizingMask_(ANCHO_FLEX)
        barra.addSubview_(self.barra)

    # -------------------------------------------------------------- contenido --
    @objc.python_method
    def cargar(self, contenido):
        """Pone el texto en la ventana con el estilo de lectura y prepara el resaltado."""
        self.texto.setTypingAttributes_({
            "NSFont": NSFont.systemFontOfSize_(self.lectura),
            "NSColor": NSColor.labelColor(),
            "NSParagraphStyle": parrafo(0.0)})
        self.texto.setString_(contenido)
        almacen = self.texto.textStorage()
        almacen.setAttributes_range_(self.texto.typingAttributes(),
                                     NSMakeRange(0, almacen.length()))
        self.guardado = contenido
        self.pintadas, self.resaltada = {}, None
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
        self.bloques, posicion, self.pintadas = [], 0, {}
        self.bloque_activo, self.anterior = None, None
        almacen = self.texto.textStorage()
        almacen.beginEditing()
        almacen.setAttributes_range_({"NSFont": NSFont.systemFontOfSize_(self.lectura),
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
                            else NSColor.secondaryLabelColor(),
                            tamano=self.lectura + 3,
                            texto=posicion + min(largo + 1, fin - posicion))
            self.bloques.append(bloque)
            if largo:                            # el «Ana:» se dibuja arriba, no en la línea
                almacen.addAttributes_range_({"NSFont": INVISIBLE, "NSColor": NSColor.clearColor()},
                                             NSMakeRange(posicion, min(largo + 1, fin - posicion)))
            almacen.addAttribute_value_range_("NSParagraphStyle", parrafo(bloque.cabecera),
                                              NSMakeRange(posicion, fin - posicion))
            posicion = fin + 1
        almacen.endEditing()
        # TextKit no aplica el hueco superior al primer párrafo: se lo da la vista
        self.aire_arriba = (self.bloques[0].cabecera if self.bloques else 0) + AIRE
        self.ajustarColumna()
        self.texto.setNeedsDisplay_(True)
        self.ventana.invalidateCursorRectsForView_(self.texto)

    def cambiarResaltado_(self, sender):
        """Menú Ver: la palabra en negrita (como Apple Music) o un fondo suave."""
        self.apagarResaltado()
        pref.escribir(pref.RESALTADO, "palabra" if sender.tag() == 0 else "fondo")
        self.pintarPanel()

    def elegirResaltado_(self, sender):
        self.apagarResaltado()
        pref.escribir(pref.RESALTADO, ("palabra", "fondo")[sender.indexOfSelectedItem()])

    def elegirFuerza_(self, sender):
        self.apagarResaltado()
        pref.escribir(pref.FUERZA, ("suave", "media", "fuerte")[sender.indexOfSelectedItem()])

    def cambiarFuerza_(self, sender):
        """Menú Ver: cuánto se marca la palabra que suena."""
        self.apagarResaltado()
        pref.escribir(pref.FUERZA, ("suave", "media", "fuerte")[sender.tag()])
        self.pintarPanel()

    def validateMenuItem_(self, item):
        """Las palomitas del menú marcan lo que está puesto ahora."""
        if item.action() == b"cambiarResaltado:":
            item.setState_(1 if pref.leer(pref.RESALTADO) ==
                           ("palabra" if item.tag() == 0 else "fondo") else 0)
        elif item.action() == b"cambiarFuerza:":
            item.setState_(1 if pref.leer(pref.FUERZA) ==
                           ("suave", "media", "fuerte")[item.tag()] else 0)
        return True

    def textoMasGrande_(self, sender):
        self.cambiarTamano(+1)

    def textoMasPequeno_(self, sender):
        self.cambiarTamano(-1)

    @objc.python_method
    def cambiarTamano(self, paso):
        """⌘+ y ⌘−: el tamaño se guarda, así que la próxima vez abre igual."""
        cerca = min(TAMANOS, key=lambda x: abs(x - self.lectura))
        i = min(max(TAMANOS.index(cerca) + paso, 0), len(TAMANOS) - 1)
        if TAMANOS[i] == self.lectura:
            return
        self.lectura = TAMANOS[i]
        pref.escribir(pref.TAMANO, str(int(self.lectura)))
        donde = self.texto.selectedRange()
        self.cargar(self.contenido()) if not self.sucio else self.repintarTexto()
        self.texto.setSelectedRange_(donde)

    @objc.python_method
    def repintarTexto(self):
        """Aplica el tamaño nuevo sin recargar el archivo (hay cambios sin guardar)."""
        almacen = self.texto.textStorage()
        almacen.beginEditing()
        almacen.addAttribute_value_range_("NSFont", NSFont.systemFontOfSize_(self.lectura),
                                          NSMakeRange(0, almacen.length()))
        almacen.endEditing()
        self.texto.setTypingAttributes_(dict(self.texto.typingAttributes(),
                                             NSFont=NSFont.systemFontOfSize_(self.lectura)))
        self.rehacerMapa()

    @objc.python_method
    def ajustarColumna(self):
        """Una columna de lectura centrada: las líneas muy largas cansan la vista."""
        ancho = self.texto.frame().size.width
        lado = max((ancho - COLUMNA) / 2.0, 0.0)
        self.texto.setTextContainerInset_((lado, getattr(self, "aire_arriba", AIRE)))
        self.texto.textContainer().setContainerSize_((max(ancho - lado * 2, 100.0), 1e7))
        self.texto.setNeedsDisplay_(True)

    def windowDidResize_(self, notificacion):
        self.ajustarColumna()

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
        """Qué persona se está renombrando ahora mismo."""
        return self.campo_nombre[1] if self.campo_nombre else None

    @objc.python_method
    def editandoEnElTexto(self):
        """Igual, pero solo si el campo está encima del propio texto: ahí sí estorba."""
        if self.campo_nombre and self.campo_nombre[0].superview() is self.texto:
            return self.campo_nombre[1]
        return None

    @objc.python_method
    def comoSeLlama(self, bloque):
        """El nombre que toca dibujar: mientras se escribe, lo que lleve escrito."""
        if self.campo_nombre and self.campo_nombre[1] == bloque.numero:
            return self.campo_nombre[0].stringValue().strip() or f"Persona {bloque.numero}"
        return bloque.nombre

    @objc.python_method
    def anchoNombre(self, bloque):
        return ui.attributed(bloque.nombre, bloque.tamano, ui.W_SEMIBOLD,
                             bloque.color).size().width + 10

    @objc.python_method
    def zonaCabecera(self, punto):
        """Qué hay bajo el ratón en la cabecera de una intervención: su nombre o su hora."""
        for bloque in self.bloques:
            if not bloque.cabecera:
                continue
            y = self.altoDeBloque(bloque)
            if y is None or not (y - bloque.cabecera <= punto.y <= y - 3):
                continue
            izquierda = self.texto.textContainerOrigin().x
            if bloque.nombre and punto.y <= y - bloque.cabecera + bloque.tamano + 6 \
                    and izquierda <= punto.x <= izquierda + self.anchoNombre(bloque):
                return bloque, "nombre"
            if bloque.desde is not None and izquierda <= punto.x <= izquierda + 120:
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
                         NSMakeRect(self.texto.textContainerOrigin().x - 3, y - bloque.cabecera,
                                    max(self.anchoNombre(bloque) + 40, 160),
                                    bloque.tamano + 8), bloque.tamano)

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
        for vista in getattr(self, "oculto", ()) or ():
            vista.setHidden_(False)
        self.oculto = None
        self.texto.setNeedsDisplay_(True)
        self.ventana.makeFirstResponder_(self.texto)

    def controlTextDidChange_(self, notificacion):
        if notificacion.object() is self.buscador:
            self.buscar_en_texto(self.buscador.stringValue())
        elif self.campo_nombre and notificacion.object() is self.campo_nombre[0]:
            self.texto.setNeedsDisplay_(True)      # el nombre se ve cambiar en el texto

    def control_textView_doCommandBySelector_(self, control, vista, selector):
        if selector != "cancelOperation:":
            return False
        if control is self.buscador:                 # Esc limpia la búsqueda
            self.buscador.setStringValue_("")
            self.buscar_en_texto("")
            self.ventana.makeFirstResponder_(self.texto)
        else:
            self.cerrarCampoNombre()
        return True

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
    def pintarDetalle(self, texto=None):
        """El subtítulo de la ventana, que pinta el sistema bajo el título."""
        if texto is None:
            ruta = biblioteca.ubicar(self.ficha)
            partes = [reloj(self.ficha.get("duracion") or 0)]
            if ruta is not None:
                partes.append("Escritorio" if ruta.parent == biblioteca.ESCRITORIO
                              else ruta.parent.name)
            texto = " · ".join(partes)
        if hasattr(self.ventana, "setSubtitle_"):
            self.ventana.setSubtitle_(texto)
        if getattr(self, "dentro_panel", None) is not None:
            self.pintarPanel()

    @objc.python_method
    def marcarSucio(self, sucio):
        self.sucio = sucio
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

    def windowDidResignKey_(self, notificacion):
        """Al salir de la ventana se guarda solo, como hacen las apps del sistema.
        Lo que se escribe aquí es tu archivo, y ⌘Z sigue deshaciendo."""
        self.cerrarCampoNombre()
        self.guardar()

    def windowShouldClose_(self, ventana):
        return self.guardar()

    def windowWillClose_(self, notificacion):
        pref.escribir(pref.PANEL, not self.item_panel.isCollapsed())
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
            CMTimeMakeWithSeconds(1.0 / 60.0, ESCALA), None, self.alSonar)

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
        self.tiempo.setAttributedStringValue_(ui.cifras(
            reloj(segundo), 11.0, NSColor.secondaryLabelColor(), ui.W_REGULAR))
        self.total.setAttributedStringValue_(ui.cifras(
            reloj(total), 11.0, NSColor.secondaryLabelColor(), ui.W_REGULAR))
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
            self.reproductor.setRate_(VELOCIDADES[self.veloz][0])
        self.boton_play.setImage_(ui.sf("pause.fill" if self.sonando() else "play.fill", 22.0))

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
        """⌘ + clic: suena desde la palabra que se ha pulsado."""
        for inicio, fin, desde, _ in self.mapa:
            if inicio <= posicion <= fin:
                self.buscar(desde)
                if not self.sonando():
                    self.alternarReproduccion()
                return

    # -------------------------------------------------------------- búsqueda --
    def buscarDocumento_(self, sender):
        """⌘F: al campo de búsqueda de esta transcripción."""
        self.ventana.makeFirstResponder_(self.buscador)

    def buscarSiguiente_(self, sender):
        self.buscar_en_texto(self.buscador.stringValue(), avanzar=True)

    @objc.python_method
    def buscar_en_texto(self, consulta, avanzar=False):
        """Marca todo lo que coincide y lleva a la siguiente coincidencia."""
        gestor = self.texto.layoutManager()
        largo = len(self.contenido())
        for rango in self.encontrado:
            gestor.removeTemporaryAttribute_forCharacterRange_(FONDO_TEMPORAL, NSMakeRange(*rango))
        self.encontrado = []
        consulta = (consulta or "").strip()
        if len(consulta) < 2:
            self.pintarCuantas(0)
            return
        texto, aguja, desde = self.contenido().lower(), consulta.lower(), 0
        while True:
            donde = texto.find(aguja, desde)
            if donde < 0 or donde + len(aguja) > largo:
                break
            self.encontrado.append((donde, len(aguja)))
            desde = donde + len(aguja)
        for rango in self.encontrado:
            gestor.addTemporaryAttributes_forCharacterRange_(
                {FONDO_TEMPORAL: NSColor.systemYellowColor().colorWithAlphaComponent_(0.35)},
                NSMakeRange(*rango))
        self.pintarCuantas(len(self.encontrado))
        if not self.encontrado:
            return
        if avanzar:
            self.cual = (self.cual + 1) % len(self.encontrado)
        else:
            self.cual = 0
        rango = NSMakeRange(*self.encontrado[self.cual])
        self.texto.scrollRangeToVisible_(rango)
        self.texto.showFindIndicatorForRange_(rango)

    @objc.python_method
    def pintarCuantas(self, cuantas):
        consulta = self.buscador.stringValue().strip()
        if not consulta:
            self.pintarDetalle()
        elif cuantas:
            self.pintarDetalle(f"{cuantas} coincidencia{'s' if cuantas > 1 else ''}"
                               f" de «{consulta}»")
        else:
            self.pintarDetalle(f"Nada que diga «{consulta}»")

    # -------------------------------------------------------------- resaltado --
    @objc.python_method
    def resaltar(self, segundo):
        """Marca la palabra que suena, sin tocar el texto ni el deshacer.

        Se pinta sobre el propio texto (atributos temporales del gestor de
        composición): nada de capas encima, así que encaja perfecto por definición.
        La negrita se hace engordando el trazo de la letra, que no cambia el ancho
        de avance y por eso el renglón no se mueve ni un píxel.
        """
        if not self.mapa:
            return
        if pref.leer(pref.RESALTADO) == "fondo":
            self.resaltarFondo(segundo)
            return
        # la siguiente empieza a marcarse un pelín antes de que acabe la anterior,
        # para que una entre mientras la otra sale y no haya saltos
        t = segundo + ANTICIPO
        i = bisect_right(self.inicios, t) - 1
        if i < 0 or t > self.mapa[i][3] + 0.5:
            i = None
        largo_texto = len(self.contenido())
        peso = PESOS.get(pref.leer(pref.FUERZA), PESOS["fuerte"])
        deseado, bloque = {}, None
        if i is not None:
            inicio, fin, desde, hasta = self.mapa[i]
            bloque = self.bloqueDe(inicio)
            if fin <= largo_texto and bloque is not None:
                letras = fin - inicio
                avance = min(max((t - desde) / max(hasta - desde, 0.08), 0.0), 1.0)
                justo = avance * letras
                enteras = min(int(justo), letras)
                resto = justo - enteras
                # lo ya dicho de esta intervención se queda marcado, como en Apple
                # Music: la luz no se apaga hasta que acaba quien está hablando
                dicho = inicio + enteras - bloque.texto
                if dicho > 0:
                    deseado[(bloque.texto, dicho)] = peso
                if enteras < letras and resto > 0.03:
                    # la letra en la que va la voz engorda poco a poco, no de golpe
                    deseado[(inicio + enteras, 1)] = round(peso * resto, 3)
                if self.sonando():
                    self.texto.scrollRangeToVisible_(NSMakeRange(inicio, letras))
        if bloque is not self.bloque_activo:
            self.anterior, self.bloque_activo, self.cambio = self.bloque_activo, bloque, segundo
        # al cambiar de intervención, la anterior se va apagando poco a poco
        queda = 1.0 - (segundo - self.cambio) / SOLTAR_BLOQUE
        if self.anterior is not None and 0.04 < queda <= 1.0 \
                and self.anterior.fin <= largo_texto:
            deseado[(self.anterior.texto, self.anterior.fin - self.anterior.texto)] = \
                round(peso * queda ** 1.8, 3)
        self.resaltada = i
        self.aplicarGrosor(deseado)

    @objc.python_method
    def bloqueDe(self, posicion):
        """La intervención a la que pertenece esa parte del texto."""
        for bloque in self.bloques:
            if bloque.inicio <= posicion < bloque.fin:
                return bloque
        return None

    @objc.python_method
    def aplicarGrosor(self, deseado):
        """Deja puesto justo lo que toca, tocando solo lo que cambió.

        Se cambia la letra a una más gruesa de verdad, no un trazo engordado: el
        trazo ensancha el dibujo sin dar más sitio y acaba comiéndose el hueco
        entre letras. La negrita sí ocupa un pelín más, así que se compensa con
        interletraje para que la línea mida exactamente lo mismo y nada se mueva.
        """
        if deseado == self.pintadas:
            return
        almacen = self.texto.textStorage()
        normal = NSFont.systemFontOfSize_(self.lectura)
        almacen.beginEditing()
        for rango in list(self.pintadas):
            if deseado.get(rango) != self.pintadas[rango]:
                almacen.addAttribute_value_range_(LETRA, normal, NSMakeRange(*rango))
                almacen.removeAttribute_range_(INTERLETRA, NSMakeRange(*rango))
                del self.pintadas[rango]
        for rango, peso in deseado.items():
            if rango in self.pintadas:
                continue
            trozo = self.contenido()[rango[0]:rango[0] + rango[1]]
            almacen.addAttributes_range_(
                {LETRA: NSFont.systemFontOfSize_weight_(self.lectura, peso),
                 INTERLETRA: self.compensar(trozo, peso)}, NSMakeRange(*rango))
            self.pintadas[rango] = peso
        almacen.endEditing()

    @objc.python_method
    def compensar(self, trozo, peso):
        """Cuánto hay que apretar cada letra para que la negrita mida lo mismo."""
        if not trozo or peso <= 0:
            return 0.0
        clave = (trozo, round(peso, 3), self.lectura)
        if clave not in self.anchos:
            de_menos = (ui.ancho(trozo, self.lectura, ui.W_REGULAR)
                        - ui.ancho(trozo, self.lectura, peso))
            self.anchos[clave] = de_menos / len(trozo)
            if len(self.anchos) > 4000:
                self.anchos.clear()
        return self.anchos[clave]

    @objc.python_method
    def resaltarFondo(self, segundo):
        """La otra forma de marcarla: un fondo suave en toda la palabra."""
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
            {FONDO_TEMPORAL: COLOR_RESALTE.colorWithAlphaComponent_(0.28)}, rango)
        if self.sonando():
            self.texto.scrollRangeToVisible_(rango)

    @objc.python_method
    def apagarResaltado(self):
        """Quita cualquier marca: al cerrar, al recargar o al cambiar de ajuste."""
        almacen = self.texto.textStorage()
        todo = NSMakeRange(0, almacen.length())
        almacen.beginEditing()
        for rango in self.pintadas:
            almacen.addAttribute_value_range_(
                LETRA, NSFont.systemFontOfSize_(self.lectura), NSMakeRange(*rango))
        almacen.removeAttribute_range_(INTERLETRA, todo)
        almacen.endEditing()
        self.texto.layoutManager().removeTemporaryAttribute_forCharacterRange_(FONDO_TEMPORAL, todo)
        self.pintadas = {}
        self.resaltada = None

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
        self.veloz = sender.indexOfSelectedItem()
        if self.sonando():
            self.reproductor.setRate_(VELOCIDADES[self.veloz][0])

    def activarResaltado_(self, sender):
        if self.dueno.calcularTiempos(self.ficha) is not None:
            sender.setEnabled_(False)
            sender.setAttributedTitle_(ui.attributed("Calculando…", 12.0, ui.W_REGULAR,
                                                     NSColor.secondaryLabelColor()))

    def mostrarEnFinder_(self, sender):
        ruta = biblioteca.ubicar(self.ficha)
        if ruta is not None:
            NSWorkspace.sharedWorkspace().activateFileViewerSelectingURLs_(
                [NSURL.fileURLWithPath_(str(ruta))])

    def menuExportar_(self, sender):
        ui.desplegar_menu(sender, ["Exportar a PDF…", "Exportar a Word…"], self, b"exportarComo:")

    def exportarComo_(self, sender):
        """Exporta a PDF o a Word, preguntando dónde guardarlo."""
        formato = "pdf" if sender.tag() == 0 else "word"
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
    def renombrarPrimera_(self, sender):
        """Desde el menú: pone nombre a la primera persona que quede sin él."""
        pendientes = [n for n in self.personas()
                      if not (self.ficha.get("personas") or {}).get(n, "").strip()]
        quien = (pendientes or self.personas() or [None])[0]
        if quien is not None and quien in self.filas_persona:
            self.renombrarPersona_(self.filas_persona[quien][1])

    def renombrarPersona_(self, sender):
        """La fila del panel se convierte en un campo, en su sitio."""
        numero = str(sender.tag())
        fila = self.filas_persona.get(numero)
        marco = sender.frame()
        self.campoNombre(sender.tag(),
                         ui.COLORES_PERSONA[(sender.tag() - 1) % len(ui.COLORES_PERSONA)],
                         self.dentro_panel,
                         NSMakeRect(marco.origin.x, marco.origin.y, marco.size.width, 28), 12.5)
        if fila is not None and self.campo_nombre is not None:
            # la fila se esconde: si no, su nombre se vería debajo del campo
            self.oculto = fila
            for vista in fila:
                vista.setHidden_(True)

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
        self.pintarPanel()
        self.dueno.alGuardarFicha(self.ficha)
