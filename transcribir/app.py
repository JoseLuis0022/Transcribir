"""Transcribir: arrastra audios o videos y obtén un .txt con la transcripción."""

import os
import subprocess
import sys
import time
from itertools import count
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

import objc  # noqa: E402
import Quartz  # noqa: E402,F401  (ver ui.py)
from AppKit import (  # noqa: E402
    NSAlert, NSApplication, NSBackingStoreBuffered, NSColor, NSImage, NSImageView, NSMenu,
    NSMenuItem, NSOpenPanel, NSPasteboardTypeFileURL, NSPasteboardURLReadingFileURLsOnlyKey,
    NSPasteboard, NSPasteboardTypeString, NSProgressIndicator, NSScrollView, NSTextField,
    NSTimer, NSView, NSVisualEffectView,
    NSWindow, NSWorkspace,
)
from Foundation import NSURL, NSMakeRect, NSObject  # noqa: E402
from PyObjCTools import AppHelper  # noqa: E402

import agentes  # noqa: E402
import avisos  # noqa: E402
import biblioteca  # noqa: E402
import exportar  # noqa: E402
import formatos  # noqa: E402
from formatos import duracion_corta  # noqa: E402
import modelos  # noqa: E402
import preferencias as pref  # noqa: E402
import recursos  # noqa: E402
import servidor  # noqa: E402
import ui  # noqa: E402
from ajustes import ControladorAjustes  # noqa: E402
from bienvenida import Bienvenida  # noqa: E402
from editor import Editor  # noqa: E402
from estado import Estado  # noqa: E402
from historial import Historial  # noqa: E402
from identidad import COMPILACION, NOMBRE, REPO, VERSION  # noqa: E402
from motor import EXTENSIONES, Motor, Trabajo, ruta_libre  # noqa: E402
from vigia import Vigia  # noqa: E402

WIN_W, WIN_H = 440.0, 718.0
PAD = 22.0
CW = WIN_W - PAD * 2
COLA_H, HECHOS_H, PIE_H = 150.0, 170.0, 48.0
FILA_COLA, FILA_HECHO = 48.0, 50.0
LISTA_PAD = 8.0            # aire arriba y abajo dentro de las listas
BOTON = 20.0               # botones de encabezados y filas
ACCION = 74.0              # botón de texto de una fila: «Abrir», «Ubicar…»

VIDEO = {".mp4", ".mov"}
VIGILADA = "Carpeta vigilada"
ATENCION_INFORMATIVA = 10       # rebote único en el Dock
CMD, OPCION, MAYUS = 1 << 20, 1 << 19, 1 << 17
DEL_HISTORIAL = 300             # cuántas transcripciones se muestran de una vez


def srgb(r, g, b):
    return NSColor.colorWithSRGBRed_green_blue_alpha_(r, g, b, 1.0)


ESTADOS = {  # (arriba, abajo) del degradado del disco
    "reposo": (srgb(0.62, 0.64, 0.68), srgb(0.42, 0.44, 0.49)),
    "trabajo": (srgb(0.64, 0.54, 1.00), srgb(0.40, 0.29, 0.90)),
    "listo": (srgb(0.42, 0.84, 0.55), srgb(0.17, 0.60, 0.34)),
}


def plural(n: int, uno: str, varios: str) -> str:
    return f"{n} {uno if n == 1 else varios}"


def corto(nombre: str, largo: int = 34) -> str:
    if len(nombre) <= largo:
        return nombre
    mitad = (largo - 1) // 2
    return f"{nombre[:mitad]}…{nombre[-mitad:]}"


def expandir(rutas: list[Path]) -> list[Path]:
    """Archivos tal cual; de las carpetas, todos sus archivos (sin los ocultos)."""
    salida = []
    for ruta in rutas:
        if ruta.is_dir():
            salida += sorted(p for p in ruta.rglob("*") if p.is_file() and not p.name.startswith("."))
        elif ruta.is_file():
            salida.append(ruta)
    return salida


def estilo_cliente(cliente: str):
    """Símbolo y color de la etiqueta que dice quién pidió el trabajo."""
    if cliente == VIGILADA:
        return "eye.fill", NSColor.systemTealColor()
    if cliente == "Terminal":
        return "terminal.fill", NSColor.systemGrayColor()
    return "sparkles", NSColor.systemPurpleColor()


# ------------------------------------------------------------------- fondo --
class FondoArrastrable(NSVisualEffectView):
    """El fondo de la ventana acepta archivos arrastrados desde Finder."""

    @objc.python_method
    def rutas(self, sender):
        urls = sender.draggingPasteboard().readObjectsForClasses_options_(
            [NSURL], {NSPasteboardURLReadingFileURLsOnlyKey: True}) or []
        return [Path(u.path()) for u in urls]

    def draggingEntered_(self, sender):
        if self.dueno.bienvenida is not None:          # primero hay que descargar el modelo
            return 0
        if any(r.is_dir() or r.suffix.lower() in EXTENSIONES for r in self.rutas(sender)):
            self.dueno.arrastrando(True)
            return 1                                      # copiar
        return 0

    def draggingExited_(self, sender):
        self.dueno.arrastrando(False)

    def performDragOperation_(self, sender):
        self.dueno.arrastrando(False)
        self.dueno.encolar(self.rutas(sender))
        return True


