"""Genera el icono de Transcribir y los glifos de la ventana (mismo método que Sereno).

Salidas, en esta carpeta:
    Transcribir.icns   icono de la app
    icono-vista.png    vista previa a 1024
    glifo-on.png       glifo del disco: hoja llena (trabajando o listo)
    glifo-off.png      glifo del disco: hoja hueca (en reposo)
"""

import math
import os
import shutil
import subprocess

from PIL import Image, ImageDraw, ImageFilter

S = 2048                      # lienzo de trabajo
ART = int(S * 0.805)          # el arte ocupa ~80,5 % como en los iconos de macOS
PAD = (S - ART) // 2
RADIUS = int(ART * 0.2237)    # curvatura squircle de macOS

NIGHT_TOP = (58, 50, 138)     # índigo noche
NIGHT_BOT = (21, 17, 60)
VIOLET = (182, 160, 255)      # la hoja iluminada
WHITE = (255, 255, 255, 255)
CLEAR = (0, 0, 0, 0)

HERE = os.path.dirname(os.path.abspath(__file__))


# ------------------------------------------------------------------ utilidades
def vertical_gradient(top, bottom):
    img = Image.new("RGB", (S, S))
    d = ImageDraw.Draw(img)
    for y in range(S):
        t = y / (S - 1)
        d.line([(0, y), (S, y)],
               fill=tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return img


def squircle_mask():
    m = Image.new("L", (S, S), 0)
    ImageDraw.Draw(m).rounded_rectangle(
        [PAD, PAD, PAD + ART, PAD + ART], radius=RADIUS, fill=255)
    return m


# ----------------------------------------------------------------------- hoja
def hoja(scale=1.0, glass=None, bars=WHITE, body=WHITE):
    """La hoja de la transcripción: marco con esquina doblada y una onda dentro.

    scale  encoge el dibujo respecto al lienzo (1.0 = tamaño del icono)
    glass  relleno del interior, o None para dejarla hueca (en reposo)
    bars   color de la onda; CLEAR la recorta y deja ver lo que haya detrás
    """
    art = Image.new("RGBA", (S, S), CLEAR)
    cx, cy = S / 2, S / 2

    def sc(v):
        return v * scale

    hw, hh = sc(S * 0.175), sc(S * 0.215)
    x0, x1, y0, y1 = cx - hw, cx + hw, cy - hh, cy + hh
    lw = sc(S * 0.034)
    fold = hw * 0.62
    r = sc(S * 0.030)

    # la página, sin la esquina superior derecha
    d = ImageDraw.Draw(art)
    d.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=body)
    d.polygon([(x1 - fold, y0 - 2), (x1 + 2, y0 - 2), (x1 + 2, y0 + fold)], fill=CLEAR)

    # el interior, un grosor de trazo hacia dentro, también sin la esquina
    inner = Image.new("RGBA", (S, S), CLEAR)
    di = ImageDraw.Draw(inner)
    di.rounded_rectangle([x0 + lw, y0 + lw, x1 - lw, y1 - lw],
                         radius=max(1.0, r - lw * 0.5), fill=glass or WHITE)
    c = x1 - fold - y0 - lw * math.sqrt(2)          # borde del doblez: x - y = c
    di.polygon([(c + y0 - 10, y0 - 10), (x1 + 10, y0 - 10), (x1 + 10, x1 + 10 - c)],
               fill=CLEAR)
    if glass is None:
        art = Image.composite(Image.new("RGBA", (S, S), CLEAR), art, inner.split()[3])
    else:
        art.alpha_composite(inner)

    # la solapa doblada
    d = ImageDraw.Draw(art)
    d.polygon([(x1 - fold, y0), (x1 - fold, y0 + fold), (x1, y0 + fold)], fill=body)

    # la onda de sonido, algo por debajo del centro (la solapa ocupa arriba)
    alturas = (0.32, 0.64, 1.0, 0.72, 0.42)
    bw, gap = sc(S * 0.028), sc(S * 0.020)
    total = len(alturas) * bw + (len(alturas) - 1) * gap
    bx, by, maxh = cx - total / 2, cy + sc(S * 0.045), sc(S * 0.20)
    for i, f in enumerate(alturas):
        h = maxh * f
        x = bx + i * (bw + gap)
        d.rounded_rectangle([x, by - h / 2, x + bw, by + h / 2], radius=bw / 2, fill=bars)
    return art


# ---------------------------------------------------------------------- salida
def night_base():
    icon = Image.new("RGBA", (S, S), CLEAR)
    mask = squircle_mask()
    icon.paste(vertical_gradient(NIGHT_TOP, NIGHT_BOT), (0, 0), mask)

    gloss = Image.new("L", (S, S), 0)
    ImageDraw.Draw(gloss).ellipse(
        [PAD - ART * 0.25, PAD - ART * 0.75, PAD + ART * 1.25, PAD + ART * 0.52], fill=34)
    gloss = gloss.filter(ImageFilter.GaussianBlur(S * 0.03))
    icon.paste(Image.new("RGBA", (S, S), (255, 255, 255, 255)), (0, 0),
               Image.composite(gloss, Image.new("L", (S, S), 0), mask))
    return icon


def compose(base, art):
    icon = base.copy()
    shadow = Image.eval(art.split()[3].filter(ImageFilter.GaussianBlur(S * 0.012)),
                        lambda v: v // 3)
    icon.paste(Image.new("RGBA", (S, S), (0, 0, 0, 90)), (0, 0),
               shadow.transform((S, S), Image.AFFINE, (1, 0, 0, 0, 1, -int(S * 0.008))))
    icon.alpha_composite(art)
    return icon


def export_icns(icon, name):
    iconset = os.path.join(HERE, name + ".iconset")
    shutil.rmtree(iconset, ignore_errors=True)
    os.makedirs(iconset)
    for size in (16, 32, 128, 256, 512):
        for s in (1, 2):
            px = size * s
            icon.resize((px, px), Image.LANCZOS).save(os.path.join(
                iconset, "icon_%dx%d%s.png" % (size, size, "@2x" if s == 2 else "")))
    subprocess.run(["/usr/bin/iconutil", "-c", "icns", iconset,
                    "-o", os.path.join(HERE, name + ".icns")], check=True)
    shutil.rmtree(iconset, ignore_errors=True)


def build():
    icono = compose(night_base(), hoja(glass=VIOLET + (255,), bars=NIGHT_BOT + (255,)))
    export_icns(icono, "Transcribir")
    icono.resize((1024, 1024), Image.LANCZOS).save(os.path.join(HERE, "icono-vista.png"))

    # glifos del disco: la hoja llena distingue trabajando de en reposo
    hoja(scale=0.88, glass=WHITE, bars=CLEAR).resize(
        (512, 512), Image.LANCZOS).save(os.path.join(HERE, "glifo-on.png"))
    hoja(scale=0.88, glass=None, bars=WHITE).resize(
        (512, 512), Image.LANCZOS).save(os.path.join(HERE, "glifo-off.png"))
    print("icono y glifos generados")


if __name__ == "__main__":
    build()
