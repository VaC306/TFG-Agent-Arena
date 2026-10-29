# Herramientas de análisis y fiabilidad

Implementación del 29 de octubre de 2026. Las tablas nuevas se crean de forma
aditiva al iniciar la API o el worker. No se reescriben snapshots, resultados ni
trazas anteriores. Reinicia API y worker para cargar el código nuevo; instala
`requirements.lock` para disponer del lector PDF.

## Encontrar los casos que explican una diferencia

Resultados permite buscar en ID, entrada y respuestas y filtrar por:

- A acierta y B falla, o B acierta y A falla.
- Respuestas distintas, formato inválido, timeout o error de ejecución.
- Respuestas completadas sin evaluación automática.

Los filtros solo cambian los casos visibles. Los resúmenes globales y las
exportaciones siguen describiendo todas las ejecuciones. Una respuesta distinta
no significa una respuesta incorrecta; los errores técnicos tampoco se convierten
en fallos de calidad.

## Revisión humana ciega

En Resultados abre **Revisión humana y comparación con una referencia anterior**.
Selecciona un caso y repetición con dos respuestas completas y entrada compartida.
La revisión abre un diálogo con las respuestas en orden aleatorio, sin las etiquetas
A/B ni sus modelos. Iníciala antes de consultar las respuestas identificadas.

La rúbrica `arena-human-v1` recoge corrección, claridad y utilidad, cada una de 1
(muy baja) a 5 (muy alta), preferencia global con empate y comentario opcional.
Todas las puntuaciones requieren una elección explícita. La correspondencia A/B
se revela después de guardar. La valoración cerrada es inmutable; para cambiar de
opinión se inicia otra revisión y se conservan ambas. Un reintento idéntico de
guardado devuelve la misma valoración.

Las revisiones pertenecen a la cuenta y se conservan al recargar. Se muestran
separadas de la evaluación automática; no modifican aciertos, resultados ni
snapshots. La anonimización afecta a la presentación: el contenido de una
respuesta podría identificar a su autor y el propietario puede consultar la
evidencia original. No se presenta esta función como un estudio ciego independiente
ni se calcula acuerdo entre evaluadores.

## Referencia anterior

En el mismo panel selecciona una comparación anterior o introduce su ID. El
contraste exige coincidencia de datos y referencias, código, protocolo, equipo y
dependencias, parámetros, repeticiones y condiciones registradas. Los modelos y
prompts pueden cambiar: esas son las variantes que se quieren examinar.

Solo se muestran mejoras o regresiones de calidad para parejas con puntuaciones
automáticas disponibles en ambas ejecuciones. Los demás casos se identifican sin
contraste de calidad. Si hay pendientes, entradas independientes, desviaciones
declaradas o diferencias incompatibles, se explican las razones y no se calculan
cambios. Los resultados son descriptivos, no una prueba de significación ni un
ranking general. Los proveedores remotos carecen de un digest verificable.

## Biblioteca personal y lotes

En Comparar abre **Biblioteca personal de datasets y prompts**. Guarda el dataset
normalizado o el prompt de A/B con nombre y etiquetas. Cada contenido distinto
bajo el mismo nombre y tipo crea una versión nueva, con SHA-256. Guardar el mismo
contenido devuelve la versión existente. Cargar una versión copia sus datos al
formulario y permite editarlos sin alterar la biblioteca ni experimentos anteriores.

En **Ejecutar varias configuraciones por lotes** añade copias de configuraciones
válidas. Cambia modelos, prompts o datos en el formulario para añadir otra variante.
El límite es diez configuraciones y 2.000 ejecuciones por lote. Cada comparación
mantiene un ID, snapshot y resultados propios. Todas se ejecutan mediante la cola
secuencial habitual. El alta del lote es transaccional: un error de creación revierte
los nuevos experimentos del lote. Las claves de envío permiten reintentar tras una
respuesta perdida sin duplicarlos.

El lote pendiente se conserva durante la visita, no después de recargar. Una vez
enviado, los experimentos se guardan en la base y aparecen en el historial.

## Historial y actualizaciones

El historial permite buscar por nombre o modelo y filtrar por motor, estado y
fechas. **Cargar más comparaciones** recupera páginas de 50; no elimina resultados
antiguos. Las fechas de la interfaz utilizan el horario del navegador.

La primera carga de la interfaz solicita una proyección compacta del snapshot.
El endpoint de detalle sigue ofreciendo el snapshot completo por defecto para
conservar compatibilidad. Mientras hay trabajo pendiente, la interfaz solicita
solo ejecuciones y resúmenes mediante `/experiments/{id}/progress`, sin reenviar
código fuente ni bytes de adjuntos. La biblioteca de resultados consulta ejecuciones
y anotaciones en bloque, con índices por experimento y estado.

## Diagnóstico previo y envíos sin duplicados

**Comprobar disponibilidad y contexto** revisa la configuración actual antes de
ejecutar. También se comprueba al enviar una comparación nueva o un lote. Para
Ollama consulta los modelos, visión y el contexto declarado. El presupuesto de
entrada se advierte con una estimación conservadora basada en caracteres: no es un
tokenizador ni garantiza ausencia de truncamiento. No se realiza inferencia de prueba
ni se descargan modelos. Para Codex se comprueba la vinculación y el catálogo.

