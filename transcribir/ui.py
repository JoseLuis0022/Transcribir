"""Piezas de interfaz nativas (AppKit), con el mismo lenguaje visual que Sereno."""

import warnings

import objc

# Importar Quartz registra CGColorRef como tipo real. Sin esto, NSColor.CGColor()
# devuelve un puntero opaco y Core Animation aborta al animar un color.
import Quartz  # noqa: F401

warnings.filterwarnings("ignore", category=objc.ObjCPointerWarning)

from AppKit import (  # noqa: E402
    NSButton, NSColor, NSFont, NSImage, NSImageView, NSMenu, NSMenuItem,
    NSMutableParagraphStyle, NSPopUpButton, NSTextField, NSView, NSWorkspace,
)
from Foundation import NSAttributedString, NSMakePoint, NSMakeRect  # noqa: E402

try:  # macOS unifica NSTextAlignment con UIKit: left=0, center=1, right=2
    from AppKit import (NSTextAlignmentCenter as ALIGN_CENTER,
                        NSTextAlignmentLeft as ALIGN_LEFT,
                        NSTextAlignmentRight as ALIGN_RIGHT)
except ImportError:
    ALIGN_LEFT, ALIGN_CENTER, ALIGN_RIGHT = 0, 1, 2

STYLE_TITLED, STYLE_CLOSABLE, STYLE_MINI, STYLE_RESIZABLE = 1, 2, 4, 8
STYLE_FULL_CONTENT = 1 << 15
IMG_SCALE_PROPORTIONAL = 3
IMAGE_ONLY = 1
BLEND_BEHIND_WINDOW, VFX_ACTIVE, MATERIAL_UNDER_WINDOW = 0, 1, 21
W_REGULAR, W_MEDIUM, W_SEMIBOLD = 0.0, 0.23, 0.3
PLUMA_BARRIDO = 0.06      # lo difuminado que va el borde del barrido
TRUNC_TAIL, TRUNC_MIDDLE = 4, 5

CAGradientLayer = objc.lookUpClass("CAGradientLayer")
CALayer = objc.lookUpClass("CALayer")
CATextLayer = objc.lookUpClass("CATextLayer")
CATransaction = objc.lookUpClass("CATransaction")
CABasicAnimation = objc.lookUpClass("CABasicAnimation")
CASpringAnimation = objc.lookUpClass("CASpringAnimation")
CAMediaTimingFunction = objc.lookUpClass("CAMediaTimingFunction")


class VistaVolteada(NSView):
    """Documento de las listas: se llena de arriba hacia abajo."""

    def isFlipped(self):
        return True


class Decorativa(NSView):
    """Adorno: no atrapa el ratón, así que el clic llega a lo que hay debajo."""

    def hitTest_(self, punto):
        return None


def colores_persona():
    """Un color por persona, en el orden en que aparecen. Los mismos en toda la app."""
    return [NSColor.systemPurpleColor(), NSColor.systemTealColor(), NSColor.systemOrangeColor(),
            NSColor.systemPinkColor(), NSColor.systemIndigoColor(), NSColor.systemGreenColor()]


COLORES_PERSONA = colores_persona()


def sf(name, size, weight=W_MEDIUM):
    """Un símbolo del sistema, a un tamaño concreto."""
    img = NSImage.imageWithSystemSymbolName_accessibilityDescription_(name, None)
    if img is None:
        return None
    try:
        cfg = objc.lookUpClass("NSImageSymbolConfiguration")
        img = img.imageWithSymbolConfiguration_(
            cfg.configurationWithPointSize_weight_scale_(size, weight, 3))
    except Exception:
        pass
    return img


def icon_view(name, frame, color, size=15.0):
    v = NSImageView.alloc().initWithFrame_(frame)
    v.setImageScaling_(IMG_SCALE_PROPORTIONAL)
    v.setContentTintColor_(color)
    img = sf(name, size)
    if img is not None:
        v.setImage_(img)
    return v


