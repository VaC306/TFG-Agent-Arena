# Agent Arena Local

Plataforma local para comparar modelos y prompts con entradas propias, archivos y datasets.
Primer hito: runner con herramientas, adaptadores simulado y Ollama, comparación
secuencial, SQLite, API/worker separados y exportación de resultados y trazas.

La interfaz Angular permite comparaciones personalizadas con Ollama o un simulador,
adjuntos de texto e imagen y datasets CSV/JSONL de hasta 100 casos.
Consulta [formato de datasets y evaluación](docs/datasets.md) y descarga los ejemplos
de `data/dataset-ejemplo.csv` y `data/dataset-ejemplo.jsonl`.

## Lanzar la aplicación completa (Windows / PowerShell)

Requisitos: **Python 3.11** y **Node.js 22.12 o posterior de la rama 22**.
Los siguientes comandos usan la ruta de esta instalación. Si clonas el repositorio en otro
directorio, cambia únicamente la ruta de `cd`.

### 1. Instalación inicial (una sola vez)

```powershell
cd "C:\Users\rishi\Desktop\UNI 2026\TFG"
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .
cd frontend
npm.cmd ci
```

### 2. Terminal 1 — API

```powershell
cd "C:\Users\rishi\Desktop\UNI 2026\TFG"
.\.venv\Scripts\python.exe -m uvicorn arena.api:app --host 127.0.0.1 --port 8000
```

### 3. Terminal 2 — worker

```powershell
cd "C:\Users\rishi\Desktop\UNI 2026\TFG"
.\.venv\Scripts\python.exe -m arena.cli worker
```

### 4. Terminal 3 — frontend Angular

```powershell
cd "C:\Users\rishi\Desktop\UNI 2026\TFG\frontend"
npm.cmd start
```

### 5. Abrir la app e iniciar sesión

