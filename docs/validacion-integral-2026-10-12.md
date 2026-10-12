# Validación integral — 12 de octubre de 2026

Se revisaron README, código y cambios pendientes antes de modificar la aplicación.
Se conservó el trabajo previo, el diseño minimalista y el historial real. No se
hicieron commits, pushes ni descargas de modelos.

## Entorno y evidencia

API de prueba en `127.0.0.1:8011`, Angular en `127.0.0.1:4201` y SQLite en
`runtime/session-audit/arena.sqlite`, con una cuenta de desarrollo independiente.
El worker se ejecutó con `--db runtime/session-audit/arena.sqlite worker --once`.
La cuenta y las comparaciones no pertenecen a `runtime/arena.sqlite`.

Los informes descargados desde el navegador se conservan sin modificaciones en
[experiments/local-flow-2026-10-12](../experiments/local-flow-2026-10-12/README.md).
Incluyen JSON con fuentes, configuración, entradas, referencias, resultados,
host, dependencias, hashes e identidades observadas. `manifest.json` identifica los
archivos de evidencia; `library.json` conserva las fichas consultadas.

## Comprobación real con modelos instalados

Experimento `eb7bbb1d-f303-4916-a8e8-36d82605af11`. Dataset existente:
`data/examples/respuestas-concretas.csv`, tres casos, una repetición, fase `dev`.
Ambas ramas usaron el prompt «Asistente general», temperatura 0, semilla 42,
contexto 2048, máximo de salida 64 y timeout de 120 segundos. Orden de las ramas
aleatorizado con semilla 42 dentro de cada caso; ejecución secuencial, sin warmup,
`keep_alive=0`. Servidor Ollama 0.40.3; modelos Q4_K_M; GPU local RTX 4060 Laptop.

| Métrica | A: qwen2.5:3b | B: qwen2.5:7b |
| --- | ---: | ---: |
| Ejecuciones / casos con referencia evaluable | 3 / 3 | 3 / 3 |
| Respuestas evaluadas | 3 | 3 |
| Aciertos | 2 | 3 |
| Incorrectas | 1 | 0 |
| Formatos inválidos / errores / pendientes | 0 / 0 / 0 | 0 / 0 / 0 |
| Tiempo medio del agente, 3 mediciones | 3,031826 s | 3,988071 s |

Digest A: `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`.
Digest B: `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`.
Datos SHA-256: `ac797c76fe08f99dc6f295a85a2c657a3e1f78e8db667124210fd2bffd639705`.

La única respuesta incorrecta fue `Paris` frente a la referencia `París`.
El criterio de texto exacto conserva acentos, mayúsculas y puntuación. Este
resultado muestra sensibilidad al criterio; no demuestra que 7b razone mejor.
Tres casos de desarrollo y una repetición no justifican un ganador ni una
generalización estadística. La latencia incluye metadatos y carga; el equipo no
estaba aislado. No se ha medido velocidad pura de generación.

El JSON identifica el código efectivo mediante las fuentes y sus hashes, además
del commit base y la marca de cambios pendientes. Algunas correcciones de esta
sesión son posteriores a esa inferencia: la evidencia conserva la versión que
realmente se ejecutó, sin reescribirla para presentar el código final como medido.

## Comprobaciones simuladas y controladas

Experimento UI simulado `0f74e176-f89d-4e9b-b79f-27346e9a2b74`: mismo CSV,
un modelo simulado, prompts distintos; seis ejecuciones, cinco respuestas
incorrectas y una cancelación intencionada de B antes de empezar. A: 0/3 aciertos,
3 evaluadas; B: 0/3 aciertos, 2 evaluadas y 1 error de ejecución. El simulador
devuelve un acuse de recepción; no debería acertar estas referencias y no mide
la calidad de un modelo real. La biblioteca permaneció vacía mientras las ramas
estaban pendientes y guardó una ficha completa al terminar.

La integración controlada reemplaza Ollama por un adaptador conocido y comprueba
respuestas correctas, incorrectas, JSON inválido, respuesta vacía, conexión fallida
y casos abiertos. Reconstruye los contadores de CSV y fichas por tipo de prueba y
los compara con resultados, protocolo, Markdown y JSON. Otra integración inicia
sesión, importa el CSV existente y verifica informes parciales tras cancelar.
Dos envíos HTTP concurrentes crean experimentos distintos; dos workers que
intentan reclamar a la vez reciben como máximo una ejecución activa.

## Recuperación y accesibilidad

