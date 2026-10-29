# Agent Arena Local — instrucciones del repositorio

Guía compartida para asistentes de código. Mantén aquí contexto duradero y reglas
específicas del proyecto; los detalles y la evidencia pertenecen a `docs/`, las
tareas a Trello y los cambios a Git. No es un historial de chats ni la memoria
personal de ChatGPT. Las instrucciones explícitas del usuario prevalecen.

## Proyecto y mapa del código

TFG de la UCM para comparar modelos y prompts con datos propios, conservando
condiciones, respuestas y trazas. La interfaz y documentación de usuario están en
español; sigue los nombres y convenciones existentes en el código.

- `arena/api.py`, `accounts.py`: API FastAPI, sesiones y aislamiento por cuenta.
- `arena/comparisons.py`, `scheduler.py`, `contracts.py`: validación, planificación
  y snapshots; `worker.py`, `runner.py`, `codex_runner.py`: ejecución independiente.
- `arena/store.py`, `database.py`: persistencia SQLite/PostgreSQL y adaptación SQL.
  `scripts/migrate_sqlite_postgres.py`: importación a un destino vacío.
- `arena/evaluator.py`, `protocol.py`, `model_results.py`, `task_analysis.py`:
  evaluación, comparabilidad y análisis; `workspace.py`: biblioteca, revisión y lotes.
- `frontend/src/app/`: Angular standalone con signals y servicios. La demo utiliza
  proveedores propios, incluido `demo-arena.service.ts`, y debe seguir aislada.
- `tests/`, `frontend/tests/`, `frontend/e2e/`: pruebas Python, Node y Playwright.
  `.github/workflows/tests.yml` define la batería de CI.

## Code Review Rules

- Conserva los snapshots y la evidencia histórica. Las referencias esperadas son
  del evaluador: no se envían al modelo. Las revisiones humanas se guardan aparte
  y no sobrescriben puntuaciones automáticas.
- Mantén una sola ejecución activa global en el modo secuencial, transacciones
  atómicas, idempotencia de envíos y cierre terminal que no pueda sobrescribirse
  con una finalización tardía. Recuperar exige detener workers; no añadas reintentos
  de inferencia transparentes que alteren el experimento.
- Distingue errores técnicos, cancelaciones, respuestas incorrectas y calidad sin
  evaluar. No conviertas métricas ausentes en cero ni agregues condiciones
  incompatibles. Simulación y pruebas controladas no demuestran calidad de modelos.
- Conserva la propiedad por cuenta en consultas, exportaciones y mutaciones.
  No registres credenciales, URLs de conexión con contraseña ni razonamiento
  privado del modelo. El esquema PostgreSQL `arena` no se expone a la Data API.
- Valida cambios de persistencia en ambos motores: revisa SQL, tipos, orden,
  conflictos y transacciones en `database.py`. Al añadir datos persistentes,
  comprueba también migración y restauración; no basta con que pasen en SQLite.
- Una nueva operación de `ArenaService` necesita su implementación estática en
  `DemoArenaService`; las escrituras de la demo se rechazan sin llamar a la API.
  Mantén contratos compatibles y los estados/filtros separados de las métricas.

## Entorno y operación

Entorno recomendado: Python 3.11 y Node 22. Las versiones admitidas y dependencias
están en `pyproject.toml`, `requirements*.lock` y `frontend/package.json`.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
npm.cmd --prefix frontend ci
.\scripts\dev.ps1
```

El lanzador usa `runtime/dev/arena.sqlite`; la CLI sin configuración utiliza
`runtime/arena.sqlite`. `ARENA_DATABASE_URL` selecciona PostgreSQL y prevalece sobre
`ARENA_DB`: API y worker deben apuntar al mismo destino. No imprimas sus valores
para diagnosticar. `runtime/`, `.env` y las bases locales están excluidos de Git.
No reinicies servicios del usuario ni migres datos reales como parte de una prueba.

## Validación proporcionada al cambio

Ejecuta las comprobaciones afectadas y amplía a la batería de CI cuando corresponda.
Para documentación sin cambios de comportamiento, verifica referencias y
`git diff --check`; no hace falta repetir inferencias ni toda la batería.

| Cambio | Comandos desde la raíz (PowerShell) |
| --- | --- |
| Backend | `.\.venv\Scripts\python.exe -m pytest -q` (o archivos afectados) |
| Lógica frontend | `npm.cmd --prefix frontend test` |
| Interfaz y tipado | `npm.cmd --prefix frontend run build` y `npm.cmd --prefix frontend run e2e:typecheck` |
| Recorrido real | `npm.cmd --prefix frontend run e2e -- research-tools.spec.ts` (elige los specs afectados) |
| Demo | `npm.cmd --prefix frontend run build:demo` y después `npm.cmd --prefix frontend run test:demo` |
| Cola, cancelación o medición | `.\.venv\Scripts\python.exe scripts/check_reliability.py` |

En Linux/macOS usa `.venv/bin/python` y `npm`. Playwright necesita Chromium:
`npm.cmd --prefix frontend run e2e:install` si aún no está instalado.

Las pruebas locales usan fixtures y bases desechables; las de Python bloquean HTTP
real. Usa el lanzador E2E del proyecto, que reserva puertos y aísla la base. No
edites el frontend mientras corre Playwright con `ng serve`: las recargas de
desarrollo pueden invalidar el recorrido. Las pruebas PostgreSQL son optativas y
requieren bases locales desechables según `tests/test_postgres_integration.py`;
nunca apuntes esas variables de prueba a Supabase real.

Informa qué se ejecutó, resultado y límites. Una prueba omitida o una CI iniciada
no equivale a una validación correcta; consulta el estado actual cuando sea relevante.

## Continuidad y trabajo en equipo

- Conserva cambios ajenos y revisa el remoto al publicar: este repositorio recibe
  trabajo concurrente. Integra conflictos preservando ambos trabajos; no fuerces
  el push. Commit, push y cambios externos siguen el alcance autorizado por el usuario.
- Tablero [TFG en Trello](https://trello.com/b/ML65yqYg/tfg): Pendiente → Preparado →
  En curso (máximo 2) → Revisión y pruebas → Hecho. Si gestionas una tarea, enlaza
  código y pruebas; no marques aceptación manual o despliegue sin evidencia.
- Actualiza esta guía solo si cambia una regla o un hecho duradero. Evita copiar
  contadores de pruebas, estados de CI, tareas temporales o instrucciones duplicadas
  para cada asistente. Añade guías por subdirectorio solo si necesitan reglas distintas.
- Consulta referencias por necesidad: [operación local](docs/operacion-local.md),
  [protocolo](docs/protocolo-evaluacion.md), [herramientas de investigación](docs/mejoras-investigacion.md),
  [Supabase](docs/supabase.md), [E2E](docs/pruebas-e2e.md),
  [demo](docs/demo-sites.md) y [conexión mediante Codex](docs/integracion-openai-suscripcion.md).
  `docs/decisiones.md` y `docs/memoria.md` contienen registros fechados: contrástalos
  con el código y la documentación específica antes de tratarlos como estado actual.

Convención: [AGENTS.md oficial](https://learn.chatgpt.com/docs/agent-configuration/agents-md).