Abre **[http://127.0.0.1:4200/](http://127.0.0.1:4200/)**. Crea una cuenta local
o entra en una existente. Mantén las tres terminales abiertas. Para detener la app,
pulsa **Ctrl+C en cada terminal**. No es necesario activar el entorno virtual: los
comandos ya llaman al Python de `.venv`. El simulador no necesita Ollama.

Cuenta de desarrollo solicitada para esta instalación: **usuario `test`, contraseña `test`**.
En otra instalación se crea explícitamente desde una cuarta terminal; no se crea sola:

```powershell
cd "C:\Users\rishi\Desktop\UNI 2026\TFG"
.\.venv\Scripts\python.exe -m arena.cli create-test-user
```

Esta excepción sirve solo para pruebas locales. El registro normal exige 10 caracteres
de contraseña. Si `test` ya existe con otra contraseña, el comando no la reemplaza.
La primera cuenta conserva los experimentos anteriores al sistema de perfiles.

Si la web abre pero las ejecuciones quedan en cola, falta el worker. Si no conecta con
el servidor, comprueba la terminal de la API. Si `npm` está bloqueado por PowerShell,
usa `npm.cmd`, como en estos ejemplos. Para inferencia real, inicia Ollama e instala
los modelos que quieras; el selector muestra los instalados y permite actualizar la lista.

## Demo desde terminal (sin interfaz)

Requisitos: Python 3.11 (verificado con 3.11.9). Ejecuta desde la raíz del repositorio.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m arena.cli demo --output experiments/mi-primera-comparacion
```

En Linux/macOS, sustituye `.\.venv\Scripts\python.exe` por `.venv/bin/python`.
El ejemplo no descarga modelos ni requiere Ollama. Crea 16 ejecuciones: cuatro
tareas de desarrollo, dos ramas y dos repeticiones. A y B usan prompts distintos
y el mismo identificador de modelo; el simulador solo interpreta una pauta de
orden del prompt y no mide la calidad de un LLM.

La salida contiene `metrics.csv`, `summary.json`, `snapshot.json`, `runs.json`
y `events.jsonl`. El directorio debe ser nuevo para no sobrescribir resultados.
Cada lanzamiento crea un experimento y ejecuciones con UUID nuevos. SQLite se
guarda en `runtime/arena.sqlite`; se cambia con `--db` antes del subcomando.

## API y worker independiente

En una terminal:

```powershell
.\.venv\Scripts\python.exe -m uvicorn arena.api:app --host 127.0.0.1 --port 8000
```

En otra:

```powershell
.\.venv\Scripts\python.exe -m arena.cli worker
```

Abre <http://127.0.0.1:8000/docs>. `POST /experiments` con
`{"config":"simulated"}` encola el preset. La API no ejecuta inferencias.
`GET /experiments/{id}` devuelve configuración y ejecuciones;
`GET /runs/{id}/events` permite inspeccionar trazas;
`GET /experiments/{id}/metrics.csv` exporta métricas, y
`POST /runs/{id}/cancel` solicita cancelación. La API requiere una sesión local:
inicia sesión desde la interfaz. Los clientes HTTP usan cookie de sesión y cabecera
`X-Arena-Request: 1` para escrituras. Mantén el bind en loopback. Los presets se editan en `configs/`; la API del
hito 1 se complementa con `POST /comparisons` para configuraciones personalizadas.

También se puede usar exclusivamente la CLI:

```powershell
.\.venv\Scripts\python.exe -m arena.cli submit --config configs/simulated.json
.\.venv\Scripts\python.exe -m arena.cli worker --once
.\.venv\Scripts\python.exe -m arena.cli status
.\.venv\Scripts\python.exe -m arena.cli export ID_DEL_EXPERIMENTO --output experiments/otra-exportacion
.\.venv\Scripts\python.exe -m arena.cli cancel ID_DE_EJECUCION
```

`--once` drena la cola disponible. Si otro worker tiene una ejecución activa,
termina sin competir con él. No lances `demo` contra una base en uso por otro
worker. Una interrupción normal del runner se registra; si el proceso se mata
abruptamente, el estado queda `running` y bloquea nuevos trabajos. Tras detener
todos los workers, ejecuta `arena.cli recover --workers-stopped`: conserva la
ejecución como `interrupted`, sin reintento automático. Encola un nuevo
experimento para repetir. La recuperación manual no debe usarse con un worker vivo.

## Interfaz Angular

La interfaz utiliza Angular 20, TypeScript, HTML y CSS propios. Permite lanzar los
presets simulado/Ollama, consultar las últimas 50 comparaciones, seguir el progreso,
comparar tasas de éxito y tiempos, filtrar por rama, inspeccionar trazas, cancelar
ejecuciones pendientes y descargar CSV. Los resultados proceden de SQLite; no se
incluyen métricas de demostración inventadas en el frontend.

La interfaz muestra indicadores de carga discretos en las solicitudes, formularios,
resultados y preparación de archivos. El indicador general evita parpadeos en
solicitudes rápidas y contempla operaciones simultáneas, errores y cancelaciones.
Los mensajes son accesibles y las animaciones respetan el movimiento reducido.

La pestaña **Modelos** conserva el último resultado completo por modelo, digest
y tipo de prueba, a partir de todo el historial de tu cuenta. Los resultados en
curso no reemplazan la ficha anterior. Puedes filtrar modelos reales o simulaciones,
seleccionar dos fichas y abrir su comparación original. La biblioteca advierte si
no coinciden los datos, prompts, parámetros, fase, código o condiciones registradas,
o si no se verificó la identidad del modelo. No mezcla cuentas ni elige un ganador.
Vaciar el historial también vacía esta biblioteca; las bases aisladas de benchmarks
no forman parte del historial de una cuenta.

Resultados distingue aciertos, respuestas incorrectas, formato inválido y errores
de ejecución. Muestra casos con referencia, respuestas evaluadas, ejecuciones
programadas y mediciones de tiempo. Las respuestas y referencias se ven lado a lado.
Puedes descargar CSV, informe legible Markdown y JSON reproducible; el tiempo
incluye preparación y carga, y no es una medida aislada de generación.

Con la API y el worker anteriores activos, abre una tercera terminal:

```powershell
cd frontend
npm ci
npm start
```

Abre <http://127.0.0.1:4200>. Se ha verificado con Node 22.16.0 y npm 10.9.2.
Las versiones exactas están fijadas en package.json y package-lock.json. No hace
falta instalar Angular CLI globalmente. `npm run build` genera el bundle estático
en `frontend/dist/arena/browser`.

El servidor de desarrollo reenvía `/api` a `http://127.0.0.1:8000` mediante
`frontend/proxy.conf.json`. Para otro puerto de backend, modifica ese destino.
La compilación de producción necesita un servidor estático con la misma regla
de proxy; todavía no se integra el frontend en Docker Compose.

Los presets del benchmark se editan en `configs/`. Las comparaciones personalizadas
permiten seleccionar modelos instalados, editar prompts y cargar entradas o datasets
desde la interfaz. El perfil recuerda modelos, prompts y parámetros, y cada cuenta
tiene su historial. Consulta [cuentas y conexiones](docs/perfiles.md).
Si los trabajos permanecen en cola, comprueba el worker:
la interfaz no lo arranca automáticamente. Aciertos/casos con referencia incluye
las ejecuciones programadas con evaluación habilitada, también errores y pendientes;
el resultado es provisional mientras queden pendientes. La calidad condicional
considera solo respuestas evaluadas. Los tiempos ausentes se muestran como «—».

## Comparación real con Ollama

El adaptador nativo se ha comprobado con `qwen2.5:3b` local y Ollama 0.40.3.
Consulta [los resultados y limitaciones de la prueba](docs/prueba-local-real.md).

1. Comprueba GPU/VRAM y memoria libre: `python -m arena.cli hardware` dentro del
   entorno virtual; `nvidia-smi` si el controlador lo permite.
2. Instala y arranca Ollama desde su [sitio oficial](https://ollama.com/).
3. Selecciona un modelo local que soporte herramientas y quepa en el equipo.
   `qwen2.5:3b` es el identificador inicial configurable, no una garantía de
   rendimiento. Para usarlo, descárgalo explícitamente con `ollama pull qwen2.5:3b`.
4. Revisa `configs/ollama.json`: mismo modelo A/B, prompts, contexto, temperatura,
   semilla y límites. Ejecuta:

```powershell
.\.venv\Scripts\python.exe -m arena.cli demo --config configs/ollama.json --output experiments/ollama-prueba-01
```

Se consultan `/api/version`, `/api/show` y `/api/tags`, registrando metadatos,
digest y cuantización. Si falla la conexión o falta el modelo, se guarda el fallo;
no se descarga nada ni se sustituye por el simulador. La semilla se envía cuando
está configurada, pero no garantiza determinismo. La política inicial no incluye
warmup y solicita `keep_alive=0` en cada llamada de las nuevas comparaciones.
Hay que fijar carga de fondo y política
de calentamiento antes de interpretar latencias.

En este entorno también está preparada la versión portátil oficial en `runtime/ollama`.
Para arrancarla de nuevo desde la raíz del proyecto, abre una terminal adicional:

```powershell
$env:OLLAMA_MODELS = Join-Path (Get-Location) 'runtime\ollama\models'
$env:OLLAMA_HOST = '127.0.0.1:11434'
.\runtime\ollama\bin\ollama.exe serve
```

Esta ruta solo existe después de descargar y extraer la distribución portátil;
los binarios y modelos de `runtime` no se incluyen en Git. Si utilizas la instalación
normal de Ollama, basta con `ollama serve`. Mantén también la API, Angular y el worker
en marcha para ejecutar comparaciones desde la interfaz.

## Datos, evaluación y métricas

Los datasets y fixtures de prueba versionados están en
[benchmarks/v1](benchmarks/v1/README.md). Incluyen desarrollo y evaluación,
diagnóstico de herramientas, manifiesto SHA-256 y comandos para ejecutar y
auditar comparaciones reales en una base aislada.

Hay ocho tareas JSONL: cuatro `dev` y cuatro `eval`. Las soluciones esperadas
permanecen fuera del historial del agente. Los pedidos se copian por rama.
Se consideran unidades no devueltas de pedidos `delivered` del mes solicitado;
pedidos devueltos por completo no aparecen en los IDs. Los importes son enteros
en céntimos. El evaluador comprueba JSON estricto, importe, conjunto de IDs sin
duplicados y herramientas permitidas, sin imponer una secuencia de llamadas.

Para comprobar el conjunto de evaluación con el simulador:

```powershell
.\.venv\Scripts\python.exe -m arena.cli demo --config configs/simulated-eval.json --output experiments/mi-evaluacion-simulada
```

| Campo CSV | Interpretación |
| --- | --- |
| success / format_ok | Corrección completa / cumplimiento del formato |
| agent_s / queue_s | Tiempo del runner, incluidos metadatos e instrumentación / espera desde encolado |
| input_tokens / output_tokens | Suma de contadores recibidos en todas las llamadas |
| server_tps | Tokens generados divididos por suma de `eval_duration` del servidor |
| agent_output_tps | Tokens generados divididos por tiempo total del runner |
| tool_calls / tool_s / tool_errors | Intentos de herramientas, duración acumulada y errores |
| status / error | Éxito, fallo, timeout, límite, cancelación o interrupción |
| usage_complete | Falso si faltan contadores; las sumas disponibles son parciales |

Los tokens y TPS del simulador son **sintéticos**. Un timeout HTTP no permite
conocer los tokens que pudo seguir generando el servidor; se marca el uso
incompleto y no se calcula TPS global. Cancelar la espera del cliente no garantiza
la parada inmediata de la inferencia en Ollama. Las muestras de RAM/GPU están en
los eventos, no son atribuciones de consumo GPU por agente. NVML es opcional
(`pip install "nvidia-ml-py==12.575.51"`); ausencia o incompatibilidad se marca
como no disponible. Se toman muestras al inicio y al final, no una serie continua.

El análisis empareja por tarea y repetición, conserva fallos en el denominador y
no analiza ejecuciones pendientes. Ofrece tasas de éxito y pares discordantes;
el test exacto de McNemar solo se calcula sin repeticiones y con discordancias.
No se tratan repeticiones de una tarea como observaciones independientes.

## Docker Compose

Se incluyen Dockerfile y Compose para API y worker con un volumen SQLite compartido:

```text
docker compose up --build
```

Configuración preparada, **no verificada en Docker** en este equipo. No incluye
Ollama ni descarga modelos. El preset Ollama de la API utiliza
`http://host.docker.internal:11434` mediante `ARENA_OLLAMA_URL`; la URL efectiva
se guarda en el snapshot. La accesibilidad de Ollama desde Docker depende de la
configuración de red del host. La ejecución nativa es la ruta verificada.

## Documentación y estado

- [Validación integral del 12 de octubre](docs/validacion-integral-2026-10-12.md): flujo aislado, métricas entre informes, recuperación y prueba pequeña con modelos reales.
- [Memoria académica](docs/memoria.md): alcance, arquitectura, metodología y resultados.
- [Decisiones](docs/decisiones.md): alternativas y justificación.
- [Protocolo de evaluación](docs/protocolo-evaluacion.md): criterios, comparaciones justas, fases y límites de reproducibilidad. Ejemplos de datasets en `data/examples/`.
- [Accesibilidad de la interfaz](docs/accesibilidad.md): comportamiento, verificaciones y revisión pendiente para WCAG 2.2 AA.
- [Resultados iniciales](experiments/simulated-dev-2026-10-08/summary.json): simulación previa a los últimos ajustes de robustez; se conserva.
- [Desarrollo, código final](experiments/simulated-dev-final-2026-10-08/summary.json): 16/16 ejecuciones simuladas correctas.
- [Evaluación, código final](experiments/simulated-eval-2026-10-08/summary.json): 8/8 ejecuciones simuladas correctas.

Validación nativa: 175 pruebas Python y 17 del frontend satisfactorias; `pip check`
correctos. Angular compila en producción. Se comprobó en navegador el lanzamiento,
actualización, cancelación, filtro, trazas y descarga CSV, además de la adaptación
a un viewport móvil de 390 px. TestClient emite una advertencia de deprecación de
Starlette/AnyIO; no afecta a los resultados de esta batería.

La comparación real con dos modelos y casos reservados está documentada en
[el diagnóstico reproducible](docs/diagnostico-herramientas.md). Pendientes:
ampliar y revisar independientemente los datasets, repetir con análisis por tarea,
monitorización periódica y shadow testing simultáneo. Angular con TypeScript,
HTML y CSS es la elección confirmada para el frontend; FastAPI y worker Python
se mantienen para el backend.
