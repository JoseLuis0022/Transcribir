#!/usr/bin/env python3
"""`transcribir` — usa la app Transcribir desde la terminal (personas y agentes de IA).

Todo pasa por la app abierta, así que lo que se pide aquí se ve en su ventana.
`transcribir guia` imprime la guía pensada para agentes.
"""

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agentes import GUIA  # noqa: E402
from identidad import ID_APP  # noqa: E402

SOCKET = Path.home() / "Library" / "Application Support" / "Transcribir" / "transcribir.sock"
SUBCOMANDOS = ("estado", "cancelar", "ajustes", "guia", "abrir", "limpiar")

AYUDA = """\
uso: transcribir ARCHIVO... [--texto] [--json] [--no-esperar] [opciones]
     transcribir estado | cancelar ID...|--todo | ajustes [CLAVE VALOR] | limpiar | abrir | guia

`transcribir guia` explica todos los comandos y opciones.
"""


class SinApp(Exception):
    """La app no está abierta o no respondió."""


class ErrorApp(Exception):
    """La app rechazó la petición."""


def quien_pide() -> str:
    """Nombre que aparece en la ventana junto al trabajo."""
    agente = os.environ.get("AI_AGENT", "").lower()
    if agente.startswith("claude-code") or os.environ.get("CLAUDECODE") == "1":
        return "Claude Code"
    if "codex" in agente or os.environ.get("CODEX_SANDBOX"):
        return "Codex"
    if agente:
        return agente.split("_")[0].replace("-", " ").title()
    return "Terminal"


def abrir_app(segundo_plano: bool) -> None:
    """Abre la app por su identificador: da igual en qué carpeta esté instalada."""
    comando = ["/usr/bin/open"]
    if segundo_plano:                      # sin robar el foco a quien está trabajando
        comando += ["-g", "--env", "TRANSCRIBIR_SEGUNDO_PLANO=1"]
    if subprocess.run(comando + ["-b", ID_APP], capture_output=True).returncode != 0:
        raise SinApp("Transcribir no está instalada (arrástrala a Aplicaciones desde el DMG)")


def conectar(abrir: bool, espera: float = 60.0) -> socket.socket:
    fin, abierta = time.time() + espera, False
    while True:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            s.connect(str(SOCKET))
            return s
        except OSError:
            s.close()
            if not abrir:
                raise SinApp("Transcribir está cerrada")
            if not abierta:
                abrir_app(segundo_plano=True)
                abierta = True
            if time.time() > fin:
                raise SinApp("Transcribir no respondió en 60 s")
            time.sleep(0.4)


def pedir(peticion: dict, abrir: bool = True):
    """Envía una petición a la app y devuelve cada línea de respuesta."""
    with conectar(abrir) as s, s.makefile("rwb") as f:
        f.write((json.dumps(peticion, ensure_ascii=False) + "\n").encode("utf-8"))
        f.flush()
        for linea in f:
            respuesta = json.loads(linea)
            if respuesta.get("ok") is False:
                raise ErrorApp(respuesta.get("error", "error desconocido"))
            yield respuesta


def unico(peticion: dict, abrir: bool = True) -> dict:
    return next(pedir(peticion, abrir))


def mostrar(valor) -> str:
    if isinstance(valor, bool):
        return "si" if valor else "no"
    return str(valor) if valor != "" else "(vacío)"


