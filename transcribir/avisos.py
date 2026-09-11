"""Notificaciones del sistema: avisos al terminar."""

import time
from pathlib import Path

import UserNotifications as UN
from AppKit import NSWorkspace
from Foundation import NSURL, NSUUID
from PyObjCTools import AppHelper

import preferencias as pref
from motor import REGISTRO

CADA_ARCHIVO, COLA, ERRORES, SONIDO = pref.AVISO_CADA, pref.AVISO_COLA, pref.AVISO_ERRORES, pref.AVISO_SONIDO
PERMITIDAS, DENEGADAS, SIN_PEDIR, NO_DISPONIBLE = (
    "permitidas", "denegadas", "sin_pedir", "no_disponible")
PRESENTAR = (UN.UNNotificationPresentationOptionBanner
             | UN.UNNotificationPresentationOptionList
             | UN.UNNotificationPresentationOptionSound)
AJUSTES_DEL_SISTEMA = ("x-apple.systempreferences:"
                       "com.apple.Notifications-Settings.extension?id=" + pref.ID_APP)

# Solo dentro de Transcribir.app: fuera del bundle, macOS aborta el proceso.
disponibles = pref.en_app
activo = pref.leer


def _centro():
    return UN.UNUserNotificationCenter.currentNotificationCenter()


def ser_delegado(delegado) -> None:
    if disponibles():
        _centro().setDelegate_(delegado)


def consultar(al_saber) -> None:
    """Llama a `al_saber(estado)` en el hilo principal con el permiso actual."""
    if not disponibles():
        al_saber(NO_DISPONIBLE)
        return

    def listo(ajustes):
        estado = {UN.UNAuthorizationStatusNotDetermined: SIN_PEDIR,
                  UN.UNAuthorizationStatusDenied: DENEGADAS}.get(
                      ajustes.authorizationStatus(), PERMITIDAS)
        AppHelper.callAfter(al_saber, estado)

    _centro().getNotificationSettingsWithCompletionHandler_(listo)


def pedir_permiso(al_responder=None) -> None:
    """Muestra la pregunta de macOS (solo la primera vez)."""
    if not disponibles():
        return

    def listo(concedido, error):
        if error is not None:
            with REGISTRO.open("a", encoding="utf-8") as log:
                log.write(f"\n[{time.ctime()}] permiso de notificaciones: {error}\n")
        if al_responder is not None:
            AppHelper.callAfter(al_responder)

    _centro().requestAuthorizationWithOptions_completionHandler_(
        UN.UNAuthorizationOptionAlert | UN.UNAuthorizationOptionSound, listo)


def pedir_si_hace_falta() -> None:
    consultar(lambda estado: pedir_permiso() if estado == SIN_PEDIR else None)


def enviar(titulo: str, cuerpo: str, ruta: str | None = None, carpeta: str | None = None) -> None:
    if not disponibles():
        return
    contenido = UN.UNMutableNotificationContent.alloc().init()
    contenido.setTitle_(titulo)
    contenido.setBody_(cuerpo)
    if activo(SONIDO):
        contenido.setSound_(UN.UNNotificationSound.defaultSound())
    info = {k: v for k, v in (("ruta", ruta), ("carpeta", carpeta)) if v}
    if info:
        contenido.setUserInfo_(info)
    peticion = UN.UNNotificationRequest.requestWithIdentifier_content_trigger_(
        NSUUID.UUID().UUIDString(), contenido, None)
    _centro().addNotificationRequest_withCompletionHandler_(peticion, None)


def abrir_desde(respuesta) -> None:
    """Clic en un aviso: muestra el archivo en Finder, o abre la carpeta de destino."""
    info = respuesta.notification().request().content().userInfo() or {}
    ruta, carpeta = info.get("ruta"), info.get("carpeta")
    espacio = NSWorkspace.sharedWorkspace()
    if ruta and Path(ruta).exists():
        espacio.activateFileViewerSelectingURLs_([NSURL.fileURLWithPath_(ruta)])
    elif carpeta and Path(carpeta).exists():
        espacio.openURL_(NSURL.fileURLWithPath_(carpeta))


def abrir_ajustes_del_sistema() -> None:
    NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_(AJUSTES_DEL_SISTEMA))
