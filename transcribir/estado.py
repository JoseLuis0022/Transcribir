"""El icono de la barra de menús: cómo va lo que se está transcribiendo.

Es un círculo que se va llenando. Está siempre ahí, así que puedes dejar la
ventana cerrada y seguir viendo el avance desde arriba, como en Sereno.
"""

import objc
from AppKit import (
    NSBezierPath, NSColor, NSImage, NSMenu, NSMenuItem, NSStatusBar, NSView,
    NSVariableStatusItemLength,
)
from Foundation import NSMakeRect, NSObject, NSPoint

import ui

LADO = 18.0
TRAZO = 1.7
ARRIBA = 90.0                    # el arco empieza a las doce


def circulo(fraccion: float) -> NSImage:
    """El anillo del avance: vacío en reposo, entero al acabar."""
    img = NSImage.alloc().initWithSize_((LADO, LADO))
    img.lockFocus()
    centro = NSPoint(LADO / 2, LADO / 2)
    radio = (LADO - TRAZO * 2 - 2) / 2

    fondo = NSBezierPath.bezierPathWithOvalInRect_(
        NSMakeRect(centro.x - radio, centro.y - radio, radio * 2, radio * 2))
    fondo.setLineWidth_(TRAZO)
    NSColor.blackColor().colorWithAlphaComponent_(0.28).setStroke()
    fondo.stroke()

    if fraccion > 0:
        arco = NSBezierPath.bezierPath()
        arco.appendBezierPathWithArcWithCenter_radius_startAngle_endAngle_clockwise_(
            centro, radio, ARRIBA, ARRIBA - 360.0 * min(fraccion, 1.0), True)
        arco.setLineWidth_(TRAZO)
        arco.setLineCapStyle_(1)                  # redondeado, como los del sistema
        NSColor.blackColor().setStroke()
        arco.stroke()
    img.unlockFocus()
    img.setTemplate_(True)                        # macOS lo recolorea solo
    return img


class Estado(NSObject):
    """El elemento de la barra de menús y su menú."""

    def initWithDueno_(self, dueno):
        self = objc.super(Estado, self).init()
        if self is None:
            return None
        self.dueno = dueno
        self.item = NSStatusBar.systemStatusBar().statusItemWithLength_(
            NSVariableStatusItemLength)
        self.item.button().setImage_(ui.sf("waveform", 14.0))
        self.item.button().setToolTip_("Transcribir")
        self.menu = NSMenu.alloc().init()
        self.menu.setAutoenablesItems_(False)
        self.item.setMenu_(self.menu)
        self.pintado = None
        self.pintarMenu(0, 0, "")
        return self

    @objc.python_method
    def quitar(self):
        NSStatusBar.systemStatusBar().removeStatusItem_(self.item)

    # ------------------------------------------------------------------ icono --
    @objc.python_method
    def actualizar(self, en_cola: int, hechos: int, fraccion: float, texto: str, queda=None):
        """`fraccion` es lo que lleva el archivo de ahora; -1 si aún no se sabe.
        `queda` son los segundos que faltan, si se pueden estimar."""
        boton = self.item.button()
        if not en_cola:
            if self.pintado != "reposo":
                boton.setImage_(ui.sf("waveform", 14.0))
                boton.setToolTip_("Transcribir · sin nada en cola")
                self.pintado = "reposo"
        else:
            # el avance es el de todo el lote, no solo el del archivo de ahora
            total = en_cola + hechos
            suyo = max(fraccion, 0.0)
            avance = (hechos + suyo) / total if total else 0.0
            clave = round(avance, 2)
            if self.pintado != clave:
                boton.setImage_(circulo(avance))
                boton.setToolTip_(f"Transcribir · {texto or 'trabajando'}")
                self.pintado = clave
        self.pintarMenu(en_cola, hechos, texto, fraccion, queda)

    # ------------------------------------------------------------------- menú --
    @objc.python_method
    def cabecera(self, en_cola, hechos, texto, fraccion, queda):
        """Lo de arriba del menú: qué se está haciendo, cuánto falta y su barra."""
        ancho, alto = 268.0, 62.0
        v = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, ancho, alto))
        if not en_cola:
            v.addSubview_(ui.label("Sin nada en cola", 13.0, ui.W_MEDIUM,
                                   NSColor.secondaryLabelColor(),
                                   NSMakeRect(14, (alto - 18) / 2, ancho - 28, 18), ui.ALIGN_LEFT))
            return v

        total = en_cola + hechos
        hecho = f"{hechos + 1} de {total}" if total > 1 else ""
        derecha = []
        if fraccion is not None and fraccion >= 0:
            derecha.append(f"{round(fraccion * 100)} %")
        if queda:
            derecha.append(f"quedan {queda}")
        elif hecho:
            derecha.append(hecho)
        aparte = " · ".join(derecha)
        suyo = ui.attributed(aparte, 11.0, ui.W_REGULAR, NSColor.secondaryLabelColor()).size().width

        v.addSubview_(ui.label(texto or "Transcribiendo", 13.0, ui.W_SEMIBOLD, NSColor.labelColor(),
                               NSMakeRect(14, alto - 24, ancho - 28 - suyo - 12, 18),
                               ui.ALIGN_LEFT, truncate=ui.TRUNC_TAIL))
        v.addSubview_(ui.label(aparte, 11.0, ui.W_REGULAR, NSColor.secondaryLabelColor(),
                               NSMakeRect(ancho - 14 - suyo - 4, alto - 23, suyo + 4, 16),
                               ui.ALIGN_RIGHT))
        v.addSubview_(ui.barra_progreso(NSMakeRect(14, alto - 40, ancho - 28, 6), fraccion))
        if hecho and queda:
            v.addSubview_(ui.label(hecho, 11.0, ui.W_REGULAR, NSColor.tertiaryLabelColor(),
                                   NSMakeRect(14, 8, ancho - 28, 14), ui.ALIGN_LEFT))
        return v

    @objc.python_method
    def pintarMenu(self, en_cola, hechos, texto, fraccion=0.0, queda=None):
        self.menu.removeAllItems()
        cabecera = ui.menu_item("", None, "")
        cabecera.setEnabled_(False)
        cabecera.setView_(self.cabecera(en_cola, hechos, texto, fraccion, queda))
        self.menu.addItem_(cabecera)
        self.menu.addItem_(NSMenuItem.separatorItem())

        for etiqueta, accion, tecla in (
                ("Mostrar Transcribir", b"mostrarVentana:", ""),
                ("Historial…", b"abrirHistorial:", ""),
                ("Agregar archivos…", b"elegirArchivos:", ""),
                ("Abrir la carpeta de destino", b"abrirCarpeta:", "")):
            self.menu.addItem_(ui.menu_item(etiqueta, accion, tecla, self.dueno))
        if en_cola:
            self.menu.addItem_(NSMenuItem.separatorItem())
            self.menu.addItem_(ui.menu_item("Cancelar todo", b"cancelarTodo:", "", self.dueno))
        self.menu.addItem_(NSMenuItem.separatorItem())
        self.menu.addItem_(ui.menu_item("Ajustes…", b"abrirAjustes:", "", self.dueno))
        self.menu.addItem_(ui.menu_item("Salir de Transcribir", b"terminate:", ""))