# ------------------------------------------------------------------ comandos --
def cmd_transcribir(args) -> int:
    opciones = {k: v for k, v in (("idioma", args.idioma), ("formato", args.formato),
                                  ("precision", args.precision), ("vocabulario", args.vocabulario))
                if v is not None}
    if args.personas:
        opciones["personas"] = True
    if args.junto:
        opciones["guardar"] = "junto"
    if args.destino:
        opciones.update(guardar="carpeta", carpeta=str(Path(args.destino).expanduser().resolve()))
    peticion = {"accion": "transcribir", "archivos": [str(Path(a).expanduser().resolve()) for a in args.archivos],
                "opciones": opciones, "cliente": args.cliente or quien_pide(), "esperar": not args.no_esperar}

    codigo, ultimo_pct = 0, {}
    for ev in pedir(peticion):
        tipo = ev.get("evento")
        if tipo == "terminado" and args.texto:
            ev["texto"] = Path(ev["ruta"]).read_text(encoding="utf-8")
        if args.json:
            print(json.dumps(ev, ensure_ascii=False), flush=True)
        if tipo == "encolado":
            for r in ev.get("rechazados", []):
                codigo = 1
                if not args.json:
                    print(f"omitido: {r['archivo']} ({r['motivo']})", file=sys.stderr)
            if not ev["trabajos"]:
                return codigo or 1
            if not args.json:
                for t in ev["trabajos"]:
                    print(f"en cola #{t['id']}: {Path(t['archivo']).name}", file=sys.stderr)
        elif tipo == "progreso" and not args.json:
            pct = round(ev["progreso"] * 100) if ev["progreso"] >= 0 else -1
            etapa = (ev["id"], ev["estado"].split(" · ")[0])     # "Descargando el modelo", "Transcribiendo…"
            if pct < 0 or pct - ultimo_pct.get(etapa, -100) >= 10:
                ultimo_pct[etapa] = pct
                if pct < 0:
                    estado = ev["estado"]
                elif not ev["estado"].startswith("Transcribiendo"):     # descargando, separando…
                    estado = f"{ev['estado']} ({pct} %)"
                else:
                    estado = f"{pct} %"
                print(f"#{ev['id']} {Path(ev['archivo']).name}: {estado}", file=sys.stderr, flush=True)
        elif tipo == "terminado" and not args.json:
            if args.texto:
                print(f"==> {ev['ruta']} <==\n{ev['texto']}")
            else:
                print(ev["ruta"])
        elif tipo == "error":
            codigo = max(codigo, 1)
            if not args.json:
                print(f"error #{ev['id']} {Path(ev['archivo']).name}: {ev['motivo']}", file=sys.stderr)
        elif tipo == "cancelado":
            codigo = codigo or 3
            if not args.json:
                print(f"cancelado #{ev['id']} {Path(ev['archivo']).name}", file=sys.stderr)
    return codigo


def cmd_estado(args) -> int:
    try:
        r = unico({"accion": "estado"}, abrir=False)
    except SinApp:
        if args.json:
            print(json.dumps({"abierta": False}))
        else:
            print("Transcribir está cerrada (se abre sola al pedirle una transcripción).")
        return 0
    r.pop("ok", None)
    r["abierta"] = True
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0
    print(f"En cola ({len(r['cola'])}):" if r["cola"] else "En cola: nada")
    for t in r["cola"]:
        estado = {"en_espera": "en espera", "preparando": "preparando el modelo"}.get(
            t["estado"], f"transcribiendo {round((t['progreso'] or 0) * 100)} %")
        quien = f"  ({t['cliente']})" if t["cliente"] else ""
        print(f"  #{t['id']} {Path(t['archivo']).name} — {estado}{quien}")
    print(f"Terminados ({len(r['terminados'])}):" if r["terminados"] else "Terminados: nada")
    for t in r["terminados"]:
        final = f"→ {t['resultado']}" if t["resultado"] else f"— {t['detalle']}"
        print(f"  #{t['id']} {Path(t['archivo']).name} [{t['estado']}] {final}")
    a = r["ajustes"]
    destino = "junto al original" if a["guardar"] == "junto" else a["carpeta"]
    print(f"Ajustes: idioma={a['idioma']} precision={a['precision']} formato={a['formato']} → {destino}")
    return 0


def cmd_cancelar(args) -> int:
    if not args.todo and not args.ids:
        print("indica los ids (transcribir estado) o --todo", file=sys.stderr)
        return 1
    r = unico({"accion": "cancelar", "ids": args.ids, "todo": args.todo}, abrir=False)
    for i in r["cancelados"]:
        print(f"cancelado #{i}")
    for i in r["no_encontrados"]:
        print(f"no está en la cola: #{i}", file=sys.stderr)
    return 0 if not r["no_encontrados"] else 1


