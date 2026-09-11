<div align="center">

<img src="docs/icono.png" width="128" alt="Transcribir">

# 🎙️ Transcribir

**Convierte audio y video en texto, en tu Mac y sin internet.**

Arrastra tus reuniones, clases, entrevistas o notas de voz: se encolan, se
transcriben con un modelo de código abierto en la GPU del chip de Apple y cada
una termina como un `.txt` limpio o como subtítulos `.srt`.

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PyObjC](https://img.shields.io/badge/PyObjC-12-6E6E73?logo=apple&logoColor=white)](https://pyobjc.readthedocs.io/)
[![AppKit](https://img.shields.io/badge/AppKit-nativo-000000?logo=apple&logoColor=white)](https://developer.apple.com/documentation/appkit)
[![MLX](https://img.shields.io/badge/MLX-0.32-000000?logo=apple&logoColor=white)](https://github.com/ml-explore/mlx)
[![Qwen3-ASR](https://img.shields.io/badge/Qwen3--ASR-1.7B-615CED)](https://huggingface.co/Qwen/Qwen3-ASR-1.7B)
[![Sherpa-ONNX](https://img.shields.io/badge/Sherpa--ONNX-1.13-2E7D32)](https://github.com/k2-fsa/sherpa-onnx)
[![AVFoundation](https://img.shields.io/badge/AVFoundation-audio-1C1C1E?logo=apple&logoColor=white)](https://developer.apple.com/documentation/avfoundation)
[![py2app](https://img.shields.io/badge/py2app-0.28-FF6F00)](https://py2app.readthedocs.io/)
[![macOS](https://img.shields.io/badge/macOS-14%2B-000000?logo=apple&logoColor=white)](https://www.apple.com/macos/)
[![Apple Silicon](https://img.shields.io/badge/Apple_Silicon-arm64-555555?logo=apple&logoColor=white)](https://support.apple.com/en-us/116943)
[![Agentes](https://img.shields.io/badge/Agent_first-Claude_Code-D97757)](#-para-agentes)
[![Licencia](https://img.shields.io/badge/Licencia-Uso_personal-CC3333)](LICENSE)

<img src="docs/ventana.png" width="400" alt="Ventana de Transcribir">

</div>

---

## 🎧 El problema

Transcribir bien suele obligar a elegir entre dos males: subir tus audios a un
servicio en la nube, o conformarte con un modelo local lento y menos preciso.

Los modelos abiertos de 2026 ya compiten con los de pago, pero correrlos a mano
es otro asunto: entornos de Python, `ffmpeg`, descargas de varios gigas, y
ninguna forma cómoda de encolar diez archivos y olvidarte.

Transcribir empaqueta el mejor modelo abierto para español que corre bien en un
Mac en una app nativa que se usa arrastrando archivos. En pruebas públicas,
**Qwen3-ASR 1.7B** comete menos errores que Whisper large-v3 en español (3,35 %
frente a 4,08 % de error por palabra en FLEURS, según el informe técnico de
Qwen) y, acelerado con MLX, transcribe varias veces más rápido que la duración
del audio.

## ✨ Qué hace

- **Cola por arrastrar y soltar**: `.m4a`, `.mp4`, `.mp3`, `.wav` y `.mov`, uno
  tras otro, con progreso y opción de **cancelar** el que está en curso.
- **Terminados** con **Mostrar en Finder**, y un botón para limpiar la lista sin
  borrar ningún archivo.
- **Tres formatos**: párrafos limpios, párrafos con marcas de tiempo `[mm:ss]` o
  subtítulos `.srt` con tiempos por palabra.
- **Separar por persona**: marca quién habla —«Persona 1:», «Persona 2:»— en
  reuniones, entrevistas o llamadas. Se combina con cualquier formato.
- **Vocabulario propio**: nombres, siglas y términos que el modelo debe escribir
  bien. Es lo que más mejora la precisión con nombres propios.
- **Carpeta vigilada**: transcribe sola cada audio o video nuevo que llegue a una
  carpeta mientras la app está abierta.
- **Notificaciones** al terminar, con clic para ver el resultado en Finder.
- **Hecha para agentes**: Claude Code y compañía la usan con un comando, y lo que
  piden **aparece en la ventana con su nombre**.

## 📥 Descargar

En [**Releases**](https://github.com/JoseLuis0022/Transcribir/releases) hay un
`.dmg` de unos 50 MB con la app ya compilada. No hace falta Python, `ffmpeg` ni
nada más: se abre y se arrastra Transcribir a Applications.

Funciona en Macs con **chip Apple** (M1 en adelante) y **macOS 14 Sonoma o
posterior**. Compruébalo en  Menú Apple → Acerca de este Mac; con "Procesador
Intel" no sirve, porque MLX necesita la GPU del chip de Apple.

### La primera vez que la abras

macOS avisará de que *"Apple no pudo verificar que Transcribir no contenga
software malicioso"*. Sale con **cualquier** app que no venga de la App Store ni
esté firmada con una cuenta de desarrollador de pago; no significa que la app
tenga nada raro. El código está aquí para que lo compruebes.

**En macOS Sequoia (15) o posterior** — el clic derecho ya no funciona:

1. En el aviso, pulsa **Listo**.
2. Abre **Ajustes del Sistema → Privacidad y Seguridad**.
3. Baja hasta el apartado **Seguridad**: verás que se bloqueó Transcribir, con
   un botón **Abrir de todos modos**.
4. Púlsalo y autentícate con Touch ID o tu contraseña.
5. Vuelve a abrir Transcribir y pulsa **Abrir**.

**En macOS Sonoma (14)**:

1. Clic derecho sobre Transcribir en Applications → **Abrir**.
2. En el aviso, **Abrir** otra vez.

**Desde la terminal**, de un tirón:

```sh
xattr -dr com.apple.quarantine /Applications/Transcribir.app
```

Solo hace falta una vez. Después se abre con normalidad.

> **¿Por qué no está firmada?** Gatekeeper solo acepta apps firmadas con un
> certificado *Developer ID Application* y notarizadas por Apple, y ambas cosas
> exigen el Apple Developer Program, que cuesta 99 USD al año. Un certificado
> *Apple Development* gratuito no vale: sirve para ejecutar tus apps en tus
> propios equipos, no para distribuirlas.

### La bienvenida: el modelo se descarga una sola vez

<img src="docs/bienvenida.png" width="340" align="right" alt="Bienvenida de Transcribir">

Los modelos no viajan dentro de la app: pesan varios gigas. La primera vez,
Transcribir te deja elegir cuál quieres y lo descarga con su progreso:

| Modelo | Tamaño | Para qué |
|---|---|---|
| **Máxima precisión** (Qwen3-ASR 1.7B) | 4,4 GB | el texto final |
| **Rápida** (Qwen3-ASR 0.6B) | 1,9 GB | borradores, ~2× más rápida |

También pregunta si conectarla con agentes de IA. Es la **única vez que usa
internet**: después todo se procesa en tu Mac.

Lo que se necesita más adelante —el alineador de tiempos para `.srt` (1,8 GB) o
los modelos de separar por persona (33 MB)— se descarga solo la primera vez que
lo pides, y lo verás en la fila de la cola.

<br clear="right">

## 🤖 Para agentes

Transcribir es *agent first*: cualquier agente con terminal —Claude Code, Codex
y similares— la descubre, la usa y la configura por completo con el comando
`transcribir`. Y lo que pide un agente **aparece en la ventana** con su
etiqueta, para que veas en todo momento qué está haciendo.

```sh
transcribir reunion.m4a --texto          # transcribe, espera e imprime el texto
transcribir entrevista.m4a --personas    # quién dijo qué
transcribir clase.mp4 --formato srt      # subtítulos
transcribir *.m4a --no-esperar           # encola y sigue trabajando
transcribir estado --json                # cola, progreso, terminados y ajustes
transcribir cancelar --todo              # cancela lo que haya en cola
transcribir ajustes idioma auto          # cambia un ajuste (se ve en la app)
transcribir limpiar                      # vacía la lista de terminados
transcribir guia                         # la guía completa, pensada para agentes
```

Cada petición acepta opciones que solo valen para ella, sin tocar tus ajustes:
`--idioma es|en|auto`, `--formato parrafos|tiempos|srt`, `--precision alta|rapida`,
`--vocabulario "…"`, `--personas` y `--destino CARPETA | --junto`.

`transcribir estado --json` devuelve todo lo que un agente necesita para decidir:

```json
{
  "cola": [
    { "id": 1, "archivo": "/Users/ana/Entrevista con cliente.mp4",
      "estado": "transcribiendo", "progreso": 0.64, "cliente": "Claude Code" }
  ],
  "terminados": [
    { "id": 4, "archivo": "/Users/ana/Clase de marketing.m4a", "estado": "listo",
      "resultado": "/Users/ana/Desktop/Clase de marketing.txt", "cliente": null }
  ],
  "ajustes": { "idioma": "es", "precision": "alta", "formato": "parrafos", "personas": false },
  "abierta": true
}
```

Los códigos de salida permiten encadenarlo: **0** bien, **1** algún archivo
falló, **2** la app no está disponible y **3** cancelado.

### Cómo se conecta

En la bienvenida, o en **Ajustes › Agentes**, se instalan dos cosas:

- **El comando** en `~/.local/bin/transcribir`. Ejecuta el Python que va dentro
  de la app, así que no depende de nada instalado aparte. Si mueves la app, se
  pone al día solo la próxima vez que la abras.
- **Una Skill de Claude Code** en `~/.claude/skills/transcribir/`. Con ella,
  Claude Code sabe que Transcribir existe y la usa en cuanto le pides una
  transcripción, sin que tengas que explicarle nada.

Para otros agentes, **Ajustes › Agentes › Copiar guía** te da el texto para
pegar en su `AGENTS.md`.

Por dentro, el comando no transcribe: le entrega el trabajo a la app por un
socket Unix local (`~/Library/Application Support/Transcribir/transcribir.sock`)
y va recibiendo los eventos. Si la app está cerrada, la abre en segundo plano
**sin robarte el foco**. Así la cola es una sola, la ventana siempre refleja lo
que pasa y un agente puede cancelar o cambiar ajustes igual que tú.

> **¿Por qué comando + Skill y no MCP?** Para agentes de terminal, un comando
> gasta muchos menos tokens que un servidor MCP y la Skill hace que Claude Code
> lo descubra solo. MCP brilla en apps de chat, y los *App Intents* de Apple
> (Siri, Apple Intelligence) solo existen en Swift. Como todo pasa por el mismo
> socket, añadir un adaptador MCP no requiere tocar la app.

## 👥 Separar por persona

<img src="docs/ajustes.png" width="360" align="right" alt="Ajustes de Transcribir">

Activa **Separar por persona** en Ajustes, o pasa `--personas`, y el resultado
sale por intervenciones:

```
Persona 1: Buenas tardes, gracias por venir. Hoy quiero hablar del
presupuesto del proyecto y de las fechas de entrega.

Persona 2: Claro, con gusto. Traigo los números del trimestre pasado y una
propuesta para reducir los costos de infraestructura.
```

Usa [Sherpa-ONNX](https://github.com/k2-fsa/sherpa-onnx) con la segmentación de
**pyannote 3.0** y huellas de voz **WeSpeaker ResNet34**, en ONNX: 33 MB de
modelos, sin cuentas ni PyTorch. Cada palabra, con su tiempo exacto del
alineador, se asigna a quien hablaba en ese momento.

¿Por qué no pyannote *community-1*, el de mejor fama? Porque añadiría ~1 GB
(PyTorch) y cada persona que reciba la app necesitaría su propia cuenta de
Hugging Face para aceptar sus condiciones, a cambio de muy poco:

| Error de diarización (DER) | pyannote 3.1 | community-1 |
|---|---|---|
| Reuniones AMI | 18,8 % | 17,0 % |
| Llamadas CALLHOME | 28,5 % | 26,7 % |
| VoxConverse | 11,2 % | 11,2 % |

Sherpa usa la misma segmentación que pyannote 3.1 y las mismas huellas de voz
que community-1. El salto grande solo lo da el modelo de pago *precision-2*, y
ese corre en la nube.

<br clear="right">

## ⚙️ Ajustes

Se abren con **⌘,** o desde el menú **Transcribir → Ajustes…**:

- **Transcripción**: idioma (español, inglés o automático), precisión (1.7B o
  rápida 0.6B) y vocabulario propio.
- **Resultado**: formato, separar por persona, dónde guardar (una carpeta o junto
  al archivo original) y qué hacer al terminar (nada, mostrar en Finder o abrir).
- **Carpeta vigilada**: activarla y elegir la carpeta.
- **Notificaciones**: al terminar cada archivo, al terminar la cola, si algo
  falla y con o sin sonido, más el estado del permiso del sistema.
- **Agentes**: instalar el comando y la Skill, y copiar la guía.

## 🔒 Privacidad

Todo el procesamiento ocurre en el Mac. La app solo se conecta a internet para
**descargar un modelo que falta**, de Hugging Face a
`~/Library/Application Support/Transcribir/Modelos`, y los carga siempre desde
esa carpeta local. Ningún audio ni texto sale de la computadora, y la telemetría
de Hugging Face está desactivada.

## 🚀 Compilar desde el código

Requiere un Mac con Apple Silicon, macOS 14 o posterior y
[uv](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/JoseLuis0022/Transcribir.git
cd Transcribir

uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt

.venv/bin/python transcribir/principal.py   # correr desde el código
./scripts/construir.sh                       # app completa en /Applications + comando y Skill
```

`construir.sh` genera el icono, empaqueta la app con py2app, la firma y la
instala en `/Applications`. Se niega a reconstruir si la app está a mitad de una
transcripción.

## 📦 Repartirla a otros

La app que sale de `construir.sh` es **autónoma**: lleva dentro Python 3.12,
MLX, Sherpa-ONNX y el resto del motor —unos 266 MB— y no conoce ninguna ruta del
Mac donde se construyó. Para dejarla lista para enviar:

```sh
./scripts/hacer-dmg.sh          # -> dist/Transcribir-1.1.dmg (~51 MB)
```

La imagen de disco trae la app, un acceso directo a Applications y un
`LÉEME primero.txt` con las instrucciones.

Dos límites conviene tenerlos claros:

**Gatekeeper.** La app va firmada ad-hoc, así que quien la reciba verá el aviso
de verificación la primera vez (ver [arriba](#la-primera-vez-que-la-abras)).
Evitarlo del todo requiere una cuenta de Apple Developer de pago.

**Arquitectura.** El bundle es `arm64` y MLX solo corre en chips de Apple: no
hay versión para Mac Intel.

## 🖥️ Stack técnico

| Capa | Tecnología |
|---|---|
| Lenguaje | [Python 3.12](https://www.python.org/) |
| Interfaz | [AppKit](https://developer.apple.com/documentation/appkit) nativo vía [PyObjC](https://pyobjc.readthedocs.io/) — `NSWindow`, `NSVisualEffectView`, `NSScrollView`, `NSSwitch`, `NSPopUpButton`, `NSProgressIndicator` |
| Animación | [Core Animation](https://developer.apple.com/documentation/quartzcore) — `CAGradientLayer`, `CABasicAnimation`, `CATransaction` |
| Reconocimiento de voz | [Qwen3-ASR](https://huggingface.co/Qwen/Qwen3-ASR-1.7B) 1.7B y 0.6B vía [mlx-qwen3-asr](https://github.com/moona3k/mlx-qwen3-asr), acelerado con [MLX](https://github.com/ml-explore/mlx) en la GPU |
| Tiempos por palabra | [Qwen3-ForcedAligner](https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B) |
| Separar por persona | [Sherpa-ONNX](https://github.com/k2-fsa/sherpa-onnx) — segmentación de pyannote 3.0 y huellas de voz WeSpeaker |
| Audio y video | [AVFoundation](https://developer.apple.com/documentation/avfoundation) (`AVAssetReader`) a PCM de 16 kHz, sin `ffmpeg` |
| Modelos | [huggingface_hub](https://github.com/huggingface/huggingface_hub): descarga única, carga siempre por ruta local |
| Notificaciones | [UserNotifications](https://developer.apple.com/documentation/usernotifications) |
| Agentes | Socket Unix con JSON por líneas, comando con `argparse` y [Skill de Claude Code](https://code.claude.com/docs/en/skills) |
| Iconografía | [SF Symbols](https://developer.apple.com/sf-symbols/) para la interfaz; el icono se dibuja por código con [Pillow](https://pillow.readthedocs.io/) y se exporta con `iconutil` |
| Preferencias | `NSUserDefaults`, con validación propia; el comando las cambia a través de la app |
| Empaquetado | [py2app](https://py2app.readthedocs.io/) para el bundle autónomo, `codesign` ad-hoc verificado y `hdiutil` para la imagen de disco |

**Diseño**: interfaz en español siguiendo las convenciones de macOS —materiales
translúcidos, esquinas continuas, tipografía del sistema y tarjetas agrupadas al
estilo de los Ajustes—, con un disco de estado que cambia de color (gris en
reposo, violeta mientras transcribe, verde al terminar) y el mismo lenguaje
visual que [Sereno](https://github.com/JoseLuis0022/sereno).

## 🏗️ Arquitectura

```
Transcribir/
├── transcribir/
│   ├── principal.py       # punto de entrada: la app, o el comando con --cli
│   ├── app.py             # ventana principal, cola, menús y delegado de la app
│   ├── bienvenida.py      # primera vez: elegir y descargar el modelo, conectar agentes
│   ├── ajustes.py         # ventana de Ajustes (⌘,)
│   ├── motor.py           # cola en segundo plano y transcripción
│   ├── audio.py           # lectura de audio y video con AVFoundation
│   ├── modelos.py         # dónde viven los modelos y cómo se descargan
│   ├── interlocutores.py  # separar por persona con Sherpa-ONNX
│   ├── formatos.py        # párrafos, tiempos, personas y subtítulos .srt
│   ├── preferencias.py    # ajustes: claves, valores por defecto y validación
│   ├── servidor.py        # socket local que atiende al comando
│   ├── cli.py             # el comando `transcribir`
│   ├── agentes.py         # guía, lanzador del comando y Skill de Claude Code
│   ├── avisos.py          # notificaciones del sistema
│   ├── vigia.py           # carpeta vigilada
│   ├── recursos.py        # recursos dentro de la app o junto al código
│   ├── identidad.py       # nombre, versión e identificador
│   ├── ui.py              # piezas de interfaz nativas
│   └── make_icon.py       # dibuja con Pillow el icono y los glifos
├── scripts/
│   ├── construir.sh       # app autónoma, instalada con su comando y su Skill
│   └── hacer-dmg.sh       # imagen de disco lista para repartir
├── setup.py               # empaquetado con py2app
└── LEEME-dmg.txt          # instrucciones para quien recibe el .dmg
```

```
agente ──> transcribir ──(socket, JSON por líneas)──> Transcribir.app ──> motor
                                                          │
                                        la ventana muestra el trabajo con la etiqueta del agente
```

La ventana y el comando son dos caras de la misma cola: el motor solo existe
dentro de la app, y todo —encolar, cancelar, cambiar ajustes— pasa por el hilo
principal. Por eso lo que hace un agente y lo que haces tú nunca se
desincronizan.

## 🔬 Notas técnicas

Cosas que cuestan una tarde de depuración si no las sabes:

**MLX busca su `mlx.metallib` junto a `libmlx.dylib`.** Y `mlx` es un paquete
sin `__init__.py`, que py2app no sabe copiar. `construir.sh` lo deja fuera del
empaquetado y lo copia intacto después, con sus librerías al lado
(`@loader_path`). Lo mismo con `sherpa_onnx`.

**El `python` que py2app deja en `Contents/MacOS` apunta al Python con que se
construyó.** Sirve en tu Mac y en ninguna otra. Por eso el comando lanza el
ejecutable principal de la app con `--cli`, que sí usa el Python de dentro.

**`HF_HUB_OFFLINE=1` bloquea también las descargas.** Para no tocar internet al
cargar y aun así poder descargar, la app pasa siempre la ruta local del modelo
(`Session(model=ruta)`), y el Hub solo se consulta al descargar.

**AppKit abre como documentos las rutas que recibe en `argv`.** Lanzar la app
con una carpeta como argumento la encola entera. Las pruebas pasan sus datos por
variables de entorno.

**El umbral por defecto de Sherpa (0,5) junta voces distintas.** Calibrado con
diálogos y monólogos, el rango bueno es 0,30–0,35: la app usa 0,33.

**Algunas librerías de Homebrew no se dejan firmar.** `liblzma` quedaba con un
formato que `codesign` rechaza, y una firma rota hace que macOS diga que la app
"está dañada". Como la app no usa `lzma`, se excluye, y la construcción verifica
la firma en modo estricto antes de dar nada por bueno.

**`NSColor.CGColor()` devuelve un puntero opaco si no importas `Quartz`**, y
Core Animation aborta al animar ese color. Un `import Quartz` basta (la misma
lección que en Sereno).

## 🙏 Créditos

- [Qwen3-ASR y Qwen3-ForcedAligner](https://huggingface.co/Qwen), del equipo Qwen de Alibaba (Apache 2.0).
- [mlx-qwen3-asr](https://github.com/moona3k/mlx-qwen3-asr), que los lleva a MLX.
- [MLX](https://github.com/ml-explore/mlx), de Apple (MIT).
- [Sherpa-ONNX](https://github.com/k2-fsa/sherpa-onnx), de k2-fsa (Apache 2.0).
- [pyannote segmentation 3.0](https://huggingface.co/pyannote/segmentation-3.0) (MIT) y [WeSpeaker](https://github.com/wenet-e2e/wespeaker).

## 📄 Licencia

Uso personal. Puedes descargarla, usarla en tus equipos y leer o modificar el
código para ti; no puedes redistribuirla ni usarla con fines comerciales sin
permiso. Los detalles, en [LICENSE](LICENSE).

No es software libre: el código está publicado para que puedas comprobar qué
hace tu Mac cuando la ejecutas. Los modelos y bibliotecas de terceros conservan
sus propias licencias.
