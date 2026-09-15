# Transcribir: deuda técnica

> Errores y arreglos pendientes que se dejaron para después, casi siempre porque la app estaba transcribiendo y no se podía reinstalar.
> Al resolver uno, seguir el «Proceso para publicar una nueva versión» de `CLAUDE.md` y moverlo a «Resueltos» con la versión donde quedó.

---

## Pendientes

_(nada por ahora)_

---

## Resueltos

### 2. El comando se queda colgado si se cierra la tubería de salida — resuelto en la 1.2.3

- **Detectado:** 14 de septiembre de 2026, en la versión 1.2.2 (ya pasaba en la 1.2.1).
- **Síntoma:** `transcribir estado --json | true` imprimía `BrokenPipeError: [Errno 32] Broken pipe` y `Launch error / See the py2app website for debugging launch issues`, y el proceso `Transcribir --cli estado --json` no terminaba (había que matarlo).
- **Causa:** `print` en `cli.py` lanza `BrokenPipeError` cuando quien lee ya cerró. La excepción llegaba sin atrapar al `__boot__.py` de py2app, que la trata como error de arranque y se queda sin salir. Cualquier otra excepción inesperada del comando tenía el mismo efecto.
- **Arreglo:** `cli.main` envuelve todo el comando (ahora en `ejecutar`) y vacía `stdout` dentro del `try`. Con `BrokenPipeError`, redirige `stdout` y `stderr` a `os.devnull` y sale con 141, como en Unix con SIGPIPE. Con cualquier otra excepción, imprime `transcribir: error inesperado (Tipo: mensaje)` y sale con 1. Nada llega ya al arranque de py2app.
- **Pruebas:**
  - Desde el código y con la 1.2.3 instalada: `estado`, `estado --json`, `historial`, `historial --json`, `guia` y `ajustes --json`, cada uno con `| head -c 5` y `| true`. Todos terminan al momento, sin traceback (141 cuando se corta la tubería).
  - Sin cortar, la salida sigue completa: `estado` sale con 0 y `estado --json` es JSON válido.
  - Una excepción simulada en un comando sale con 1 y un mensaje corto.
  - `transcribir ARCHIVO --json | head -1` en medio de una transcripción: el comando sale, no queda colgado y el trabajo sigue en la cola de la app (luego se canceló con `transcribir cancelar`).
  - Siguen igual: los códigos de salida de un archivo que no es audio (1) y de una ficha inexistente (1), `cancelar` y `estado`.

### 1. `transcribir estado` falla con `'id'` — resuelto en la 1.2.2

- **Detectado:** 14 de septiembre de 2026, en la versión 1.2.1 (compilación 4).
- **Síntoma:** `transcribir estado` y `transcribir estado --json` imprimían `transcribir: 'id'` en cuanto terminaba bien una transcripción en la sesión de la app.
- **Causa:**
  1. `app.py`, `estadoParaAgente`: leía `h["id"]`, `h["origen"]` y `h["detalle"]` de todo `self.hechos`, pero las transcripciones que salen bien se guardan ahí (`alTerminar`) sin esas claves (`{"tipo": "ficha", "ficha", …}`). Salía un `KeyError` y la app lo devolvía como error.
  2. `cli.py`, `cmd_estado`: la salida en texto imprimía `t['id']`, pero las entradas del historial traen `ficha`.
- **Arreglo:** `estadoParaAgente` salta los `hechos` de tipo `ficha` (ya van en la lista por el historial, así no salen repetidos), y `cmd_estado` usa `id` o `ficha`, y tolera un archivo de origen vacío.
- **Pruebas:**
  - Desde el código, con una app simulada (cola en espera y en curso; hechos de tipo ficha, error y cancelado; historial con y sin origen): el código de la 1.2.1 da `KeyError: 'id'` y el nuevo responde bien en texto y en `--json`.
  - Con la 1.2.2 instalada: `estado` con la app cerrada, después de una transcripción exitosa, de un error (archivo que no es audio) y de un cancelado. Texto y `--json` responden con código 0, sin entradas duplicadas. `historial`, `ajustes` y `texto` siguen igual.
