"""Cómo se escribe cada transcripción: párrafos, párrafos con tiempos o subtítulos."""

import re

FIN_ORACION = re.compile(r"[.!?…]$")


def en_parrafos(texto: str, largo: int = 600) -> str:
    """Agrupa oraciones en párrafos de ~600 caracteres separados por una línea en blanco."""
    parrafos, actual = [], ""
    for oracion in re.split(r"(?<=[.!?…])\s+", texto.strip()):
        actual = f"{actual} {oracion}".strip()
        if len(actual) >= largo:
            parrafos.append(actual)
            actual = ""
    if actual:
        parrafos.append(actual)
    return "\n\n".join(parrafos)


def _normal(palabra: str) -> str:
    return re.sub(r"[^\w]", "", palabra.lower())


def palabras_con_tiempo(texto: str, segmentos: list[dict]) -> list[tuple[str, float, float]]:
    """Empareja las palabras del texto (con su puntuación) con los tiempos del alineador.

    El alineador da una palabra por segmento y a veces sin puntuación; aquí se
    recupera la del texto. Lo que no empareja toma el siguiente tiempo disponible.
    """
    items = [(s["text"], float(s["start"]), float(s["end"]))
             for s in segmentos if _normal(str(s.get("text", "")))]
    salida, j, ultimo = [], 0, 0.0
    for palabra in texto.split():
        n = _normal(palabra)
        encontrado = None
        if n:
            for k in range(j, min(j + 6, len(items))):
                if _normal(items[k][0]) == n:
                    encontrado = k
                    break
        if encontrado is not None:
            _, inicio, fin = items[encontrado]
            j = encontrado + 1
        elif n and j < len(items):
            _, inicio, fin = items[j]
            j += 1
        else:
            inicio = fin = ultimo
        salida.append((palabra, inicio, fin))
        ultimo = fin
    return salida


def _reloj(segundos: float, srt: bool = False) -> str:
    ms = int(round(max(segundos, 0.0) * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    if srt:
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def con_tiempos(texto: str, segmentos: list[dict], bloque: float = 30.0) -> str:
    """Párrafos de ~30 s que empiezan con su marca de tiempo: «[02:15] Texto…»."""
    palabras = palabras_con_tiempo(texto, segmentos)
    if not palabras:
        raise ValueError("No se pudieron calcular las marcas de tiempo")
    parrafos, actual, inicio = [], [], None
    for palabra, t0, t1 in palabras:
        inicio = t0 if inicio is None else inicio
        actual.append(palabra)
        duracion = t1 - inicio
        if (duracion >= bloque and FIN_ORACION.search(palabra)) or duracion >= bloque * 2:
            parrafos.append(f"[{_reloj(inicio)}] {' '.join(actual)}")
            actual, inicio = [], None
    if actual:
        parrafos.append(f"[{_reloj(inicio)}] {' '.join(actual)}")
    return "\n\n".join(parrafos)


def _dos_lineas(texto: str, ancho: int = 42) -> str:
    """Parte un subtítulo largo en dos líneas lo más parejas posible."""
    if len(texto) <= ancho:
        return texto
    mitad = len(texto) // 2
    espacios = [i for i, c in enumerate(texto) if c == " "]
    if not espacios:
        return texto
    corte = min(espacios, key=lambda i: abs(i - mitad))
    return f"{texto[:corte]}\n{texto[corte + 1:]}"


def a_srt(texto: str, segmentos: list[dict], max_chars: int = 84, max_seg: float = 6.0) -> str:
    """Subtítulos: hasta dos líneas de ~42 caracteres y 6 s, cortando en la puntuación."""
    palabras = palabras_con_tiempo(texto, segmentos)
    if not palabras:
        raise ValueError("No se pudieron calcular los tiempos de los subtítulos")

    def unir(bloque):
        return " ".join(p for p, _, _ in bloque)

    grupos, actual = [], []
    for palabra, t0, t1 in palabras:
        if actual and (len(f"{unir(actual)} {palabra}") > max_chars or t1 - actual[0][1] > max_seg):
            grupos.append(actual)
            actual = []
        actual.append((palabra, t0, t1))
        largo = len(unir(actual))
        if (FIN_ORACION.search(palabra) and largo >= 25) or (palabra.endswith(",") and largo >= 60):
            grupos.append(actual)
            actual = []
    if actual:
        grupos.append(actual)

    bloques = []
    for i, grupo in enumerate(grupos):
        inicio, fin = grupo[0][1], grupo[-1][2]
        fin = max(fin, inicio + 0.8)                     # que dé tiempo a leerlo
        if i + 1 < len(grupos):
            fin = min(fin, grupos[i + 1][0][1])          # sin solaparse con el siguiente
        fin = max(fin, inicio + 0.05)
        bloques.append(f"{i + 1}\n{_reloj(inicio, True)} --> {_reloj(fin, True)}\n"
                       f"{_dos_lineas(unir(grupo))}")
    return "\n\n".join(bloques)