Los envíos de comparaciones y presets admiten `request_id`. La base vincula esa
clave, por cuenta, con el hash del contenido y el ID creado. Un reintento idéntico
devuelve el ID existente; una misma clave con otro contenido se rechaza. La interfaz
conserva las claves inciertas, incluidas las de borradores personalizados recuperados.
Después de confirmar un envío, otra ejecución deliberada utiliza una clave nueva.

## Recuperar el worker

Cuando no hay señal reciente y tu cuenta conserva ejecuciones activas, el estado del
worker ofrece **Recuperar ejecuciones abandonadas**. Detén todos los workers de esa
base y marca la casilla correspondiente. La API exige ausencia de señales activas en
los últimos 60 segundos y que las ejecuciones tengan al menos 60 segundos.

La recuperación solo afecta a tu cuenta: marca las ejecuciones `running` como
`interrupted`, conserva sus eventos, registra el cierre y evita que una finalización
tardía sobrescriba ese estado. No reintenta ni vuelve a puntuar una respuesta. Los
trabajos en cola permanecen disponibles al reiniciar el worker. La señal temporal
no demuestra que un proceso haya muerto: detener los workers es un requisito.

## PDF de texto y streaming

Los adjuntos PDF admiten hasta 1 MiB y 20 páginas con texto extraíble. La interfaz
muestra el texto extraído antes del envío. El original y el texto utilizado se
conservan en el snapshot. Se rechazan PDF cifrados, dañados, sin texto o que excedan
los límites; la extracción se ejecuta en un proceso con tiempo máximo de diez
segundos y límites de contenido. No hay OCR ni interpretación visual del documento.
El texto conjunto de los adjuntos mantiene el límite de 20.000 caracteres.

Las comparaciones de texto sin herramientas con Ollama utilizan streaming. La
interfaz muestra fragmentos parciales mediante la actualización de progreso; no
mantiene una conexión SSE con el navegador. Se agrupan eventos de fragmentos para
evitar una escritura por token. La respuesta final conserva los contadores del
servidor. Los fragmentos de razonamiento privado no se registran.

`first_visible_token_s` mide el intervalo observado desde la petición de inferencia
hasta el primer fragmento de texto visible. No incluye preparación y calentamiento,
no mide razonamiento interno y no se inventa para otros adaptadores. Se conserva
en resultados y CSV. Los benchmarks con herramientas mantienen su transporte
anterior. Una interrupción conserva el texto parcial sin convertirlo en un acierto.

## Copias de seguridad y restauración

La CLI utiliza la API de backup de SQLite para crear una copia consistente, incluso
con WAL activo. Verifica integridad, referencias y tablas de Arena. Incluye toda la
base local: cuentas, experimentos, biblioteca y revisiones, no solo la cuenta activa.
No sobrescribe ningún archivo existente.

```powershell
.\.venv\Scripts\python.exe -m arena.cli --db runtime/dev/arena.sqlite backup --output runtime/backups/arena-2026-10-29.sqlite
.\.venv\Scripts\python.exe -m arena.cli restore --source runtime/backups/arena-2026-10-29.sqlite --output runtime/restored/arena.sqlite
```

La restauración crea una base nueva y elimina sesiones de navegador, vinculaciones
de proveedor y señales de procesos de la copia restaurada. Conserva las cuentas:
vuelve a iniciar sesión y vincula el proveedor si procede. Los trabajos que estaban
activos se conservan como evidencia pendiente de recuperación explícita; no se
asume que continuaron. Para usar la copia, configura `ARENA_DB` con la nueva ruta al
iniciar API y worker, o usa la opción de base de datos del lanzador local.

## Verificación

Las pruebas dedicadas están en `tests/test_workspace.py`,
`frontend/tests/workspace.test.cjs` y `frontend/e2e/research-tools.spec.ts`.
Comprueban aislamiento entre cuentas, idempotencia concurrente, rollback de lotes,
versiones inmutables, revisión sin identidad antes de guardar, comparación de
diseños, recuperación con cierre tardío, copia/restauración, PDF y streaming con
transporte controlado. Los recorridos de navegador cubren escritorio y móvil.
No implican una nueva evaluación real de capacidad de modelos.

Verificación final de esta implementación:

- Backend: 294 pruebas correctas.
- Frontend: 64 pruebas correctas; tipado E2E correcto.
- Repetición final de 18 recorridos afectados de navegador, en escritorio y móvil:
  correctos. Incluye navegación durante cargas, errores/cancelación, biblioteca,
  lotes, revisión humana, referencia anterior y flujo completo con campañas.
- Compilaciones de producción y demo: correctas. Pruebas de la demo en escritorio
  y móvil: correctas, incluido aislamiento de peticiones.
- Fiabilidad: 72 pruebas críticas correctas en cada uno de los tres órdenes y
  semillas del script del proyecto.
- Dependencias: `pip check` correcto. Se conserva un aviso de deprecación de
  Starlette/AnyIO que no afecta al resultado de las pruebas.

La pasada general inicial de navegador tuvo 73 de 76 recorridos correctos; dos
fallos correspondían a un interceptor que esperaba la URL anterior de detalle y
otro ocurrió durante recarga de desarrollo mientras se editaba el frontend. Tras
ajustar el interceptor y cerrar los cambios, la repetición de 18 recorridos cubrió
los tres casos y pasó. No se volvió a repetir la batería completa de 76 después.
