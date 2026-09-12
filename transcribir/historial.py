"""La ventana del historial: todo lo que has transcrito, con su buscador.

La ventana principal solo enseña lo de esta sesión, que se vacía al salir. Aquí
está todo lo demás, que vive en las fichas de la biblioteca.
"""

from pathlib import Path

import objc
from AppKit import (
    NSApplication, NSBackingStoreBuffered, NSColor, NSOpenPanel, NSScrollView, NSSearchField,
    NSView, NSVisualEffectView, NSWindow, NSWorkspace,
)
from Foundation import NSURL, NSMakeRect, NSObject

import biblioteca
import exportar
import formatos
import ui

W, H = 620.0, 660.0
PAD = 20.0
BUSCADOR = 56.0                  # la barra de arriba
FILA = 56.0
BOTON, ACCION = 20.0, 74.0


class Historial(NSObject):

    def initWithDueno_(self, dueno):
        self = objc.super(Historial, self).init()
        if self is None:
            return None
        self.dueno = dueno          # el delegado de la app
        self.ventana = None
        self.filtro = ""
        self.claves = {}            # id de ficha -> número, que es lo que entiende un tag
        return self

    @objc.python_method
    def mostrar(self, buscar=False):
        if self.ventana is None:
            self.construir()
        self.pintar()
        self.ventana.makeKeyAndOrderFront_(None)
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        self.ventana.makeFirstResponder_(self.buscador if buscar else None)

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

        barra = ui.material(NSMakeRect(0, H - BUSCADOR, W, BUSCADOR), ui.MATERIAL_BARRA)
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
        scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(0, 0, W, alto))
        scroll.setHasVerticalScroller_(True)
        scroll.setAutohidesScrollers_(True)
        scroll.setDrawsBackground_(False)
        scroll.setAutoresizingMask_(2 | 16)
        self.lista = ui.VistaVolteada.alloc().initWithFrame_(NSMakeRect(0, 0, W, alto))
        self.lista.setAutoresizingMask_(2)
        scroll.setDocumentView_(self.lista)
        fondo.addSubview_(scroll)
        self.scroll = scroll

    # ---------------------------------------------------------------- lista --
    @objc.python_method
    def pintar(self):
        for vista in list(self.lista.subviews()):
            vista.removeFromSuperview()
        fichas = biblioteca.buscar(self.filtro, self.dueno.historial)
        ancho = self.scroll.contentSize().width
        self.lista.setFrameSize_((ancho, max(len(fichas) * FILA + 8, self.scroll.contentSize().height)))
        for i, ficha in enumerate(fichas):
            fila = self.fila(ficha, ancho, ultima=i == len(fichas) - 1)
            fila.setFrameOrigin_((0, 4 + i * FILA))
            self.lista.addSubview_(fila)
        total = len(self.dueno.historial)
        if not fichas:
            self.vacio(ancho)
            self.cuenta.setStringValue_("")
        elif self.filtro:
            self.cuenta.setStringValue_(f"{len(fichas)} de {total}")
        else:
            self.cuenta.setStringValue_(
                f"{total} transcripciones" if total != 1 else "1 transcripción")

    @objc.python_method
    def vacio(self, ancho):
        simbolo = "magnifyingglass" if self.filtro else "clock.arrow.circlepath"
        texto = (f"Nada que diga «{self.filtro}»" if self.filtro
                 else "Aquí se irá guardando todo lo que transcribas")
        alto = self.scroll.contentSize().height
        self.lista.addSubview_(ui.icon_view(simbolo, NSMakeRect((ancho - 26) / 2, alto / 3, 26, 24),
                                            NSColor.tertiaryLabelColor(), 20.0))
        self.lista.addSubview_(ui.label(texto, 12.5, ui.W_REGULAR, NSColor.tertiaryLabelColor(),
                                        NSMakeRect(PAD, alto / 3 + 36, ancho - PAD * 2, 20)))

    @objc.python_method
    def fila(self, ficha, ancho, ultima):
        v = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, ancho, FILA))
        v.setAutoresizingMask_(2)
        ruta = biblioteca.ubicar(ficha)
        etiqueta = self.claves.setdefault(ficha["id"], len(self.claves) + 1)
        x_icono = ancho - PAD - BOTON
        x_boton = x_icono - 8 - ACCION
        ancho_texto = x_boton - PAD - 46

        simbolo, color = (("checkmark.circle.fill", NSColor.systemGreenColor()) if ruta
                          else ("questionmark.circle.fill", NSColor.tertiaryLabelColor()))
        v.addSubview_(ui.icon_view(simbolo, NSMakeRect(PAD, 18, 20, 20), color, 15.0))
        v.addSubview_(ui.label(ficha.get("nombre", ""), 13.0, ui.W_MEDIUM, NSColor.labelColor(),
                               NSMakeRect(PAD + 30, 28, ancho_texto, 18), ui.ALIGN_LEFT,
                               truncate=ui.TRUNC_MIDDLE))
        v.addSubview_(ui.label(self.detalle(ficha, ruta), 11.0, ui.W_REGULAR,
                               NSColor.systemOrangeColor() if ruta is None
                               else NSColor.tertiaryLabelColor(),
                               NSMakeRect(PAD + 30, 11, ancho_texto, 15), ui.ALIGN_LEFT,
                               truncate=ui.TRUNC_TAIL))
        if ruta is None:
            v.addSubview_(ui.bezel_button("Ubicar…", NSMakeRect(x_boton, 18, ACCION, 24),
                                          self, b"ubicar:", tag=etiqueta))
            v.addSubview_(ui.symbol_button("xmark.circle.fill",
                                           NSMakeRect(x_icono, 22, BOTON, BOTON), self,
                                           b"olvidar:", tag=etiqueta, size=14.0,
                                           tooltip="Quitar del historial",
                                           tint=NSColor.tertiaryLabelColor()))
        else:
            abrir = ui.bezel_button("Abrir", NSMakeRect(x_boton, 18, ACCION, 24),
                                    self, b"abrir:", tag=etiqueta)
            abrir.setToolTip_(f"Ver, escuchar y corregir\n{ruta}")
            v.addSubview_(abrir)
            v.addSubview_(ui.symbol_button("folder.circle.fill",
                                           NSMakeRect(x_icono, 22, BOTON, BOTON), self,
                                           b"enFinder:", tag=etiqueta, size=14.0,
                                           tooltip=f"Mostrar en Finder\n{ruta}",
                                           tint=NSColor.secondaryLabelColor()))
        if not ultima:
            v.addSubview_(ui.hairline(NSMakeRect(PAD, 0, ancho - PAD * 2, 1)))
        return v

    @objc.python_method
    def detalle(self, ficha, ruta):
        if ruta is None:
            return "No encontrado · se movió o se borró"
        partes = [exportar.fecha_corta(ficha.get("creado")),
                  formatos.duracion_corta(ficha.get("duracion") or 0)]
        if ficha.get("coincidencia"):
            partes.append(ficha["coincidencia"])
        else:
            partes.append("Escritorio" if ruta.parent == biblioteca.ESCRITORIO else ruta.parent.name)
            if ficha.get("personas"):
                partes.append(", ".join(v for v in ficha["personas"].values() if v.strip()))
        return " · ".join(p for p in partes if p)

    @objc.python_method
    def ficha(self, etiqueta):
        id_ficha = next((k for k, v in self.claves.items() if v == etiqueta), None)
        return next((f for f in self.dueno.historial if f["id"] == id_ficha), None)

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

    def abrir_(self, sender):
        self.dueno.abrirFicha(self.ficha(sender.tag()))

    def enFinder_(self, sender):
        ruta = biblioteca.ubicar(self.ficha(sender.tag()) or {})
        if ruta is None:
            self.pintar()
            return
        NSWorkspace.sharedWorkspace().activateFileViewerSelectingURLs_(
            [NSURL.fileURLWithPath_(str(ruta))])

    def ubicar_(self, sender):
        ficha = self.ficha(sender.tag())
        if ficha is None:
            return
        panel = NSOpenPanel.openPanel()
        panel.setCanChooseFiles_(True)
        panel.setCanChooseDirectories_(False)
        panel.setPrompt_("Usar este")
        panel.setMessage_(f"¿Dónde está ahora «{Path(ficha.get('salida', '')).name}»?")
        if panel.runModal() == 1:
            biblioteca.apuntar(ficha, "salida", Path(panel.URL().path()))
            self.pintar()

    def olvidar_(self, sender):
        ficha = self.ficha(sender.tag())
        if ficha is None:
            return
        self.dueno.olvidarFicha(ficha)
        self.pintar()

    def windowDidResize_(self, notificacion):
        self.pintar()
