# Transcribir: partes faltantes y hoja de ruta

> Comparación con **MacWhisper** (Jordi Bruin / Good Snooze) y las misiones para llegar a donde queremos.
> Investigación hecha el **10 de septiembre de 2026**. Las fuentes están al final (§8). Los datos que no se pudieron comprobar en una fuente oficial van marcados como **(sin verificar)**.

---

## Índice

1. [Resumen ejecutivo](#1-resumen-ejecutivo)
2. [Qué es MacWhisper: planes y precio](#2-qué-es-macwhisper-planes-y-precio)
3. [Comparación función por función](#3-comparación-función-por-función)
4. [Partes faltantes por área](#4-partes-faltantes-por-área)
5. [Misiones](#5-misiones)
6. [Decisiones que debe tomar el usuario](#6-decisiones-que-debe-tomar-el-usuario)
7. [Lo que conscientemente no haremos](#7-lo-que-conscientemente-no-haremos)
8. [Fuentes](#8-fuentes)

---

## 1. Resumen ejecutivo

- **Dónde estamos.** Transcribir ya resuelve bien el caso principal: convertir archivos en texto dentro del Mac. Tiene cola, separación por persona, subtítulos con tiempos por palabra, carpeta vigilada y una integración con agentes que MacWhisper no iguala (Skill de Claude Code y trabajos del agente visibles en la ventana). Todo es gratis y 100 % local.
- **Dónde está MacWhisper.** Es un producto maduro (versión 14, julio de 2026). Pro cuesta **64 €, pago único** (el sitio oficial, consultado hoy). Cubre además todo lo que pasa **después** de transcribir (editor, reproductor sincronizado, búsqueda, nombres de hablantes, 10 o más formatos de exportación, traducción, resúmenes y chat con IA) y todo lo que pasa **antes** (grabar el micrófono, el audio del sistema y reuniones detectadas solas, dictado en cualquier app, URLs de YouTube).
- **La brecha real** no es el motor, donde en español vamos igual o mejor con Qwen3-ASR. Es la **falta de biblioteca**: hoy cada resultado es un `.txt` suelto y el historial se pierde al cerrar la app. Casi todo lo que falta (editor, búsqueda, renombrar hablantes, reexportar, resumir, traducir) necesita primero guardar la transcripción de forma estructurada.
- **Propuesta.** **16 misiones en 3 fases**:
  - **Fase 1**: biblioteca, exportación, hablantes, calidad del texto y distribución firmada.
  - **Fase 2**: editor con reproductor, grabación, reuniones y dictado.
  - **Fase 3**: IA local, traducción, modo en vivo, automatización, URLs, otros motores e interfaz en inglés.
- **Principio rector.** Toda paridad se consigue **sin nube**: LLM local con MLX en lugar de OpenAI/Claude, y Core Audio en lugar de bots en la reunión. Cada misión añade su comando al CLI para que un agente pueda hacer lo mismo, y se vea en la ventana.

---

## 2. Qué es MacWhisper: planes y precio

**Qué es.** Es una app de macOS que transcribe audio, video, reuniones y audio del sistema **en el propio Mac** con modelos locales (Whisper, WhisperKit, NVIDIA Parakeet). Opcionalmente usa proveedores en la nube con tus propias claves de API. Se vende en dos ediciones:

- **MacWhisper**, por descarga directa desde macwhisper.com o Gumroad, con licencia de pago único.
- **Whisper Transcription**, en la Mac App Store, con suscripciones. Tiene menos funciones: no incluye dictado, detección de reuniones, CLI, todos los proveedores de IA ni MDM.

Hay además una app para iPhone y iPad desde abril de 2025.

### 2.1 Planes de la edición de descarga directa (la que compararemos)

| Plan | Precio | Tipo | Fuente |
|---|---|---|---|
| **Free** | 0 € | "Free forever" | macwhisper.com |
| **Pro** | **64 €** por licencia | Pago único, "Includes lifetime updates" | macwhisper.com (consultado el 10 sep 2026) |
| Paquetes por volumen | 5, 10, 20 o 50 licencias, con descuento progresivo | Pago único | docs.macwhisper.com (artículo 40) |
| Estudiantes, periodistas y ONG | 25 % de descuento, bajo petición | — | docs.macwhisper.com (artículo 40) |
| Dispositivos por licencia | "soft limit of 3" | — | docs.macwhisper.com (artículo 39) |

**Sobre el precio.** El sitio oficial muestra hoy **64 €**, igual que la reseña de Vowen de julio de 2026, y eso coincide con los "unos 63 €" que recordaba el usuario. Reseñas de abril a julio de 2026 (Voibe, LumeVoice) citan **59 €**. Lo más probable es que el precio subiera a mediados de 2026 (inferencia, sin verificar). La página de Gumroad se genera con JavaScript y no se pudo leer el precio directamente: solo muestra la opción gratuita (0,0 EUR).

### 2.2 Edición Mac App Store ("Whisper Transcription")

Es gratis con compras dentro de la app. Precios en dólares de la tienda de EE. UU.:

| Compra | Precio |
|---|---|
| Pro | 6,99 $ / 8,99 $ / 29,99 $ |
| Pro Lifetime | 89,99 $ / 99,99 $ |
| Pro & Assistant | 12,99 $ |
| Assistant (semanal / mensual / anual) | 5,99 $ / 9,99 $ / 89,99 $ |

Las reseñas interpretan esas compras como Pro a 6,99 $/mes, 29,99 $/año o 99,99 $ vitalicio. **Assistant** es una suscripción con traducción a más de 30 idiomas, chat, resúmenes y **transcripción en sus servidores**. Sus propios documentos advierten: *"don't use this feature with sensitive data"*.

La ficha de la App Store pide **macOS 14.0 o posterior**. Su interfaz está en **inglés, neerlandés, francés y alemán, no en español**.

### 2.3 Funciones Free y Pro (lista oficial de macwhisper.com, literal)

- **Free:** grabar desde el micrófono; mp3, wav, m4a, ogg, opus, mov y mp4; unos 100 idiomas; exportar .srt, .vtt y .txt; dictado en todo el sistema.
- **Pro (añade):** exportar a .txt, .md, .pdf, .html, .dote y .docx; reconocimiento automático de hablantes; transcribir URLs de YouTube y de medios; transcribir podcasts con un archivo por hablante; transcripción por lotes; limpieza automática (quitar muletillas); traducir transcripciones; dictado de alta calidad; mejora gramatical automática; dictado con prompts de IA; prompts por app; reproductor de video integrado con subtítulos; traducción automática de subtítulos.
- **Funciones que el sitio anuncia sin asignarlas a un plan:**
  - grabación automática de reuniones (Zoom, Teams, Webex, Skype, Chime, Discord…) con detección de inicio y fin;
  - audio de cualquier app;
  - búsqueda y editor;
  - resúmenes, chat y prompts con IA (OpenAI, Anthropic, xAI, Gemini, Grok, Ollama, DeepSeek, Azure, LM Studio, OpenRouter, Deepgram, ElevenLabs, Gladia y endpoints compatibles con OpenAI);
  - carpetas vigiladas;
  - integraciones con Notion, Zapier, Obsidian, n8n, Make y webhooks;
  - CLI.

  Según los documentos, **las carpetas vigiladas y las integraciones son Pro**. Los reseñadores sitúan en Pro la grabación de audio del sistema y las IA (sin verificar oficialmente).

### 2.4 Hitos recientes (para saber a qué ritmo avanza)

| Fecha | Versión | Novedad | Fuente |
|---|---|---|---|
| 18 mar 2025 | 12 | Reconocimiento de hablantes **en el dispositivo** (WhisperKit Pro + SpeakerKit de Argmax), solo Pro | 9to5Mac |
| abr 2025 | — | App para iPhone y iPad | 9to5Mac |
| 27 jun 2025 | 13 | NVIDIA **Parakeet** (Pro; en su lanzamiento, **solo inglés**). Según terceros, luego Parakeet v3 multilingüe con español (sin verificar) | 9to5Mac, Australian Apple News |
| 17 feb 2026 | 13.13 | Historial rediseñado, exportación de tiempos por palabra, recuperar transcripciones borradas, disparadores de carpeta vigilada | MacUpdate |
| 23 abr 2026 | 13.20 | **CLI `mw`**: habla con la app por un socket local y la abre si hace falta | 9to5Mac, docs |
| 14 jul 2026 | 14 | **Nuevo editor de transcripciones** (editar en la pantalla principal, reasignar hablantes, favoritos), mejor rendimiento y reproducción | 9to5Mac |
| jul–sep 2026 | 14.1 a 14.4.1 | Gladia como proveedor en la nube; la documentación ya cita la 14.4.1 (1467) | 9to5Mac, docs |

**Requisitos.** macOS 14 o posterior. Funciona en Intel, pero **WhisperKit, Parakeet y el reconocimiento de hablantes local exigen Apple Silicon** (docs: artículo 29; Vowen; blazingfasttranscription).

---

## 3. Comparación función por función

Leyenda: ✅ sí · ⚠️ parcial · ❌ no · ❓ sin verificar

### 3.1 Motor e idiomas

| Función | MW Gratis | MW Pro | Transcribir hoy | Nota |
|---|---|---|---|---|
| Transcripción local de archivos | ✅ | ✅ | ✅ | — |
| Modelos | Whisper pequeños ❓ | Whisper hasta Large v3, WhisperKit, Parakeet | Qwen3-ASR 1.7B y 0.6B (MLX) | En la versión gratuita de MW, terceros citan Tiny, Base y Small (sin verificar). |
| Precisión en español | Whisper | Whisper y Parakeet v3 ❓ | **Qwen3-ASR 1.7B** | Error por palabra en FLEURS-es: 3,35 % con Qwen3-ASR frente a 4,08 % con Whisper large-v3 (informe de Qwen). No hay cifra de Parakeet v3 en español. **Ventaja probable nuestra.** |
| Idiomas | ~100 | ~100 | es / en / auto | **El motor ya admite 30 idiomas y 22 dialectos**; solo falta ofrecerlos en la app. |
| Varios idiomas en un archivo | ❌ (docs) | ❌ (docs) | ❓ | MW lo reconoce como limitación. Hay que probar el cambio de idioma con Qwen3-ASR en modo automático. |
| Transcripción en la nube (OpenAI, Groq, ElevenLabs, Deepgram, Gladia) | — | ✅ con clave propia | ❌ | **No la haremos** (§7). |
| Vocabulario o contexto | ❓ | ❓ | ✅ vocabulario propio | MW tiene reemplazos globales; los "diccionarios propios" solo aparecen en reseñas (sin verificar). |
| Reemplazos automáticos (buscar → reemplazar) | ✅ ❓ | ✅ | ❌ | MW: lista importable en JSON, opciones de mayúsculas y palabra completa. Solo se aplica a transcripciones nuevas. |
| Quitar muletillas ("eh", "um") | ❌ | ✅ | ❌ | — |
| Formatos de entrada | mp3 wav m4a ogg opus mov mp4 | igual | m4a mp4 mp3 wav mov | Nos faltan ogg y opus: AVFoundation no lee Ogg. |

### 3.2 Flujo de trabajo

| Función | MW Gratis | MW Pro | Transcribir hoy | Nota |
|---|---|---|---|---|
| Varios archivos a la vez (cola o lotes) | ❌ | ✅ | ✅ **gratis** | Ventaja nuestra: MW pide Pro. |
| Cancelar el trabajo en curso | ❓ | ❓ | ✅ | — |
| Carpeta vigilada | ❌ | ✅ (beta) | ⚠️ solo con la app abierta | — |
| Transcribir URLs (YouTube) | ❌ | ✅ | ❌ | MW no admite URLs en lotes ni videos con restricción de edad. |
| Podcast con un archivo por hablante | ❌ | ✅ | ❌ | — |
| Historial persistente | ✅ | ✅ | ❌ | MW recupera incluso transcripciones borradas (13.13). |
| Notificaciones | ❓ | ❓ | ✅ | — |
| Barra de menús | ✅ | ✅ | ❌ | 9to5Mac menciona arreglos en la barra de menús de MW 14. |

### 3.3 Hablantes

| Función | MW Gratis | MW Pro | Transcribir hoy | Nota |
|---|---|---|---|---|
| Separar por persona (diarización) | ❌ | ✅ local (Apple Silicon) | ✅ **gratis**, local (Sherpa-ONNX) | Ventaja nuestra en precio. En calidad, MW está en beta y "puede partir a un hablante en varios" (Voibe). |
| Renombrar hablantes | — | ✅ | ❌ | MW sugiere nombres a partir de hablantes guardados en Ajustes. |
| Fusionar hablantes y reasignar segmentos | — | ✅ (atajos 1, 2, 3) | ❌ | — |
| Colores por hablante | — | ✅ | ❌ | — |
| Fijar el número de hablantes | ❓ | ❓ | ❌ | Sherpa ya lo permite (`num_clusters`). |

### 3.4 Revisar y editar

| Función | MW Gratis | MW Pro | Transcribir hoy | Nota |
|---|---|---|---|---|
| Visor de la transcripción en la app | ✅ | ✅ | ❌ | Hoy solo "Mostrar en Finder" o abrir el `.txt`. |
| Editor | ✅ ❓ | ✅ | ❌ | Rediseñado en MW 14. El plan exacto no está verificado. |
| Reproductor sincronizado con el texto | ✅ ❓ | ✅ (video con subtítulos) | ❌ | Espacio para reproducir y pausar, velocidad con ⇧< y ⇧>. |
| Buscar en la transcripción | ✅ | ✅ | ❌ | ⌘F; buscar y reemplazar con ⌘⇧F. |
| Favoritos o resaltados | ❓ | ✅ | ❌ | — |

### 3.5 Exportación

| Función | MW Gratis | MW Pro | Transcribir hoy | Nota |
|---|---|---|---|---|
| .txt | ✅ | ✅ | ✅ | Nosotros además ofrecemos párrafos con marcas `[mm:ss]`. |
| .srt | ✅ | ✅ | ✅ tiempos por palabra | — |
| .vtt | ✅ | ✅ | ❌ | — |
| .csv | ✅ (CLI) | ✅ | ❌ | — |
| .md / .html / .pdf / .docx | ❌ | ✅ | ❌ | — |
| .json (estructurado) | ❌ | ✅ | ❌ | Clave para los agentes. |
| Avid / DOTE | ❌ | ✅ | ❌ | Formatos de nicho: edición de video y análisis de conversación. |
| Tiempos por palabra | ❓ | ✅ (13.13) | ⚠️ solo dentro del .srt | — |
| Varios formatos a la vez | — | ✅ | ❌ | Uno por trabajo. |
| Reexportar sin volver a transcribir | ✅ | ✅ | ❌ | Requiere biblioteca. |

### 3.6 Captura: grabación y dictado

| Función | MW Gratis | MW Pro | Transcribir hoy | Nota |
|---|---|---|---|---|
| Grabar el micrófono | ✅ | ✅ | ❌ | — |
| Grabar el audio del sistema o de una app | ❓ | ✅ ❓ | ❌ | "App Audio" en el sitio; los reseñadores lo sitúan en Pro. |
| Detectar y grabar reuniones (Zoom, Teams, Meet en el navegador, Slack, WhatsApp…) | ❓ | ✅ (beta) | ❌ | Sin bots. Pide permisos de grabación de pantalla y micrófono. **FaceTime no se puede** por restricciones de macOS. Solo en la edición directa. |
| Dictado en cualquier app | ✅ | ✅ alta calidad | ❌ | Solo en la edición directa. Una reseña mide más de 2,4 s de latencia (LumeVoice). |
| Dictado con prompts de IA y prompts por app | ❌ | ✅ | ❌ | Usa el LLM que configures (OpenAI según los documentos). |
| "Global": ventana flotante, grabar y copiar | ❌ | ✅ | ❌ | — |
| Subtítulos en vivo, también traducidos | ❓ | ❓ | ❌ | Solo en reseñas (sin verificar). |

### 3.7 IA y traducción

| Función | MW Gratis | MW Pro | Transcribir hoy | Nota |
|---|---|---|---|---|
| Resúmenes, chat y prompts | ❓ | ✅ con clave propia (nube o Ollama/LM Studio) | ❌ | Nosotros lo haríamos con un LLM local vía MLX (M10). |
| Traducir transcripciones y subtítulos | ❌ | ✅ | ❌ | DeepL (2024) y Assistant en la nube; la traducción local está sin verificar. |

### 3.8 Automatización y agentes

| Función | MW Gratis | MW Pro | Transcribir hoy | Nota |
|---|---|---|---|---|
| CLI | ✅ `mw` (formatos txt, srt, vtt, csv) | ✅ (+ json, md, html, avid) | ✅ `transcribir` | Ambos hablan con la app por un socket local. **Solo nosotros**: Skill de Claude Code instalada, guía para `AGENTS.md`, trabajos del agente visibles con etiqueta, cancelar y cambiar ajustes desde el CLI. **MW**: listar y elegir modelos, `--stream`. |
| Integraciones (Notion, Zapier, n8n, Make, webhook, Obsidian) | ❌ | ✅ | ❌ | Envían el texto a servicios externos, salvo Obsidian por su API REST local. |
| Atajos, AppleScript, Raycast | ❓ | ❓ | ❌ | No se encontró documentación oficial de MW. |
| MDM (despliegue en empresas) | ✅ | ✅ | ❌ | **No lo haremos** (§7). |

### 3.9 Plataforma y distribución

| Función | MW Gratis | MW Pro | Transcribir hoy | Nota |
|---|---|---|---|---|
| Idioma de la interfaz | Inglés, neerlandés, francés, alemán | igual | **Español** | **Ventaja nuestra** para hispanohablantes. Nos falta el inglés. |
| Mac Intel | ✅ (con límites) | ✅ | ❌ | MLX solo corre en Apple Silicon. |
| iPhone y iPad | ✅ | ✅ | ❌ | Fuera de alcance. |
| Firma y notarización | ✅ ❓ | ✅ ❓ | ❌ firma ad-hoc | Asumido: se descarga y abre como app firmada (sin verificar formalmente). |
| Privacidad | Local por defecto; nube opcional | igual | **100 % local**, sin opción de nube | La nube opcional de MW (Assistant, APIs) exige al usuario vigilar qué sale. |
| Precio | 0 € | 64 € | 0 € | La licencia de Transcribir es de uso personal: ver la decisión 6.4. |

### 3.10 Ventajas de Transcribir, dicho con honestidad

1. **Agent first de verdad.**
   - MW ya tiene CLI desde abril de 2026, así que el CLI **ya no es exclusivo nuestro**.
   - Sí son nuestros: la Skill que Claude Code descubre sola, la guía para otros agentes, **los trabajos del agente visibles en la ventana con su nombre**, y la paridad de cancelar y cambiar ajustes.
2. **Español primero.** Qwen3-ASR 1.7B es más preciso que Whisper large-v3 en español según el informe técnico de Qwen, y la interfaz está en español. MW no ofrece su interfaz en español.
3. **Gratis lo que en MW es Pro:** cola por lotes, separar por persona, carpeta vigilada y `.srt` con tiempos por palabra.
4. **Privacidad sin matices.** No existe un modo nube que activar por error.
5. **Código auditable.** El usuario puede leer qué hace la app (aunque la licencia no es de código abierto; ver 6.4).
6. **Cancelar un trabajo en curso**, desde la ventana o desde un agente.

**Y con la misma honestidad, lo que nos pesa:**

- no hay biblioteca ni editor;
- tres formatos de salida frente a más de diez;
- no se puede grabar nada;
- no hay IA posterior;
- no funciona en Intel;
- no está notarizada: el primer arranque muestra el aviso de Gatekeeper;
- dos idiomas en la interfaz del motor frente a unos 100.

---

## 4. Partes faltantes por área

| Área | Qué falta | Misión |
|---|---|---|
| **Biblioteca** | Historial persistente; transcripción guardada con palabras, tiempos y personas; búsqueda en todas las transcripciones; borrar y recuperar | M1 |
| **Exportación** | VTT, Markdown, JSON, CSV, DOCX, PDF, HTML; varios formatos a la vez; reexportar; opciones de subtítulo | M2 |
| **Hablantes** | Renombrar, fusionar, reasignar, colores; fijar el número de personas; (extra) reconocer voces conocidas; podcast con una pista por hablante | M3 |
| **Calidad del texto** | Los 30 idiomas del motor; reemplazos automáticos; quitar muletillas; perfiles de vocabulario; entrada ogg y opus | M4 |
| **Distribución** | Developer ID, notarización, entitlements y actualizaciones | M5 |
| **Revisión** | Visor y editor; reproductor de audio y video sincronizado; buscar y reemplazar; favoritos | M6 |
| **Captura** | Grabar el micrófono; barra de menús | M7 |
| **Captura** | Grabar el audio del sistema y reuniones con detección automática | M8 |
| **Captura** | Dictado en cualquier app, con atajo global | M9 |
| **IA** | Resúmenes, puntos de acción, prompts propios, chat con la transcripción | M10 |
| **Traducción** | Traducir transcripciones y subtítulos conservando los tiempos | M11 |
| **Tiempo real** | Transcripción y subtítulos en vivo | M12 |
| **Automatización** | Esquema de URL, Atajos, AppleScript, carpeta vigilada sin la app abierta, adaptador MCP, exportar a Obsidian | M13 |
| **Entrada** | Transcribir desde URLs (YouTube, podcasts) | M14 |
| **Motores** | Parakeet (velocidad) y Whisper (100 idiomas) como alternativas | M15 |
| **Idioma** | Interfaz en inglés | M16 |

---

## 5. Misiones

**Escala de esfuerzo** (una persona con agentes de IA): **S** = hasta 3 días · **M** = 1 a 2 semanas · **L** = 3 a 4 semanas · **XL** = más de un mes.

**Regla de paridad para agentes.** Toda misión termina con:

- su comando o su opción en `transcribir`;
- su sección en `transcribir guia` y en la Skill;
- los campos nuevos en `estado --json`;
- la acción visible en la ventana con la etiqueta del cliente.

**Orden.** Por impacto dividido entre esfuerzo, respetando dependencias.

```
Fase 1  M1 Biblioteca ──┬─> M2 Exportación
                        ├─> M3 Hablantes
                        └─> (M6)            M4 Calidad del texto     M5 Distribución firmada
Fase 2  M6 Editor + reproductor <── M1      M7 Micrófono + barra de menús <── M5
        M8 Sistema y reuniones <── M5, M7   M9 Dictado <── M5, M7
Fase 3  M10 IA local ──> M11 Traducción     M12 En vivo <── M7 (M8)
        M13 Automatización   M14 URLs   M15 Otros motores   M16 Interfaz en inglés
```

---

### Fase 1: imprescindibles (cimientos y paridad con archivos)

#### M1 · Biblioteca: historial persistente y búsqueda

- **Objetivo.** Que cada transcripción viva en la app, no solo como un `.txt` suelto: se ve, se busca y se reutiliza después de cerrar la app.
- **Funciones que cubre:**
  - historial persistente;
  - búsqueda en todas las transcripciones;
  - borrar y recuperar (papelera de 30 días);
  - base para editor, reexportación, hablantes, IA y traducción.
- **Por qué importa.** Es la dependencia de casi todo lo demás, y hoy "Terminados" se pierde al cerrar. MW lo tiene en todas las versiones.
- **Enfoque técnico:**
  - Un documento estructurado por transcripción en `~/Library/Application Support/Transcribir/Biblioteca/<id>.json`, con:
    - origen (ruta y marcador *bookmark* si el archivo se mueve);
    - duración, idioma, modelo, vocabulario;
    - texto;
    - lista de palabras con inicio, fin y persona;
    - nombres de hablantes;
    - fechas.
  - Un índice **SQLite con FTS5** (`sqlite3` de Python) para listar y buscar al instante. Hay que confirmar que el Python empaquetado trae FTS5.
  - `motor.py` debe guardar siempre las palabras con tiempo. Hoy solo alinea si el formato lo pide. **Decisión técnica:** alinear siempre, a costa de tiempo y de descargar el alineador (1,8 GB), o guardar solo el texto cuando no se pidió alineación y ofrecer "Calcular tiempos" después.
  - El `.txt` o `.srt` de salida se sigue escribiendo como hoy: la biblioteca no cambia el flujo actual.
  - En la ventana: sección "Biblioteca" (lista con búsqueda) que sustituye o amplía "Terminados".
- **Paridad para agentes:**
  ```sh
  transcribir historial [--json] [--desde 2026-09-01]
  transcribir buscar "presupuesto" [--json]
  transcribir texto ID [--formato json]
  transcribir borrar ID
  ```
  `estado --json` añade `biblioteca_total` y el `id` de biblioteca de cada terminado.
- **Dependencias.** Ninguna.
- **Esfuerzo.** **M**
- **Riesgos:**
  - migrar el formato del JSON en el futuro (hay que versionar el esquema);
  - espacio en disco (bajo: el texto pesa poco);
  - rutas que cambian si el original se mueve (usar *security-scoped bookmarks* no es necesario sin sandbox; basta un *bookmark* normal).
- **Criterios de aceptación:**
  - Tras reiniciar la app, la biblioteca muestra las transcripciones anteriores.
  - Buscar una palabra en más de 500 transcripciones devuelve resultados en menos de 200 ms.
  - `transcribir buscar` y la ventana muestran los mismos resultados.
  - Borrar no toca el `.txt` exportado ni el audio original.

#### M2 · Exportación completa

- **Objetivo.** Exportar a cualquier formato útil, varios a la vez y sin volver a transcribir.
- **Funciones que cubre:**
  - VTT, Markdown, JSON (palabras, tiempos y hablantes), CSV (segmentos), HTML, DOCX, PDF;
  - varios formatos por trabajo;
  - reexportar desde la biblioteca;
  - opciones de subtítulo (caracteres por línea, duración máxima, con o sin nombre de hablante);
  - tiempos por palabra.
- **Por qué importa.** Es la brecha más visible frente a MW Pro, y el JSON es el mejor formato para los agentes.
- **Enfoque técnico:**
  - `formatos.py` ya tiene la lógica de bloques; VTT, Markdown, CSV y JSON son transformaciones directas.
  - **DOCX, HTML y RTF sin dependencias nuevas**: `NSAttributedString` de AppKit escribe Office Open XML, HTML, RTF y OpenDocument (hay que verificar la fidelidad de estilos).
  - **PDF** con AppKit o Quartz (ya empaquetado), dibujando el texto con estilo del sistema.
  - Si `NSAttributedString` no da un DOCX aceptable, la alternativa es `python-docx` (MIT).
  - En Ajustes, "Formato" pasa de menú a lista de casillas. En la biblioteca, botón "Exportar…" con selector de formatos.
- **Paridad para agentes:**
  ```sh
  transcribir clase.mp4 --formato srt,vtt,json
  transcribir exportar ID --formato docx,pdf --destino ~/Documentos
  transcribir exportar ID --formato srt --max-caracteres 32 --sin-hablantes
  ```
- **Dependencias.** M1, para reexportar. Los formatos nuevos al transcribir no dependen de nada.
- **Esfuerzo.** **M**
- **Riesgos:** calidad del DOCX y PDF generados por AppKit; nombres de archivo repetidos al exportar varios formatos (resuelto con `ruta_libre`).
- **Criterios de aceptación:**
  - Los 9 formatos se abren sin errores en Word, Pages, VLC, un validador WebVTT y un lector de JSON.
  - Exportar 3 formatos de una transcripción de 1 hora tarda menos de 3 s.
  - Un agente obtiene el JSON con tiempos por palabra solo con el CLI.

#### M3 · Hablantes con nombre

- **Objetivo.** Pasar de "Persona 1 y Persona 2" a "Ana y Luis", y corregir los errores de la separación.
- **Funciones que cubre:**
  - fijar el número de personas;
  - renombrar;
  - fusionar dos hablantes;
  - reasignar un segmento;
  - colores;
  - (extra) reconocer voces ya conocidas;
  - (extra) "podcast": una pista por hablante, cada una con su nombre.
- **Por qué importa.** Es lo primero que se nota en actas y entrevistas, y MW lo cobra como Pro.
- **Enfoque técnico:**
  - **Número de personas:** `interlocutores.py` usa `FastClusteringConfig(num_clusters=-1)`; con `--personas N` se pasa N (Sherpa lo admite).
  - **Renombrar, fusionar y reasignar:** operan sobre la biblioteca (M1) y reescriben las exportaciones. Si la transcripción ya se exportó, se ofrece "Reexportar".
  - **Voces conocidas (extra):** guardar la huella WeSpeaker media de cada hablante con nombre y compararla, con la misma distancia que ya se calibró (0,33), para sugerir "¿Es Ana?". Son datos biométricos: solo en local y con permiso explícito (decisión 6.8).
  - **Podcast:** soltar varias pistas y marcarlas como "una persona por archivo". Se transcriben por separado y se intercalan por tiempo, sin diarización.
- **Paridad para agentes:**
  ```sh
  transcribir entrevista.m4a --personas 2
  transcribir hablantes ID                      # lista con tiempos de habla
  transcribir hablantes ID --renombrar 1=Ana 2=Luis
  transcribir hablantes ID --fusionar 3 1
  ```
- **Dependencias.** M1. Las voces conocidas dependen además de la decisión 6.8.
- **Esfuerzo.** **S–M**: S para el número y los nombres, M con fusionar y reasignar desde la interfaz (la reasignación fina llega con M6).
- **Riesgos:** la calidad de la separación en llamadas con ruido; si se reconoce a alguien por su voz sin avisar, se perderá la confianza del usuario.
- **Criterios de aceptación:**
  - Renombrar actualiza la biblioteca y las nuevas exportaciones en todos los formatos.
  - `--personas 2` nunca produce "Persona 3".
  - Lo hecho por CLI se ve en la ventana al momento.

#### M4 · Calidad del texto e idiomas

- **Objetivo.** Aprovechar lo que el motor ya sabe hacer y limpiar el texto final.
- **Funciones que cubre:**
  - los 30 idiomas y 22 dialectos de Qwen3-ASR en Ajustes y en el CLI;
  - reemplazos automáticos (lista original → reemplazo, importable y exportable en JSON, con opciones de mayúsculas y palabra completa, también sobre transcripciones pasadas, cosa que MW no hace);
  - quitar muletillas ("eh", "este", "o sea", "um"; lista por idioma y desactivable);
  - perfiles de vocabulario guardados ("Clase de marketing", "Equipo legal");
  - entrada `.m4v`, `.aac`, `.flac`, `.caf`, y estudiar ogg y opus.
- **Por qué importa.** Mejoras baratas y visibles. MW cobra la limpieza como Pro.
- **Enfoque técnico:**
  - `motor.IDIOMAS` e `preferencias.ESQUEMA` pasan a leer la lista de idiomas del paquete (`mlx-qwen3-asr --list-languages`).
  - Reemplazos y muletillas en un paso posterior en `formatos.py`, determinista (expresiones regulares sobre palabras) para no romper los tiempos por palabra.
  - Ogg y Opus no los lee AVFoundation. Añadir un decodificador libre (por ejemplo `soundfile`/libsndfile, LGPL) cuesta tamaño; hay que decidir si vale la pena.
- **Paridad para agentes:**
  ```sh
  transcribir audio.m4a --idioma pt
  transcribir ajustes reemplazos --importar lista.json
  transcribir audio.m4a --sin-muletillas --perfil "Equipo legal"
  ```
  `ajustes --json` lista los idiomas válidos.
- **Dependencias.** Ninguna. Aplicar reemplazos a transcripciones pasadas depende de M1.
- **Esfuerzo.** **S**
- **Riesgos:** calidad del reconocimiento en idiomas poco probados; quitar muletillas puede borrar palabras legítimas ("este" como demostrativo), así que conviene aplicarlo solo en muletillas aisladas y dejarlo desactivable.
- **Criterios de aceptación:**
  - Transcribir en portugués o francés desde la ventana y el CLI.
  - Un reemplazo "cuit → CUIT" se aplica con palabra completa y sin alterar el `.srt`.
  - Los tiempos siguen alineados tras quitar muletillas.

#### M5 · Distribución firmada y notarizada

- **Objetivo.** Que la app se abra sin el aviso de Gatekeeper y que los permisos de micrófono, audio del sistema y accesibilidad sean estables.
- **Funciones que cubre:**
  - firma Developer ID con *hardened runtime*;
  - notarización y *staple* del DMG;
  - entitlements: `com.apple.security.device.audio-input` y excepciones de JIT o memoria si MLX o Python las requieren;
  - (opcional) actualizaciones con Sparkle (MIT).
- **Por qué importa.** Hoy los 5 pasos del README para abrirla ahuyentan a quien la recibe. Y es **requisito práctico de la Fase 2**: macOS asocia los permisos de privacidad (TCC) a la firma. Con firma ad-hoc, cada compilación cambia de identidad y macOS vuelve a pedir o pierde el permiso. El permiso de audio del sistema, además, solo aparece en binarios bien firmados.
- **Enfoque técnico:**
  - `construir.sh` firma de dentro hacia fuera todas las librerías (`mlx`, `sherpa_onnx`, `.so` de Python) con `--options runtime` y marca de tiempo.
  - `notarytool submit --wait` y `stapler staple` para el DMG.
  - Actualizaciones: Sparkle o una comprobación simple de la última versión en GitHub Releases. Ambas usan internet (decisión 6.3).
- **Paridad para agentes.** `transcribir version --json` (versión, compilación, firma válida y notarizada, actualización disponible).
- **Dependencias.** **Decisión 6.2**: Apple Developer Program, 99 USD al año.
- **Esfuerzo.** **S**, más la espera de la cuenta.
- **Riesgos:**
  - librerías que no pasan la notarización (ya pasó con `liblzma`);
  - MLX y Python bajo *hardened runtime* pueden necesitar `allow-jit` o `allow-unsigned-executable-memory` (hay que probarlo).
- **Criterios de aceptación:**
  - Un Mac limpio con macOS 14 y otro con macOS 15 abren el DMG descargado sin avisos.
  - `spctl -a -vv` devuelve "Notarized Developer ID".
  - El permiso de micrófono sobrevive a una actualización.

---

### Fase 2: revisar y capturar

#### M6 · Visor y editor con reproducción sincronizada

- **Objetivo.** Revisar y corregir la transcripción escuchando el audio, sin salir de la app.
- **Funciones que cubre:**
  - ventana de transcripción con texto por intervenciones;
  - reproductor de audio y video;
  - la palabra que suena, resaltada;
  - clic en una palabra para saltar a ese momento;
  - velocidad de reproducción;
  - edición de texto que conserva los tiempos;
  - buscar y reemplazar (⌘F, ⌘⇧F);
  - reasignar hablante a un bloque (atajos 1, 2, 3);
  - favoritos;
  - video con subtítulos superpuestos.
- **Por qué importa.** Es el núcleo de la experiencia "después de transcribir" de MW, que lo acaba de rediseñar en su versión 14. Sin él, las transcripciones largas no se pueden corregir con comodidad.
- **Enfoque técnico:**
  - `AVPlayer` y `AVPlayerView` (hay que añadir `pyobjc-framework-AVKit`), con `addPeriodicTimeObserverForInterval` para resaltar.
  - `NSTextView` con los tiempos guardados como atributos de cada rango de palabras.
  - Al editar, emparejar el texto nuevo con las palabras antiguas; se puede reutilizar la idea de `formatos.palabras_con_tiempo`.
  - Guardado automático en la biblioteca y opción "Reexportar".
  - Diseño: la ventana de documento sigue el lenguaje de Sereno (materiales, esquinas continuas, tipografía del sistema).
- **Paridad para agentes:**
  ```sh
  transcribir abrir ID [--en 12:30]                        # abre el visor en ese momento, visible
  transcribir editar ID --reemplazar "Sanchez" "Sánchez"
  transcribir editar ID --segmento 42 --texto "…" [--persona 2]
  ```
  Lo que edita un agente aparece resaltado con su etiqueta.
- **Dependencias.** M1. Mejor tras M2 y M3.
- **Esfuerzo.** **L**
- **Riesgos:**
  - rendimiento de `NSTextView` con transcripciones de 3 horas (más de 30 000 palabras): pintar por bloques;
  - conservar los tiempos al hacer ediciones grandes;
  - archivos originales movidos o borrados (mostrar texto sin reproductor).
- **Criterios de aceptación:**
  - En una grabación de 2 horas, el clic en una palabra salta con un error menor de 0,3 s y el resaltado sigue sin tirones.
  - Editar y reexportar a SRT mantiene los tiempos del resto.
  - La edición hecha por CLI aparece al instante si el visor está abierto.

#### M7 · Grabar el micrófono y barra de menús

- **Objetivo.** Grabar desde la app (notas de voz, clases presenciales, entrevistas) y tenerla a mano sin ventana.
- **Funciones que cubre:**
  - grabar, pausar y detener, con elección de micrófono y nivel de entrada;
  - al detener, transcribir con los ajustes actuales;
  - icono en la barra de menús (`NSStatusItem`) con grabar, estado de la cola y últimas transcripciones;
  - base técnica de M8, M9 y M12.
- **Por qué importa.** Es gratis en MW, y muchos usuarios esperan un botón de grabar en una app de transcripción.
- **Enfoque técnico:**
  - `AVAudioEngine`: *tap* del nodo de entrada escrito a `AVAudioFile` AAC `.m4a` en `Application Support/Transcribir/Grabaciones`.
  - Permiso con `AVCaptureDevice.requestAccessForMediaType_` y `NSMicrophoneUsageDescription` en el `plist` de `setup.py`.
  - Guardado incremental para no perder nada si la app se cierra.
  - Barra de menús con `NSStatusItem` y el glifo del disco de estado (gris, violeta, verde).
- **Paridad para agentes:**
  ```sh
  transcribir grabar [--microfono "MacBook Pro"] [--max 90m] [--no-transcribir]
  transcribir detener
  transcribir estado --json          # añade "grabando": {"desde": …, "segundos": …}
  ```
  La ventana y la barra de menús muestran "Grabando · Claude Code". **Un agente nunca puede grabar sin que se vea**: indicador obligatorio y aviso del sistema.
- **Dependencias.** M5 (permisos estables). Recomendable M1.
- **Esfuerzo.** **M**
- **Riesgos:**
  - privacidad: que un agente active el micrófono sin que el usuario lo sepa. Mitigación: ajuste "Permitir que los agentes graben", desactivado por defecto, además de indicador y notificación;
  - cambio de dispositivo durante la grabación (AirPods).
- **Criterios de aceptación:**
  - Una grabación de 2 horas no se corta ni pierde audio si se desconectan los auriculares.
  - Al detener, entra sola en la cola.
  - Con el ajuste de agentes desactivado, `transcribir grabar` falla con código 1 y un mensaje claro.

#### M8 · Audio del sistema y reuniones

- **Objetivo.** Transcribir llamadas de Zoom, Teams, Meet, Slack o WhatsApp, y cualquier audio que suene en el Mac, **sin bots** y sin nube.
- **Funciones que cubre:**
  - grabar el audio del sistema o de una app concreta;
  - grabación de reunión con dos pistas (micrófono = "Yo"; sistema = los demás, separados por diarización);
  - detección de reuniones con notificación "¿Grabar reunión?" y fin automático;
  - funciona con cualquier app de llamadas; FaceTime queda excluido por macOS, igual que en MW.
- **Por qué importa.** Es la función de más valor diario para profesionales y la razón principal por la que muchos compran MW Pro.
- **Enfoque técnico:**
  - **Opción A (preferida): Core Audio *process taps*** (`CATapDescription` y `AudioHardwareCreateProcessTap`, **macOS 14.2 o posterior**).
    - Captura el audio de salida de todo el sistema o de procesos concretos, sin el permiso de grabación de pantalla.
    - Pide el permiso "grabación de audio del sistema" (`NSAudioCaptureUsageDescription`).
    - Algunos ejemplos públicos (AudioCap) exigen 14.4.
  - **Opción B: ScreenCaptureKit** (`SCStream` con `capturesAudio`, macOS 13 o posterior). Es más sencilla desde PyObjC (`pyobjc-framework-ScreenCaptureKit`), pero pide **permiso de grabación de pantalla**, que asusta, y macOS 15 lo vuelve a confirmar periódicamente (sin verificar la frecuencia exacta).
  - **Si las bindings de PyObjC para taps no alcanzan**, un **ayudante nativo pequeño** (Swift o C, compilado en `construir.sh`) que escribe PCM por su salida. Es el mismo patrón que el proceso aparte `--separar` que ya usamos (decisión 6.6).
  - **Detección:**
    - `NSWorkspace` avisa cuando se abren Zoom, Teams, Webex o Slack;
    - `kAudioDevicePropertyDeviceIsRunningSomewhere` indica que el micrófono está en uso;
    - la lista de procesos de audio de Core Audio (14.2 o posterior) dice qué proceso usa el micrófono, lo que sirve para Meet en el navegador.
  - **Dos pistas:** se transcriben por separado; la de sistema pasa por Sherpa y se intercalan por tiempo. El resultado sale mejor etiquetado que la diarización de una sola mezcla.
- **Paridad para agentes:**
  ```sh
  transcribir grabar sistema [--app zoom.us]
  transcribir grabar reunion
  transcribir ajustes detectar_reuniones si
  ```
  `estado --json` informa de la reunión detectada y de la grabación en curso. Mismas salvaguardas que M7.
- **Dependencias.** M5 (obligatoria en la práctica) y M7. Decisión 6.5 sobre la versión mínima de macOS.
- **Esfuerzo.** **XL**
- **Riesgos:**
  - las APIs de Core Audio son de bajo nivel y están poco documentadas desde Python;
  - cambios de permisos en cada versión de macOS;
  - aspectos legales de grabar llamadas: avisar al usuario de que informe a los participantes;
  - eco o doble captura si el usuario no usa auriculares (el micrófono capta los altavoces). Mitigación: detectar y descartar el eco por correlación o sugerir auriculares.
- **Criterios de aceptación:**
  - Una llamada de Zoom de 30 minutos queda en la biblioteca con "Yo" y "Persona 1…".
  - Con la app cerrada, la detección no hace nada; con la app abierta, avisa en menos de 10 s.
  - Funciona en macOS 14.2 o posterior (o la versión mínima que se decida) sin permiso de grabación de pantalla con la opción A.

#### M9 · Dictado en cualquier app

- **Objetivo.** Mantener pulsado un atajo, hablar y que el texto aparezca donde está el cursor.
- **Funciones que cubre:**
  - atajo global (pulsar y mantener, o alternar);
  - modelo 0.6B en 4 bits, siempre cargado;
  - insertar en el campo activo;
  - vocabulario y reemplazos (M4);
  - (con M10) prompts de IA: corregir gramática, tono, prompts distintos por app.
- **Por qué importa.** Es gratis en MW, aunque una reseña mide más de 2,4 s de latencia. Con Qwen3-ASR 0.6B en 4 bits (unos 0,17 s por cada 10 s de audio en un M4 Pro, según mlx-qwen3-asr) podemos **ser más rápidos que MW**.
- **Enfoque técnico:**
  - Atajo global con `CGEventTap` (Quartz, ya empaquetado), que pide permiso de **Accesibilidad** o **Supervisión de entrada**.
  - Captura con el motor de M7.
  - Inserción: guardar el portapapeles, escribir el texto, simular ⌘V con `CGEventCreateKeyboardEvent` y restaurar el portapapeles. Alternativa: `AXUIElement` para fijar el valor directamente.
  - Ventanita flotante con el nivel de voz, en el lenguaje visual de Sereno.
  - Mantener el modelo residente en la GPU. Si el Mac tiene 8 GB, cargarlo solo mientras el dictado esté activado.
- **Paridad para agentes.** Un agente no dicta, pero sí configura:
  ```sh
  transcribir ajustes dictado si
  transcribir ajustes dictado_atajo "⌥Espacio"
  transcribir dictados --json          # historial de dictados si se decide guardarlo
  ```
- **Dependencias.** M5 y M7. Los prompts dependen de M10.
- **Esfuerzo.** **L**
- **Riesgos:**
  - pedir permiso de Accesibilidad genera desconfianza: explicarlo bien en la bienvenida;
  - apps que bloquean el pegado simulado (MW tiene un artículo sobre ello);
  - memoria: 0.6B residente más 1.7B para archivos más un LLM.
- **Criterios de aceptación:**
  - Una frase de 5 s aparece en TextEdit, Mail, Slack y VS Code en menos de 1 s tras soltar la tecla, en un M1.
  - El portapapeles del usuario queda intacto.
  - El dictado funciona sin conexión.

---

### Fase 3: inteligencia local y ecosistema

#### M10 · IA local: resúmenes, prompts y chat

- **Objetivo.** Convertir una transcripción en un acta, un resumen o respuestas, **sin que el texto salga del Mac**.
- **Funciones que cubre:**
  - prompts incluidos (resumen, puntos clave, tareas y responsables, acta de reunión, preguntas frecuentes, título);
  - prompts propios;
  - ejecución automática al terminar (por ejemplo "acta" en la carpeta vigilada);
  - chat con la transcripción, con citas de tiempo [mm:ss] que saltan al reproductor (M6).
- **Por qué importa.** MW lo ofrece conectando OpenAI, Anthropic, etc., o Ollama y LM Studio. Nuestra ventaja: todo **local por defecto**, sin claves ni cuentas.
- **Enfoque técnico:**
  - **mlx-lm** (MIT) con un modelo instruct abierto y cuantizado en 4 bits, por ejemplo **Qwen3 4B u 8B** (Apache 2.0), de unos 2 a 5 GB. Se descarga una vez y es opcional, como el alineador.
  - Corre en **proceso aparte**, como `--separar`, para no bloquear la interfaz y liberar memoria al terminar.
  - Transcripciones largas: resumen por tramos (resumir bloques y luego el conjunto), y chat recuperando fragmentos con el índice FTS5 de M1.
  - Opcional, según la decisión 6.1: aceptar un endpoint local compatible con OpenAI (Ollama o LM Studio en `localhost`) para quien ya tenga uno.
- **Paridad para agentes:**
  ```sh
  transcribir resumir ID [--prompt acta] [--json]
  transcribir preguntar ID "¿Qué fechas se acordaron?"
  transcribir prompts                     # lista y gestiona prompts
  ```
  Nota: un agente como Claude Code ya es un LLM y puede resumir con `transcribir texto ID`. El valor de M10 es para el usuario sin agente. Aun así se expone por CLI para mantener la paridad y porque el resultado se guarda en la biblioteca y se ve en la ventana.
- **Dependencias.** M1. Mejor con M6. Decisión 6.1.
- **Esfuerzo.** **L**
- **Riesgos:**
  - la calidad de un modelo de 4 a 8B en actas largas es menor que la de un modelo en la nube;
  - memoria en Macs de 8 GB (limitar a 4B o desactivar);
  - alucinaciones (mostrar siempre las citas de tiempo para verificar);
  - disco.
- **Criterios de aceptación:**
  - Una reunión de 60 minutos produce un acta con tareas y responsables en menos de 2 minutos en un M1 Pro de 16 GB.
  - Cada punto enlaza a su momento en el audio.
  - Funciona sin conexión tras la descarga.

#### M11 · Traducción local

- **Objetivo.** Traducir transcripciones y subtítulos a otro idioma conservando los tiempos.
- **Funciones que cubre:**
  - traducir el texto completo;
  - traducir `.srt` y `.vtt` bloque a bloque sin mover los tiempos;
  - subtítulos bilingües (dos líneas);
  - exportar la traducción en cualquier formato de M2.
- **Por qué importa.** Es Pro en MW y muy útil para clases y videos. Además es la base de los subtítulos traducidos en vivo (M12).
- **Enfoque técnico:**
  - Reutilizar el LLM local de M10 (Qwen3 traduce bien entre los idiomas principales), con prompts que respetan la numeración y el largo de cada bloque.
  - **Evitar modelos de traducción con licencia no comercial**, como NLLB-200 (CC BY-NC).
  - Guardar la traducción como variante dentro de la biblioteca.
- **Paridad para agentes:**
  ```sh
  transcribir traducir ID --a en [--formato srt,txt] [--bilingue]
  ```
- **Dependencias.** M10 y M1. M2 para los formatos.
- **Esfuerzo.** **M**
- **Riesgos:** calidad variable en idiomas poco comunes; bloques que se alargan al traducir (del inglés al español se alarga alrededor de un 20 %), lo que obliga a re-partir las líneas.
- **Criterios de aceptación:**
  - Un `.srt` de 45 minutos traducido del español al inglés conserva el número de bloques y los tiempos exactos.
  - Ninguna línea supera el máximo de caracteres configurado.

#### M12 · Transcripción y subtítulos en vivo

- **Objetivo.** Ver el texto mientras se habla: en una clase, una llamada o un video.
- **Funciones que cubre:**
  - transcripción en directo del micrófono o del sistema en una ventana flotante (subtítulos);
  - (con M11) traducción en vivo;
  - al terminar, la transcripción final de alta calidad entra en la biblioteca.
- **Por qué importa.** Según las reseñas, MW tiene subtítulos en vivo con traducción (sin verificar). Además sirve de accesibilidad para personas con pérdida auditiva.
- **Enfoque técnico:**
  - **mlx-qwen3-asr trae streaming** (`init_streaming`, `feed_audio`, `finish_streaming`, con caché y refinado de la cola del texto) y modo `--mic`.
  - Usar el 0.6B para el directo y, al terminar, pasar el 1.7B y el alineador por el archivo completo.
  - Ventana flotante con `NSPanel`, siempre encima y ajustable.
- **Paridad para agentes:**
  ```sh
  transcribir vivo [--fuente microfono|sistema] --json     # emite eventos de texto parcial y final
  transcribir detener
  ```
  Esto permite que un agente "escuche" una reunión en curso, siempre visible en la ventana.
- **Dependencias.** M7 (y M8 para el audio del sistema). M11 para la traducción.
- **Esfuerzo.** **L**
- **Riesgos:** latencia y consumo de GPU sostenido (batería); competir por la GPU con otra transcripción en cola (pausar la cola o avisar).
- **Criterios de aceptación:**
  - Retraso menor de 2 s entre la voz y el texto en un M1.
  - Una hora continua sin fugas de memoria.
  - La transcripción final aparece en la biblioteca con la calidad del 1.7B.

#### M13 · Automatización en macOS

- **Objetivo.** Que Transcribir encaje en Atajos, Raycast, Alfred, AppleScript y otros agentes, y que la carpeta vigilada funcione aunque la app esté cerrada.
- **Funciones que cubre:**
  - **esquema de URL** `transcribir://` (transcribir una ruta, abrir un ID, grabar);
  - **Atajos**: acciones de ejemplo `.shortcut` que usan "Ejecutar script de shell" con el CLI (funciona hoy, solo falta documentarlo y empaquetarlo);
  - **AppleScript** básico (diccionario `.sdef`);
  - **carpeta vigilada sin la app abierta** mediante un LaunchAgent de `launchd` con `WatchPaths` que llama al CLI y abre la app en segundo plano;
  - **adaptador MCP** opcional sobre el mismo socket;
  - exportar a un **vault de Obsidian** (es una carpeta: basta con un destino y Markdown de M2);
  - **webhook local** opcional (por ejemplo a n8n autoalojado).
- **Por qué importa.** Refuerza la identidad *agent first* y cubre las integraciones de MW sin mandar datos a terceros.
- **Enfoque técnico:**
  - URL: `CFBundleURLTypes` en el `plist` y un manejador de `NSAppleEventManager` para `kAEGetURL`, que PyObjC soporta.
  - AppleScript desde PyObjC es posible pero laborioso (Cocoa Scripting). Priorizar URL y Atajos.
  - **App Intents** (Siri, Spotlight, acciones nativas de Atajos) **solo existen en Swift**. Quedan fuera salvo que se acepte un componente Swift (decisión 6.6).
  - Adaptador MCP: un proceso pequeño que traduce las herramientas MCP a las peticiones JSON del socket, como ya prevé el README.
- **Paridad para agentes.** Por definición:
  ```sh
  transcribir vigilar --siempre si       # instala o quita el LaunchAgent
  transcribir mcp                        # arranca el adaptador MCP por stdio
  ```
- **Dependencias.** Ninguna fuerte. El Markdown depende de M2 y el MCP se beneficia de M1.
- **Esfuerzo.** **M** (**L** con AppleScript completo).
- **Riesgos:** los LaunchAgents se disparan de más con `WatchPaths` (hay que usar el estado de `vigia.py` para no repetir archivos); mantener el MCP y el CLI sincronizados (generar ambos desde una sola tabla de acciones).
- **Criterios de aceptación:**
  - Con la app cerrada, soltar un audio en la carpeta vigilada produce su transcripción.
  - Un atajo de ejemplo transcribe el archivo seleccionado en Finder.
  - `open "transcribir://abrir?id=12"` abre el visor.
  - Un cliente MCP puede listar, transcribir y leer.

#### M14 · Transcribir desde URLs

- **Objetivo.** Pegar un enlace de YouTube, de un podcast o de un archivo en la web y obtener la transcripción.
- **Funciones que cubre:**
  - campo "Pegar enlace" y arrastrar URLs;
  - descarga solo del audio;
  - entra en la cola como cualquier archivo;
  - metadatos (título, canal, fecha) en la biblioteca.
- **Por qué importa.** Es Pro en MW y muy pedido para clases y conferencias en video.
- **Enfoque técnico:**
  - **yt-dlp** (Unlicense) como paquete Python dentro de la app, pidiendo formatos de audio que AVFoundation lee directamente (`m4a`/AAC) para **no necesitar ffmpeg**.
  - URLs directas a archivos con `urllib`.
  - Mantener yt-dlp actualizable, porque YouTube cambia a menudo.
- **Paridad para agentes:**
  ```sh
  transcribir https://youtu.be/… --formato srt
  ```
- **Dependencias.** Decisión 6.3, porque rompe la regla "internet solo para modelos".
- **Esfuerzo.** **M**
- **Riesgos:**
  - legales y de términos de servicio (responsabilidad del usuario; mostrar aviso);
  - roturas frecuentes de yt-dlp;
  - videos con restricción de edad o geográfica, igual que en MW.
- **Criterios de aceptación:**
  - Un video público de YouTube de 20 minutos se transcribe sin ffmpeg.
  - Con conexión, pero con la función desactivada en Ajustes, la app no hace ninguna petición de red salvo las descargas de modelos.

#### M15 · Motores alternativos: Parakeet y Whisper

- **Objetivo.** Elegir el motor según la tarea: Qwen3-ASR para español (por defecto), **Parakeet** para velocidad máxima y **Whisper** para idiomas que Qwen no cubre.
- **Funciones que cubre:**
  - selector de motor por trabajo;
  - modelos descargables bajo demanda;
  - comparación de velocidad y precisión en la bienvenida.
- **Por qué importa.** MW presume de Parakeet ("un pódcast de 30 minutos en menos de 8 s") y de unos 100 idiomas.
- **Enfoque técnico:**
  - `parakeet-mlx` (Apache 2.0, sin verificar su madurez) y `mlx-whisper` (MIT), ambos sobre MLX, sin salir del stack.
  - Sus tiempos por palabra permiten reutilizar `formatos.py`, las personas y el SRT.
- **Paridad para agentes:**
  ```sh
  transcribir modelos [--json]
  transcribir modelos descargar parakeet
  transcribir audio.m4a --motor whisper
  ```
  Equivale a `mw models list` y `mw models select`.
- **Dependencias.** M1 (guardar qué motor se usó). Decisión 6.7.
- **Esfuerzo.** **L**
- **Riesgos:** más superficie que mantener, más disco y más opciones que confunden. Mitigación: ocultarlo en "Avanzado" y dejar Qwen3-ASR por defecto.
- **Criterios de aceptación:**
  - Los tres motores producen TXT y SRT con personas desde la ventana y el CLI.
  - Una tabla de pruebas propia en español e inglés documenta velocidad y error por palabra.

#### M16 · Interfaz en inglés

- **Objetivo.** Abrir la app a usuarios que no hablan español sin perder la voz propia en español.
- **Funciones que cubre:**
  - todos los textos de la interfaz, notificaciones, la guía para agentes y el README en inglés;
  - idioma según el sistema, con opción de forzarlo.
- **Por qué importa.** Amplía la audiencia. MW no tiene interfaz en español; nosotros no la tenemos en inglés.
- **Enfoque técnico:**
  - Extraer los textos a un catálogo (`gettext` o tablas `.strings` con `NSBundle.localizedStringForKey`).
  - El CLI mantiene los comandos en español y añade alias en inglés (`transcribe`, `status`), para no romper a los agentes existentes.
- **Paridad para agentes.** `transcribir guia --idioma en` y alias en inglés.
- **Dependencias.** Mejor al final, cuando la interfaz esté estable.
- **Esfuerzo.** **M**
- **Riesgos:** textos cortados en la interfaz (el inglés suele ser más corto, pero la maquetación es manual en AppKit); doble mantenimiento de textos.
- **Criterios de aceptación:** con el sistema en inglés, ningún texto visible queda en español, y los comandos antiguos siguen funcionando.

### 5.1 Resumen de prioridades

| # | Misión | Fase | Impacto | Esfuerzo | Depende de |
|---|---|---|---|---|---|
| M1 | Biblioteca e historial | 1 | Muy alto | M | — |
| M2 | Exportación completa | 1 | Alto | M | M1 (reexportar) |
| M3 | Hablantes con nombre | 1 | Alto | S–M | M1 |
| M4 | Calidad del texto e idiomas | 1 | Medio-alto | S | — |
| M5 | Distribución firmada | 1 | Alto (y prerrequisito) | S | Decisión 6.2 |
| M6 | Editor y reproductor sincronizado | 2 | Muy alto | L | M1 |
| M7 | Micrófono y barra de menús | 2 | Alto | M | M5 |
| M8 | Audio del sistema y reuniones | 2 | Muy alto | XL | M5, M7 |
| M9 | Dictado en cualquier app | 2 | Alto | L | M5, M7 |
| M10 | IA local | 3 | Alto | L | M1, decisión 6.1 |
| M11 | Traducción local | 3 | Medio | M | M10 |
| M12 | En vivo | 3 | Medio | L | M7 (M8) |
| M13 | Automatización macOS | 3 | Medio (alto para agentes) | M | — |
| M14 | URLs y YouTube | 3 | Medio | M | Decisión 6.3 |
| M15 | Parakeet y Whisper | 3 | Medio-bajo | L | M1, decisión 6.7 |
| M16 | Interfaz en inglés | 3 | Medio | M | — |

**Arranque sugerido.** M4 y M5 en paralelo (son pequeñas y M5 tiene espera de Apple). Después M1, M2 y M3. Con esa base, la Fase 2 empieza por M6.

---

## 6. Decisiones que debe tomar el usuario

| # | Decisión | Opciones | Recomendación |
|---|---|---|---|
| **6.1** | **IA: nube o local.** MW conecta con OpenAI, Anthropic, Gemini, etc. mediante claves de API. | a) Solo LLM local con MLX. b) Local más un endpoint compatible con OpenAI **solo en `localhost`** (Ollama, LM Studio). c) También APIs en la nube con clave propia. | **a + b.** La c rompe el principio "100 % local" y es justo lo que diferencia a Transcribir. Quien quiera la nube puede usar un agente sobre `transcribir texto`. |
| **6.2** | **Cuenta de Apple Developer** (99 USD al año) para Developer ID y notarización. | Pagarla o seguir con firma ad-hoc. | **Pagarla antes de la Fase 2.** Sin firma estable, los permisos de micrófono, audio del sistema y accesibilidad se vuelven frágiles, y el aviso de Gatekeeper frena a quien recibe la app. |
| **6.3** | **Uso de internet más allá de los modelos** (URLs de YouTube en M14; comprobar actualizaciones en M5). | Prohibido, opcional o activado por defecto. | **Opcional y desactivado por defecto**, con un interruptor visible "Permitir conexiones para URLs y actualizaciones" y el texto exacto de qué se conecta. |
| **6.4** | **Licencia.** Los principios dicen "de código abierto", pero `LICENSE` dice **"NO es software libre ni de código abierto"** (uso personal, sin redistribución). Los modelos y librerías sí son abiertos. | a) Mantener la licencia de uso personal y cambiar el discurso a "código visible y auditable". b) Publicar con licencia abierta (MIT, Apache 2.0, GPL-3.0). c) Código disponible con licencia no comercial. | **Decidir antes de publicar más.** Afecta a qué código de terceros podemos reutilizar: por ejemplo, MacParakeet es GPL-3.0 y no podemos copiar su código con la licencia actual. |
| **6.5** | **Versión mínima de macOS** para audio del sistema. | Mantener 14.0 y activar M8 solo en 14.2 o posterior, o subir el mínimo a 14.2 o 14.4. | **Mantener 14.0** y ofrecer M8 solo en 14.2 o posterior (o 14.4 si las pruebas lo exigen). |
| **6.6** | **¿Aceptamos componentes nativos pequeños (Swift o C)?** Hacen falta para Core Audio taps si PyObjC no llega, para App Intents y para un atajo global más robusto. | Solo Python o ayudantes compilados en `construir.sh`. | **Aceptar ayudantes pequeños** en proceso aparte (mismo patrón que `--separar`) cuando Python no llegue. La app sigue siendo Python y PyObjC. |
| **6.7** | **Más motores** (Parakeet, Whisper) frente a un único motor muy bien afinado. | Solo Qwen3-ASR o motores alternativos en "Avanzado". | Posponer a Fase 3 y **decidir con datos** (prueba propia en español). |
| **6.8** | **Reconocer voces conocidas** (huellas de voz guardadas: son datos biométricos). | Sí, con consentimiento por persona, o no. | Sí, **opcional**, local, con borrado fácil y sin activarse sola. |
| **6.9** | **Agentes que graban.** ¿Puede un agente iniciar el micrófono o el audio del sistema? | Nunca, con permiso explícito en Ajustes, o siempre. | **Solo con un ajuste explícito**, desactivado por defecto, y siempre con un indicador visible. |
| **6.10** | **Espacio en disco.** Con el LLM (2–5 GB) y otros motores, la app podría pedir más de 10 GB. | Descargas bajo demanda o modelos fijos. | Todo bajo demanda y con un panel "Modelos" para ver y borrar lo descargado (`transcribir modelos`). |

---

## 7. Lo que conscientemente no haremos

| No haremos | Por qué |
|---|---|
| **Transcripción en la nube** (Assistant, OpenAI, Groq, ElevenLabs, Deepgram, Gladia) | Contradice el principio 100 % local. Los propios documentos de MW desaconsejan su nube para datos sensibles. |
| **Integraciones que suben el texto a terceros** (Zapier, Make, Notion en la nube) | Mismo motivo. Se cubre con exportar a carpeta u Obsidian, un webhook **local** opcional, y agentes que ya saben usar esas APIs si el usuario lo decide. |
| **Versión para Mac Intel** | MLX solo corre en Apple Silicon. Mantener otro motor solo para Intel (whisper.cpp en CPU) duplicaría el trabajo para un parque de Macs cada vez menor. |
| **Mac App Store y suscripciones** | El *sandbox* complica instalar el comando en `~/.local/bin`, la Skill, los procesos aparte y la carpeta vigilada. py2app no es un camino cómodo para la tienda. La distribución directa notarizada (M5) basta. |
| **Bots que entran en la reunión** | Innecesarios: el audio se captura en el propio Mac (M8), igual que en MW ("No bots joining"). |
| **Grabar FaceTime** | macOS no lo permite, según los propios documentos de MW. |
| **App para iPhone y iPad** | Otro producto, otro stack (Swift). Fuera de alcance. |
| **MDM y licencias por volumen** | No hay modelo comercial ni clientes de empresa. Reconsiderar solo si cambia la licencia (6.4). |
| **Formatos Avid y DOTE** (por ahora) | Muy de nicho. Se revisará si alguien los pide. El JSON de M2 permite convertir a ellos. |
| **Modelos de traducción con licencia no comercial** (NLLB-200) | Incompatibles con un proyecto que quiere ser abierto. Usar modelos Apache o MIT. |
| **Telemetría o analíticas de uso** | No encaja con la promesa de privacidad. Para diagnóstico ya existe el registro local `~/Library/Logs/Transcribir.log`. |

---

## 8. Fuentes

Todas consultadas el **10 de septiembre de 2026**.

**Oficiales de MacWhisper y Good Snooze**

- Sitio oficial, planes, precio y funciones: https://macwhisper.com
- Gumroad (se genera con JavaScript; solo expone el precio de la opción gratuita): https://goodsnooze.gumroad.com/l/macwhisper
- Centro de ayuda (antes macwhisper.helpscoutdocs.com): https://docs.macwhisper.com/
  - CLI `mw`: https://docs.macwhisper.com/article/57-macwhisper-command-line-tool
  - Grabar reuniones: https://docs.macwhisper.com/article/30-record-meetings
  - Reconocimiento de hablantes: https://docs.macwhisper.com/article/32-automatic-speaker-recognition-in-macwhisper
  - Dictado: https://docs.macwhisper.com/article/14-how-to-use-the-dictation-feature
  - Prompts de dictado por app: https://docs.macwhisper.com/article/31-app-specific-dictation-prompts
  - Diferencias entre MacWhisper y Whisper Transcription: https://docs.macwhisper.com/article/40-macwhisper-whisper-transcription-difference
  - Licencias: https://docs.macwhisper.com/article/39-licensing
  - Transcripción por lotes: https://docs.macwhisper.com/article/19-batch-transcription
  - Global: https://docs.macwhisper.com/article/16-global
  - IA (ChatGPT): https://docs.macwhisper.com/article/7-how-to-use-chatgpt-in-macwhisper
  - Assistant: https://docs.macwhisper.com/article/22-assistant
  - Carpetas vigiladas: https://docs.macwhisper.com/article/35-automatically-transcribing-files-in-watch-folders
  - Integraciones: https://docs.macwhisper.com/article/53-integrating-macwhisper-with-other-services
  - YouTube: https://docs.macwhisper.com/article/51-how-to-transcribe-youtube-videos
  - WhisperKit: https://docs.macwhisper.com/article/29-switching-to-a-whisperkit-model
  - Buscar y reemplazar: https://docs.macwhisper.com/article/37-find-and-replace-in-transcriptions
  - Transcripción en la nube: https://docs.macwhisper.com/article/18-cloud-transcription
  - Varios idiomas en un archivo: https://docs.macwhisper.com/article/23-multiple-languages-in-a-file
  - Atajos de teclado: https://docs.macwhisper.com/article/28-keyboard-shortcuts
- Mac App Store, "Whisper Transcription": https://apps.apple.com/us/app/whisper-transcription/id1668083311

**Prensa y reseñas (2025–2026)**

- 9to5Mac, MacWhisper 14 (14 jul 2026): https://9to5mac.com/2026/07/14/macwhisper-14-launches-with-a-new-transcript-editor-faster-performance-more/
- 9to5Mac, CLI (23 abr 2026): https://9to5mac.com/2026/04/23/new-macwhisper-cli-lets-users-automate-ai-transcriptions-from-the-terminal/
- 9to5Mac, MacWhisper 12 y hablantes (18 mar 2025): https://9to5mac.com/2025/03/18/macwhisper-12-delivers-the-most-requested-feature-to-the-leading-ai-transcription-app/
- 9to5Mac, Parakeet (27 jun 2025): https://9to5mac.com/2025/06/27/macwhisper-13-supports-nvidia-parakeet-transcription-model/
- 9to5Mac, archivo de artículos: https://9to5mac.com/guides/macwhisper/
- Australian Apple News, Parakeet: https://australianapplenews.com/2025/06/30/macwhisper-gets-a-parakeet-powered-speed-boost/
- MacUpdate, versión 13.13 y requisitos: https://whisper-transcription.macupdate.com/
- Vowen, reseña (jul 2026, 64 €): https://vowen.ai/blog/macwhisper-review/
- Voibe, reseña (jun–jul 2026): https://www.getvoibe.com/resources/macwhisper-review/
- Voibe, precios (abr–jul 2026, 59 €): https://www.getvoibe.com/resources/macwhisper-pricing/
- LumeVoice, precios (jul 2026, 59 €): https://lumevoice.com/blog/macwhisper-pricing-2026/
- LumeVoice, reseña (latencia del dictado): https://lumevoice.com/blog/is-macwhisper-worth-it/
- Blazing Fast Transcription, requisitos (Intel y Apple Silicon): https://blazingfasttranscription.com/blog/macwhisper-review
- Fuente descartada por datos incoherentes con las oficiales: https://whipscribe.com/tools/macwhisper

**Referencias técnicas para las misiones**

- mlx-qwen3-asr (streaming, 30 idiomas y 22 dialectos, alineador, Apache 2.0): https://github.com/moona3k/mlx-qwen3-asr
- mlx-lm (LLM local en MLX, MIT): https://github.com/ml-explore/mlx-lm
- Core Audio taps, documentación de Apple: https://developer.apple.com/documentation/coreaudio/capturing-system-audio-with-core-audio-taps
- Core Audio taps, ejemplo de referencia: https://github.com/insidegui/AudioCap
- Core Audio taps, macOS 14.2: https://gist.github.com/sudara/34f00efad69a7e8ceafa078ea0f76f6f
- MacParakeet (referencia abierta, GPL-3.0: inspiración, no código): https://github.com/moona3k/macparakeet
- Formato DOTE: https://bigsoftvideo.github.io/DOTE/export.html

**Datos sin verificar (resumen)**

- El precio exacto en Gumroad: la página no se deja leer. Se toma el de macwhisper.com.
- Qué modelos incluye MW Free.
- Si el editor, el audio del sistema, la IA y los subtítulos en vivo son Free o Pro.
- Que Parakeet v3 multilingüe (con español) esté ya en MW.
- Si MW tiene Atajos, AppleScript o extensión de Raycast.
- Los "diccionarios propios" de MW.
- La frecuencia con que macOS 15 vuelve a pedir el permiso de grabación de pantalla.
- La madurez de `parakeet-mlx`.
- Que el Python empaquetado incluya FTS5 y que `NSAttributedString` genere DOCX aceptables. Se confirma al implementar.