def label(text, size, weight, color, frame, align=ALIGN_CENTER, truncate=None):
    """Texto fijo. `truncate` (TRUNC_TAIL / TRUNC_MIDDLE) lo deja en una línea."""
    f = NSTextField.alloc().initWithFrame_(frame)
    f.setStringValue_(text)
    f.setBezeled_(False)
    f.setDrawsBackground_(False)
    f.setEditable_(False)
    f.setSelectable_(False)
    f.setAlignment_(align)
    f.setFont_(NSFont.systemFontOfSize_weight_(size, weight))
    f.setTextColor_(color)
    if truncate is None:
        f.cell().setWraps_(True)
    else:
        f.cell().setWraps_(False)
        f.cell().setUsesSingleLineMode_(True)
        f.cell().setLineBreakMode_(truncate)
    return f


def section_title(text, frame):
    """Encabezado de sección, al estilo de Ajustes del Sistema."""
    return label(text, 11.5, W_SEMIBOLD, NSColor.secondaryLabelColor(), frame, ALIGN_LEFT)


def continuous(layer, radius):
    layer.setCornerRadius_(radius)
    if hasattr(layer, "setCornerCurve_"):
        try:
            layer.setCornerCurve_("continuous")   # squircle de Apple
        except Exception:
            pass


def rounded(frame, radius, fill=None, border=None, clase=NSView):
    v = clase.alloc().initWithFrame_(frame)
    v.setWantsLayer_(True)
    continuous(v.layer(), radius)
    if fill is not None:
        v.layer().setBackgroundColor_(fill.CGColor())
    if border is not None:
        v.layer().setBorderWidth_(1.0)
        v.layer().setBorderColor_(border.CGColor())
    return v


def card(frame, radius=12.0):
    return rounded(frame, radius,
                   fill=NSColor.controlBackgroundColor().colorWithAlphaComponent_(0.6),
                   border=NSColor.separatorColor())


def gradient_view(frame, radius, colors, start=(0.0, 1.0), end=(1.0, 0.0)):
    v = NSView.alloc().initWithFrame_(frame)
    lay = CAGradientLayer.layer()
    lay.setColors_([c.CGColor() for c in colors])
    lay.setStartPoint_(start)
    lay.setEndPoint_(end)
    lay.setMasksToBounds_(True)
    continuous(lay, radius)
    v.setLayer_(lay)
    v.setWantsLayer_(True)
    return v


def hairline(frame):
    v = NSView.alloc().initWithFrame_(frame)
    v.setWantsLayer_(True)
    v.layer().setBackgroundColor_(NSColor.separatorColor().CGColor())
    return v


def attributed(text, size, weight, color, align=ALIGN_CENTER):
    para = NSMutableParagraphStyle.alloc().init()
    para.setAlignment_(align)
    return NSAttributedString.alloc().initWithString_attributes_(
        text, {"NSFont": NSFont.systemFontOfSize_weight_(size, weight),
               "NSColor": color, "NSParagraphStyle": para})


def cifras(text, size, color, weight=W_MEDIUM):
    """Texto con cifras de ancho fijo: los tiempos no bailan al cambiar."""
    para = NSMutableParagraphStyle.alloc().init()
    para.setAlignment_(ALIGN_LEFT)
    return NSAttributedString.alloc().initWithString_attributes_(
        text, {"NSFont": NSFont.monospacedDigitSystemFontOfSize_weight_(size, weight),
               "NSColor": color, "NSParagraphStyle": para})


def bezel_button(title, frame, target, action, tag=0, size=12.0):
    b = NSButton.alloc().initWithFrame_(frame)
    b.setBezelStyle_(1)
    b.setAttributedTitle_(attributed(title, size, W_REGULAR, NSColor.labelColor()))
    b.setTarget_(target)
    b.setAction_(action)
    b.setTag_(tag)
    return b


def symbol_button(name, frame, target, action, tag=0, tooltip=None, size=13.0, tint=None):
    """Botón sin borde con un símbolo del sistema."""
    b = NSButton.alloc().initWithFrame_(frame)
    b.setBordered_(False)
    b.setImagePosition_(IMAGE_ONLY)
    img = sf(name, size)
    if img is not None:
        b.setImage_(img)
    b.setTarget_(target)
    b.setAction_(action)
    b.setTag_(tag)
    if tooltip:
        b.setToolTip_(tooltip)
    if tint is not None:
        b.setContentTintColor_(tint)
    return b


