# Asistente Linux

Middleware conversacional de administracion visual para usuarios nuevos de Ubuntu/Linux. Traduce solicitudes en lenguaje natural a diagnosticos y acciones CLI guiadas, con interfaz grafica, seguridad adaptativa y auditoria local.

## Funciones principales

- Chat con Groq y tool calling para acciones del sistema.
- Herramientas para actualizar el sistema, abrir aplicaciones, buscar paquetes, leer/escribir archivos personales y gestionar servicios.
- Vistas graficas para usuarios nuevos: procesos, red, instalacion y actualizaciones con barras/progreso.
- Capa de seguridad para bloquear comandos destructivos y guiar acciones sensibles hacia confirmaciones graficas.
- Diagnosticos locales para sintomas como "mi maquina esta lenta" y "no tengo internet", con explicacion de los comandos equivalentes.
- Memoria conversacional y auditoria en SQLite: `~/.config/asistente-linux/assistant.db`.
- Cuatro tablas de auditoria: sesiones, mensajes, ejecuciones con `stdout`/`stderr`/codigo de salida y capturas de recursos.
- Panel visual con CPU, RAM, disco, red, paquetes y kernel.
- Voz con `pyttsx3` y reconocimiento offline con Vosk si hay modelo disponible.
- Carga diferida de voz para mantener el arranque por debajo del objetivo de 200 MB de RAM.

## Arquitectura

```text
src/gui/app.py             Ventana principal, chat, layout y coordinacion visual.
src/gui/visual_views.py    Vistas graficas para procesos, red, paquetes y actualizacion.
src/core/agent.py          Orquestador con LLM, system prompt y tool calling.
src/core/tools.py          Herramientas Linux llamadas por el agente.
src/core/security.py       Reglas de seguridad para comandos, sudo y rutas sensibles.
src/core/storage.py        SQLite: sesiones, mensajes, ejecuciones y capturas del sistema.
src/core/memory.py         Acceso a memoria SQLite y migracion del JSON anterior.
src/nlp/router.py          Enrutamiento unico y determinista entre acciones locales e IA.
src/nlp/processor.py       Ejecucion de la ruta local o delegacion al agente.
```

La filosofia del proyecto es priorizar acciones visuales y explicaciones claras para principiantes. La terminal queda como respaldo para casos avanzados o cuando Ubuntu necesita pedir permisos.

## Correspondencia con el concepto

- Traductor natural a CLI: el enrutador resuelve acciones conocidas y diagnosticos locales; el agente de IA cubre solicitudes que requieren razonamiento.
- Centro de Control: chat, estado en tiempo real, procesos, red, instalacion apt/Snap/Flatpak/.deb y actualizaciones.
- Seguridad adaptativa: riesgo bajo, medio, alto o critico; las acciones sensibles requieren confirmacion y las destructivas se bloquean.
- Persistencia y auditoria: SQLite registra `sessions`, `messages`, `tool_runs` y `system_snapshots`.

## Instalacion

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Edita `.env` y coloca tu clave. Groq queda como proveedor por defecto:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_tu_clave_aqui
GROQ_MODEL=openai/gpt-oss-20b
```

Para probar NVIDIA NIM/build.nvidia.com sin borrar Groq:

```env
LLM_PROVIDER=nvidia
NVIDIA_API_KEY=nvapi_tu_clave_aqui
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL=deepseek-ai/deepseek-v4-pro-0813
```

## Ejecutar

```bash
venv/bin/python main.py
```

Para abrir también la ventana independiente de la academia al iniciar:

```bash
bash run.sh --learn
```

## Academia: Aprende Linux

El acceso **Aprende Linux** abre una ventana propia; si ya está abierta la recupera.
Incluye seis cursos gratuitos de lectura y práctica: Linux desde cero, Domina la
terminal, Administra tu sistema, Redes y seguridad esencial, Git desde Linux y Docker
y contenedores. Cada curso contiene cinco módulos, quince lecciones y un examen con
**75 preguntas distintas**, cuatro opciones por pregunta y una explicación de la
respuesta correcta.

El catálogo permite buscar, filtrar por categoría o nivel, guardar cursos y continuar
el aprendizaje. Cada lección tiene ejemplos, una práctica y apuntes personales. La
academia también ofrece una biblioteca de ejemplos por curso, pruebas rápidas de diez
preguntas y una videoteca local para importar, reproducir y organizar videos de
aprendizaje. Los comandos se presentan como texto y no se ejecutan desde la academia.

Los exámenes se pueden pausar y retomar, permiten marcar preguntas para revisar y
requieren responder las 75 antes de entregar. Se aprueba con 53 aciertos. La corrección
incluye resultados por módulo, revisión de respuestas y los últimos diez intentos.
Completar todas las lecciones y aprobar permite descargar una constancia personal de
autoestudio en texto; no constituye una acreditación oficial.

El contenido funciona sin conexión. Los enlaces a manuales externos sí requieren
internet. En la aplicación, progreso, notas y exámenes se guardan mediante escritura
atómica en `~/.config/asistente-linux/learning.json`, incluso con el modo privado de
PyWebView. La vista previa en navegador usa almacenamiento local del navegador.

El dashboard incluye resumen animado de terminal, racha de aprendizaje, XP, reto
diario, hoja de comandos, terminal de práctica simulada, actividad de las últimas
16 semanas, ranking personal de cursos y agenda de estudio local. Los retos y la
agenda se guardan junto al progreso anterior. Cada lección completada suma 50 XP,
cada curso con examen aprobado 250 XP y cada reto diario resuelto 150 XP, una sola
vez por día. El mapa usa actividad registrada y los minutos de lectura son
estimados según las lecciones. La terminal de práctica no ejecuta comandos en el
sistema. Los efectos pueden desactivarse en Personalizar; también respetan la
preferencia de movimiento reducido del equipo.

Verificación de la academia:

```bash
node tests/academy.test.cjs
node tests/academy-dashboard.test.cjs
venv/bin/python -m pytest tests/test_academy.py -q
```

## Verificacion rapida

```bash
venv/bin/python test.py
venv/bin/python -m pytest tests/test_core.py -q
venv/bin/python -m py_compile main.py src/core/*.py src/gui/*.py src/nlp/*.py src/voice/*.py
```

## Enrutamiento local e IA

Las consultas de sensores y recursos, la apertura de aplicaciones y paneles, la red,
los procesos, las actualizaciones y el instalador visual se resuelven localmente. Las
preguntas explicativas, ambiguas o no reconocidas se envian a la IA. La interfaz marca
cada respuesta como `LOCAL`, `IA` o `SISTEMA` para mostrar el camino que realmente uso.

Las llamadas remotas tienen limites configurables en `.env` mediante
`LLM_REQUEST_TIMEOUT` y `LLM_TOTAL_TIMEOUT`; una falla de red ya no puede dejar el chat
esperando indefinidamente.
