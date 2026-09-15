"""La ventana del historial: todo lo que has transcrito, con su buscador.

La ventana principal solo enseña lo de esta sesión, que se vacía al salir. Aquí
está todo lo demás, que vive en las fichas de la biblioteca.

La lista es una tabla del sistema, así que una fila se puede deslizar con dos
dedos para quitarla o ubicarla, igual que en Notas o en Mail.
"""

from pathlib import Path

import objc
from AppKit import (
    NSApplication, NSBackingStoreBuffered, NSColor, NSOpenPanel, NSScrollView, NSSearchField,
    NSTableColumn, NSTableView, NSTableViewRowAction, NSView, NSVisualEffectView, NSWindow,
    NSWorkspace,
)
from Foundation import NSURL, NSMakeRect, NSObject

import biblioteca
import exportar
import formatos
import ui

W, H = 620.0, 660.0
PAD = 20.0
BUSCADOR = 56.0                  # la barra de arriba
FILA = 58.0
BOTON, ACCION = 20.0, 74.0
DESTRUCTIVA, NORMAL = 1, 0       # estilos de una acción al deslizar
DERECHA = 1                      # el borde por el que se desliza


class Fila(NSView):
    """Una fila de la lista, que se recoloca sola.

    La tabla decide el ancho de la fila después de crearla —y con el estilo de
    Notas le quita márgenes por los lados—, así que las posiciones se calculan
    cada vez que cambia, y no al pintarla: si no, los botones acaban pegados al
    borde derecho.
    """

    def setFrameSize_(self, tamano):
        objc.super(Fila, self).setFrameSize_(tamano)
        self.colocar()

    @objc.python_method
    def colocar(self):
        ancho = self.frame().size.width
        if ancho <= 0 or getattr(self, "icono", None) is None:
            return
        x_icono = ancho - PAD - BOTON
        x_boton = x_icono - 10 - ACCION
        ancho_texto = max(x_boton - PAD - 40, 20.0)
        self.icono.setFrameOrigin_((x_icono, self.icono.frame().origin.y))
        self.accion.setFrameOrigin_((x_boton, self.accion.frame().origin.y))
        for texto in (self.titulo, self.detalle):
            marco = texto.frame()
            texto.setFrameSize_((ancho_texto, marco.size.height))


