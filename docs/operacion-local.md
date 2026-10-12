# Operación local y CLI

Todos los comandos se ejecutan desde la raíz del repositorio.

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


## Cuenta de pruebas opcional

El registro normal se realiza desde Angular. Para una instalación de pruebas aislada:

```powershell
.\.venv\Scripts\python.exe -m arena.cli create-test-user
```

Crea explícitamente `test/test`; no sustituye una contraseña existente.
