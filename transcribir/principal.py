"""Punto de entrada de Transcribir.app.

`Transcribir --cli …` ejecuta el comando `transcribir` con el Python de dentro
de la app, sin abrir ventanas; sin argumentos, abre la app.
"""

import sys


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        from cli import main as comando
        sys.exit(comando(sys.argv[2:]))
    from app import main as abrir
    abrir()


if __name__ == "__main__":
    main()
