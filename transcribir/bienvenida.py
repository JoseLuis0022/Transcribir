"""Bienvenida: la primera vez, elegir el modelo, descargarlo y conectar con agentes."""

import threading

import objc
from AppKit import NSColor, NSProgressIndicator, NSSwitch, NSView
from Foundation import NSMakeRect, NSObject
from PyObjCTools import AppHelper

import modelos
import ui

PAD = 22.0
OPCIONES = (("alta", f"Máxima precisión · {modelos.gb(modelos.CATALOGO['alta'][1])}"),
            ("rapida", f"Rápida · {modelos.gb(modelos.CATALOGO['rapida'][1])}"))


class Bienvenida(NSObject):
    """Ocupa el lugar de las listas hasta que el modelo elegido está descargado."""

    def initWithDueno_marco_(self, dueno, marco):
        self = objc.super(Bienvenida, self).init()
        if self is None:
            return None
        self.dueno = dueno              # el delegado de la app
        self.descargando = False
        self.cancelado = False
        self.vista = NSView.alloc().initWithFrame_(marco)
        self.construir(marco.size.width, marco.size.height)
        return self

    @objc.python_method
    def construir(self, ancho, alto):
        cw = ancho - PAD * 2
        y = alto - 14.0 - 16.0
        self.vista.addSubview_(ui.section_title("PARA EMPEZAR", NSMakeRect(PAD + 4, y, cw, 16)))

        h = 50.0 + 50.0 + 46.0 + 16.0
        y -= 6.0 + h
        caja = ui.card(NSMakeRect(PAD, y, cw, h))
        self.vista.addSubview_(caja)

        fila = h - 8 - 50
        caja.addSubview_(ui.label("Modelo", 13.0, ui.W_MEDIUM, NSColor.labelColor(),
                                  NSMakeRect(16, fila + 26, 160, 20), ui.ALIGN_LEFT))
        caja.addSubview_(ui.label("Se descarga una sola vez", 11.0, ui.W_REGULAR,
                                  NSColor.tertiaryLabelColor(), NSMakeRect(16, fila + 6, 160, 18),
                                  ui.ALIGN_LEFT))
        self.menu = ui.popup(NSMakeRect(cw - 16 - 214, fila + 12, 214, 26),
                             [t for _, t in OPCIONES], self, None)
        caja.addSubview_(self.menu)
        caja.addSubview_(ui.hairline(NSMakeRect(16, fila, cw - 32, 1)))

        fila -= 50
        caja.addSubview_(ui.label("Conectar con agentes de IA", 13.0, ui.W_MEDIUM, NSColor.labelColor(),
                                  NSMakeRect(16, fila + 26, cw - 90, 20), ui.ALIGN_LEFT))
        caja.addSubview_(ui.label("Claude Code y otros agentes podrán usar Transcribir", 11.0,
                                  ui.W_REGULAR, NSColor.tertiaryLabelColor(),
                                  NSMakeRect(16, fila + 6, cw - 90, 18), ui.ALIGN_LEFT))
        self.interruptor = NSSwitch.alloc().initWithFrame_(NSMakeRect(cw - 54, fila + 14, 38, 22))
        self.interruptor.setState_(1)
        caja.addSubview_(self.interruptor)
        caja.addSubview_(ui.hairline(NSMakeRect(16, fila, cw - 32, 1)))

        fila -= 46
        caja.addSubview_(ui.icon_view("lock.shield.fill", NSMakeRect(16, fila + 14, 18, 18),
                                      NSColor.secondaryLabelColor(), 13.0))
        caja.addSubview_(ui.label("Todo se procesa en tu Mac. Internet solo se usa para esta descarga.",
                                  11.5, ui.W_REGULAR, NSColor.secondaryLabelColor(),
                                  NSMakeRect(44, fila + 6, cw - 60, 32), ui.ALIGN_LEFT))

        # botón principal, y en su lugar el progreso mientras descarga
        y -= 22.0 + 32.0
        self.boton = ui.bezel_button("Descargar y empezar", NSMakeRect((ancho - 220) / 2, y, 220, 32),
                                     self, b"empezar:", size=13.0)
        self.boton.setKeyEquivalent_("\r")                  # botón por defecto, en azul
        self.vista.addSubview_(self.boton)

        self.barra = NSProgressIndicator.alloc().initWithFrame_(NSMakeRect(PAD, y + 16, cw, 12))
        self.barra.setStyle_(0)
        self.barra.setControlSize_(1)
        self.barra.setIndeterminate_(False)
        self.barra.setMinValue_(0.0)
        self.barra.setMaxValue_(100.0)
        self.vista.addSubview_(self.barra)
        self.estado = ui.label("", 11.5, ui.W_REGULAR, NSColor.secondaryLabelColor(),
                               NSMakeRect(PAD, y - 6, cw - 104, 16), ui.ALIGN_LEFT, truncate=ui.TRUNC_TAIL)
        self.vista.addSubview_(self.estado)
        self.boton_cancelar = ui.bezel_button("Cancelar", NSMakeRect(PAD + cw - 96, y - 10, 96, 24),
                                              self, b"cancelar:", size=11.5)
        self.vista.addSubview_(self.boton_cancelar)
        self.mostrarProgreso(False)

        self.error = ui.label("", 11.5, ui.W_REGULAR, NSColor.systemOrangeColor(),
                              NSMakeRect(PAD, y - 34, cw, 30))
        self.vista.addSubview_(self.error)

    @objc.python_method
    def mostrarProgreso(self, visible):
        for v in (self.barra, self.estado, self.boton_cancelar):
            v.setHidden_(not visible)
        self.boton.setHidden_(visible)
        self.menu.setEnabled_(not visible)
        self.interruptor.setEnabled_(not visible)

    # ------------------------------------------------------------- acciones --
    def empezar_(self, sender):
        self.clave = OPCIONES[self.menu.indexOfSelectedItem()][0]
        self.cancelado, self.descargando = False, True
        self.error.setStringValue_("")
        self.barra.setDoubleValue_(0.0)
        self.estado.setStringValue_("Conectando…")
        self.mostrarProgreso(True)
        self.dueno.pintar()
        threading.Thread(target=self.bajar, args=(self.clave,), daemon=True).start()

    def cancelar_(self, sender):
        self.cancelado = True
        self.estado.setStringValue_("Cancelando…")

    @objc.python_method
    def bajar(self, clave):
        try:
            modelos.descargar(clave, lambda b, t: AppHelper.callAfter(self.avance, b, t),
                              lambda: self.cancelado)
            AppHelper.callAfter(self.listo)
        except modelos.DescargaCancelada:
            AppHelper.callAfter(self.detener, "")
        except Exception as e:
            AppHelper.callAfter(self.detener, str(e))

    @objc.python_method
    def avance(self, bajado, total):
        if self.cancelado:
            return
        fraccion = bajado / total if total else 0.0
        self.barra.setDoubleValue_(fraccion * 100)
        self.estado.setStringValue_(
            f"Descargando el modelo… {modelos.gb(bajado)} de {modelos.gb(total)} · {round(fraccion * 100)} %")

    @objc.python_method
    def detener(self, error):
        self.descargando = False
        self.mostrarProgreso(False)
        self.boton.setAttributedTitle_(ui.attributed("Reintentar" if error else "Descargar y empezar",
                                                     13.0, ui.W_REGULAR, NSColor.labelColor()))
        self.error.setStringValue_(error)
        self.dueno.pintar()

    @objc.python_method
    def listo(self):
        self.descargando = False
        self.dueno.terminarBienvenida(self.clave, self.interruptor.state() == 1)
