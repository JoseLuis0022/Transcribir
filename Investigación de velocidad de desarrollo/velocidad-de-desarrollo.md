# Investigación de velocidad de desarrollo

**Cuánto tarda hoy construir software con modelos, agentes de IA, buenos prompts y un programador que sabe qué pedir.** Caso medido: la app de macOS *Transcribir*, construida el 10 de septiembre de 2026.

> **En una línea:** una app que un desarrollador senior sin IA habría tardado **unas 400 horas (10 semanas)** en construir se programó en **2 h 44 min**, entre el primer y el último archivo de código. Es unas **146 veces más rápido**; contando investigación y documentos, unas **89 veces**.

---

## Índice

1. [Qué se construyó](#1-qué-se-construyó)
2. [Cómo se midió](#2-cómo-se-midió)
3. [Línea de tiempo real](#3-línea-de-tiempo-real)
4. [La estimación a ciegas](#4-la-estimación-a-ciegas)
5. [Comparación](#5-comparación)
6. [Matices honestos](#6-matices-honestos)
7. [Qué influye en la velocidad](#7-qué-influye-en-la-velocidad)
8. [Lecciones aprendidas de este proyecto](#8-lecciones-aprendidas-de-este-proyecto)
9. [Componentes reutilizables](#9-componentes-reutilizables)
10. [Cómo construir la siguiente app aún más rápido](#10-cómo-construir-la-siguiente-app-aún-más-rápido)
11. [Cómo medir mejor la próxima vez](#11-cómo-medir-mejor-la-próxima-vez)
12. [Estimación: cuánto falta para competir con MacWhisper](#12-estimación-cuánto-falta-para-competir-con-macwhisper)

---

## 1. Qué se construyó

*Transcribir* es una app nativa de macOS que convierte audio y video en texto, en el Mac y sin internet.

| Área | Qué tiene |
|---|---|
| Motor | Qwen3-ASR 1.7B y 0.6B, acelerado con MLX en la GPU; audio leído con AVFoundation, sin ffmpeg; vocabulario propio; español, inglés o detección automática |
| Formatos | Párrafos, marcas de tiempo `[mm:ss]` y subtítulos `.srt` con tiempos por palabra (Qwen3-ForcedAligner) |
| Separar por persona | Sherpa-ONNX (segmentación pyannote 3.0 y huellas WeSpeaker) en un proceso aparte, con umbral calibrado |
| Interfaz | AppKit nativo vía PyObjC: cola con arrastrar y soltar, cancelar, Terminados, disco de estado animado, bienvenida con descarga de modelos, Ajustes (⌘,), notificaciones, carpeta vigilada |
| Agentes | Comando `transcribir`, servidor de socket Unix, Skill de Claude Code; lo que pide un agente aparece en la ventana |
| Distribución | App autónoma de 266 MB con su propio Python, firma ad-hoc verificada, DMG de 51 MB y Release en GitHub |
| Documentación | README profesional con capturas, licencia, LÉEME del DMG y plan de producto frente a MacWhisper |

**En números:**
- 3.709 líneas en 23 archivos (unas 3.620 de Python).
- 127 escrituras y ediciones de código.
- 32 commits.
- Una versión publicada.

---

## 2. Cómo se midió

### Tiempo real
- **Fuente:** el registro de la sesión de Claude Code, que guarda la hora de cada mensaje y de cada archivo escrito o editado.
- **Qué cuenta como desarrollo:** el tramo que va del primer archivo de la app al último cambio de código. No se usan los commits, porque su hora es la del commit y no la del trabajo.
- **Qué queda fuera:**
  - la investigación inicial, cuando todavía no existía la app;
  - una pausa larga del usuario sin mensajes;
  - los documentos escritos después de terminar el código.

### Estimación a ciegas
Un agente independiente estimó cuánto tardarían humanos **sin asistentes de IA** en construir la plataforma exactamente como está. Para que no pudiera deducir el tiempo real:
- Se le dio una **copia del proyecto sin git** y **con todas las fechas de archivo cambiadas al 1 de enero de 2000**.
- Se quitaron el plan de producto, los bundles y los entornos.
- Se le prohibió consultar git, fechas de archivos, el registro de la sesión, la carpeta original y búsquedas del proyecto en internet.
- Solo pudo basarse en el código, el README (que documenta decisiones y problemas resueltos), los scripts y las capturas.

---

## 3. Línea de tiempo real

| Hora | Qué pasó |
|---|---|
| **14:41** | Primer mensaje: revisar la potencia del Mac |
| 14:44–15:06 | Investigación del mejor modelo (Qwen3-ASR frente a Whisper, benchmarks), con un script de comparación que después se borró |
| 15:06–16:33 | **Pausa del usuario**, sin mensajes |
| 16:33–16:39 | ¿Vale la pena el cambio de modelo? Números de precisión y decisión |
| **16:46:22** | **Primer archivo de la app** (`transcribir/motor.py`) |
| 16:46–17:04 | Primera versión de la app (Qt), instalada y probada |
| 17:04–17:40 | Rehecha con controles nativos de macOS al estilo de Sereno: logo, notificaciones, Ajustes |
| 17:40–18:18 | Integración con agentes (comando, servidor, Skill), cancelar, 8 ajustes nuevos; repositorio en GitHub |
| 18:19–19:05 | App compartible y autónoma, sin ffmpeg; bienvenida con descargas; separar por persona; Release v1.1 con DMG |
| 19:05–19:31 | README profesional, licencia, arreglo de la traba al separar por persona, ubicación en Terminados |
| **19:30:57** | **Último cambio de código** (`transcribir/app.py`) |
| 20:18–20:41 | Investigación de MacWhisper y plan de 16 misiones (`PARTES_FALTANTES.md`) |
| 20:46 | Esta medición |

| Medida | Tiempo |
|---|---|
| **Desarrollo de la app** (primer → último archivo de código) | **2 h 44 min** |
| Trabajo efectivo total (investigación + app + documentos, sin la pausa) | ~4 h 30 min |
| Reloj total de la sesión | 6 h 05 min |

Las 2 h 44 min incluyen todo lo que pasó en ese tramo: los mensajes y capturas del usuario, las construcciones de la app, las pruebas, los commits y la publicación.

---

## 4. La estimación a ciegas

### Por componente (desarrollador senior, horas)

| Componente | Optimista | Probable | Pesimista |
|---|---|---|---|
| Investigación y elección de modelos | 16 | 28 | 45 |
| Arquitectura y entorno | 4 | 6 | 10 |
| Audio con AVFoundation y CoreMedia desde PyObjC | 6 | 10 | 18 |
| Motor: cola, cancelación, carga perezosa | 10 | 16 | 26 |
| Formatos: párrafos, tiempos, SRT | 10 | 16 | 26 |
| Separación por persona: Sherpa, proceso aparte, calibración | 16 | 28 | 48 |
| Modelos y descargas | 6 | 10 | 18 |
| Ventana principal y lógica de la cola | 40 | 60 | 95 |
| Diseño de UI/UX y piezas nativas | 8 | 12 | 20 |
| Iconografía por código | 8 | 14 | 24 |
| Ajustes y preferencias | 18 | 28 | 44 |
| Notificaciones | 6 | 10 | 18 |
| Carpeta vigilada | 4 | 6 | 10 |
| Bienvenida y descargas | 8 | 12 | 20 |
| Integración con agentes (socket, CLI, Skill) | 20 | 32 | 50 |
| Empaquetado autónomo (py2app, MLX, Sherpa) | 16 | 30 | 60 |
| Firma, verificación y DMG | 6 | 12 | 24 |
| Pruebas y depuración | 24 | 40 | 70 |
| Documentación | 8 | 12 | 18 |
| **Total** | **234** | **382** | **644** |

La media ponderada (PERT) da **unas 400 horas**.

### Por perfil

| Perfil | Horas | Calendario (40 h/semana) |
|---|---|---|
| Senior Python con experiencia en macOS/PyObjC, solo | ~400 h (280–560) | **~10 semanas** (7–14) |
| Nivel medio, solo | ~700 h (450–1.100) | ~17–18 semanas |
| Equipo de 2–3 personas | ~470 h entre todos | ~6 semanas |

El estimador añade que con 30 h productivas reales por semana, el calendario del senior sube a unas 13 semanas.

### Lo que el estimador vio como "lo invisible"
Donde puso más horas no fue en escribir código, sino en:
- investigación y calibraciones;
- problemas de empaquetado y firma;
- el bloqueo del intérprete que causaba Sherpa;
- las trampas de PyObjC.

En sus palabras: *"las líneas se escriben rápido; lo que se lleva el tiempo es lo invisible"*.

---

## 5. Comparación

| | Humano sin IA (estimado) | IA + agentes + programador (real) | Proporción |
|---|---|---|---|
| Solo el código | ~400 h | 2 h 44 min | **~146 veces más rápido** |
| Todo el trabajo efectivo | ~400 h | ~4 h 30 min | **~89 veces más rápido** |
| Rango (extremos) | 280–560 h | 2,7–4,5 h | ~62 a ~204 veces |
| Calendario | ~10 semanas | una tarde | — |

**Semanas de trabajo convertidas en una tarde: dos órdenes de magnitud.**

---

## 6. Matices honestos

1. **Se reutilizó Sereno**, la app anterior del mismo autor: su lenguaje visual, las piezas de interfaz, el método del icono, el guion de construcción, el DMG y varias lecciones. El estimador supuso empezar desde cero y calcula que eso ahorra 15–25 h. No cambia el orden de magnitud, pero es justamente la tesis de la sección 7.
2. **Menos pruebas que un humano.** Las 400 h incluyen unas 40 h de pruebas. Aquí se probó sobre todo con voces sintéticas y audios cortos; faltan reuniones reales largas, audios con ruido y probar en otro Mac. Las funciones están, pero la solidez todavía no es la de 10 semanas de pruebas.
3. **El programador cuenta.** Las 2 h 44 min no son "la IA sola": incluyen al usuario dando las ideas, las capturas, las correcciones y las decisiones. El resultado es IA + agentes + alguien que sabe qué pedir.
4. **El estimador también es una IA.** Conviene contrastar su cifra con uno o dos desarrolladores humanos.
5. **El motor no se creó aquí.** Qwen3-ASR es un modelo de código abierto de Alibaba. Lo que se comprimió fue investigar, elegir, integrar, empaquetar y pulir.
6. **Hubo trabajo en paralelo.** Agentes en segundo plano hicieron investigación (MacWhisper) y la estimación mientras se seguía trabajando. Eso también es parte del nuevo método.

---

## 7. Qué influye en la velocidad

La velocidad no sale solo del modelo de IA. Sale de cinco palancas que se suman.

### 7.1 Saber pedir
- **Objetivos claros y en pocas palabras:** "un .txt limpio, sin markdown, cola con arrastrar y soltar, mostrar en Finder".
- **Capturas de pantalla con el detalle exacto:** un botón desalineado o un texto 2 pt más arriba. Una imagen evita párrafos de explicación.
- **Referencias concretas:** "quiero esta calidad, como Sereno". Da un estándar visual y técnico ya resuelto.
- **Decisiones rápidas cuando se preguntan:** firma, modelos, agentes. Cada decisión desbloquea trabajo.
- **Corregir el rumbo pronto:** "solo quería la investigación". Evita horas en la dirección equivocada.
- **Pedir honestidad antes de gastar:** "¿de verdad vale la pena pyannote?". Se evitó añadir 1 GB por una mejora de 1–2 puntos.

### 7.2 Reutilizar componentes
Casi todo lo que hace que Transcribir se vea y se distribuya bien ya existía en Sereno:
- el lenguaje visual (disco con halo, tarjetas agrupadas, SF Symbols, fondo translúcido);
- las piezas de interfaz (`ui.py`) y el método para dibujar el icono con Pillow;
- los guiones de construcción y de DMG, y el LÉEME con los pasos de Gatekeeper;
- el patrón del comando para agentes y la estructura del README.

Cada componente reutilizado ahorra horas y, sobre todo, **vueltas de diseño**.

### 7.3 Reutilizar lecciones aprendidas — la palanca más importante
Una lección aprendida es un problema que ya no hay que volver a descubrir. El estimador calculó **de 1 a 3 días** para diagnosticar cosas como el bloqueo del intérprete, la firma rota o el archivo de GPU de MLX. Quien ya conoce la lección lo resuelve en minutos. Por ejemplo, la lección de Sereno *"importa `Quartz` o Core Animation aborta"* evitó un fallo que cuesta una tarde.

**Si aprendes a reutilizar componentes y lecciones, la siguiente app no empieza de cero: empieza donde terminó la anterior.** Por eso la sección 8 es un catálogo pensado para copiar.

### 7.4 Agentes en paralelo
Mientras se programaba, otros agentes investigaban MacWhisper o estimaban a ciegas. El trabajo que no depende entre sí no se hace en fila.

### 7.5 Verificar con datos, no a ojo
- Benchmarks públicos antes de elegir modelo.
- Una "sonda" que medía cuánto tiempo se quedaba sin responder la ventana: así se encontró el bloqueo de 17 s.
- Calibrar el umbral de separación por persona con diálogos y monólogos.
- Revisar la firma y buscar rutas de la máquina dentro de la app antes de publicarla.
- Capturas de la ventana real para revisar el diseño.

Medir convierte "creo que funciona" en "funciona", y evita arreglos a ciegas.

---

## 8. Lecciones aprendidas de este proyecto

Catálogo reutilizable. Cada lección: el problema, la causa y la solución.

### Empaquetar apps de Python para macOS (py2app)
| Problema | Causa | Solución |
|---|---|---|
| py2app no encuentra `mlx` | Es un paquete sin `__init__.py` | Excluirlo de py2app y copiarlo intacto después (rsync) a `Resources/lib/python3.x` |
| MLX no carga su código de GPU | Busca `mlx.metallib` junto a `libmlx.dylib` | Copiar el paquete completo, con sus librerías al lado (`@loader_path`) |
| Librerías con `@rpath` (Sherpa-ONNX) se rompen | py2app no las reubica bien | Tratarlas igual que MLX: copiarlas intactas |
| El `python` de `Contents/MacOS` no funciona en otra Mac | Apunta al Python con que se construyó | Lanzar el ejecutable principal de la app con un modo propio (`--cli`, `--separar`) |
| La firma queda rota, y macOS dice "la app está dañada" | Una librería de Homebrew (`liblzma`) no se deja firmar | Excluir los módulos que no se usan (`lzma`, Pillow) y firmar de dentro hacia fuera con verificación estricta |
| Poner un icono con `setIcon` rompe la firma | Añade un archivo dentro del bundle | En apps autónomas, usar solo `CFBundleIconFile` con un archivo real |
| El Info.plist lleva rutas de la máquina | py2app anota `PythonExecutable` | Borrarlo con PlistBuddy antes de firmar |
| En modo enlazado (`-A`) la app depende de la carpeta del proyecto | Así funciona ese modo | Solo sirve para desarrollo; para compartir, el build completo |

### PyObjC y AppKit
| Problema | Causa | Solución |
|---|---|---|
| Core Animation aborta al animar colores | Sin `import Quartz`, `CGColor()` es un puntero opaco | Importar `Quartz` siempre |
| El texto queda ~2 pt más arriba que el icono y el botón | `NSTextField` dibuja pegado arriba de su marco | Marco del alto de la letra (17 pt para 13 pt), centrado en la fila |
| La alineación sale al revés | `NSTextAlignment` en macOS sigue el orden de UIKit | Importar las constantes de AppKit, no usar números |
| Animaciones de color solapadas abortan | Encadenar transiciones de Core Animation | Recolorear solo al cambiar de estado, sin animar si hubo otra hace < 0,4 s |
| La app encola lo que recibe en `argv` | AppKit abre como documentos las rutas de la línea de comandos | Pasar los datos de prueba por variables de entorno |
| UserNotifications aborta el proceso | Fuera de un bundle con identificador no se permite | Solo usar notificaciones dentro de la app instalada |
| Cambiar el identificador de la app | macOS lo trata como otra app | Migrar los ajustes y avisar que se vuelve a pedir el permiso de notificaciones |
| Las capturas de la ventana salen en miniatura | Stage Manager, o la ventana no está al frente | Activar la app y la ventana antes de capturar |

### Rendimiento y concurrencia
| Problema | Causa | Solución |
|---|---|---|
| La ventana se congelaba hasta 17 s al terminar | Sherpa-ONNX no suelta el intérprete de Python (GIL) | Proceso aparte, que informa su avance por su salida y se cancela matándolo |
| La separación por persona era lenta | Sherpa usa un solo núcleo por defecto | `num_threads` = núcleos − 2; de ~200 s a ~56 s para 6 min |
| Asignar palabras a personas crecía con el cuadrado | Comparar cada palabra con todos los turnos | Búsqueda binaria (`bisect`) sobre los turnos |
| Cancelar una transcripción larga | La biblioteca no trae cancelación | Lanzar una excepción desde el callback de progreso, entre fragmentos |

### Modelos de IA locales
| Problema | Causa | Solución |
|---|---|---|
| `HF_HUB_OFFLINE=1` impedía descargar | Bloquea también las descargas | Cargar siempre por ruta local del modelo; el Hub solo al descargar |
| Progreso de descarga impredecible | Descargas por XET | `HF_HUB_DISABLE_XET=1` y medir los bytes de la carpeta |
| Modelos a medias parecen completos | Falta una marca de fin | Escribir un archivo de "completo" solo cuando termina la descarga |
| El umbral por defecto de Sherpa (0,5) juntaba voces distintas | Umbral demasiado permisivo | Calibrar con diálogos y monólogos: 0,30–0,35 funciona; usar 0,33 |
| ¿pyannote community-1 o Sherpa? | Community-1 mejora solo 1–2 puntos de error, añade ~1 GB y exige cuenta | Sherpa: 33 MB, sin cuentas, apto para compartir |
| Decodificar audio sin ffmpeg | La biblioteca llama a `ffmpeg` por nombre | AVFoundation (`AVAssetReader`) a PCM float de 16 kHz y pasar el arreglo |

### Hacer apps para agentes ("agent first")
| Lección | Detalle |
|---|---|
| Comando + Skill antes que MCP | Para agentes de terminal gasta menos tokens, y la Skill hace que Claude Code la descubra sola |
| Una sola cola | El comando no transcribe: le entrega el trabajo a la app por un socket Unix. Así la ventana siempre refleja lo que pasa |
| Que se vea lo que hace el agente | Etiqueta con el nombre del agente, detectado con `AI_AGENT` o `CLAUDECODE` |
| No robar el foco | Abrir la app con `open -g --env TRANSCRIBIR_SEGUNDO_PLANO=1` |
| Salidas legibles por máquina | `--json`, eventos por línea y códigos de salida documentados (0/1/2/3) |
| Guía única | La misma guía alimenta `transcribir guia`, la Skill y el botón "Copiar guía" |

### Proceso de trabajo
| Lección | Detalle |
|---|---|
| No ampliar el alcance sin pedirlo | Una petición de investigación no es permiso para instalar 7 GB |
| No interrumpir al usuario | El guion de construcción se niega a reconstruir si la app está transcribiendo |
| Las pruebas no escriben en el Escritorio del usuario | Siempre con `--destino` a una carpeta temporal |
| Lo que confunde es un fallo de interfaz | "¿Por qué se guardó ahí?" se resolvió mostrando en la fila dónde quedó cada archivo |
| Commits por tema | Rama, commits en español con estilo consistente y merge `--no-ff`: el historial se lee como un changelog |
| Honestidad con los números | Decir "no vale la pena" o "esto no lo pude verificar" ahorra decisiones malas |

---

## 9. Componentes reutilizables

Lo que la siguiente app puede copiar tal cual o casi tal cual:

| Componente | Archivo | Para qué sirve en otra app |
|---|---|---|
| Piezas de interfaz nativas | `transcribir/ui.py` | Tarjetas, pastillas, símbolos SF, degradados, pulso, menús desplegables, campos de texto |
| Ventana de Ajustes declarativa | `transcribir/ajustes.py` | Secciones con filas de menú, interruptor, carpeta y texto |
| Preferencias con esquema | `transcribir/preferencias.py` | Validación, valores por defecto y migraciones |
| Icono y glifos por código | `transcribir/make_icon.py` | Squircle de macOS, degradado, brillo, sombra, exportación `.icns` |
| Notificaciones | `transcribir/avisos.py` | Permiso, envío, clic que abre Finder |
| Descargas de modelos | `transcribir/modelos.py` | Una descarga por modelo, progreso en bytes, marca de completado |
| Patrón de agentes | `servidor.py` + `cli.py` + `agentes.py` | Socket Unix + comando + Skill de Claude Code |
| Proceso aparte para código que retiene el GIL | `transcribir/interlocutores.py` | Protocolo por stdout con avance y cancelación |
| Punto de entrada multimodo | `transcribir/principal.py` | App, `--cli` y trabajos pesados en el mismo ejecutable |
| Construcción autónoma | `setup.py` + `scripts/construir.sh` | py2app con paquetes nativos copiados, firma verificada, instalación |
| DMG para compartir | `scripts/hacer-dmg.sh` + `LEEME-dmg.txt` | Imagen con enlace a Aplicaciones, icono de volumen e instrucciones de Gatekeeper |
| README profesional | `README.md` | Estructura con insignias, capturas, stack, arquitectura y notas técnicas |
| Licencia de uso personal | `LICENSE` | Plantilla con componentes de terceros |

---

## 10. Cómo construir la siguiente app aún más rápido

1. **Empezar de una plantilla**, no de cero: copiar las piezas de la sección 9 (interfaz, ajustes, icono, construcción, DMG, README, licencia, patrón de agentes).
2. **Leer primero la sección 8.** Cada lección que ya se conoce es un día que no se pierde.
3. **Definir el "hecho" con referencias:** "calidad como Sereno", "botones en la misma columna", "se abre en otra Mac sin nada instalado".
4. **Decidir pronto lo que cambia la arquitectura:** firma de Apple, modelos dentro o descargados, nube o local, integración con agentes.
5. **Pedir planes antes de lo grande y aprobarlos rápido.** El modo plan evitó rehacer trabajo.
6. **Mandar agentes en paralelo** para investigar, revisar o estimar mientras se construye.
7. **Medir en vez de suponer:** sondas de bloqueo, calibraciones, verificación de firma, capturas reales.
8. **Guardar cada lección nueva en este documento** o en la memoria del proyecto al momento de aprenderla, no al final.
9. **Commits por tema desde el principio**, para que el historial documente solo el avance.

---

## 11. Cómo medir mejor la próxima vez

- Pedir la misma estimación a ciegas a **uno o dos desarrolladores humanos** y comparar con la del agente.
- Registrar además el **costo en tokens** y el tiempo de espera por construcciones y pruebas.
- Separar el tiempo de **decisión humana** del de **ejecución** para saber cuánto aporta cada uno.
- Medir también la **calidad**: cuántos fallos aparecen en el primer mes de uso real, y compararlo con lo que tendría una app de 10 semanas de pruebas.
- Repetir la medición en la próxima app que reutilice estas piezas, para cuantificar cuánto aceleran los componentes y las lecciones reutilizadas.

---

## 12. Estimación: cuánto falta para competir con MacWhisper

Aplicación del método a trabajo futuro: las 16 misiones de `PARTES_FALTANTES.md` más el trabajo transversal necesario para competir de verdad.

### Humano sin IA (estimación a ciegas)
El mismo método que en la sección 2. Un agente independiente vio el código y el plan, pero no los tiempos reales.

| Alcance | Horas (PERT) | Senior solo |
|---|---|---|
| Fase 1 (M1–M5): biblioteca, exportación, hablantes, calidad, firma | 426 h | ~11 semanas |
| Fase 2 (M6–M9): editor, micrófono, reuniones, dictado | 850 h | ~21 semanas |
| Fase 3 (M10–M16): IA local, traducción, en vivo, automatización, URLs, motores, inglés | 1.027 h | ~26 semanas |
| Transversal: pruebas, corpus de audio real, QA en varias Macs, Sparkle, sitio web, accesibilidad, reorganización del código | ~850 h | ~21 semanas |
| **Total** | **~3.155 h** (2.500–4.200) | **~18 meses a tiempo completo, cerca de 2 años de calendario** |

### Con IA + agentes + programador
No todo se acelera igual, así que el trabajo se separa en tres tipos:

| Tipo de trabajo | Horas humanas | Factor | Tiempo con IA |
|---|---|---|---|
| **Conocido**, parecido a lo ya hecho | ~1.400 h | 89–146× (medido en este proyecto) | 10–16 h |
| **Nuevo en macOS**, sin lecciones previas (Core Audio, CGEventTap, editor, notarización) | ~1.100 h | 40–60× (supuesto: trampas de plataforma por descubrir) | 18–28 h |
| **Humano o físico** (permisos, reuniones reales, varias Macs, audio de referencia) | ~600 h | 3–5× | 120–200 h de pruebas humanas |

**En total:**
- **Programación:** unas **34 h**, es decir 7–8 sesiones como la de este proyecto.
- **Pruebas y validación humanas:** unas **150 h**.
- **Aceleración total:** unas **17 veces**.

**Conclusión:** con IA, el cuello de botella deja de ser programar y pasa a ser **probar en el mundo real**.

| Meta | Tiempo de calendario |
|---|---|
| Paridad funcional (todo construido y probado en uso propio) | ~2–3 semanas de sesiones por las tardes |
| Producto para competir (QA en varias Macs, reuniones reales, beta, notarización) | ~2,5–3 meses, dominado por pruebas y esperas externas |

**Esperas que no dependen de programar:**
- la cuenta de Apple Developer: 1–3 días como persona física, 1–4 semanas como empresa;
- la beta con usuarios: 4–8 semanas;
- coordinar reuniones de prueba con otras personas;
- el ciclo anual de macOS.

**Mayor incertidumbre:**
- M8, grabar reuniones: Core Audio falla sin avisar y seguramente hará falta un ayudante en Swift;
- M6, el editor sincronizado;
- M9, el dictado, por la latencia y porque macOS apaga el atajo si Python tarda en responder.

**Validar:** al construir las misiones, medir si el factor de 40–60× para lo nuevo se sostiene, y actualizar esta sección con los datos reales.

---

*Medición hecha a partir del registro de la sesión de Claude Code y de una estimación independiente a ciegas. Proyecto: [JoseLuis0022/Transcribir](https://github.com/JoseLuis0022/Transcribir).*
