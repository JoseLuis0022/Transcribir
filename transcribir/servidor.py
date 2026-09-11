"""Servidor local para el comando `transcribir`: socket Unix con JSON por líneas.

Cada petición se atiende en su propio hilo. Todo lo que toca la cola o la
ventana se ejecuta en el hilo principal (`AppHelper.callAfter`) y el hilo de
la conexión espera la respuesta; así lo que pide un agente se ve en la ventana.
"""

import json
import os
import queue
import socketserver
import threading
from pathlib import Path

from PyObjCTools import AppHelper

SOPORTE = Path.home() / "Library" / "Application Support" / "Transcribir"
SOCKET = SOPORTE / "transcribir.sock"
FINALES = ("terminado", "error", "cancelado")


def en_hilo_principal(funcion, *args):
    """Ejecuta `funcion` en el hilo principal y devuelve su resultado (o relanza su error)."""
    listo, caja = threading.Event(), {}

    def llamar():
        try:
            caja["valor"] = funcion(*args)
        except Exception as e:  # se relanza en el hilo de la conexión
            caja["error"] = e
        finally:
            listo.set()

    AppHelper.callAfter(llamar)
    if not listo.wait(30):
        raise TimeoutError("La app no respondió a tiempo")
    if "error" in caja:
        raise caja["error"]
    return caja.get("valor")


class _Manejador(socketserver.StreamRequestHandler):

    def handle(self):
        app = self.server.app
        try:
            peticion = json.loads(self.rfile.readline() or b"{}")
            accion = peticion.get("accion")
            if accion == "transcribir":
                self._transcribir(app, peticion)
            else:
                self._enviar({"ok": True, **(en_hilo_principal(app.atenderAgente, accion, peticion) or {})})
        except (BrokenPipeError, ConnectionResetError):
            pass                                  # el comando se fue; los trabajos siguen en la app
        except Exception as e:
            try:
                self._enviar({"ok": False, "error": str(e)})
            except OSError:
                pass

    def _enviar(self, datos):
        self.wfile.write((json.dumps(datos, ensure_ascii=False) + "\n").encode("utf-8"))
        self.wfile.flush()

    def _transcribir(self, app, peticion):
        esperar = peticion.get("esperar", True)
        eventos = queue.Queue()
        creados = en_hilo_principal(app.encolarDesdeAgente, peticion, eventos.put if esperar else None)
        self._enviar({"ok": True, "evento": "encolado", **creados})
        if not esperar:
            return
        pendientes = {t["id"] for t in creados["trabajos"]}
        while pendientes:
            evento = eventos.get()
            self._enviar(evento)
            if evento["evento"] in FINALES:
                pendientes.discard(evento["id"])
        self._enviar({"evento": "fin"})


class _Servidor(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


def iniciar(app):
    SOPORTE.mkdir(parents=True, exist_ok=True)
    if SOCKET.exists():
        SOCKET.unlink()                        # restos de una ejecución anterior
    servidor = _Servidor(str(SOCKET), _Manejador)
    servidor.app = app
    os.chmod(SOCKET, 0o600)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    return servidor


def detener(servidor) -> None:
    if servidor is None:
        return
    servidor.shutdown()
    servidor.server_close()
    if SOCKET.exists():
        SOCKET.unlink()