def popup(frame, titles, target, action, tag=0):
    """Menú desplegable de una sola elección."""
    p = NSPopUpButton.alloc().initWithFrame_pullsDown_(frame, False)
    p.addItemsWithTitles_(titles)
    p.setTarget_(target)
    p.setAction_(action)
    p.setTag_(tag)
    return p


def menu_button(title, titles, frame, target, action, tag=0):
    """Botón con menú desplegable: el título no cambia al elegir (menú de acciones)."""
    p = NSPopUpButton.alloc().initWithFrame_pullsDown_(frame, True)
    p.addItemsWithTitles_([title] + list(titles))
    p.setTarget_(target)
    p.setAction_(action)
    p.setTag_(tag)
    return p


def barra_iconos(simbolos, frame, target, tamano=15.0):
    """Una fila de botones de solo icono, como las barras de herramientas del sistema.

    `simbolos` es [(símbolo, acción, ayuda), …] de izquierda a derecha; devuelve
    la vista y la lista de botones, por si hay que activarlos o apagarlos.
    """
    lado = frame.size.height
    hueco = 4.0
    v = NSView.alloc().initWithFrame_(frame)
    botones = []
    for i, (simbolo, accion, ayuda) in enumerate(simbolos):
        b = symbol_button(simbolo, NSMakeRect(i * (lado + hueco), 0, lado, lado),
                          target, accion, tooltip=ayuda, size=tamano,
                          tint=NSColor.secondaryLabelColor())
        v.addSubview_(b)
        botones.append(b)
    return v, botones


def desplegar_menu(boton, opciones, target, accion):
    """Saca un menú justo debajo de un botón de icono."""
    menu = NSMenu.alloc().init()
    for i, titulo in enumerate(opciones):
        it = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(titulo, accion, "")
        it.setTarget_(target)
        it.setTag_(i)
        menu.addItem_(it)
    menu.popUpMenuPositioningItem_atLocation_inView_(
        None, NSMakePoint(0, boton.frame().size.height + 4), boton)


def text_field(frame, placeholder, target, action, tag=0):
    """Campo editable; su acción salta al pulsar Intro o al salir del campo."""
    f = NSTextField.alloc().initWithFrame_(frame)
    f.setPlaceholderString_(placeholder)
    f.setBezeled_(True)
    f.setBezelStyle_(1)                      # redondeado
    f.setFont_(NSFont.systemFontOfSize_(12.0))
    f.setTarget_(target)
    f.setAction_(action)
    f.setTag_(tag)
    f.cell().setSendsActionOnEndEditing_(True)
    f.cell().setUsesSingleLineMode_(True)
    f.cell().setScrollable_(True)
    return f


def pill(text, symbol, color, alto=16.0, tamano=10.5, decorativa=False):
    """Etiqueta breve con fondo tenue: quién pidió un trabajo, quién habla…

    Se coloca con setFrameOrigin_. El icono y el texto van centrados en la altura,
    y el texto en un marco del alto de su letra para que no quede pegado arriba.
    """
    icono = 10.0 if alto <= 18 else 12.0
    lado = 6.0 if alto <= 18 else 9.0
    hueco = 5.0
    ancho_texto = attributed(text, tamano, W_SEMIBOLD, color).size().width
    alto_letra = tamano + 4
    v = rounded(NSMakeRect(0, 0, lado * 2 + icono + hueco + ancho_texto + 2, alto), alto / 2,
                fill=color.colorWithAlphaComponent_(0.16),
                clase=Decorativa if decorativa else NSView)
    v.addSubview_(icon_view(symbol, NSMakeRect(lado, (alto - icono) / 2, icono, icono),
                            color, icono * 0.85))
    v.addSubview_(label(text, tamano, W_SEMIBOLD, color,
                        NSMakeRect(lado + icono + hueco, (alto - alto_letra) / 2 - 1,
                                   ancho_texto + 6, alto_letra),
                        ALIGN_LEFT))
    return v