| Escenario | Verificación y alcance |
| --- | --- |
| Inicio de sesión, configuración e importación | Navegador real, cuenta aislada, CSV versionado de tres casos |
| Ejecución, resultados, biblioteca y descargas | Navegador + worker real/simulado; CSV, Markdown y JSON descargados y auditados |
| API inaccesible | Se detuvo solo la API de prueba; aviso, carga terminada y comparación de fichas bloqueada; recarga y reintento recuperaron la sesión |
| Ollama detenido | Parada real del servidor portátil de esta sesión; aviso y envío deshabilitado; restauración de la lista |
| Timeout y cancelación en inferencia | Adaptadores lentos/controlados en pruebas Python; no se provocó un timeout ni se canceló una generación real |
| Cancelación en cola | Navegador real en la comparación simulada; se conserva resultado y estado |
| Solicitudes simultáneas | HTTP/TestClient con hilos y dos reclamaciones de worker; promesas diferidas de componentes e indicador global |
| Navegación y selección durante carga | Métodos reales de componentes con respuestas diferidas; respuesta antigua no sustituye selección nueva ni cambia la vista elegida |
| Recarga durante ejecución | Navegador real; mantiene sesión e historial, vuelve a Comparar y recupera resultados desde SQLite; entradas/dataset aún no enviados deben cargarse otra vez |
| Teclado y modales | Modal de configuración: foco inicial, Tab, Shift+Tab, Escape; foco en encabezado al navegar y Escape del historial |
| Móvil | Formulario/modal/resultados a 390 px; biblioteca e historial a 320 px, sin desbordamiento horizontal de página; tablas con scroll propio |
| Contraste | Inspección de colores y cálculo básico del texto visible de biblioteca: sin incumplimientos detectados; no es auditoría completa |
| Movimiento reducido | Revisión de CSS: animaciones, transiciones y scroll suave desactivados; falta prueba independiente con preferencia del sistema |

## Correcciones

- Un solo resumen para resultados, biblioteca e informe del protocolo: cancelaciones,
  límites, interrupciones y timeouts se clasifican como errores de ejecución;
  las mediciones negativas/no finitas y los tiempos de errores no entran en la media.
  Un fallo antiguo sin respuesta tampoco se presenta como calidad evaluada.
- CSV con categoría de resultado, referencia y referencia evaluable, configuración
  del agente, fase, repeticiones, orden, condiciones y hashes. Cabecera de descarga
  explícita. Markdown incluye evidencia de host, código y condiciones. JSON mantiene
  fuentes y entradas completas; el CSV protege celdas con posible fórmula, por lo
  que el contenido literal original se debe consultar en JSON.
- Biblioteca identifica qué difiere: datos/archivos, prompt, parámetros/límites,
  fase, repeticiones, código, evaluador, servidor, equipo/dependencias y orden.
  Las versiones de modelos se distinguen por digest; simulaciones e identidades
  sin verificar no se consideran una comparación directa de modelos.
- Inicialización no reemplaza una selección realizada durante la carga ni termina
  prematuramente su indicador; la biblioteca agrupa llamadas simultáneas de refresco.
  Destruir un editor de archivos libera su actividad y el bloqueo de lectura del
  formulario. Un fallo temporal de Ollama conserva los modelos elegidos.
- Las fuentes y hashes del snapshot proceden de una única lectura de bytes;
  se conservan los saltos CRLF para verificar exactamente las fuentes exportadas.

## Controles y repetición

Pruebas Python: 175 satisfactorias. Pruebas frontend: 17 satisfactorias.
Compilación Angular de producción y `pip check` correctos. Única advertencia
Python: alias obsoleto de Starlette/AnyIO en TestClient. Se observó un aviso
Angular NG0956 durante el cambio de opciones en desarrollo, sin fallo funcional.
Las pruebas de componentes usan dependencias Angular/HTTP sustituidas; no son una
batería automatizada de DOM Angular ni sustituyen la comprobación en navegador.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
cd frontend
npm.cmd test
npm.cmd run build
```

Para repetir el flujo manual usa una ruta SQLite **nueva** con `ARENA_DB` en la
API y `--db` en el worker; ambos deben apuntar a la misma base. Crea un proxy
Angular que reenvíe `/api` a esa API, eliminando el prefijo `/api`, y un puerto
frontend distinto del habitual. Inicia sesión con una cuenta de esa base,
importa el CSV, selecciona los dos modelos ya instalados e introduce los
parámetros anteriores. Guarda cada repetición en una carpeta nueva y consulta
el JSON para identificar exactamente los prompts y versiones observadas.

Pendiente para el TFG: ampliar/revisar independientemente datos de evaluación
reservados, analizar por tarea y repetir bajo condiciones de carga controladas.
Accesibilidad pendiente: lector de pantalla, zoom 200/400 %, espaciado, colores
forzados, preferencia real de movimiento reducido y respuestas/archivos grandes.
No se verificaron Docker ni otras máquinas. La reproducibilidad registra un
procedimiento y condiciones comprobables; no garantiza respuestas idénticas
en otro hardware, servidor o ejecución.
