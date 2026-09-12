"""Cómo se escribe cada transcripción: párrafos, con tiempos, por persona o subtítulos."""

import re
from bisect import bisect_right

FIN_ORACION = re.compile(r"[.!?…]$")

# Lo que adorna una línea y no es habla: el número y el tiempo de un subtítulo,
# la marca «[02:15]» y el «Persona 1:» del principio.
SOLO_NUMERO = re.compile(r"^\d+$")
MARCA = re.compile(r"^\[\d+:\d\d(?::\d\d)?\]\s*")
QUIEN = re.compile(r"^Persona \d+:\s*")


def tokens(contenido: str, nombres=()) -> list[tuple[str, int, int]]:
    """Las palabras habladas del archivo, cada una con su sitio: (palabra, inicio, fin).

    Deja fuera lo que es formato y no texto, para que los tiempos encajen igual
    en un .txt de párrafos, en uno con marcas de tiempo y en un .srt.
    """
    quienes = [QUIEN] + [re.compile(rf"^{re.escape(n)}:\s*") for n in nombres if n.strip()]
    salida, base = [], 0
    for linea in contenido.splitlines(keepends=True):
        cruda, inicio = linea.rstrip("\n"), 0
        if not SOLO_NUMERO.match(cruda.strip()) and "-->" not in cruda:
            for patron in (MARCA, *quienes):
                encontrado = patron.match(cruda[inicio:])
                if encontrado:
                    inicio += encontrado.end()
            for palabra in re.finditer(r"\S+", cruda[inicio:]):
                salida.append((palabra.group(), base + inicio + palabra.start(),
                               base + inicio + palabra.end()))
        base += len(linea)
    return salida


def limpiar(contenido: str, nombres=()) -> str:
    """Solo el habla, sin marcas ni nombres: lo que hay que alinear con el audio."""
    return " ".join(p for p, _, _ in tokens(contenido, nombres))


def mapear_tiempos(contenido: str, palabras: list, nombres=()) -> list[tuple[int, int, float, float]]:
    """Empareja cada palabra del archivo con su momento: (inicio, fin, desde, hasta).

    Es lo que permite resaltar la palabra que suena sobre el texto tal como está
    escrito, sin volver a tocar el archivo.
    """
    return [(i, f, p[1], p[2]) for (_, i, f), p in zip(tokens(contenido, nombres), palabras)]


def renombrar_personas(contenido: str, nombres: dict, actuales=None) -> str:
    """Cambia «Persona 1:» (o el nombre que tenga ahora) por el nuevo, en todo el archivo.

    `nombres` y `actuales` son {"1": "Ana"}; un nombre vacío devuelve «Persona 1:».
    """
    actuales = actuales or {}
    # de más largo a más corto, para que «Ana García» gane sobre «Ana»
    etiquetas = sorted(
        [(f"Persona {n}", n) for n in set(nombres) | set(actuales)]
        + [(v.strip(), n) for n, v in actuales.items() if v.strip()],
        key=lambda p: -len(p[0]))

    def cambiar(linea):
        marca = MARCA.match(linea)
        desde = marca.end() if marca else 0
        for etiqueta, numero in etiquetas:
            if linea[desde:].startswith(f"{etiqueta}:"):
                nuevo = (nombres.get(numero) or "").strip() or f"Persona {numero}"
                resto = linea[desde + len(etiqueta) + 1:].lstrip(" ")
                return f"{linea[:desde]}{nuevo}: {resto}"
        return linea

    return "\n".join(cambiar(linea) for linea in contenido.split("\n"))


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


def asignar_personas(palabras: list[tuple[str, float, float]], turnos: list[tuple[float, float, int]]) -> list[int]:
    """Número de persona de cada palabra (desde 1, en orden de aparición)."""
    if not turnos:
        return [1] * len(palabras)
    turnos = sorted(turnos)
    inicios = [t[0] for t in turnos]

    def distancia(turno, centro):
        return 0.0 if turno[0] <= centro <= turno[1] else min(abs(centro - turno[0]), abs(centro - turno[1]))

    crudas = []
    for _, t0, t1 in palabras:
        centro = (t0 + t1) / 2
        # búsqueda binaria: basta mirar los turnos vecinos (una hora de audio son
        # miles de turnos y comparar con todos retenía la ventana varios segundos)
        i = bisect_right(inicios, centro) - 1
        vecinos = [turnos[k] for k in (i - 1, i, i + 1) if 0 <= k < len(turnos)]
        crudas.append(min(vecinos, key=lambda t: distancia(t, centro))[2])
    # una palabra suelta entre dos de la misma persona es ruido del borde de un turno
    for i in range(1, len(crudas) - 1):
        if crudas[i - 1] == crudas[i + 1] != crudas[i]:
            crudas[i] = crudas[i - 1]
    orden: dict[int, int] = {}
    return [orden.setdefault(p, len(orden) + 1) for p in crudas]


def _reloj(segundos: float, srt: bool = False) -> str:
    ms = int(round(max(segundos, 0.0) * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    if srt:
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def con_tiempos(palabras: list[tuple[str, float, float]], bloque: float = 30.0) -> str:
    """Párrafos de ~30 s que empiezan con su marca de tiempo: «[02:15] Texto…»."""
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


def con_personas(palabras: list[tuple[str, float, float]], personas: list[int],
                 con_marca: bool = False, largo: int = 600) -> str:
    """Un párrafo por intervención: «Persona 1: …», o «[02:15] Persona 1: …» con tiempos."""
    parrafos, actual, quien, inicio = [], [], None, 0.0

    def cerrar():
        if actual:
            marca = f"[{_reloj(inicio)}] " if con_marca else ""
            parrafos.append(f"{marca}Persona {quien}: {' '.join(actual)}")

    for (palabra, t0, _), persona in zip(palabras, personas):
        largo_actual = len(" ".join(actual))
        if persona != quien or (largo_actual >= largo and FIN_ORACION.search(actual[-1])):
            cerrar()
            actual, quien, inicio = [], persona, t0
        actual.append(palabra)
    cerrar()
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


def a_srt(palabras: list[tuple[str, float, float]], personas: list[int] | None = None,
          max_chars: int = 84, max_seg: float = 6.0) -> str:
    """Subtítulos: hasta dos líneas de ~42 caracteres y 6 s, cortando en la puntuación
    y, si hay personas, en cada cambio de quien habla («Persona 2: …»)."""
    def unir(bloque):
        return " ".join(p for p, _, _, _ in bloque)

    grupos, actual = [], []
    for i, (palabra, t0, t1) in enumerate(palabras):
        quien = personas[i] if personas else None
        if actual and (len(f"{unir(actual)} {palabra}") > max_chars or t1 - actual[0][1] > max_seg
                       or quien != actual[0][3]):
            grupos.append(actual)
            actual = []
        actual.append((palabra, t0, t1, quien))
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
        texto = unir(grupo)
        if grupo[0][3] is not None:
            texto = f"Persona {grupo[0][3]}: {texto}"
        bloques.append(f"{i + 1}\n{_reloj(inicio, True)} --> {_reloj(fin, True)}\n{_dos_lineas(texto)}")
    return "\n\n".join(bloques)
