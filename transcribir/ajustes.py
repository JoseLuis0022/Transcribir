"""La ventana de Ajustes (⌘,)."""

from pathlib import Path

import objc
from AppKit import (
    NSApplication, NSBackingStoreBuffered, NSColor, NSOpenPanel, NSPasteboard,
    NSPasteboardTypeString, NSScrollView, NSSwitch, NSVisualEffectView, NSWindow,
)
from Foundation import NSURL, NSMakeRect, NSNotificationCenter, NSObject

import agentes
import avisos
import carpetas
import preferencias as pref
import ui

W, H = 480.0, 640.0
PAD = 24.0
CW = W - PAD * 2
FILA = 50.0
RELLENO = 8.0
CONTROL_W = 196.0          # ancho de los menús desplegables


def nombre_carpeta(valor: str) -> str:
    if not valor:
        return "Sin elegir"
    ruta = Path(valor)
    return "Escritorio" if ruta == pref.ESCRITORIO else ruta.name


class ControladorAjustes(NSObject):

    def initWithDueno_(self, dueno):
        self = objc.super(ControladorAjustes, self).init()
        if self is None:
            return None
        self.dueno = dueno          # el delegado de la app: aplica los cambios en todas partes
        self.ventana = None
        self.estado = None
        self.controles = {}         # clave -> (tipo, control, valores)
        self.claves = []            # tag del control -> clave
        return self

    @objc.python_method
    def mostrar(self):
        if self.ventana is None:
            self.construir()
        self.sincronizar()
        self.ventana.makeKeyAndOrderFront_(None)
        self.ventana.makeFirstResponder_(None)     # que no abra con el campo de vocabulario activo
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)

    def alDesplazar_(self, notificacion):
        """La línea bajo el título solo cuando hay contenido por encima."""
        arriba = self.scroll.contentView().bounds().origin.y <= 0.5
        self.linea.setAlphaValue_(0.0 if arriba else 1.0)

    def windowDidBecomeKey_(self, notification):
        # al volver de Ajustes del Sistema, el permiso puede haber cambiado
        avisos.consultar(self.pintarPermiso)

    # ------------------------------------------------------------- interfaz --
    @objc.python_method
    def construir(self):
        rect = NSMakeRect(0, 0, W, H)
        self.ventana = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, ui.STYLE_TITLED | ui.STYLE_CLOSABLE | ui.STYLE_FULL_CONTENT,
            NSBackingStoreBuffered, False)
        self.ventana.setTitle_("Ajustes")
        self.ventana.setTitlebarAppearsTransparent_(True)
        self.ventana.setMovableByWindowBackground_(True)
        self.ventana.setReleasedWhenClosed_(False)
        self.ventana.setDelegate_(self)
        self.ventana.center()

        fondo = NSVisualEffectView.alloc().initWithFrame_(rect)
        fondo.setMaterial_(ui.MATERIAL_UNDER_WINDOW)
        fondo.setBlendingMode_(ui.BLEND_BEHIND_WINDOW)
        fondo.setState_(ui.VFX_ACTIVE)
        fondo.setAutoresizingMask_(2 | 16)
        self.ventana.setContentView_(fondo)

        self.scroll = scroll = NSScrollView.alloc().initWithFrame_(rect)
        scroll.setDrawsBackground_(False)
        scroll.setHasVerticalScroller_(True)
        scroll.setAutohidesScrollers_(True)
        scroll.setAutoresizingMask_(2 | 16)
        doc = ui.VistaVolteada.alloc().initWithFrame_(NSMakeRect(0, 0, W, H))
        scroll.setDocumentView_(doc)
        fondo.addSubview_(scroll)

        # la barra del título, encima del contenido: al desplazar, lo que pasa por
        # detrás se difumina en vez de verse nítido sobre el título
        alto_barra = NSWindow.frameRectForContentRect_styleMask_(
            rect, ui.STYLE_TITLED).size.height - H
        barra = ui.material(NSMakeRect(0, H - alto_barra, W, alto_barra), ui.MATERIAL_BARRA)
        barra.setAutoresizingMask_(2 | 8)
        self.linea = ui.hairline(NSMakeRect(0, 0, W, 1))
        self.linea.setAutoresizingMask_(2)
        self.linea.setAlphaValue_(0.0)          # solo se ve cuando hay algo arriba
        barra.addSubview_(self.linea)
        fondo.addSubview_(barra)

        scroll.contentView().setPostsBoundsChangedNotifications_(True)
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(
            self, b"alDesplazar:", "NSViewBoundsDidChangeNotification", scroll.contentView())

        y = 52.0
        y = self.seccion(doc, y, "TRANSCRIPCIÓN", [
            self.filaMenu("Idioma", "Idioma que se habla en el audio", pref.IDIOMA),
            self.filaMenu("Precisión", "La rápida sirve para borradores", pref.PRECISION),
            self.filaCampo("Vocabulario", "Nombres, siglas o términos que aparecen en tus audios",
                           pref.VOCABULARIO, "Ej.: Kubernetes, OKR, Dra. Ramírez, Monterrey"),
        ])
        y = self.seccion(doc, y, "RESULTADO", [
            self.filaMenu("Formato", "Texto, tiempos o subtítulos", pref.FORMATO),
            self.filaInterruptor("Separar por persona",
                                 "Marca quién habla: «Persona 1:», «Persona 2:»…", pref.PERSONAS),
            self.filaMenu("Cuántas personas",
                          "Si lo sabes, acierta mucho más", pref.CUANTAS),
            self.filaInterruptor("Preparar el resaltado",
                                 "Guarda cuándo suena cada palabra para el editor. Tarda un poco más",
                                 pref.TIEMPOS),
            self.filaMenu("Dónde guardar", "Carpeta fija o junto al audio", pref.GUARDAR),
            self.filaCarpeta("Carpeta de destino", pref.CARPETA),
            self.filaMenu("Al terminar", "Solo con lo que agregas tú", pref.AL_TERMINAR),
        ])
        y = self.seccion(doc, y, "EDITOR", [
            self.filaMenu("Tamaño del texto", "También con ⌘+ y ⌘− en el editor", pref.TAMANO),
            self.filaMenu("Resaltado al reproducir",
                          "Cómo se marca la palabra que suena en el editor", pref.RESALTADO),
            self.filaMenu("Fuerza del resaltado", "Cuánto se nota la palabra que suena",
                          pref.FUERZA),
        ])
        y = self.seccion(doc, y, "HISTORIAL", [self.filaHistorial()])
        y = self.seccion(doc, y, "CARPETA VIGILADA", [
            self.filaInterruptor("Vigilar una carpeta",
                                 "Transcribe sola cada audio o video nuevo mientras la app está abierta",
                                 pref.VIGILAR),
            self.filaCarpeta("Carpeta vigilada", pref.CARPETA_VIGILADA, conocidas=True),
        ])
        y = self.seccion(doc, y, "NOTIFICACIONES", [
            self.filaInterruptor("Al terminar cada archivo", "Un aviso por cada transcripción lista",
                                 pref.AVISO_CADA),
            self.filaInterruptor("Al terminar toda la cola",
                                 "Un solo aviso cuando ya no queda nada pendiente", pref.AVISO_COLA),
            self.filaInterruptor("Si un archivo falla", "Te dice qué archivo no se pudo transcribir",
                                 pref.AVISO_ERRORES),
            self.filaInterruptor("Con sonido", "Reproduce el sonido de notificación del sistema",
                                 pref.AVISO_SONIDO),
        ])
        y = self.seccion(doc, y, "PERMISO DEL SISTEMA", [self.filaPermiso()])
        y = self.seccion(doc, y, "AGENTES", [
            self.filaAgente("terminal.fill", "Comando transcribir", "comando", b"instalarComando:"),
            self.filaAgente("sparkles", "Skill de Claude Code", "skill", b"instalarSkill:"),
            self.filaGuia(),
        ])
        doc.setFrameSize_((W, y))

    @objc.python_method
    def seccion(self, doc, y, titulo, filas):
        """Título de sección y su tarjeta, de arriba hacia abajo (el documento está volteado)."""
        doc.addSubview_(ui.section_title(titulo, NSMakeRect(PAD + 4, y, CW, 16)))
        alto = sum(a for a, _ in filas) + RELLENO * 2
        caja = ui.card(NSMakeRect(PAD, y + 22, CW, alto))
        doc.addSubview_(caja)
        arriba = alto - RELLENO
        for i, (alto_fila, construir) in enumerate(filas):
            abajo = arriba - alto_fila
            construir(caja, abajo)
            if i < len(filas) - 1:
                caja.addSubview_(ui.hairline(NSMakeRect(16, abajo, CW - 32, 1)))
            arriba = abajo
        return y + 22 + alto + 24

    @objc.python_method
    def registrar(self, clave):
        self.claves.append(clave)
        return len(self.claves) - 1

    @objc.python_method
    def textos(self, caja, abajo, titulo, explicacion, ancho):
        caja.addSubview_(ui.label(titulo, 13.0, ui.W_MEDIUM, NSColor.labelColor(),
                                  NSMakeRect(16, abajo + 26, ancho, 20), ui.ALIGN_LEFT))
        caja.addSubview_(ui.label(explicacion, 11.0, ui.W_REGULAR, NSColor.tertiaryLabelColor(),
                                  NSMakeRect(16, abajo + 6, ancho, 18), ui.ALIGN_LEFT,
                                  truncate=ui.TRUNC_TAIL))

    @objc.python_method
    def filaMenu(self, titulo, explicacion, clave):
        def construir(caja, abajo):
            self.textos(caja, abajo, titulo, explicacion, CW - 32 - CONTROL_W - 8)
            opciones = list(pref.ETIQUETAS[clave].items())
            menu = ui.popup(NSMakeRect(CW - 16 - CONTROL_W, abajo + 12, CONTROL_W, 26),
                            [t for _, t in opciones], self, b"cambiarMenu:", tag=self.registrar(clave))
            caja.addSubview_(menu)
            self.controles[clave] = ("menu", menu, [v for v, _ in opciones])
        return FILA, construir

    @objc.python_method
    def filaCampo(self, titulo, explicacion, clave, ejemplo):
        def construir(caja, abajo):
            caja.addSubview_(ui.label(titulo, 13.0, ui.W_MEDIUM, NSColor.labelColor(),
                                      NSMakeRect(16, abajo + 58, CW - 32, 20), ui.ALIGN_LEFT))
            caja.addSubview_(ui.label(explicacion, 11.0, ui.W_REGULAR, NSColor.tertiaryLabelColor(),
                                      NSMakeRect(16, abajo + 40, CW - 32, 18), ui.ALIGN_LEFT))
            campo = ui.text_field(NSMakeRect(16, abajo + 10, CW - 32, 24), ejemplo, self,
                                  b"cambiarCampo:", tag=self.registrar(clave))
            caja.addSubview_(campo)
            self.controles[clave] = ("campo", campo, None)
        return 86.0, construir

    @objc.python_method
    def filaInterruptor(self, titulo, explicacion, clave):
        def construir(caja, abajo):
            self.textos(caja, abajo, titulo, explicacion, CW - 90)
            sw = NSSwitch.alloc().initWithFrame_(NSMakeRect(CW - 54, abajo + 14, 38, 22))
            sw.setTarget_(self)
            sw.setAction_(b"cambiarInterruptor:")
            sw.setTag_(self.registrar(clave))
            caja.addSubview_(sw)
            self.controles[clave] = ("interruptor", sw, None)
        return FILA, construir

    @objc.python_method
    def filaCarpeta(self, titulo, clave, conocidas=False):
        def construir(caja, abajo):
            caja.addSubview_(ui.icon_view("folder.fill", NSMakeRect(16, abajo + 15, 20, 20),
                                          NSColor.secondaryLabelColor(), 14.0))
            # textos del alto de su letra y centrados en la fila, como el icono y el botón
            caja.addSubview_(ui.label(titulo, 13.0, ui.W_MEDIUM, NSColor.labelColor(),
                                      NSMakeRect(46, abajo + (FILA - 17) / 2, 150, 17), ui.ALIGN_LEFT))
            valor = ui.label("", 13.0, ui.W_SEMIBOLD, NSColor.labelColor(),
                             NSMakeRect(196, abajo + (FILA - 17) / 2, CW - 196 - 16 - 96 - 10, 17),
                             ui.ALIGN_RIGHT, truncate=ui.TRUNC_MIDDLE)
            caja.addSubview_(valor)
            accion = b"menuCarpeta:" if conocidas else b"elegirCarpeta:"
            caja.addSubview_(ui.bezel_button("Elegir…", NSMakeRect(CW - 16 - 96, abajo + 11, 96, 28),
                                             self, accion, tag=self.registrar(clave)))
            self.controles[clave] = ("carpeta", valor, None)
        return FILA, construir

    @objc.python_method
    def filaHistorial(self):
        """Cuántas transcripciones recuerda la app, y cómo olvidarlas todas."""
        def construir(caja, abajo):
            caja.addSubview_(ui.icon_view("clock.arrow.circlepath", NSMakeRect(16, abajo + 40, 20, 20),
                                          NSColor.secondaryLabelColor(), 15.0))
            caja.addSubview_(ui.label("Transcripciones guardadas", 13.0, ui.W_MEDIUM,
                                      NSColor.labelColor(),
                                      NSMakeRect(46, abajo + 40, CW - 46 - 250, 20), ui.ALIGN_LEFT))
            self.cuenta_historial = ui.label("", 13.0, ui.W_SEMIBOLD, NSColor.labelColor(),
                                             NSMakeRect(CW - 16 - 150 - 12 - 70, abajo + 41, 70, 18),
                                             ui.ALIGN_RIGHT)
            caja.addSubview_(self.cuenta_historial)
            caja.addSubview_(ui.bezel_button("Vaciar el historial…",
                                             NSMakeRect(CW - 16 - 150, abajo + 36, 150, 28),
                                             self, b"vaciarHistorial:"))
            caja.addSubview_(ui.hairline(NSMakeRect(16, abajo + 30, CW - 32, 1)))
            caja.addSubview_(ui.label(
                "La app recuerda qué transcribiste y dónde quedó cada archivo, para el editor "
                "y el historial. Vaciarlo no borra ningún .txt: siguen en tu carpeta.",
                11.0, ui.W_REGULAR, NSColor.tertiaryLabelColor(),
                NSMakeRect(16, abajo + 2, CW - 32, 28), ui.ALIGN_LEFT))
        return 76.0, construir

    def vaciarHistorial_(self, sender):
        if self.dueno.vaciarHistorial():
            self.sincronizar()

    @objc.python_method
    def filaPermiso(self):
        def construir(caja, abajo):
            self.icono_permiso = ui.icon_view("bell.fill", NSMakeRect(16, abajo + 48, 20, 20),
                                              NSColor.secondaryLabelColor(), 15.0)
            caja.addSubview_(self.icono_permiso)
            self.texto_permiso = ui.label("", 13.0, ui.W_MEDIUM, NSColor.labelColor(),
                                          NSMakeRect(46, abajo + 48, CW - 46 - 196, 20), ui.ALIGN_LEFT)
            caja.addSubview_(self.texto_permiso)
            self.boton_permiso = ui.bezel_button("", NSMakeRect(CW - 16 - 180, abajo + 44, 180, 28),
                                                 self, b"botonPermiso:")
            caja.addSubview_(self.boton_permiso)
            caja.addSubview_(ui.hairline(NSMakeRect(16, abajo + 36, CW - 32, 1)))
            self.nota_permiso = ui.label("", 11.0, ui.W_REGULAR, NSColor.tertiaryLabelColor(),
                                         NSMakeRect(16, abajo + 2, CW - 32, 30), ui.ALIGN_LEFT)
            caja.addSubview_(self.nota_permiso)
        return 80.0, construir

    @objc.python_method
    def filaAgente(self, simbolo, titulo, cual, accion):
        def construir(caja, abajo):
            caja.addSubview_(ui.icon_view(simbolo, NSMakeRect(16, abajo + 15, 20, 20),
                                          NSColor.secondaryLabelColor(), 15.0))
            caja.addSubview_(ui.label(titulo, 13.0, ui.W_MEDIUM, NSColor.labelColor(),
                                      NSMakeRect(46, abajo + (FILA - 17) / 2, 170, 17), ui.ALIGN_LEFT))
            estado = ui.label("", 12.0, ui.W_REGULAR, NSColor.secondaryLabelColor(),
                              NSMakeRect(CW - 16 - 110 - 10 - 110, abajo + (FILA - 15) / 2, 110, 15),
                              ui.ALIGN_RIGHT)
            caja.addSubview_(estado)
            boton = ui.bezel_button("", NSMakeRect(CW - 16 - 110, abajo + 11, 110, 28), self, accion)
            caja.addSubview_(boton)
            setattr(self, f"estado_{cual}", estado)
            setattr(self, f"boton_{cual}", boton)
        return FILA, construir

    @objc.python_method
    def filaGuia(self):
        def construir(caja, abajo):
            caja.addSubview_(ui.label(
                "Claude Code encuentra Transcribir sola gracias a la Skill. Para Codex u otros "
                "agentes, copia la guía y pégala en su AGENTS.md o CLAUDE.md.",
                11.5, ui.W_REGULAR, NSColor.secondaryLabelColor(),
                NSMakeRect(16, abajo + 40, CW - 32, 32), ui.ALIGN_LEFT))
            self.boton_guia = ui.bezel_button("Copiar guía para agentes",
                                              NSMakeRect(16, abajo + 8, 196, 28), self, b"copiarGuia:")
            caja.addSubview_(self.boton_guia)
        return 80.0, construir

    # ------------------------------------------------------------ refrescar --
    @objc.python_method
    def sincronizar(self):
        if self.ventana is None:
            return
        for clave, (tipo, control, valores) in self.controles.items():
            valor = pref.leer(clave)
            if tipo == "menu":
                control.selectItemAtIndex_(valores.index(valor) if valor in valores else 0)
            elif tipo == "interruptor":
                control.setState_(1 if valor else 0)
            elif tipo == "campo":
                if control.currentEditor() is None:      # no pisar lo que se está escribiendo
                    control.setStringValue_(valor)
            elif tipo == "carpeta":
                control.setStringValue_(carpetas.como_se_llama(valor) if valor
                                        else nombre_carpeta(valor))
                control.setToolTip_(valor or "")
        # la carpeta de destino no cuenta cuando se guarda junto al original
        junto = pref.leer(pref.GUARDAR) == "junto"
        self.controles[pref.CARPETA][1].setTextColor_(
            NSColor.tertiaryLabelColor() if junto else NSColor.labelColor())
        if getattr(self, "cuenta_historial", None) is not None:
            cuantas = len(self.dueno.historial)
            self.cuenta_historial.setStringValue_(str(cuantas) if cuantas else "Ninguna")
        self.sincronizarAgentes()
        avisos.consultar(self.pintarPermiso)

    @objc.python_method
    def sincronizarAgentes(self):
        comando = agentes.comando_instalado(self.dueno.ejecutableComando())
        for cual, instalado in (("comando", comando), ("skill", agentes.skill_instalada())):
            estado = getattr(self, f"estado_{cual}")
            estado.setStringValue_("Instalado" if instalado else "No instalado")
            estado.setTextColor_(NSColor.systemGreenColor() if instalado else NSColor.tertiaryLabelColor())
            getattr(self, f"boton_{cual}").setAttributedTitle_(ui.attributed(
                "Reinstalar" if instalado else "Instalar", 12.0, ui.W_REGULAR, NSColor.labelColor()))

    @objc.python_method
    def pintarPermiso(self, estado):
        self.estado = estado
        simbolo, color, texto, boton, nota = {
            avisos.PERMITIDAS: (
                "bell.badge.fill", NSColor.systemGreenColor(), "Permitidas",
                "Abrir Ajustes del Sistema…",
                "macOS decide cómo se ven: banners, sonido y Centro de notificaciones."),
            avisos.DENEGADAS: (
                "bell.slash.fill", NSColor.systemOrangeColor(), "Desactivadas en macOS",
                "Abrir Ajustes del Sistema…",
                "Actívalas en Ajustes del Sistema › Notificaciones › Transcribir."),
            avisos.SIN_PEDIR: (
                "bell.fill", NSColor.secondaryLabelColor(), "Aún sin permiso", "Permitir…",
                "macOS te preguntará una sola vez si Transcribir puede avisarte."),
            avisos.NO_DISPONIBLE: (
                "bell.slash", NSColor.tertiaryLabelColor(), "No disponibles", "",
                "Las notificaciones solo funcionan desde Transcribir.app."),
        }[estado]
        self.icono_permiso.setImage_(ui.sf(simbolo, 15.0))
        self.icono_permiso.setContentTintColor_(color)
        self.texto_permiso.setStringValue_(texto)
        self.boton_permiso.setHidden_(not boton)
        self.boton_permiso.setAttributedTitle_(ui.attributed(boton, 12.0, ui.W_REGULAR, NSColor.labelColor()))
        self.nota_permiso.setStringValue_(nota)

    # ------------------------------------------------------------- acciones --
    @objc.python_method
    def guardar(self, clave, valor):
        try:
            pref.escribir(clave, valor)
        except ValueError as e:
            self.dueno.alerta("No se pudo guardar el ajuste", str(e), ["Aceptar"])
        self.dueno.alCambiarAjuste(clave)          # ventana principal, vigía y esta misma ventana

    @objc.python_method
    def pedirCarpeta(self, inicial):
        panel = NSOpenPanel.openPanel()
        panel.setCanChooseDirectories_(True)
        panel.setCanChooseFiles_(False)
        panel.setCanCreateDirectories_(True)
        panel.setPrompt_("Elegir")
        panel.setDirectoryURL_(NSURL.fileURLWithPath_(inicial or str(Path.home())))
        return panel.URL().path() if panel.runModal() == 1 else None

    def cambiarMenu_(self, sender):
        clave = self.claves[sender.tag()]
        self.guardar(clave, self.controles[clave][2][sender.indexOfSelectedItem()])

    def cambiarCampo_(self, sender):
        clave = self.claves[sender.tag()]
        if sender.stringValue() != pref.leer(clave):
            self.guardar(clave, sender.stringValue())

    def cambiarInterruptor_(self, sender):
        clave = self.claves[sender.tag()]
        encender = sender.state() == 1
        if clave == pref.VIGILAR and encender and not pref.leer(pref.CARPETA_VIGILADA):
            carpeta = self.pedirCarpeta(None)        # sin carpeta todavía: pedirla primero
            if carpeta is None:
                sender.setState_(0)
                return
            pref.escribir(pref.CARPETA_VIGILADA, carpeta)
        self.guardar(clave, encender)

    def menuCarpeta_(self, sender):
        """Las carpetas que suelen interesar, sin tener que ir a buscarlas."""
        self.conocidas = carpetas.disponibles()
        opciones = [f"{nombre} — {nota}" for _, nombre, _, _, nota in self.conocidas]
        ui.desplegar_menu(sender, opciones + ["Otra carpeta…"], self, b"elegirConocida:")

    def elegirConocida_(self, sender):
        clave = self.claves[-1] if not self.claves else pref.CARPETA_VIGILADA
        if sender.tag() >= len(self.conocidas):
            carpeta = self.pedirCarpeta(pref.leer(clave))
            if carpeta is None:
                return
        else:
            carpeta = str(self.conocidas[sender.tag()][2])
        self.guardar(clave, carpeta)
        if not pref.leer(pref.VIGILAR):
            self.guardar(pref.VIGILAR, True)

    def elegirCarpeta_(self, sender):
        clave = self.claves[sender.tag()]
        carpeta = self.pedirCarpeta(pref.leer(clave))
        if carpeta is None:
            return
        if clave == pref.CARPETA:
            pref.escribir(pref.GUARDAR, "carpeta")
        self.guardar(clave, carpeta)

    def instalarComando_(self, sender):
        agentes.instalar_comando(self.dueno.ejecutableComando())
        self.sincronizarAgentes()

    def instalarSkill_(self, sender):
        agentes.instalar_skill()
        self.sincronizarAgentes()

    def copiarGuia_(self, sender):
        tablero = NSPasteboard.generalPasteboard()
        tablero.clearContents()
        tablero.setString_forType_(agentes.GUIA, NSPasteboardTypeString)
        self.boton_guia.setAttributedTitle_(ui.attributed("Guía copiada ✓", 12.0, ui.W_REGULAR,
                                                          NSColor.labelColor()))
        self.performSelector_withObject_afterDelay_(b"restaurarGuia:", None, 2.0)

    def restaurarGuia_(self, _):
        self.boton_guia.setAttributedTitle_(ui.attributed("Copiar guía para agentes", 12.0,
                                                          ui.W_REGULAR, NSColor.labelColor()))

    def botonPermiso_(self, sender):
        if self.estado == avisos.SIN_PEDIR:
            avisos.pedir_permiso(self.sincronizar)
        else:
            avisos.abrir_ajustes_del_sistema()