def cmd_ajustes(args) -> int:
    if args.clave is None:
        r = unico({"accion": "ajustes_leer"})
        if args.json:
            print(json.dumps({"ajustes": r["ajustes"], "opciones": r["opciones"]}, ensure_ascii=False, indent=2))
        else:
            for clave, valor in r["ajustes"].items():
                opciones = r["opciones"][clave]
                opciones = " | ".join(opciones) if isinstance(opciones, list) else opciones
                print(f"{clave:20} {mostrar(valor):28} ({opciones})")
        return 0
    if args.valor is None:
        print(f"falta el valor: transcribir ajustes {args.clave} VALOR", file=sys.stderr)
        return 1
    r = unico({"accion": "ajustes_cambiar", "clave": args.clave, "valor": args.valor})
    print(f"{r['clave']} = {mostrar(r['valor'])}")
    return 0


def cmd_limpiar(args) -> int:
    r = unico({"accion": "limpiar"}, abrir=False)
    print(f"lista de terminados vacía ({r['limpiados']} quitados; los archivos siguen en su sitio)")
    return 0


def cmd_abrir(args) -> int:
    abrir_app(segundo_plano=False)
    unico({"accion": "mostrar"})
    return 0


def cmd_guia(args) -> int:
    sys.stdout.write(GUIA)
    return 0


# -------------------------------------------------------------------- partes --
def parser_transcribir() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="transcribir", description="Transcribe audio o video con Transcribir.")
    p.add_argument("archivos", nargs="+", help="audios o videos (.m4a .mp4 .mp3 .wav .mov) o carpetas")
    p.add_argument("--texto", action="store_true", help="imprime también el texto transcrito")
    p.add_argument("--json", action="store_true", help="una línea JSON por evento")
    p.add_argument("--no-esperar", action="store_true", help="encola y termina sin esperar")
    p.add_argument("--idioma", choices=("es", "en", "auto"))
    p.add_argument("--formato", choices=("parrafos", "tiempos", "srt"))
    p.add_argument("--precision", choices=("alta", "rapida"))
    p.add_argument("--vocabulario", help="nombres, siglas o términos del audio")
    p.add_argument("--personas", action="store_true", help="separa por interlocutor (Persona 1:, Persona 2:)")
    destino = p.add_mutually_exclusive_group()
    destino.add_argument("--destino", help="carpeta donde guardar el resultado")
    destino.add_argument("--junto", action="store_true", help="guardar junto al archivo original")
    p.add_argument("--cliente", help="nombre que se muestra en la ventana (por defecto se detecta)")
    return p


def parser_subcomandos() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="transcribir")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("estado", help="cola, progreso, terminados y ajustes")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_estado)
    s = sub.add_parser("cancelar", help="cancela trabajos en espera o en curso")
    s.add_argument("ids", nargs="*", type=int)
    s.add_argument("--todo", action="store_true")
    s.set_defaults(func=cmd_cancelar)
    s = sub.add_parser("ajustes", help="ver o cambiar ajustes")
    s.add_argument("clave", nargs="?")
    s.add_argument("valor", nargs="?")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_ajustes)
    sub.add_parser("limpiar", help="vacía la lista de terminados").set_defaults(func=cmd_limpiar)
    sub.add_parser("abrir", help="trae la ventana al frente").set_defaults(func=cmd_abrir)
    sub.add_parser("guia", help="guía para agentes").set_defaults(func=cmd_guia)
    return p


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help", "ayuda"):
        sys.stdout.write(AYUDA)
        return 0
    try:
        if argv[0] in SUBCOMANDOS:
            args = parser_subcomandos().parse_args(argv)
            return args.func(args)
        return cmd_transcribir(parser_transcribir().parse_args(argv))
    except SinApp as e:
        print(f"transcribir: {e}", file=sys.stderr)
        return 2
    except ErrorApp as e:
        print(f"transcribir: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\ninterrumpido: lo que estaba en cola sigue en la app (transcribir estado)", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