def pill_button(text, symbol, color, target, action, tag=0, alto=24.0):
    """Una pastilla en la que se puede pulsar: los nombres de quien habla.

    El dibujo es el mismo `pill`, encima de un botón sin borde: así el clic llega
    al botón y la pastilla queda idéntica a las demás de la app.
    """
    dentro = pill(text, symbol, color, alto=alto, tamano=11.0, decorativa=True)
    b = NSButton.alloc().initWithFrame_(dentro.frame())
    b.setBordered_(False)
    b.setTitle_("")
    b.setTarget_(target)
    b.setAction_(action)
    b.setTag_(tag)
    b.addSubview_(dentro)
    return b


def menu_item(title, action, key, target=None, modifiers=None):
    it = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, action, key)
    if target is not None:
        it.setTarget_(target)
    if modifiers is not None:
        it.setKeyEquivalentModifierMask_(modifiers)
    return it


def poca_animacion() -> bool:
    """True si el usuario pidió reducir el movimiento en Accesibilidad."""
    try:
        return bool(NSWorkspace.sharedWorkspace().accessibilityDisplayShouldReduceMotion())
    except Exception:
        return False


def paradas(avance):
    """Dónde está el borde del barrido: antes de `avance` una cosa, después la otra."""
    borde = min(max(avance, 0.0), 1.0)
    if borde > 0.995:                      # ya está toda: sin degradado que la apague al final
        return [0.0, 1.0, 1.0, 1.0]
    return [0.0, max(borde - PLUMA_BARRIDO, 0.0), min(borde + PLUMA_BARRIDO, 1.0), 1.0]


def barrido(ancho, alto, avance, invertida=False):
    """Máscara que recorre la palabra de izquierda a derecha con el borde difuminado.

    La normal descubre; la invertida esconde. Las dos juntas se reparten la palabra
    sin solaparse, que es lo que evita que se vea doble.
    """
    blanco = NSColor.whiteColor()
    opaco, claro = blanco.CGColor(), blanco.colorWithAlphaComponent_(0.0).CGColor()
    lados = [claro, claro, opaco, opaco] if invertida else [opaco, opaco, claro, claro]
    m = CAGradientLayer.layer()
    m.setColors_(lados)
    m.setLocations_(paradas(avance))
    m.setStartPoint_((0.0, 0.5))
    m.setEndPoint_((1.0, 0.5))
    m.setFrame_(NSMakeRect(0, 0, ancho, alto))
    return m


def escala(factor):
    """Transformación de escala para una capa."""
    return Quartz.CGAffineTransformMakeScale(factor, factor)


def muelle(key_path, desde, hasta, rigidez=280.0, amortiguacion=20.0):
    """Muelle, como las animaciones del sistema: acelera y frena sola, sin tirones."""
    a = CASpringAnimation.animationWithKeyPath_(key_path)
    a.setMass_(1.0)
    a.setStiffness_(rigidez)
    a.setDamping_(amortiguacion)
    a.setInitialVelocity_(0.0)
    a.setFromValue_(desde)
    a.setToValue_(hasta)
    a.setDuration_(a.settlingDuration())
    return a


def suave(key_path, desde, hasta, seconds, curva="easeOut"):
    a = CABasicAnimation.animationWithKeyPath_(key_path)
    a.setFromValue_(desde)
    a.setToValue_(hasta)
    a.setDuration_(seconds)
    a.setTimingFunction_(CAMediaTimingFunction.functionWithName_(curva))
    return a


def con_animaciones(seconds, al_acabar=None):
    """Bloque de animación: `with con_animaciones(0.2): capa.setOpacity_(0)`."""
    class _Bloque:
        def __enter__(self):
            CATransaction.begin()
            CATransaction.setAnimationDuration_(seconds)
            if al_acabar is not None:
                CATransaction.setCompletionBlock_(al_acabar)
            return self

        def __exit__(self, *_):
            CATransaction.commit()
            return False

    return _Bloque()


def pulse(key_path, start, end, seconds):
    """Animación de ida y vuelta, en bucle: el resplandor del disco."""
    a = CABasicAnimation.animationWithKeyPath_(key_path)
    a.setFromValue_(start)
    a.setToValue_(end)
    a.setDuration_(seconds)
    a.setAutoreverses_(True)
    a.setRepeatCount_(float("inf"))
    a.setTimingFunction_(CAMediaTimingFunction.functionWithName_("easeInEaseOut"))
    return a