# ---------------------------------------------------------------- delegado --
class DelegadoTranscribir(NSObject, protocols=[objc.protocolNamed("UNUserNotificationCenterDelegate")]):

    def applicationWillFinishLaunching_(self, notification):
        pref.registrar()
        self.ids = count(1)
        self.cola = []           # {"id", "ruta", "fraccion", "cliente", "cancelando"}; fraccion None = en espera
        self.hechos = []         # lo de esta sesión que no llega al historial: errores y cancelados
        self.historial = biblioteca.todas()[:DEL_HISTORIAL]   # las transcripciones de siempre
        self.editores = {}       # id de ficha -> ventana de editor abierta
        self.claves_fila = {}    # id de ficha -> número, que es lo que entiende el tag de un botón
        self.filas_cola = {}     # id -> (barra, porcentaje) de la fila activa
        self.suscriptores = {}   # id -> función que recibe los eventos (comando `transcribir`)
        self.pintado = None
        self.ultimo_color = 0.0
        self.sobre = False
        self.aviso = None
        self.cafeina = None
        self.lote_listos, self.lote_errores = [], 0   # lo terminado desde que se llenó la cola
        self.ventana_ajustes = None
        self.ventana_historial = None
        self.estado = None
        self.bienvenida = None
        self.glifos = {k: NSImage.alloc().initWithContentsOfFile_(str(recursos.ruta(f"glifo-{k}.png")))
                       for k in ("on", "off")}
        avisos.ser_delegado(self)
        self.motor = Motor(self.alAvanzar, self.alTerminar, self.alFallar, self.alCancelar,
                           AppHelper.callAfter)
        self.motor.start()
        self.construirMenu()
        self.construir()
        self.pintarCola()
        self.pintarHechos()
        self.pintarPie()
        self.pintar()
        if not pref.bienvenida_hecha() or modelos.ruta_local(pref.leer(pref.PRECISION)) is None:
            self.mostrarBienvenida()
        self.vigia = Vigia(lambda rutas: self.encolar(rutas, cliente=VIGILADA))
        self.configurarVigia(rebaselinar=False)
        self.reloj_vigia = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            3.0, self, b"revisarCarpeta:", None, True)
        self.estado = Estado.alloc().initWithDueno_(self)
        # solo la app instalada atiende al comando `transcribir`
        self.servidor = servidor.iniciar(self) if pref.en_app() else None

    def applicationDidFinishLaunching_(self, notification):
        if os.environ.get("TRANSCRIBIR_SEGUNDO_PLANO"):
            self.ventana.orderFrontRegardless()          # la abrió un agente: sin robar el foco
        else:
            self.ventana.makeKeyAndOrderFront_(None)
            NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        avisos.pedir_si_hace_falta()
        self.refrescarConectorAgentes()

    def application_openFiles_(self, app, nombres):
        """Archivos abiertos con la app o soltados sobre su icono del Dock."""
        self.encolar([Path(n) for n in nombres])
        app.replyToOpenOrPrint_(0)

    def applicationShouldTerminateAfterLastWindowClosed_(self, app):
        return True

    def applicationShouldHandleReopen_hasVisibleWindows_(self, app, visible):
        if not visible:
            self.ventana.makeKeyAndOrderFront_(None)
        return True

    def applicationShouldTerminate_(self, app):
        if not self.cola:
            return 1
        eleccion = self.alerta(
            "Hay archivos en cola",
            "Si sales ahora se detiene la transcripción en curso y se pierde la cola.",
            ["Salir", "Cancelar"])
        return 1 if eleccion == 1000 else 0

    def applicationWillTerminate_(self, notification):
        if self.estado is not None:
            self.estado.quitar()
        if self.cafeina is not None:
            self.cafeina.terminate()
        servidor.detener(self.servidor)

    # ---------------------------------------------------------------- menús --
    @objc.python_method
    def construirMenu(self):
        app = NSApplication.sharedApplication()
        barra = NSMenu.alloc().init()

        def submenu(titulo, elementos):
            contenedor = NSMenuItem.alloc().init()
            menu = NSMenu.alloc().initWithTitle_(titulo)
            for el in elementos:
                menu.addItem_(el or NSMenuItem.separatorItem())
            contenedor.setSubmenu_(menu)
            barra.addItem_(contenedor)
            return menu

        submenu("Transcribir", [
            ui.menu_item("Acerca de Transcribir", b"acercaDe:", "", self),
            None,
            ui.menu_item("Ajustes…", b"abrirAjustes:", ",", self),
            None,
            ui.menu_item("Ocultar Transcribir", b"hide:", "h"),
            ui.menu_item("Ocultar otras", b"hideOtherApplications:", "h", modifiers=1 << 19 | 1 << 20),
            ui.menu_item("Mostrar todo", b"unhideAllApplications:", ""),
            None,
            ui.menu_item("Salir de Transcribir", b"terminate:", "q"),
        ])
        submenu("Archivo", [
            ui.menu_item("Agregar archivos…", b"elegirArchivos:", "o", self),
            ui.menu_item("Abrir carpeta de destino", b"abrirCarpeta:", "O", self),
            ui.menu_item("Cambiar carpeta de destino…", b"cambiarCarpeta:", "", self),
            None,
            ui.menu_item("Buscar…", b"buscarDocumento:", "f"),
            ui.menu_item("Historial", b"abrirHistorial:", "y", self),
            ui.menu_item("Limpiar la lista", b"limpiarTerminados:", "\x08", self),
            None,
            ui.menu_item("Cerrar", b"performClose:", "w"),
        ])
        submenu("Edición", [
            ui.menu_item("Deshacer", b"undo:", "z"),
            ui.menu_item("Rehacer", b"redo:", "Z", modifiers=CMD | MAYUS),
            None,
            ui.menu_item("Cortar", b"cut:", "x"),
            ui.menu_item("Copiar", b"copy:", "c"),
            ui.menu_item("Pegar", b"paste:", "v"),
            ui.menu_item("Eliminar", b"delete:", ""),
            ui.menu_item("Seleccionar todo", b"selectAll:", "a"),
        ])
        submenu("Ver", [
            ui.menu_item("Texto más grande", b"textoMasGrande:", "+"),
            ui.menu_item("Texto más pequeño", b"textoMasPequeno:", "-"),
            None,
            ui.menu_item("Mostrar u ocultar el panel", b"toggleInspector:", "i",
                         modifiers=CMD | OPCION),
            None,
            ui.submenu_item("Resaltado al reproducir", [
                ui.menu_item("La palabra en negrita", b"cambiarResaltado:", "", tag=0),
                ui.menu_item("Un fondo suave", b"cambiarResaltado:", "", tag=1),
                None,
                ui.menu_item("Marcado suave", b"cambiarFuerza:", "", tag=0),
                ui.menu_item("Marcado medio", b"cambiarFuerza:", "", tag=1),
                ui.menu_item("Marcado fuerte", b"cambiarFuerza:", "", tag=2),
            ]),
        ])
        submenu("Transcripción", [
            ui.menu_item("Reproducir o pausar", b"reproducir:", " ", modifiers=OPCION),
            ui.menu_item("Retroceder 15 s", b"atras:", "[", modifiers=CMD),
            ui.menu_item("Avanzar 15 s", b"adelante:", "]", modifiers=CMD),
            None,
            ui.menu_item("Buscar siguiente", b"buscarSiguiente:", "g", modifiers=CMD),
            None,
            ui.menu_item("Exportar a PDF…", b"exportarComo:", "", tag=0),
            ui.menu_item("Exportar a Word…", b"exportarComo:", "", tag=1),
            ui.menu_item("Mostrar en Finder", b"mostrarEnFinder:", "r", modifiers=CMD | MAYUS),
            None,
            ui.menu_item("Calcular los tiempos", b"activarResaltado:", ""),
            ui.menu_item("Poner nombre a quien habla…", b"renombrarPrimera:", ""),
        ])
        ventana = submenu("Ventana", [
            ui.menu_item("Minimizar", b"performMiniaturize:", "m"),
            None,
            ui.menu_item("Traer todo al frente", b"arrangeInFront:", ""),
        ])
        ayuda = submenu("Ayuda", [
            ui.menu_item("Guía para agentes de IA", b"copiarGuiaAgentes:", "", self),
            ui.menu_item("Código y novedades en GitHub", b"abrirRepositorio:", "", self),
            None,
            ui.menu_item("Acerca de Transcribir", b"acercaDe:", "", self),
        ])
        app.setMainMenu_(barra)
        app.setWindowsMenu_(ventana)
        app.setHelpMenu_(ayuda)

    # ------------------------------------------------------------- interfaz --
    @objc.python_method
    def construir(self):
        rect = NSMakeRect(0, 0, WIN_W, WIN_H)
        self.ventana = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, ui.STYLE_TITLED | ui.STYLE_CLOSABLE | ui.STYLE_MINI | ui.STYLE_FULL_CONTENT,
            NSBackingStoreBuffered, False)
        self.ventana.setTitle_("Transcribir")
        self.ventana.setTitleVisibility_(1)
        self.ventana.setTitlebarAppearsTransparent_(True)
        self.ventana.setMovableByWindowBackground_(True)
        self.ventana.center()

        fondo = FondoArrastrable.alloc().initWithFrame_(rect)
        fondo.dueno = self
        fondo.registerForDraggedTypes_([NSPasteboardTypeFileURL])
        fondo.setMaterial_(ui.MATERIAL_UNDER_WINDOW)
        fondo.setBlendingMode_(ui.BLEND_BEHIND_WINDOW)
        fondo.setState_(ui.VFX_ACTIVE)
        fondo.setAutoresizingMask_(2 | 16)
        self.ventana.setContentView_(fondo)

        # ---- disco con halo
        self.lavado = ui.gradient_view(NSMakeRect(0, WIN_H - 240, WIN_W, 240), 0.0,
                                       [NSColor.clearColor(), NSColor.clearColor()],
                                       start=(0.5, 1.0), end=(0.5, 0.0))
        fondo.addSubview_(self.lavado)

        halo_d, disco_d = 120.0, 88.0
        disco_y = WIN_H - 62.0 - disco_d
        self.halo = ui.rounded(NSMakeRect((WIN_W - halo_d) / 2, disco_y - (halo_d - disco_d) / 2,
                                          halo_d, halo_d), halo_d / 2)
        fondo.addSubview_(self.halo)

        self.disco = NSView.alloc().initWithFrame_(
            NSMakeRect((WIN_W - disco_d) / 2, disco_y, disco_d, disco_d))
        self.disco.setWantsLayer_(True)
        self.disco.layer().setMasksToBounds_(False)
        self.disco.layer().setShadowOffset_((0, -4))
        self.disco.layer().setShadowRadius_(16.0)
        fondo.addSubview_(self.disco)

        self.relleno = ui.gradient_view(NSMakeRect(0, 0, disco_d, disco_d), disco_d / 2,
                                        list(ESTADOS["reposo"]))
        self.disco.addSubview_(self.relleno)
        self.glifo = NSImageView.alloc().initWithFrame_(NSMakeRect(0, 0, disco_d, disco_d))
        self.glifo.setImageScaling_(ui.IMG_SCALE_PROPORTIONAL)
        self.relleno.addSubview_(self.glifo)

        y = disco_y - 16.0 - 26.0
        self.titulo = ui.label("", 20.0, ui.W_SEMIBOLD, NSColor.labelColor(),
                               NSMakeRect(PAD, y, CW, 26))
        fondo.addSubview_(self.titulo)
        y -= 4.0 + 36.0
        self.subtitulo = ui.label("", 13.0, ui.W_REGULAR, NSColor.secondaryLabelColor(),
                                  NSMakeRect(PAD + 12, y, CW - 24, 36))
        fondo.addSubview_(self.subtitulo)

        # ---- listas y pie, en un contenedor que la bienvenida reemplaza
        self.fondo = fondo
        self.contenido = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, WIN_W, y))
        fondo.addSubview_(self.contenido)
        fondo = self.contenido

        # ---- en cola
        y -= 14.0 + 16.0
        fondo.addSubview_(ui.section_title("EN COLA", NSMakeRect(PAD + 4, y, 120, 16)))
        self.cuenta_cola = self.contador(fondo, y, botones=1)
        fondo.addSubview_(self.botonEncabezado("plus.circle.fill", y, 0, b"elegirArchivos:",
                                               "Agregar archivos (⌘O)"))
        y -= 6.0 + COLA_H
        self.lista_cola = self.tarjetaLista(fondo, y, COLA_H)

        # ---- historial
        y -= 18.0 + 16.0
        titulo = ui.section_title("EN ESTA SESIÓN", NSMakeRect(PAD + 4, y, 140, 16))
        fondo.addSubview_(titulo)
        self.cuenta_hechos = self.contador(fondo, y, botones=3)
        boton_buscar = self.botonEncabezado("clock.arrow.circlepath", y, 2, b"abrirHistorial:",
                                            "Ver todo el historial (⌘Y)")
        fondo.addSubview_(boton_buscar)
        boton_carpeta = self.botonEncabezado("folder.circle.fill", y, 1, b"abrirCarpeta:",
                                             "Abrir carpeta de destino")
        fondo.addSubview_(boton_carpeta)
        self.boton_limpiar = self.botonEncabezado("trash.circle.fill", y, 0, b"limpiarTerminados:",
                                                  "Vaciar la lista (no borra tus archivos)")
        fondo.addSubview_(self.boton_limpiar)

        y -= 6.0 + HECHOS_H
        self.lista_hechos = self.tarjetaLista(fondo, y, HECHOS_H)

        # ---- carpeta de destino
        pie = ui.card(NSMakeRect(PAD, y - 14.0 - PIE_H, CW, PIE_H))
        fondo.addSubview_(pie)
        pie.addSubview_(ui.icon_view("folder.fill", NSMakeRect(16, 14, 20, 20),
                                     NSColor.secondaryLabelColor(), 14.0))
        # el texto se dibuja pegado arriba de su marco: marco del alto de la letra (17 pt),
        # centrado en la fila como el icono y el botón
        pie.addSubview_(ui.label("Guardar en", 13.0, ui.W_MEDIUM, NSColor.labelColor(),
                                 NSMakeRect(46, (PIE_H - 17) / 2, 100, 17), ui.ALIGN_LEFT))
        self.valor_carpeta = ui.label("", 13.0, ui.W_SEMIBOLD, NSColor.labelColor(),
                                      NSMakeRect(140, (PIE_H - 17) / 2, CW - 140 - 16 - 96 - 10, 17),
                                      ui.ALIGN_RIGHT, truncate=ui.TRUNC_MIDDLE)
        pie.addSubview_(self.valor_carpeta)
        pie.addSubview_(ui.bezel_button("Cambiar…", NSMakeRect(CW - 16 - 96, 10, 96, 28),
                                        self, b"cambiarCarpeta:"))

    @objc.python_method
    def botonEncabezado(self, simbolo, y, posicion, accion, ayuda):
        """Botón de un encabezado de sección; `posicion` 0 es el de más a la derecha.
        Todos iguales (símbolo relleno en círculo, 14 pt), centrados con el título y en la
        misma vertical que los botones de las filas, que van 16 pt hacia dentro de la tarjeta."""
        x = PAD + CW - 16 - BOTON - posicion * (BOTON + 6)
        return ui.symbol_button(simbolo, NSMakeRect(x, y - 2, BOTON, BOTON), self, accion,
                                tooltip=ayuda, size=14.0, tint=NSColor.secondaryLabelColor())

    @objc.python_method
    def contador(self, fondo, y, botones):
        derecha = PAD + CW - 16 - botones * (BOTON + 6)
        etiqueta = ui.label("", 11.5, ui.W_SEMIBOLD, NSColor.tertiaryLabelColor(),
                            NSMakeRect(derecha - 60, y, 60, 16), ui.ALIGN_RIGHT)
        fondo.addSubview_(etiqueta)
        return etiqueta

    @objc.python_method
    def tarjetaLista(self, fondo, y, alto):
        tarjeta = ui.card(NSMakeRect(PAD, y, CW, alto))
        tarjeta.layer().setMasksToBounds_(True)
        fondo.addSubview_(tarjeta)
        scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(0, 0, CW, alto))
        scroll.setDrawsBackground_(False)
        scroll.setHasVerticalScroller_(True)
        scroll.setAutohidesScrollers_(True)
        doc = ui.VistaVolteada.alloc().initWithFrame_(NSMakeRect(0, 0, CW, alto))
        scroll.setDocumentView_(doc)
        tarjeta.addSubview_(scroll)
        return doc

    # ---------------------------------------------------------------- listas --
    @objc.python_method
    def vaciar(self, doc, filas, alto_fila, alto_min):
        for v in list(doc.subviews()):
            v.removeFromSuperview()
        doc.setFrameSize_((CW, max(alto_min, filas * alto_fila + 2 * LISTA_PAD)))

    @objc.python_method
    def estadoVacio(self, doc, alto, simbolo, texto, con_boton):
        bloque = 22 + 10 + 18 + (38 if con_boton else 0)
        top = (alto - bloque) / 2
        doc.addSubview_(ui.icon_view(simbolo, NSMakeRect((CW - 24) / 2, top, 24, 22),
                                     NSColor.tertiaryLabelColor(), 18.0))
        doc.addSubview_(ui.label(texto, 12.0, ui.W_REGULAR, NSColor.tertiaryLabelColor(),
                                 NSMakeRect(16, top + 32, CW - 32, 18)))
        if con_boton:
            doc.addSubview_(ui.bezel_button("Elegir archivos…",
                                            NSMakeRect((CW - 140) / 2, top + 58, 140, 28),
                                            self, b"elegirArchivos:"))

    @objc.python_method
    def nombreConEtiqueta(self, v, nombre, cliente, ancho):
        """Nombre del archivo y, a su derecha, quién lo pidió (si no fue el usuario)."""
        ancho_nombre = ancho
        if cliente:
            simbolo, color = estilo_cliente(cliente)
            pastilla = ui.pill(cliente, simbolo, color)
            ancho_pastilla = pastilla.frame().size.width
            ancho_nombre = ancho - ancho_pastilla - 8
            pastilla.setFrameOrigin_((46 + ancho - ancho_pastilla, 25))
            v.addSubview_(pastilla)
        v.addSubview_(ui.label(nombre, 13.0, ui.W_MEDIUM, NSColor.labelColor(),
                               NSMakeRect(46, 24, ancho_nombre, 18), ui.ALIGN_LEFT,
                               truncate=ui.TRUNC_MIDDLE))

    @objc.python_method
    def pintarCola(self):
        doc = self.lista_cola
        self.vaciar(doc, len(self.cola), FILA_COLA, COLA_H)
        self.filas_cola = {}
        if not self.cola:
            self.estadoVacio(doc, COLA_H, "tray.and.arrow.down",
                             "Arrastra audios o videos a esta ventana", True)
        for i, item in enumerate(self.cola):
            fila = self.filaCola(item, ultima=i == len(self.cola) - 1)
            fila.setFrameOrigin_((0, LISTA_PAD + i * FILA_COLA))
            doc.addSubview_(fila)
        self.cuenta_cola.setStringValue_(str(len(self.cola)) if self.cola else "")

    @objc.python_method
    def filaCola(self, item, ultima):
        v = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, CW, FILA_COLA))
        activa = item["fraccion"] is not None
        simbolo = "film" if item["ruta"].suffix.lower() in VIDEO else "waveform"
        v.addSubview_(ui.icon_view(simbolo, NSMakeRect(16, 14, 20, 20),
                                   ESTADOS["trabajo"][1] if activa else NSColor.secondaryLabelColor(),
                                   14.0))
        ancho = CW - 46 - 100
        self.nombreConEtiqueta(v, item["ruta"].name, item["cliente"], ancho)
        x_boton = CW - 16 - BOTON
        if item.get("cancelando"):
            v.addSubview_(ui.label("Cancelando…", 11.0, ui.W_REGULAR, NSColor.tertiaryLabelColor(),
                                   NSMakeRect(46, 8, ancho, 15), ui.ALIGN_LEFT))
        elif activa:
            sin_pct = item["fraccion"] < 0
            barra = NSProgressIndicator.alloc().initWithFrame_(NSMakeRect(46, 8, ancho, 12))
            barra.setStyle_(0)
            barra.setControlSize_(1)
            barra.setMinValue_(0.0)
            barra.setMaxValue_(100.0)
            barra.setIndeterminate_(sin_pct)
            if sin_pct:
                barra.startAnimation_(None)
            else:
                barra.setDoubleValue_(item["fraccion"] * 100)
            v.addSubview_(barra)
            pct = ui.label("" if sin_pct else f"{round(item['fraccion'] * 100)} %", 13.0,
                           ui.W_SEMIBOLD, NSColor.labelColor(),
                           NSMakeRect(x_boton - 8 - 56, 15, 56, 18), ui.ALIGN_RIGHT)
            v.addSubview_(pct)
            self.filas_cola[item["id"]] = (barra, pct)
            v.addSubview_(ui.symbol_button(
                "xmark.circle.fill", NSMakeRect(x_boton, 14, BOTON, BOTON), self, b"cancelar:",
                tag=item["id"], tooltip="Cancelar la transcripción", size=14.0,
                tint=NSColor.secondaryLabelColor()))
        else:
            v.addSubview_(ui.label("En espera", 11.0, ui.W_REGULAR, NSColor.tertiaryLabelColor(),
                                   NSMakeRect(46, 8, ancho, 15), ui.ALIGN_LEFT))
            v.addSubview_(ui.symbol_button(
                "xmark.circle.fill", NSMakeRect(x_boton, 14, BOTON, BOTON), self, b"cancelar:",
                tag=item["id"], tooltip="Quitar de la cola", size=14.0,
                tint=NSColor.tertiaryLabelColor()))
        if not ultima:
            v.addSubview_(ui.hairline(NSMakeRect(16, 0, CW - 32, 1)))
        return v

    @objc.python_method
    def entradas(self):
        """Lo que se ve en la ventana: solo lo de esta sesión, de lo más nuevo a lo
        más viejo. Todo lo demás vive en la ventana de Historial."""
        return list(self.hechos)

    @objc.python_method
    def pintarHechos(self):
        doc = self.lista_hechos
        lista = self.entradas()
        self.vaciar(doc, len(lista), FILA_HECHO, HECHOS_H)
        if not lista:
            self.estadoVacio(doc, HECHOS_H, "doc.text",
                             "Aquí aparecerán tus transcripciones", False)
        for i, entrada in enumerate(lista):
            fila = self.filaEntrada(entrada, ultima=i == len(lista) - 1)
            fila.setFrameOrigin_((0, LISTA_PAD + i * FILA_HECHO))
            doc.addSubview_(fila)
        self.cuenta_hechos.setStringValue_(str(len(lista)) if lista else "")
        self.boton_limpiar.setEnabled_(bool(lista))

    @objc.python_method
    def filaEntrada(self, entrada, ultima):
        v = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, CW, FILA_HECHO))
        if entrada["tipo"] == "ficha":
            self.pintarFilaFicha(v, entrada["ficha"])
        else:
            simbolo, color = (("exclamationmark.triangle.fill", NSColor.systemOrangeColor())
                              if entrada["tipo"] == "error"
                              else ("xmark.circle.fill", NSColor.tertiaryLabelColor()))
            v.addSubview_(ui.icon_view(simbolo, NSMakeRect(16, 15, 20, 20), color, 15.0))
            ancho = CW - 46 - 16
            self.nombreConEtiqueta(v, entrada["nombre"], entrada["cliente"], ancho)
            v.addSubview_(ui.label(entrada["detalle"], 11.0, ui.W_REGULAR, color,
                                   NSMakeRect(46, 9, ancho, 15), ui.ALIGN_LEFT,
                                   truncate=ui.TRUNC_TAIL))
        if not ultima:
            v.addSubview_(ui.hairline(NSMakeRect(16, 0, CW - 32, 1)))
        return v

    @objc.python_method
    def pintarFilaFicha(self, v, ficha):
        """Una transcripción del historial. Si su archivo ya no está, lo dice y ofrece ubicarlo."""
        ruta = biblioteca.ubicar(ficha)
        etiqueta = self.claves_fila.setdefault(ficha["id"], len(self.claves_fila) + 1)
        # todas las filas con la misma rejilla: botón y, a su derecha, icono en la
        # misma vertical que los botones del encabezado
        x_icono = CW - 16 - BOTON
        x_boton = x_icono - 6 - ACCION
        ancho = x_boton - 46 - 10

        if ruta is None:
            v.addSubview_(ui.icon_view("questionmark.circle.fill", NSMakeRect(16, 15, 20, 20),
                                       NSColor.tertiaryLabelColor(), 15.0))
            self.nombreConEtiqueta(v, ficha["nombre"], ficha.get("cliente"), ancho)
            v.addSubview_(ui.label("No encontrado · se movió o se borró", 11.0, ui.W_REGULAR,
                                   NSColor.systemOrangeColor(), NSMakeRect(46, 9, ancho, 15),
                                   ui.ALIGN_LEFT, truncate=ui.TRUNC_TAIL))
            v.addSubview_(ui.bezel_button("Ubicar…", NSMakeRect(x_boton, 11, ACCION, 28),
                                          self, b"ubicarArchivo:", tag=etiqueta))
            v.addSubview_(ui.symbol_button(
                "xmark.circle.fill", NSMakeRect(x_icono, 15, BOTON, BOTON),
                self, b"quitarDelHistorial:", tag=etiqueta, size=14.0,
                tooltip="Quitar del historial", tint=NSColor.tertiaryLabelColor()))
            return

        v.addSubview_(ui.icon_view("checkmark.circle.fill", NSMakeRect(16, 15, 20, 20),
                                   NSColor.systemGreenColor(), 15.0))
        self.nombreConEtiqueta(v, ficha["nombre"], ficha.get("cliente"), ancho)
        v.addSubview_(ui.label(ficha.get("coincidencia") or self.detalleFicha(ficha, ruta),
                               11.0, ui.W_REGULAR, NSColor.tertiaryLabelColor(),
                               NSMakeRect(46, 9, ancho, 15), ui.ALIGN_LEFT, truncate=ui.TRUNC_TAIL))
        abrir = ui.bezel_button("Abrir", NSMakeRect(x_boton, 11, ACCION, 28),
                                self, b"abrirEditor:", tag=etiqueta)
        abrir.setToolTip_(f"Ver, escuchar y corregir\n{ruta}")
        v.addSubview_(abrir)
        v.addSubview_(ui.symbol_button(
            "folder.circle.fill", NSMakeRect(x_icono, 15, BOTON, BOTON), self,
            b"mostrarEnFinder:", tag=etiqueta, size=14.0, tooltip=f"Mostrar en Finder\n{ruta}",
            tint=NSColor.secondaryLabelColor()))

    @objc.python_method
    def detalleFicha(self, ficha, ruta):
        """«12 min de audio · en el Escritorio», y dónde quedó si no es la carpeta de siempre."""
        detalle = f"{duracion_corta(ficha.get('duracion', 0))} de audio"
        if str(ruta.parent) != pref.leer(pref.CARPETA):
            detalle += f" · en «{ruta.parent.name}»"
        elif ficha.get("tiempos"):
            detalle += " · con resaltado"
        if ruta.suffix == ".srt":
            detalle += " · subtítulos"
        return detalle

    @objc.python_method
    def fichaDe(self, etiqueta):
        """La ficha a la que apunta el botón de una fila."""
        id_ficha = next((k for k, v in self.claves_fila.items() if v == etiqueta), None)
        return next((f for f in self.historial if f["id"] == id_ficha), None)

    @objc.python_method
    def pintarPie(self):
        if pref.leer(pref.GUARDAR) == "junto":
            texto, ayuda = "Junto al original", "Cada resultado se guarda junto a su archivo"
        else:
            ruta = Path(pref.leer(pref.CARPETA))
            texto, ayuda = ("Escritorio" if ruta == pref.ESCRITORIO else ruta.name), str(ruta)
        self.valor_carpeta.setStringValue_(texto)
        self.valor_carpeta.setToolTip_(ayuda)

    # ------------------------------------------------------------------ disco --
    @objc.python_method
    def colorear(self, estado):
        """Recolorea el disco solo al cambiar de estado, y sin encadenar
        animaciones solapadas (hacen abortar a Core Animation)."""
        if self.pintado == estado:
            return
        animar = self.pintado is not None and time.time() - self.ultimo_color > 0.4
        self.pintado, self.ultimo_color = estado, time.time()
        arriba, abajo = ESTADOS[estado]
        encendido = estado != "reposo"

        ui.CATransaction.begin()
        if animar:
            ui.CATransaction.setAnimationDuration_(0.28)
        else:
            ui.CATransaction.setDisableActions_(True)
        self.relleno.layer().setColors_([arriba.CGColor(), abajo.CGColor()])
        self.disco.layer().setShadowColor_(abajo.CGColor())
        self.disco.layer().setShadowOpacity_(0.45 if encendido else 0.18)
        self.halo.layer().setBackgroundColor_(
            arriba.colorWithAlphaComponent_(0.22 if encendido else 0.07).CGColor())
        self.lavado.layer().setColors_([
            arriba.colorWithAlphaComponent_(0.16 if encendido else 0.05).CGColor(),
            NSColor.clearColor().CGColor()])
        ui.CATransaction.commit()

        glifo = self.glifos["on" if encendido else "off"]
        if glifo is not None:
            self.glifo.setImage_(glifo)

        if estado == "trabajo":
            self.halo.layer().addAnimation_forKey_(ui.pulse("opacity", 0.5, 1.0, 1.9), "resplandor")
            self.disco.layer().addAnimation_forKey_(
                ui.pulse("shadowOpacity", 0.28, 0.62, 1.9), "resplandor")
        else:
            self.halo.layer().removeAnimationForKey_("resplandor")
            self.disco.layer().removeAnimationForKey_("resplandor")

    @objc.python_method
    def pintar(self):
        """Título, subtítulo y color del disco según lo que esté pasando."""
        self.pintarEstado()
        activa = next((c for c in self.cola if c["fraccion"] is not None), None)
        listos = sum(1 for h in self.hechos if h["tipo"] == "ficha")
        errores = sum(1 for h in self.hechos if h["tipo"] == "error")

        if self.bienvenida is not None:
            descargando = self.bienvenida.descargando
            self.colorear("trabajo" if descargando else "reposo")
            self.titulo.setStringValue_(f"Bienvenido a {NOMBRE}")
            self.subtitulo.setStringValue_(
                "Descargando el modelo: es la única vez que hace falta internet." if descargando
                else "Convierte audio y video en texto, en tu Mac y sin internet.")
            return
        if self.sobre:
            estado, titulo, sub = "trabajo", "Suelta para agregar", "Se transcribirán en orden, uno por uno."
        elif self.cola:
            estado, titulo = "trabajo", "Transcribiendo"
            if activa is None:
                sub = "Empezando…"
            else:
                texto = activa.get("texto", "")
                quien = ""
                if activa["cliente"] == VIGILADA:
                    quien = "Carpeta vigilada · "
                elif activa["cliente"]:
                    quien = f"{activa['cliente']} pidió "
                nombre = f"{quien}{corto(activa['ruta'].name, 30)}"
                pct = round(activa["fraccion"] * 100)
                if activa["fraccion"] < 0:
                    sub = f"{nombre} · {texto or 'Preparando el modelo…'}"
                elif texto and not texto.startswith("Transcribiendo"):    # descargando, separando…
                    sub = f"{nombre}\n{texto} · {pct} %"
                else:
                    sub = f"{nombre} · {pct} %"
            if len(self.cola) > 1 and "\n" not in sub:
                sub += f"\n{len(self.cola) - 1} más en espera"
        elif listos or errores:
            estado = "listo" if listos else "reposo"
            titulo = "Todo listo" if listos else "No se pudo transcribir"
            sub = f"{plural(listos, 'transcripción guardada', 'transcripciones guardadas')} {self.fraseDestino()}."
            if errores:
                sub += f" {plural(errores, 'archivo', 'archivos')} con error."
        else:
            estado, titulo = "reposo", "Listo para transcribir"
            sub = f"Arrastra audios o videos a esta ventana. El texto se guarda {self.fraseDestino()}."

        if self.aviso is not None:
            sub = self.aviso
        self.colorear(estado)
        self.titulo.setStringValue_(titulo)
        self.subtitulo.setStringValue_(sub)

    @objc.python_method
    def pintarEstado(self):
        """El círculo de la barra de menús, con el avance de todo el lote."""
        if self.estado is None:
            return
        activa = next((c for c in self.cola if c["fraccion"] is not None), None)
        texto = ""
        if activa is not None:
            texto = (activa.get("texto") or "Transcribiendo…").rstrip("…")
        self.estado.actualizar(len(self.cola), len(self.lote_listos),
                               activa["fraccion"] if activa else 0.0, texto)

    @objc.python_method
    def fraseDestino(self):
        if pref.leer(pref.GUARDAR) == "junto":
            return "junto al archivo original"
        ruta = Path(pref.leer(pref.CARPETA))
        return "en el Escritorio" if ruta == pref.ESCRITORIO else f"en «{ruta.name}»"

    # ------------------------------------------------------------------ cola --
    @objc.python_method
    def opcionesActuales(self, extra=None):
        opciones = {clave: pref.leer(clave) for clave in pref.DEL_TRABAJO}
        opciones.update(extra or {})
        return opciones

    @objc.python_method
    def arrastrando(self, sobre):
        self.sobre = sobre
        self.pintar()

    @objc.python_method
    def encolar(self, rutas, cliente=None, extra=None, suscriptor=None):
        """Agrega archivos a la cola y devuelve los trabajos creados.

        `cliente` es quién lo pide (None = el usuario desde la ventana), `extra`
        opciones solo para estos archivos y `suscriptor` recibe sus eventos."""
        if not self.cola:                      # empieza un lote nuevo
            self.lote_listos, self.lote_errores = [], 0
        base = self.opcionesActuales(extra)
        creados, ignorados = [], 0
        for ruta in expandir(rutas):
            if ruta.suffix.lower() not in EXTENSIONES:
                ignorados += 1
                continue
            destino = ruta.parent if base[pref.GUARDAR] == "junto" else Path(base[pref.CARPETA])
            trabajo = Trabajo(next(self.ids), ruta, dict(base, destino=str(destino)), cliente)
            item = {"id": trabajo.id, "ruta": ruta, "fraccion": None, "cliente": cliente}
            self.cola.append(item)
            creados.append(item)
            if suscriptor is not None:
                self.suscriptores[trabajo.id] = suscriptor
            self.motor.encolar(trabajo)
        if ignorados and cliente is None:
            self.avisar(f"Se ignoró 1 archivo: solo audio o video" if ignorados == 1 else
                        f"Se ignoraron {ignorados} archivos: solo audio o video")
        self.pintarCola()
        self.pintar()
        self.cafe()
        return creados

    @objc.python_method
    def emitir(self, id_trabajo, evento, final=False):
        """Pasa un evento al comando que pidió ese trabajo, si sigue esperando."""
        funcion = self.suscriptores.get(id_trabajo)
        if funcion is None:
            return
        funcion({"id": id_trabajo, **evento})
        if final:
            self.suscriptores.pop(id_trabajo, None)

    @objc.python_method
    def avisar(self, texto):
        self.aviso = texto
        self.performSelector_withObject_afterDelay_(b"limpiarAviso:", None, 5.0)

    def limpiarAviso_(self, _):
        self.aviso = None
        self.pintar()

    @objc.python_method
    def sacar(self, id_trabajo):
        """Saca el trabajo de la cola. None si ya no estaba."""
        item = next((c for c in self.cola if c["id"] == id_trabajo), None)
        if item is not None:
            self.cola.remove(item)
        return item

    @objc.python_method
    def cancelarTrabajo(self, id_trabajo):
        """Quita uno en espera o detiene el que está en curso. False si no está en la cola."""
        item = next((c for c in self.cola if c["id"] == id_trabajo), None)
        if item is None:
            return False
        self.motor.cancelar(id_trabajo)
        if item["fraccion"] is None:           # no había empezado: sale de la cola sin más
            self.cola.remove(item)
            self.emitir(id_trabajo, {"evento": "cancelado", "archivo": str(item["ruta"])}, final=True)
        else:                                  # el motor confirma con alCancelar
            item["cancelando"] = True
        self.pintarCola()
        self.pintar()
        self.cafe()
        return True

    @objc.python_method
    def agregarHecho(self, item, tipo, detalle):
        """Lo que no llega al historial: un archivo que falló o que se canceló."""
        self.hechos.insert(0, {"tipo": tipo, "cuando": time.time(), "id": item["id"],
                               "nombre": item["ruta"].name, "origen": str(item["ruta"]),
                               "detalle": detalle, "cliente": item["cliente"]})

    @objc.python_method
    def alAvanzar(self, id_trabajo, texto, fraccion):
        item = next((c for c in self.cola if c["id"] == id_trabajo), None)
        if item is None or item.get("cancelando"):
            return
        item["texto"] = texto
        antes, item["fraccion"] = item["fraccion"], fraccion
        fila = self.filas_cola.get(id_trabajo)
        if fila is not None and antes is not None and antes >= 0 and fraccion >= 0:
            barra, pct = fila
            barra.setDoubleValue_(fraccion * 100)
            pct.setStringValue_(f"{round(fraccion * 100)} %")
        else:
            self.pintarCola()
        self.pintar()
        self.emitir(id_trabajo, {"evento": "progreso", "archivo": str(item["ruta"]),
                                 "estado": texto, "progreso": fraccion})

    @objc.python_method
    def alTerminar(self, id_trabajo, ruta_txt, duracion, segundos, id_ficha=None):
        item = self.sacar(id_trabajo)
        if item is None:
            return
        ficha = biblioteca.leer(id_ficha) if id_ficha else None
        if ficha is not None:
            self.historial = [f for f in self.historial if f["id"] != ficha["id"]]
            self.historial.insert(0, ficha)
            if item.get("tarea") != "tiempos":
                self.hechos.insert(0, {"tipo": "ficha", "cuando": time.time(), "ficha": ficha,
                                       "nombre": ficha["nombre"], "cliente": ficha.get("cliente")})
            editor = self.editores.get(ficha["id"])
            if editor is not None:                  # ya estaba abierta: ahora con resaltado
                editor.recargar(ficha)
            if self.ventana_historial is not None:
                self.ventana_historial.pintar()
        if item.get("tarea") == "tiempos":      # solo se calculó el resaltado: nada que anunciar
            self.alCambiarCola()
            return
        self.lote_listos.append((item["ruta"].name, ruta_txt))
        self.alCambiarCola()
        self.emitir(id_trabajo, {"evento": "terminado", "archivo": str(item["ruta"]), "ruta": ruta_txt,
                                 "duracion": round(duracion, 1), "segundos": round(segundos, 1)}, final=True)
        self.notificar(item["ruta"].name, ruta_txt, f"{duracion_corta(duracion)} de audio")
        if item["cliente"] is None:            # "al terminar" solo con lo que agregó el usuario
            accion = pref.leer(pref.AL_TERMINAR)
            if accion == "finder":
                NSWorkspace.sharedWorkspace().activateFileViewerSelectingURLs_([NSURL.fileURLWithPath_(ruta_txt)])
            elif accion == "abrir":
                NSWorkspace.sharedWorkspace().openURL_(NSURL.fileURLWithPath_(ruta_txt))

    @objc.python_method
    def alFallar(self, id_trabajo, motivo):
        item = self.sacar(id_trabajo)
        if item is None:
            return
        self.agregarHecho(item, "error", motivo)
        self.lote_errores += 1
        self.alCambiarCola()
        self.emitir(id_trabajo, {"evento": "error", "archivo": str(item["ruta"]), "motivo": motivo}, final=True)
        self.notificar(item["ruta"].name, None, motivo)

    @objc.python_method
    def alCancelar(self, id_trabajo):
        item = self.sacar(id_trabajo)
        if item is None:                       # ya había salido de la cola
            return
        self.agregarHecho(item, "cancelado", "Cancelada")
        self.alCambiarCola()
        self.emitir(id_trabajo, {"evento": "cancelado", "archivo": str(item["ruta"])}, final=True)

    @objc.python_method
    def alCambiarCola(self):
        self.pintarCola()
        self.pintarHechos()
        self.pintar()
        self.cafe()
        if not self.cola:
            NSApplication.sharedApplication().requestUserAttention_(ATENCION_INFORMATIVA)

    @objc.python_method
    def notificar(self, nombre, ruta_txt, detalle):
        """Avisos del sistema según Ajustes. El de la cola resume el lote y
        sustituye al del último archivo, para no avisar dos veces de lo mismo."""
        cierra_cola = not self.cola and bool(self.lote_listos) and avisos.activo(avisos.COLA)
        if ruta_txt is None:
            if avisos.activo(avisos.ERRORES):
                avisos.enviar("No se pudo transcribir", f"{nombre}: {detalle}")
        elif avisos.activo(avisos.CADA_ARCHIVO) and not cierra_cola:
            titulo = "Subtítulos listos" if ruta_txt.endswith(".srt") else "Transcripción lista"
            avisos.enviar(titulo, f"{nombre} · {detalle}", ruta=ruta_txt)
        if not cierra_cola:
            return
        if len(self.lote_listos) == 1 and not self.lote_errores:
            nombre_listo, ruta_lista = self.lote_listos[0]
            titulo = "Subtítulos listos" if ruta_lista.endswith(".srt") else "Transcripción lista"
            avisos.enviar(titulo, f"{nombre_listo}. Haz clic para verla en Finder.", ruta=ruta_lista)
        else:
            cuerpo = (f"{plural(len(self.lote_listos), 'transcripción guardada', 'transcripciones guardadas')}"
                      f" {self.fraseDestino()}.")
            if self.lote_errores:
                cuerpo += f" {plural(self.lote_errores, 'archivo', 'archivos')} con error."
            avisos.enviar("Todo listo", cuerpo, carpeta=str(Path(self.lote_listos[-1][1]).parent))

    @objc.python_method
    def cafe(self):
        """Mientras haya trabajo, el Mac no se duerme."""
        if self.cola and self.cafeina is None:
            self.cafeina = subprocess.Popen(["/usr/bin/caffeinate", "-i", "-w", str(os.getpid())])
        elif not self.cola and self.cafeina is not None:
            self.cafeina.terminate()
            self.cafeina = None

    @objc.python_method
    def limpiar(self):
        """Quita de la lista lo que falló o se canceló. El historial se conserva."""
        cuantos = len(self.hechos)
        self.hechos = []
        self.pintarHechos()
        self.pintar()
        return cuantos

    # ---------------------------------------------------------------- ajustes --
    @objc.python_method
    def alCambiarAjuste(self, clave):
        """Refleja un ajuste nuevo en todas partes, venga de Ajustes o de un agente."""
        if clave in (pref.VIGILAR, pref.CARPETA_VIGILADA):
            self.configurarVigia(rebaselinar=True)
        self.pintarPie()
        self.pintar()
        if self.ventana_ajustes is not None:
            self.ventana_ajustes.sincronizar()

    @objc.python_method
    def configurarVigia(self, rebaselinar):
        carpeta = pref.leer(pref.CARPETA_VIGILADA)
        activa = pref.leer(pref.VIGILAR) and carpeta and Path(carpeta).is_dir()
        self.vigia.configurar(Path(carpeta) if activa else None, rebaselinar)

    def revisarCarpeta_(self, timer):
        self.vigia.revisar()

    # ------------------------------------------------------------ bienvenida --
    @objc.python_method
    def mostrarBienvenida(self):
        self.bienvenida = Bienvenida.alloc().initWithDueno_marco_(self, self.contenido.frame())
        self.contenido.setHidden_(True)
        self.fondo.addSubview_(self.bienvenida.vista)
        self.pintar()

    @objc.python_method
    def terminarBienvenida(self, precision, conectar_agentes):
        pref.escribir(pref.PRECISION, precision)
        pref.marcar_bienvenida()
        if conectar_agentes:
            agentes.instalar_todo(self.ejecutableComando())
        self.bienvenida.vista.removeFromSuperview()
        self.bienvenida = None
        self.contenido.setHidden_(False)
        self.alCambiarAjuste(pref.PRECISION)

    @objc.python_method
    def ejecutableComando(self):
        """Cómo arranca el comando `transcribir`: con el Python de dentro de la app."""
        app = recursos.app()
        if app is None:
            return agentes.ejecutable_desarrollo()
        return [str(app / "Contents" / "MacOS" / NOMBRE), "--cli"]

    @objc.python_method
    def refrescarConectorAgentes(self):
        """Si la app cambió de lugar o de versión, pone al día el comando y la Skill instalados."""
        try:
            if agentes.comando_existe() and not agentes.comando_instalado(self.ejecutableComando()):
                agentes.instalar_comando(self.ejecutableComando())
            if agentes.skill_existe() and not agentes.skill_instalada():
                agentes.instalar_skill()
        except OSError:
            pass

    # --------------------------------------------------------------- agentes --
    @objc.python_method
    def encolarDesdeAgente(self, peticion, suscriptor):
        extra = {}
        for clave, valor in (peticion.get("opciones") or {}).items():
            if clave not in pref.DEL_TRABAJO:
                raise ValueError(f"Opción no válida para una petición: {clave}")
            extra[clave] = pref.validar(clave, valor)
        rutas, rechazados = [], []
        for texto in peticion.get("archivos") or []:
            ruta = Path(texto).expanduser()
            if not ruta.exists():
                rechazados.append({"archivo": texto, "motivo": "no existe"})
                continue
            for archivo in expandir([ruta]):
                if archivo.suffix.lower() in EXTENSIONES:
                    rutas.append(archivo)
                elif not ruta.is_dir():
                    rechazados.append({"archivo": str(archivo),
                                       "motivo": "formato no compatible (.m4a .mp4 .mp3 .wav .mov)"})
        creados = self.encolar(rutas, cliente=peticion.get("cliente") or "Terminal",
                               extra=extra, suscriptor=suscriptor)
        if creados and not self.ventana.isVisible():
            self.ventana.orderFrontRegardless()        # que se vea, sin robar el foco
        return {"trabajos": [{"id": c["id"], "archivo": str(c["ruta"])} for c in creados],
                "rechazados": rechazados}

    @objc.python_method
    def atenderAgente(self, accion, peticion):
        if accion == "estado":
            return self.estadoParaAgente()
        if accion == "cancelar":
            ids = [c["id"] for c in self.cola] if peticion.get("todo") else [int(i) for i in peticion.get("ids") or []]
            cancelados = [i for i in ids if self.cancelarTrabajo(i)]
            return {"cancelados": cancelados, "no_encontrados": [i for i in ids if i not in cancelados]}
        if accion == "ajustes_leer":
            return {"ajustes": pref.todas(), "opciones": pref.opciones_validas()}
        if accion == "ajustes_cambiar":
            clave = peticion.get("clave")
            valor = pref.escribir(clave, peticion.get("valor"))
            self.alCambiarAjuste(clave)
            return {"clave": clave, "valor": valor}
        if accion == "limpiar":
            return {"limpiados": self.limpiar()}
        if accion == "historial":
            fichas = biblioteca.buscar(peticion.get("consulta") or "", self.historial)
            limite = int(peticion.get("limite") or 50)
            return {"total": len(self.historial),
                    "transcripciones": [self.fichaParaAgente(f) for f in fichas[:limite]]}
        if accion == "texto":
            ficha = self.buscarFicha(peticion.get("ficha"))
            contenido = biblioteca.texto(ficha)
            if contenido is None:
                raise ValueError("No se encontró el archivo de esa transcripción")
            datos = self.fichaParaAgente(ficha)
            datos["texto"] = contenido
            if peticion.get("con_tiempos"):
                datos["palabras"] = [{"palabra": p, "inicio": t0, "fin": t1, "persona": q}
                                     for p, t0, t1, q in (biblioteca.palabras(ficha["id"]) or [])]
            return datos
        if accion == "abrir_ficha":
            ficha = self.buscarFicha(peticion.get("ficha"))
            if self.abrirFicha(ficha, peticion.get("segundo")) is None:
                raise ValueError("No se encontró el archivo de esa transcripción")
            return self.fichaParaAgente(ficha)
        if accion == "personas":
            ficha = self.buscarFicha(peticion.get("ficha"))
            nombres = {str(k): str(v) for k, v in (peticion.get("nombres") or {}).items()}
            if nombres:
                editor = self.editores.get(ficha["id"])
                if editor is not None:
                    editor.renombrarPersonas(nombres)
                else:
                    self.renombrarPersonas(ficha, nombres)
            return self.fichaParaAgente(ficha)
        if accion == "exportar":
            ficha = self.buscarFicha(peticion.get("ficha"))
            origen = biblioteca.ubicar(ficha)
            if origen is None:
                raise ValueError("No se encontró el archivo de esa transcripción")
            carpeta = Path(peticion["destino"]) if peticion.get("destino") else origen.parent
            archivos = []
            for formato in peticion.get("formatos") or ["pdf"]:
                if formato not in exportar.FORMATOS:
                    raise ValueError(f"Formato desconocido: {formato}. Válidos: pdf, word")
                destino = ruta_libre(carpeta, origen.stem, exportar.FORMATOS[formato])
                archivos.append(str(exportar.exportar(ficha, formato, destino)))
            return {"archivos": archivos}
        if accion == "olvidar":
            ficha = self.buscarFicha(peticion.get("ficha"))
            biblioteca.olvidar(ficha["id"])
            self.historial = [f for f in self.historial if f["id"] != ficha["id"]]
            self.pintarHechos()
            return {"olvidada": ficha["id"]}
        if accion == "tiempos":
            ficha = self.buscarFicha(peticion.get("ficha"))
            if ficha.get("tiempos"):
                return {"ficha": ficha["id"], "trabajo": None, "ya_estaban": True}
            id_trabajo = self.calcularTiempos(ficha)
            if id_trabajo is None:
                raise ValueError("No se encontró el audio original de esa transcripción")
            return {"ficha": ficha["id"], "trabajo": id_trabajo, "ya_estaban": False}
        if accion == "mostrar":
            self.ventana.makeKeyAndOrderFront_(None)
            NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
            return {}
        raise ValueError(f"Acción desconocida: {accion}")

    @objc.python_method
    def buscarFicha(self, id_ficha):
        """La ficha por su id; también vale el nombre del archivo, para que un agente
        no tenga que pedir el historial antes de cada cosa."""
        texto = str(id_ficha or "").strip()
        if not texto:
            raise ValueError("Falta el identificador de la transcripción (transcribir historial)")
        ficha = next((f for f in self.historial if f["id"] == texto), None)
        if ficha is None:
            candidatas = [f for f in self.historial
                          if texto.lower() in f.get("nombre", "").lower()
                          or texto.lower() in Path(f.get("salida", "")).name.lower()]
            if len(candidatas) > 1:
                raise ValueError(f"«{texto}» coincide con {len(candidatas)} transcripciones; "
                                 "usa el id (transcribir historial)")
            ficha = candidatas[0] if candidatas else None
        if ficha is None:
            raise ValueError(f"No hay ninguna transcripción con «{texto}» (transcribir historial)")
        return ficha

    @objc.python_method
    def fichaParaAgente(self, ficha):
        ruta = biblioteca.ubicar(ficha)
        return {"id": ficha["id"], "nombre": ficha.get("nombre"), "creado": ficha.get("creado"),
                "audio": ficha.get("origen"), "archivo": str(ruta) if ruta else None,
                "encontrado": ruta is not None, "formato": ficha.get("formato"),
                "duracion": ficha.get("duracion"), "tiempos": bool(ficha.get("tiempos")),
                "personas": ficha.get("personas") or {}, "cliente": ficha.get("cliente"),
                "coincidencia": ficha.get("coincidencia") or None}

    @objc.python_method
    def estadoParaAgente(self):
        def en_cola(c):
            f = c["fraccion"]
            estado = "en_espera" if f is None else ("preparando" if f < 0 else "transcribiendo")
            if c.get("cancelando"):
                estado = "cancelando"
            return {"id": c["id"], "archivo": str(c["ruta"]), "estado": estado,
                    "progreso": None if f is None or f < 0 else round(f, 3), "cliente": c["cliente"]}

        def hecha(f):
            ruta = biblioteca.ubicar(f)
            return {"ficha": f["id"], "archivo": f.get("origen"),
                    "estado": "listo" if ruta else "no_encontrado",
                    "resultado": str(ruta) if ruta else None,
                    "detalle": f"{duracion_corta(f.get('duracion', 0))} de audio",
                    "cliente": f.get("cliente")}

        return {"cola": [en_cola(c) for c in self.cola],
                "terminados": [{"id": h["id"], "archivo": h["origen"], "estado": h["tipo"],
                                "resultado": None, "detalle": h["detalle"], "cliente": h["cliente"]}
                               for h in self.hechos] + [hecha(f) for f in self.historial[:20]],
                "historial_total": len(self.historial),
                "ajustes": pref.todas()}

    # -------------------------------------------------------------- acciones --
    def elegirArchivos_(self, sender):
        panel = NSOpenPanel.openPanel()
        panel.setAllowsMultipleSelection_(True)
        panel.setCanChooseDirectories_(False)
        panel.setAllowedFileTypes_([e[1:] for e in sorted(EXTENSIONES)])
        panel.setPrompt_("Agregar")
        if panel.runModal() == 1:
            self.encolar([Path(u.path()) for u in panel.URLs()])

    def cambiarCarpeta_(self, sender):
        panel = NSOpenPanel.openPanel()
        panel.setCanChooseDirectories_(True)
        panel.setCanChooseFiles_(False)
        panel.setCanCreateDirectories_(True)
        panel.setPrompt_("Guardar aquí")
        panel.setDirectoryURL_(NSURL.fileURLWithPath_(pref.leer(pref.CARPETA)))
        if panel.runModal() == 1:
            pref.escribir(pref.GUARDAR, "carpeta")
            pref.escribir(pref.CARPETA, panel.URL().path())
            self.alCambiarAjuste(pref.CARPETA)

    def mostrarVentana_(self, sender):
        self.ventana.makeKeyAndOrderFront_(None)
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)

    def cancelarTodo_(self, sender):
        for item in list(self.cola):
            self.cancelarTrabajo(item["id"])

    def abrirCarpeta_(self, sender):
        NSWorkspace.sharedWorkspace().openURL_(NSURL.fileURLWithPath_(pref.leer(pref.CARPETA)))

    def limpiarTerminados_(self, sender):
        self.limpiar()

    def cancelar_(self, sender):
        self.cancelarTrabajo(sender.tag())

    def mostrarEnFinder_(self, sender):
        ficha = self.fichaDe(sender.tag())
        ruta = biblioteca.ubicar(ficha) if ficha else None
        if ruta is None:
            self.pintarHechos()                # acaba de desaparecer: la fila lo dirá
            return
        NSWorkspace.sharedWorkspace().activateFileViewerSelectingURLs_(
            [NSURL.fileURLWithPath_(str(ruta))])

    # -------------------------------------------------------------- historial --
    def abrirEditor_(self, sender):
        self.abrirFicha(self.fichaDe(sender.tag()))

    @objc.python_method
    def abrirFicha(self, ficha, segundo=None):
        """Abre (o trae al frente) el editor de una transcripción."""
        if ficha is None:
            return None
        abierto = self.editores.get(ficha["id"])
        if abierto is None:
            abierto = Editor.alloc().initWithDueno_ficha_(self, ficha)
            if abierto is None:
                self.alerta("No se encontró la transcripción",
                            "El archivo se movió o se borró. Usa «Ubicar…» para volver a encontrarlo.",
                            ["Aceptar"])
                self.pintarHechos()
                return None
            self.editores[ficha["id"]] = abierto
        abierto.mostrar(segundo)
        return abierto

    @objc.python_method
    def alCerrarEditor(self, id_ficha):
        self.editores.pop(id_ficha, None)

    @objc.python_method
    def alGuardarFicha(self, ficha):
        """El editor guardó cambios: que el historial los refleje."""
        self.historial = [ficha if f["id"] == ficha["id"] else f for f in self.historial]
        self.pintarHechos()

    @objc.python_method
    def renombrarPersonas(self, ficha, nombres):
        """Pone nombre a quien habla y reescribe tu archivo: «Persona 1:» pasa a «Ana:»."""
        contenido = biblioteca.texto(ficha)
        if contenido is None:
            raise ValueError("No se encontró el archivo de esa transcripción")
        actuales = ficha.get("personas") or {}
        biblioteca.escribir_texto(ficha, formatos.renombrar_personas(contenido, nombres, actuales))
        ficha["personas"] = {**actuales, **nombres}
        biblioteca.guardar(ficha)
        self.alGuardarFicha(ficha)
        return ficha

    @objc.python_method
    def calcularTiempos(self, ficha):
        """Encola el cálculo del resaltado de una transcripción ya hecha."""
        audio_origen = biblioteca.ubicar(ficha, "origen")
        if audio_origen is None:
            self.alerta("No se encontró el audio",
                        f"Para calcular los tiempos hace falta el archivo original:\n"
                        f"{ficha.get('origen', '')}", ["Aceptar"])
            return None
        ajustes = ficha.get("ajustes") or {}
        opciones = {"idioma": ajustes.get("idioma") or "es",
                    "precision": ajustes.get("precision") or "alta",
                    "vocabulario": ajustes.get("vocabulario") or "",
                    "formato": "parrafos", "destino": str(audio_origen.parent),
                    "ficha": ficha["id"]}
        trabajo = Trabajo(next(self.ids), audio_origen, opciones, "Resaltado", tarea="tiempos")
        self.cola.append({"id": trabajo.id, "ruta": audio_origen, "fraccion": None,
                          "cliente": "Resaltado", "tarea": "tiempos"})
        self.motor.encolar(trabajo)
        self.pintarCola()
        self.pintar()
        self.cafe()
        return trabajo.id

    def ubicarArchivo_(self, sender):
        ficha = self.fichaDe(sender.tag())
        if ficha is None:
            return
        panel = NSOpenPanel.openPanel()
        panel.setCanChooseFiles_(True)
        panel.setCanChooseDirectories_(False)
        panel.setPrompt_("Usar este")
        panel.setMessage_(f"¿Dónde está ahora «{Path(ficha.get('salida', '')).name}»?")
        if panel.runModal() == 1:
            biblioteca.apuntar(ficha, "salida", Path(panel.URL().path()))
            self.pintarHechos()

    def quitarDelHistorial_(self, sender):
        ficha = self.fichaDe(sender.tag())
        if ficha is None:
            return
        biblioteca.olvidar(ficha["id"])
        self.historial = [f for f in self.historial if f["id"] != ficha["id"]]
        self.pintarHechos()
        self.pintar()

    # ------------------------------------------------------------- historial --
    def abrirHistorial_(self, sender):
        self.verHistorial()

    def buscarDocumento_(self, sender):
        self.verHistorial(buscar=True)

    @objc.python_method
    def verHistorial(self, buscar=False):
        """La ventana con todo lo transcrito, que es lo que sobrevive a la sesión."""
        if self.ventana_historial is None:
            self.ventana_historial = Historial.alloc().initWithDueno_(self)
        self.ventana_historial.mostrar(buscar=buscar)

    @objc.python_method
    def olvidarFicha(self, ficha):
        biblioteca.olvidar(ficha["id"])
        self.historial = [f for f in self.historial if f["id"] != ficha["id"]]
        self.hechos = [e for e in self.hechos
                       if e["tipo"] != "ficha" or e["ficha"]["id"] != ficha["id"]]
        self.pintarHechos()
        self.pintar()

    def copiarGuiaAgentes_(self, sender):
        tablero = NSPasteboard.generalPasteboard()
        tablero.clearContents()
        tablero.setString_forType_(agentes.GUIA, NSPasteboardTypeString)
        self.avisar("Guía para agentes copiada: pégala en el AGENTS.md o CLAUDE.md de tu proyecto.")
        self.pintar()

    def abrirRepositorio_(self, sender):
        NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_(REPO))

    def acercaDe_(self, sender):
        creditos = ui.attributed(
            "Convierte audio y video en texto, en tu Mac y sin internet.\n"
            "Motor: Qwen3-ASR (código abierto) acelerado con MLX.\n"
            f"Agentes de IA: comando `transcribir`.\n{REPO}",
            11.0, ui.W_REGULAR, NSColor.secondaryLabelColor())
        app = NSApplication.sharedApplication()
        app.orderFrontStandardAboutPanelWithOptions_({
            "ApplicationName": NOMBRE, "ApplicationVersion": VERSION, "Version": COMPILACION,
            "Credits": creditos})
        app.activateIgnoringOtherApps_(True)

    def abrirAjustes_(self, sender):
        if self.ventana_ajustes is None:
            self.ventana_ajustes = ControladorAjustes.alloc().initWithDueno_(self)
        self.ventana_ajustes.mostrar()

    # ---------------------------------------------------------- notificaciones --
    def userNotificationCenter_willPresentNotification_withCompletionHandler_(
            self, centro, aviso, responder):
        responder(avisos.PRESENTAR)          # también con la app al frente

    def userNotificationCenter_didReceiveNotificationResponse_withCompletionHandler_(
            self, centro, respuesta, responder):
        avisos.abrir_desde(respuesta)
        responder()

    @objc.python_method
    def alerta(self, titulo, texto, botones):
        a = NSAlert.alloc().init()
        a.setMessageText_(titulo)
        a.setInformativeText_(texto)
        for b in botones:
            a.addButtonWithTitle_(b)
        return a.runModal()

    @objc.python_method
    def preguntarTexto(self, titulo, explicacion, valor="", ejemplo=""):
        """Un texto corto (el nombre de quien habla). None si se cancela."""
        a = NSAlert.alloc().init()
        a.setMessageText_(titulo)
        a.setInformativeText_(explicacion)
        a.addButtonWithTitle_("Guardar")
        a.addButtonWithTitle_("Cancelar")
        campo = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 0, 240, 24))
        campo.setStringValue_(valor)
        campo.setPlaceholderString_(ejemplo)
        a.setAccessoryView_(campo)
        a.window().setInitialFirstResponder_(campo)
        if a.runModal() != 1000:
            return None
        return campo.stringValue().strip()


def main():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(0)
    icono = recursos.ruta("Transcribir.icns")
    if icono.exists():
        app.setApplicationIconImage_(NSImage.alloc().initWithContentsOfFile_(str(icono)))
    delegado = DelegadoTranscribir.alloc().init()
    app.setDelegate_(delegado)
    AppHelper.runEventLoop()


if __name__ == "__main__":
    main()