class Historial(NSObject):

    def initWithDueno_(self, dueno):
        self = objc.super(Historial, self).init()
        if self is None:
            return None
        self.dueno = dueno          # el delegado de la app
        self.ventana = None
        self.filtro = ""
        self.fichas = []            # lo que se está enseñando ahora
        return self

    @objc.python_method
    def mostrar(self, buscar=False):
        if self.ventana is None:
            self.construir()
        self.pintar()
        self.ventana.makeKeyAndOrderFront_(None)
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        self.ventana.makeFirstResponder_(self.buscador if buscar else self.tabla)

    # ------------------------------------------------------------- interfaz --
    @objc.python_method
    def construir(self):
        rect = NSMakeRect(0, 0, W, H)
        self.ventana = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, ui.STYLE_TITLED | ui.STYLE_CLOSABLE | ui.STYLE_MINI | ui.STYLE_RESIZABLE,
            NSBackingStoreBuffered, False)
        self.ventana.setTitle_("Historial")
        self.ventana.setReleasedWhenClosed_(False)
        self.ventana.setMinSize_((480, 380))
        self.ventana.setDelegate_(self)
        self.ventana.center()

        fondo = NSVisualEffectView.alloc().initWithFrame_(rect)
        fondo.setMaterial_(ui.MATERIAL_UNDER_WINDOW)
        fondo.setBlendingMode_(ui.BLEND_BEHIND_WINDOW)
        fondo.setState_(ui.VFX_ACTIVE)
        fondo.setAutoresizingMask_(2 | 16)
        self.ventana.setContentView_(fondo)

        barra = NSView.alloc().initWithFrame_(NSMakeRect(0, H - BUSCADOR, W, BUSCADOR))
        barra.setAutoresizingMask_(2 | 8)
        fondo.addSubview_(barra)
        barra.addSubview_(ui.hairline(NSMakeRect(0, 0, W, 1)))
        self.buscador = NSSearchField.alloc().initWithFrame_(
            NSMakeRect(PAD, (BUSCADOR - 24) / 2, W - PAD * 2 - 130, 24))
        self.buscador.setPlaceholderString_("Buscar en todas tus transcripciones")
        self.buscador.setAutoresizingMask_(2)
        self.buscador.setDelegate_(self)
        self.buscador.setTarget_(self)
        self.buscador.setAction_(b"buscar:")
        barra.addSubview_(self.buscador)
        self.cuenta = ui.label("", 11.5, ui.W_REGULAR, NSColor.secondaryLabelColor(),
                               NSMakeRect(W - PAD - 120, (BUSCADOR - 15) / 2, 120, 15),
                               ui.ALIGN_RIGHT)
        self.cuenta.setAutoresizingMask_(1)
        barra.addSubview_(self.cuenta)

        alto = H - BUSCADOR
        self.scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(0, 0, W, alto))
        self.scroll.setHasVerticalScroller_(True)
        self.scroll.setAutohidesScrollers_(True)
        self.scroll.setDrawsBackground_(False)
        self.scroll.setAutoresizingMask_(2 | 16)

        self.tabla = NSTableView.alloc().initWithFrame_(NSMakeRect(0, 0, W, alto))
        columna = NSTableColumn.alloc().initWithIdentifier_("fila")
        columna.setResizingMask_(1)                  # se estira con la ventana
        columna.setMinWidth_(240.0)
        columna.setWidth_(W)
        self.tabla.addTableColumn_(columna)
        self.tabla.setColumnAutoresizingStyle_(1)    # la única columna ocupa el ancho
        self.tabla.setHeaderView_(None)
        self.tabla.setRowHeight_(FILA)
        self.tabla.setBackgroundColor_(NSColor.clearColor())
        self.tabla.setIntercellSpacing_((0, 0))
        self.tabla.setGridStyleMask_(0)
        if hasattr(self.tabla, "setStyle_"):
            self.tabla.setStyle_(2)                  # con márgenes, como en Notas
        self.tabla.setDataSource_(self)
        self.tabla.setDelegate_(self)
        self.tabla.setTarget_(self)
        self.tabla.setDoubleAction_(b"abrirSeleccion:")
        self.scroll.setDocumentView_(self.tabla)
        fondo.addSubview_(self.scroll)

        self.vacio = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, W, alto))
        self.vacio.setAutoresizingMask_(2 | 16)
        self.vacio.setHidden_(True)
        fondo.addSubview_(self.vacio)

    # ---------------------------------------------------------------- lista --
    @objc.python_method
    def pintar(self):
        self.fichas = biblioteca.buscar(self.filtro, self.dueno.historial)
        self.tabla.reloadData()
        total = len(self.dueno.historial)
        self.pintarVacio()
        if not self.fichas:
            self.cuenta.setStringValue_("")
        elif self.filtro:
            self.cuenta.setStringValue_(f"{len(self.fichas)} de {total}")
        else:
            self.cuenta.setStringValue_(
                f"{total} transcripciones" if total != 1 else "1 transcripción")

    @objc.python_method
    def pintarVacio(self):
        for vista in list(self.vacio.subviews()):
            vista.removeFromSuperview()
        self.vacio.setHidden_(bool(self.fichas))
        if self.fichas:
            return
        ancho = self.vacio.frame().size.width
        alto = self.vacio.frame().size.height
        simbolo = "magnifyingglass" if self.filtro else "clock.arrow.circlepath"
        texto = (f"Nada que diga «{self.filtro}»" if self.filtro
                 else "Aquí se irá guardando todo lo que transcribas")
        self.vacio.addSubview_(ui.icon_view(simbolo, NSMakeRect((ancho - 26) / 2, alto * 0.58, 26, 24),
                                            NSColor.tertiaryLabelColor(), 20.0))
        self.vacio.addSubview_(ui.label(texto, 12.5, ui.W_REGULAR, NSColor.tertiaryLabelColor(),
                                        NSMakeRect(PAD, alto * 0.58 - 34, ancho - PAD * 2, 20)))

    # ---------------------------------------------- de dónde salen las filas --
    def numberOfRowsInTableView_(self, tabla):
        return len(self.fichas)

    def tableView_viewForTableColumn_row_(self, tabla, columna, fila):
        if fila >= len(self.fichas):
            return None
        return self.fila(self.fichas[fila], tabla.frame().size.width, fila)

    @objc.python_method
    def fila(self, ficha, ancho, indice):
        v = Fila.alloc().initWithFrame_(NSMakeRect(0, 0, ancho, FILA))
        v.setAutoresizingMask_(2)
        ruta = biblioteca.ubicar(ficha)

        simbolo, color = (("checkmark.circle.fill", NSColor.systemGreenColor()) if ruta
                          else ("questionmark.circle.fill", NSColor.tertiaryLabelColor()))
        v.addSubview_(ui.icon_view(simbolo, NSMakeRect(PAD, 19, 20, 20), color, 15.0))
        v.titulo = ui.label(ficha.get("nombre", ""), 13.0, ui.W_MEDIUM, NSColor.labelColor(),
                            NSMakeRect(PAD + 30, 29, 100, 18), ui.ALIGN_LEFT,
                            truncate=ui.TRUNC_MIDDLE)
        v.detalle = ui.label(self.detalle(ficha, ruta), 11.0, ui.W_REGULAR,
                             NSColor.systemOrangeColor() if ruta is None
                             else NSColor.tertiaryLabelColor(),
                             NSMakeRect(PAD + 30, 12, 100, 15), ui.ALIGN_LEFT,
                             truncate=ui.TRUNC_TAIL)
        if ruta is None:
            v.accion = ui.bezel_button("Ubicar…", NSMakeRect(0, 19, ACCION, 24),
                                       self, b"ubicar:", tag=indice)
            v.icono = ui.symbol_button("xmark.circle.fill",
                                       NSMakeRect(0, 23, BOTON, BOTON), self,
                                       b"olvidar:", tag=indice, size=14.0,
                                       tooltip="Quitar del historial",
                                       tint=NSColor.tertiaryLabelColor())
        else:
            v.accion = ui.bezel_button("Abrir", NSMakeRect(0, 19, ACCION, 24),
                                       self, b"abrir:", tag=indice)
            v.accion.setToolTip_(f"Ver, escuchar y corregir\n{ruta}")
            v.icono = ui.symbol_button("folder.circle.fill",
                                       NSMakeRect(0, 23, BOTON, BOTON), self,
                                       b"enFinder:", tag=indice, size=14.0,
                                       tooltip=f"Mostrar en Finder\n{ruta}",
                                       tint=NSColor.secondaryLabelColor())
        for vista in (v.titulo, v.detalle, v.accion, v.icono):
            v.addSubview_(vista)
        v.colocar()
        return v

    @objc.python_method
    def detalle(self, ficha, ruta):
        if ruta is None:
            return "No encontrado · se movió o se borró"
        partes = [exportar.fecha_corta(ficha.get("creado")),
                  formatos.duracion_corta(ficha.get("duracion") or 0)]
        if ficha.get("aviso"):                   # archivo cortado: se transcribió lo que había
            partes.append("incompleto")
        if ficha.get("coincidencia"):
            partes.append(ficha["coincidencia"])
        else:
            partes.append("Escritorio" if ruta.parent == biblioteca.ESCRITORIO else ruta.parent.name)
            if ficha.get("personas"):
                partes.append(", ".join(v for v in ficha["personas"].values() if v.strip()))
        return " · ".join(p for p in partes if p)

    # -------------------------------------------------- deslizar con la mano --
    def tableView_rowActionsForRow_edge_(self, tabla, fila, borde):
        """Deslizando la fila con dos dedos, como en Notas."""
        if borde != DERECHA or fila >= len(self.fichas):
            return []
        quitar = NSTableViewRowAction.rowActionWithStyle_title_handler_(
            DESTRUCTIVA, "Quitar", lambda accion, cual: self.quitarFila(cual))
        if biblioteca.ubicar(self.fichas[fila]) is None:
            otra = NSTableViewRowAction.rowActionWithStyle_title_handler_(
                NORMAL, "Ubicar…", lambda accion, cual: self.ubicarFila(cual))
        else:
            otra = NSTableViewRowAction.rowActionWithStyle_title_handler_(
                NORMAL, "Finder", lambda accion, cual: self.enFinderFila(cual))
        return [quitar, otra]

    @objc.python_method
    def quitarFila(self, fila):
        if fila < len(self.fichas):
            self.dueno.olvidarFicha(self.fichas[fila])
            self.pintar()

    @objc.python_method
    def ubicarFila(self, fila):
        if fila >= len(self.fichas):
            return
        ficha = self.fichas[fila]
        self.tabla.setRowActionsVisible_(False)
        panel = NSOpenPanel.openPanel()
        panel.setCanChooseFiles_(True)
        panel.setCanChooseDirectories_(False)
        panel.setPrompt_("Usar este")
        panel.setMessage_(f"¿Dónde está ahora «{Path(ficha.get('salida', '')).name}»?")
        if panel.runModal() == 1:
            biblioteca.apuntar(ficha, "salida", Path(panel.URL().path()))
            self.pintar()

    @objc.python_method
    def enFinderFila(self, fila):
        self.tabla.setRowActionsVisible_(False)
        if fila >= len(self.fichas):
            return
        ruta = biblioteca.ubicar(self.fichas[fila])
        if ruta is None:
            self.pintar()
            return
        NSWorkspace.sharedWorkspace().activateFileViewerSelectingURLs_(
            [NSURL.fileURLWithPath_(str(ruta))])

    # -------------------------------------------------------------- acciones --
    def buscar_(self, sender):
        self.filtro = sender.stringValue().strip()
        self.pintar()

    def controlTextDidChange_(self, notificacion):
        self.filtro = self.buscador.stringValue().strip()
        self.pintar()

    def control_textView_doCommandBySelector_(self, control, vista, selector):
        if selector == "cancelOperation:":
            self.buscador.setStringValue_("")
            self.filtro = ""
            self.pintar()
            return True
        return False

    def abrirSeleccion_(self, sender):
        fila = self.tabla.clickedRow()
        if 0 <= fila < len(self.fichas):
            self.dueno.abrirFicha(self.fichas[fila])

    def abrir_(self, sender):
        if sender.tag() < len(self.fichas):
            self.dueno.abrirFicha(self.fichas[sender.tag()])

    def enFinder_(self, sender):
        self.enFinderFila(sender.tag())

    def ubicar_(self, sender):
        self.ubicarFila(sender.tag())

    def olvidar_(self, sender):
        self.quitarFila(sender.tag())

    def windowDidResize_(self, notificacion):
        self.pintarVacio()
        self.tabla.reloadData()
