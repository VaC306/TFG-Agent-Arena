# Pruebas de fiabilidad y E2E

Las pruebas verifican la plataforma del TFG de la Universidad Complutense de
Madrid. No fijan todavía la pregunta experimental final ni miden modelos reales.

## Ejecutar

Tras instalar las dependencias del README, desde la raíz:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/check_reliability.py
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
npm.cmd --prefix frontend run e2e:typecheck
npm.cmd --prefix frontend run e2e:install
npm.cmd --prefix frontend run e2e
npm.cmd --prefix frontend run e2e:repeat
```

En Linux/macOS usa `.venv/bin/python` y `npm`. `ARENA_TEST_PYTHON` permite elegir
otro intérprete; sin esa variable se usa `.venv` si existe y después `python`.
Chromium se instala una vez. No se descarga ningún modelo.
Para un caso concreto: `npm.cmd --prefix frontend run e2e -- --project=chromium --grep Timeout`.

`check_reliability.py` crea tres intérpretes con pares orden/hash
17/1, 91/42 y 203/98765. Ejecuta los tests de worker, recursos, medición,
cancelación, cuentas y concurrencia. También se puede mezclar toda la suite con
`pytest -q --arena-order-seed=314`. Los tests Python bloquean HTTP real y cambian
`ARENA_DB` antes de importar la API. Los eventos y relojes controlados sincronizan
las carreras; se conservan deadlines reales y accesos concurrentes a SQLite.

## Aislamiento y ciclo de vida

`e2e/run.cjs` reserva dos puertos libres, los entrega a Playwright y rechaza
reutilizar servidores existentes. La API y Angular se enlazan solo a loopback.
Cada ejecución usa un directorio temporal `arena-e2e-*`, incluso si el entorno
contiene `ARENA_DB`, `ARENA_ROOT` o una URL de Ollama reales. Nunca se lee, migra ni
borra el historial de `runtime/arena.sqlite`.

La API FastAPI ejecuta el worker real en su lifespan. El adaptador controlado vive
solo en `frontend/e2e/server.py`: devuelve `hola` y contadores sintéticos,
`[fail]` lanza un error y `[block]` espera un evento sin respuesta. Así se ejercitan
la cancelación y el timeout reales del runner. La interfaz usa la opción Ollama
para probar descubrimiento e identidad, pero las respuestas y el digest son
fixtures; no interviene un servidor Ollama. La API y la persistencia no se
simulan en los flujos completos.
El sensor también es controlado y se identifica como tal en los informes:
el ciclo de vida del monitor y sus escrituras son reales, pero no se consulta
el driver de GPU del equipo. La instrumentación del host se prueba en Python.

Cada test tiene un contexto de navegador y una cuenta nueva. Una dirección
documental distinta por test/repetición a través del proxy local aísla también el
contador de intentos de autenticación; no se desactiva la protección en producción.
Playwright termina sus procesos. El lanzador elimina únicamente los archivos
SQLite conocidos y su propio directorio vacío al terminar, incluso tras fallos
de assertions. En Windows el servidor se termina forzosamente, por lo que la
limpieza del directorio pertenece al lanzador. Un cierre forzoso del lanzador o
del sistema puede dejar un directorio temporal; no afecta al historial real.

## Cobertura

Los archivos `*.spec.ts` ejecutan los mismos nueve escenarios en Chromium de
escritorio y con emulación Pixel 7:

- Registro, salida, acceso mediante teclado y persistencia de sesión al recargar.
- Modal nativo: foco inicial, Tab/Shift+Tab, Escape y restitución del foco.
- Importación CSV y JSONL, formato inválido, error de conexión y reimportación.
- Configuración, comparación A/B, resultado, biblioteca y cambio de filtros con
  eliminación de la selección anterior.
- Campaña desde resultado, repetición del diseño y anotación de condiciones.
- Descargas CSV, Markdown y JSON: estados, denominadores, tokens, tiempos,
  semilla, hashes, condiciones y anotaciones coherentes con la evidencia guardada.
- Cancelación durante inferencia, trazas conservadas y uso posterior del worker.
- Timeout real de un segundo y fallo del adaptador: calidad sin puntuar,
  errores separados y ausencia de indicadores de carga persistentes.
- API inaccesible, reintento, navegación durante cargas, respuestas tardías,
  cambio de comparación y recarga sin recuperar un resultado obsoleto.

Las rutas interceptadas en los casos de fallo abortan conexiones o retienen una
respuesta real hasta liberar una promesa; no sustituyen las respuestas de los
flujos completos. Se usan localizadores por rol/etiqueta, estados observables y
aserciones reintentables. No hay `waitForTimeout` ni pausas fijas.
Véanse [servidores de Playwright](https://playwright.dev/docs/test-webserver) y
[aserciones](https://playwright.dev/docs/test-assertions).

## CI y límites

Validación local del 13 de octubre de 2026 (Windows, Python 3.11 y Node 22):
249 tests Python; 72 tests críticos con cada uno de los tres pares de semillas;
30 tests de frontend; build Angular y tipos E2E; 54 E2E sin reintentos
(nueve escenarios × dos viewports × tres repeticiones). También pasó la suite
Python completa con orden 314. Starlette emite una advertencia de deprecación
de `BlockingPortal`, sin fallos de tests.
El equipo debe permanecer activo: suspenderlo invalida las comprobaciones de
deadlines reales. Los límites no se amplían ni se reintentan para ocultarlo.

GitHub Actions ejecuta Python, repeticiones de fiabilidad, tests de frontend,
build, comprobación TypeScript y tres repeticiones de ambos proyectos E2E.
No se reintentan automáticamente los fallos: una intermitencia hace fallar el job.
En fallos se guardan informe HTML y trazas durante siete días. Contienen datos
de fixtures, cuentas y cookies temporales; no se deben usar con datos reales.

Se prueban Chromium y emulación móvil, no un dispositivo físico, Firefox, WebKit
ni lectores de pantalla. El worker E2E comparte proceso con la API; el arranque
de la CLI independiente, múltiples workers y el aislamiento concurrente de
SQLite se cubren en Python. No se simula una caída abrupta del equipo ni se
garantiza recuperar automáticamente una ejecución interrumpida.

El determinismo de fixtures y sincronización de tests no implica reproducibilidad
de respuestas de modelos reales entre máquinas. Duraciones, recursos, UUID y
fechas varían: se contrasta su coherencia dentro de cada informe, no su igualdad
entre ejecuciones. Ollama real queda fuera de esta suite; cualquier comprobación
manual opcional se ejecuta por separado según `docs/diagnostico-herramientas.md`,
con modelos ya instalados y una base de datos propia de esa comprobación.
