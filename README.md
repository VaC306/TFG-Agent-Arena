# Agent Arena Local

Plataforma local para comparar dos prompts del mismo agente sobre pedidos ficticios.
Primer hito: runner con herramientas, adaptadores simulado y Ollama, comparación
secuencial, SQLite, API/worker separados y exportación de resultados y trazas.

## Inicio rápido (Windows / PowerShell)

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
`POST /runs/{id}/cancel` solicita cancelación. API local sin autenticación:
mantén el bind en loopback. Los presets se editan en `configs/`; la API del
hito 1 no incluye todavía un editor de configuraciones.

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

## Comparación real con Ollama

El adaptador nativo está implementado y su payload se prueba con HTTP simulado.
**Todavía no se ha validado con un modelo real.**

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
warmup y conserva el modelo cinco minutos. Hay que fijar carga de fondo y política
de calentamiento antes de interpretar latencias.

## Datos, evaluación y métricas

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

- [Memoria académica](docs/memoria.md): alcance, arquitectura, metodología y resultados.
- [Decisiones](docs/decisiones.md): alternativas y justificación.
- [Resultados iniciales](experiments/simulated-dev-2026-10-08/summary.json): simulación previa a los últimos ajustes de robustez; se conserva.
- [Desarrollo, código final](experiments/simulated-dev-final-2026-10-08/summary.json): 16/16 ejecuciones simuladas correctas.
- [Evaluación, código final](experiments/simulated-eval-2026-10-08/summary.json): 8/8 ejecuciones simuladas correctas.

Validación nativa: 42 pruebas satisfactorias, instalación editable y `pip check`
correctos. TestClient emite una advertencia de deprecación de Starlette/AnyIO;
no afecta a los resultados de esta batería.

Pendientes: validación real, interfaz de comparación, monitorización periódica
y shadow testing simultáneo. Angular con TypeScript es la recomendación para
la interfaz por la experiencia del equipo; la elección final está pendiente.
FastAPI y worker Python permanecen implementados; no hay frontend todavía.
