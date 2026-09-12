"""Carpeta vigilada: transcribe sola lo que llegue a una carpeta, con la app abierta."""

import json
from pathlib import Path

import carpetas
from motor import EXTENSIONES

SOPORTE = Path.home() / "Library" / "Application Support" / "Transcribir"
VISTOS = SOPORTE / "vistos.json"


class Vigia:
    """Llamar a `revisar()` cada pocos segundos desde el hilo principal.

    Un archivo se toma cuando su tamaño no cambió entre dos revisiones (ya
    terminó de copiarse). Lo ya visto se recuerda entre sesiones, así que lo que
    llegó con la app cerrada se transcribe al abrirla.
    """

    def __init__(self, al_encontrar):
        self.al_encontrar = al_encontrar
        self.carpeta: Path | None = None
        self.tamanos: dict[str, int] = {}
        try:
            self.vistos = json.loads(VISTOS.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.vistos = {}

    def configurar(self, carpeta: Path | None, rebaselinar: bool) -> None:
        """None la apaga. Con `rebaselinar`, lo que ya había en la carpeta se ignora."""
        self.carpeta, self.tamanos = carpeta, {}
        if carpeta is not None and (rebaselinar or str(carpeta) not in self.vistos):
            self.vistos[str(carpeta)] = sorted(str(p) for p in self._medios())
            self._guardar()

    def revisar(self) -> None:
        if self.carpeta is None or not self.carpeta.is_dir():
            return
        vistos = set(self.vistos.get(str(self.carpeta), []))
        listos = []
        for ruta in self._medios():
            clave = str(ruta)
            if clave in vistos:
                continue
            try:
                tamano = ruta.stat().st_size
            except OSError:
                continue
            if tamano > 0 and self.tamanos.get(clave) == tamano:
                listos.append(ruta)
                vistos.add(clave)
                self.tamanos.pop(clave, None)
            else:
                self.tamanos[clave] = tamano
        if listos:
            self.vistos[str(self.carpeta)] = sorted(vistos)
            self._guardar()
            self.al_encontrar(listos)

    def medios(self) -> list[Path]:
        """Los audios y videos que hay ahora mismo en la carpeta vigilada."""
        return self._medios()

    def _medios(self) -> list[Path]:
        """Los audios y videos de la carpeta. Algunas, como las de Notas, los
        guardan dentro de subcarpetas con nombres de UUID: ahí hay que entrar."""
        if self.carpeta is None or not self.carpeta.is_dir():
            return []
        if not carpetas.hay_que_hondear(self.carpeta):
            try:
                hijos = list(self.carpeta.iterdir())
            except OSError:              # macOS puede no dejar leer ahí
                return []
            return [p for p in hijos
                    if p.is_file() and not p.name.startswith(".")
                    and p.suffix.lower() in EXTENSIONES]
        salida = []
        for hondura, hijo in self._recorrer(self.carpeta, 0):
            if hondura and hijo.suffix.lower() in EXTENSIONES:
                salida.append(hijo)
        return salida

    def _recorrer(self, carpeta: Path, nivel: int):
        """Recorre hasta cuatro niveles, que es donde llegan las carpetas de Apple."""
        if nivel > 4:
            return
        try:
            hijos = list(carpeta.iterdir())
        except OSError:
            return
        for hijo in hijos:
            if hijo.name.startswith("."):
                continue
            if hijo.is_dir():
                yield from self._recorrer(hijo, nivel + 1)
            elif hijo.is_file():
                yield True, hijo

    def _guardar(self) -> None:
        SOPORTE.mkdir(parents=True, exist_ok=True)
        VISTOS.write_text(json.dumps(self.vistos, ensure_ascii=False, indent=1), encoding="utf-8")
