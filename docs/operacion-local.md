# Operación local y CLI

Todos los comandos se ejecutan desde la raíz del repositorio.

## Lanzador de desarrollo en Windows

```powershell
.\scripts\dev.ps1
```

Comprueba dependencias y puertos, inicia la API, el worker y Angular en segundo
plano, espera a que la interfaz y el proxy respondan y abre el navegador habitual.
Mantén esta terminal abierta; `Ctrl+C` detiene únicamente los procesos que ha
iniciado el lanzador. El worker recibe una petición de parada cooperativa para
conservar una ejecución interrumpida y finalizar sus escrituras. No borra historial
ni recupera ejecuciones automáticamente.

La API y el worker comparten **`runtime/dev/arena.sqlite`** por defecto. Esta base
se conserva entre arranques y está separada de `runtime/arena.sqlite`, que usan los
comandos manuales. Crea una cuenta local en la base de desarrollo. Puedes usar el
simulador sin iniciar Ollama ni descargar modelos.

```powershell
# Primera instalación de dependencias y arranque (requiere acceso a la red).
# Instala antes Python 3.11 y Node 22.12 o posterior de la rama 22.
.\scripts\dev.ps1 -Setup

# Puertos propios; la configuración del proxy se genera para este arranque.
.\scripts\dev.ps1 -ApiPort 8010 -UiPort 4210

# Iniciar sin abrir otra pestaña del navegador.
.\scripts\dev.ps1 -NoBrowser

# Elegir una base distinta; las rutas relativas se resuelven desde el proyecto.
.\scripts\dev.ps1 -Database runtime\mi-desarrollo\arena.sqlite

# Comprobar arranque, proxy y worker y detenerlos al terminar.
.\scripts\dev.ps1 -Check
```

El lanzador rechaza puertos ocupados antes de crear servicios; permite escoger
otros y no detiene procesos ajenos. Cada arranque guarda logs independientes de
API, worker y frontend en `runtime/dev/sessions/<id>/`, junto al proxy usado.
Si falla una dependencia o un servicio, muestra una explicación y la ubicación
de sus logs. `-Setup` instala las dependencias fijadas del proyecto; no instala
Python, Node, Ollama ni modelos. El navegador se abre solo después de comprobar
que los servicios responden.

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
