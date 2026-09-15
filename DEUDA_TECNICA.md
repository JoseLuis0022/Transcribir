# Transcribir: deuda técnica

> Errores y arreglos pendientes que se dejaron para después, casi siempre porque la app estaba transcribiendo y no se podía reinstalar.
> Al resolver uno, seguir el «Proceso para publicar una nueva versión» de `CLAUDE.md` y moverlo a «Resueltos» con la versión donde quedó.

---

## Pendientes

### 2. El comando se queda colgado si se cierra la tubería de salida

- **Detectado:** 14 de septiembre de 2026, en la versión 1.2.2 (ya pasaba en la 1.2.1: la línea que falla no cambió).
- **Gravedad:** baja. Solo pasa si otro programa deja de leer la salida antes de tiempo, pero a un agente o a un script le deja un proceso colgado.
- **Síntoma:** `transcribir estado --json | true` imprime `BrokenPipeError: [Errno 32] Broken pipe` y `Launch error / See the py2app website for debugging launch issues`, y el proceso `Transcribir --cli estado --json` **no termina** (hay que matarlo).
- **Causa probable:** `print` en `cli.py` lanza `BrokenPipeError` cuando el lector ya cerró. La excepción llega sin atrapar al `__boot__.py` de py2app, que la trata como error de arranque y no sale.
- **Arreglo propuesto:** en `cli.main` (o en `principal.py` con `--cli`), atrapar `BrokenPipeError`, redirigir `stdout` a `os.devnull` y salir con código 141 (lo normal en Unix con SIGPIPE). De paso, revisar que ninguna otra excepción sin atrapar llegue a py2app: el comando siempre debe terminar con un mensaje corto y un código de salida.
- **Cómo probarlo:** `transcribir estado --json | true` y `transcribir historial --json | head -c 10` deben terminar al momento, sin traceback.

---

## Resueltos

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
