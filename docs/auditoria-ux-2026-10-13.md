# Auditoría UX de Agent Arena Local

Fecha: 13 de octubre de 2026. Contexto: TFG de la Universidad Complutense de Madrid; pregunta experimental pendiente de decidir.

## Alcance y método

Revisión breve del README y arranque, seguida de tareas en un navegador real (navegador integrado de Codex). API en 8018 e interfaz en 4218; SQLite aislada en `C:\Users\rishi\AppData\Local\Temp\arena-ux-review-20261013\arena.sqlite`. Cuenta y archivos ficticios. Solo simulador; no se descargaron modelos ni se utilizó Ollama. No se borró historial ni se hizo commit/push.

Recorridos completados: registro, cierre de sesión, login incorrecto y correcto; comparación manual de prompts; cola sin worker y cancelación; arranque del worker; resultados y trazas; CSV válido de dos casos y CSV inválido con IDs duplicados; comparación de dos modelos con adjunto TXT compartido; biblioteca y selección de dos fichas; creación de campaña, repetición y anotación; exportaciones CSV, Markdown y JSON; perfil, guía y contacto; recarga, cambio de modo y viewport móvil de 390 × 844.

Se crearon cinco comparaciones (incluido un intento repetido), con 26 ejecuciones programadas, una cancelada. El benchmark simulado completó 16 ejecuciones con eventos de herramientas. El JSON exportado se pudo parsear y el Markdown contiene el diseño fijado. Esto verifica el circuito de la plataforma, no calidad o rendimiento de modelos reales.

Límites: no se verificaron modelos reales, cancelación durante inferencias largas, caída de servidor durante una petición, archivos grandes, lectura con lector de pantalla ni interacción táctil en un dispositivo físico. La demora inicial de una subida no se atribuye al producto porque el entorno de automatización puede intervenir. Los errores de localizadores de la herramienta no se cuentan como fallos de la aplicación.

## Valoración

La plataforma permite completar experimentos y conservar evidencia. Son buenas bases la validación que enfoca el campo obligatorio, la vista previa de datasets con número de ejecuciones, el seguimiento automático, la distinción entre evaluación y respuesta completada y las campañas con diseño fijado. El principal coste UX está en recuperar trabajo, interpretar estados coherentemente y encontrar la siguiente acción entre textos metodológicos y secciones extensas.

## Observaciones comprobadas

| ID | Sección y pasos | Observación e impacto | Cambio concreto propuesto |
| --- | --- | --- | --- |
| UX-01 | Comparar: escribir entrada A sin ejecutar y recargar | Se conserva nombre/modelos/prompts, pero desaparecen las entradas. El aviso sobre preferencias no equivale a un borrador recuperable. Riesgo de rehacer trabajo. | Borrador local por cuenta, estado explícito «Borrador guardado», recuperación tras recarga y descarte deliberado. Para adjuntos, comunicar cuándo hay que reseleccionar el archivo. |
| UX-02 | Modelos: abrir sección y recargar | Vuelve a Comparar; la URL permanece en `/` al cambiar de sección. No se recupera el contexto de navegación. | Rutas de sección y comparación, restaurar selección válida y permitir Atrás/Adelante. Mantener estados vacíos para IDs inexistentes. |
| UX-03 | Resultados: cancelar rama B en cola; abrir historial y campaña | La tabla dice «Cancelada», la tarjeta suma «1 errores de ejecución» y el historial dice «2/2 completadas». La ayuda afirma que las cancelaciones se muestran aparte. | Separar canceladas de errores; usar «finalizadas» para progreso terminal. Revisar consistencia en resultados, campañas, biblioteca e informes. |
| UX-04 | Comparar: modo inicial Un modelo, entradas manuales; después dataset | Manual requiere entradas A/B independientes; dataset comparte los casos. Comparar prompts exige duplicar entrada manual y leer advertencias. | Compartir datos por defecto al comparar prompts y ofrecer «Entradas independientes» como opción explícita. Mostrar «Cambia: prompt / modelo / datos» antes de ejecutar. |
| UX-05 | Resultados: comparación terminada; buscar respuestas | El bloque para crear campaña aparece antes de métricas y respuestas; respuestas plegadas y tabla repiten tareas/estados. Más desplazamiento para revisar el resultado. | Priorizar resumen y respuestas por caso en A/B; llevar «Crear campaña» a una acción secundaria; agrupar trazas y métricas detalladas bajo cada caso. |
| UX-06 | Campañas: crear desde comparación cancelada y repetir | Pantalla muy extensa, con varios bloques de advertencias e intervalos no disponibles, incluso en simulación y sin referencias. Dificulta reconocer lo accionable. | Resumen con intentos, pendientes y compatibilidad; pestañas/secciones «Intentos», «Por tarea», «Método». En simulación mostrar una razón breve y método desplegable. |
| UX-07 | Modelos: seleccionar dos fichas y filtrar por simulated-a | Pasa de 2/2 a 0/2 seleccionados. El filtro borra la selección, incluso la ficha que sigue visible. | Conservar selección independiente del filtro con chips removibles y aviso de seleccionados fuera del filtro. |
| UX-08 | Dataset: importar CSV con dos filas de ID repetido | Mensaje «Cada caso debe tener un id único» sin ID ni fila. Hay que buscar el conflicto manualmente. | Indicar ID, filas en conflicto y archivo; enlazar formato; conservar visible el error junto al selector. |
| UX-09 | Navegación a 887 px de ancho | Ancho de documento 908 px y botón Perfil parcialmente fuera de pantalla. Hay desplazamiento horizontal de toda la página. | Ajustar breakpoint y distribución de cabecera para conservar acceso a perfil e historial sin overflow global. |
| UX-10 | Navegación a 390 × 844 | Contacto ocupa una segunda fila; introducción y cabecera consumen buena parte del primer viewport. Las tarjetas pasan a una columna. | Reducir introducción móvil y trasladar Guía/Contacto a menú secundario. Mantener Comparar, Resultados, historial y perfil accesibles. |
| UX-11 | Traza: abrir y pulsar Escape | El panel de traza permanece abierto; la ayuda modal sí cierra con Escape y devuelve el foco. Los eventos muestran nombres técnicos en inglés y un mensaje «Cancelled before execution». | Definir la traza como panel no modal con Escape y retorno de foco; traducir estados y añadir resumen legible por paso, conservando JSON técnico desplegable. |
| UX-12 | Comparar: desplegar benchmark al final y ejecutarlo en simulación | El preset menciona qwen2.5:3b y los resultados usan ese nombre aunque la ejecución es simulada. El ejemplo inicial es difícil de descubrir. | Ofrecer «Probar ejemplo simulado» junto al inicio; mostrar «Simulador · preset de pedidos», distinguiendo modelo configurado de motor realmente utilizado. |
| UX-13 | Perfil y Campañas | Perfil muestra ChatGPT/Claude «Próximamente». El estado de worker está en Campañas, aunque se necesita al ejecutar desde Comparar. | Perfil centrado en cuenta/preferencias locales; conexiones futuras en información secundaria. Estado resumido de worker junto a Ejecutar y al progreso. |
| UX-14 | Campañas: guardar anotación de tipo Observación | Confirmación: «Anotación guardada. Las diferencias declaradas excluyen el intento…», pese a elegir una observación que conserva compatibilidad. | Confirmación específica: observación guardada sin exclusión, o diferencia guardada con efecto sobre compatibilidad. |

### Evidencias

Archivos en `runtime/ux-review-evidence/`:

- `cancelacion.jpg`: tarjeta B con un error y respuesta B cancelada.
- `historial.jpg`: historial con «completadas» para el intento que incluye cancelación.
- `movil.jpg`: cabecera y formulario a 390 px.
- `campana.jpg`: pantalla de campaña tras guardar una anotación.

![Cancelación contabilizada como error](../runtime/ux-review-evidence/cancelacion.jpg)

![Inicio en móvil](../runtime/ux-review-evidence/movil.jpg)

## Comportamientos que funcionaron

- Registro y login local; credenciales erróneas generan un mensaje claro.
- Ejecutar sin entrada enfoca Entrada A y muestra que es obligatoria.
- La cola se actualiza automáticamente y se puede cancelar conservando evidencia.
- Dataset válido muestra todos los casos, referencias y total de ejecuciones; inválido impide ejecutar.
- El adjunto TXT aparece identificado y se guarda con la comparación.
- Cambiar de dos modelos a uno y volver conserva la entrada compartida en la sesión.
- Ayuda: foco inicial en el título, Tab permanece dentro, Escape cierra y devuelve foco.
- A 390 px no se observó overflow global en Resultados; la tabla tiene desplazamiento propio.
- Biblioteca advierte incompatibilidades y no declara ganador.
- Campaña conserva origen e intentos; exportaciones y anotaciones funcionan.

## Backlog priorizado

Estimaciones orientativas de implementación y verificación para una persona familiarizada con el proyecto; no compromisos.

| Prioridad | IDs | Trabajo y beneficio | Esfuerzo | Criterios de aceptación | Estado |
| --- | --- | --- | --- | --- | --- |
| P1 | UX-03 | Estados coherentes: evitar confundir cancelación con fallo o éxito | 1–2 días | Una ejecución cancelada cuenta como finalizada y cancelada, no como error; tarjetas, historial, campañas, biblioteca e informes coinciden; no cambia su puntuación de calidad. | Corregido; ver segunda iteración |
| P1 | UX-01 | Recuperación de borradores: evitar pérdida de trabajo | 2–4 días | Recarga recupera texto/configuración de la cuenta; cuentas no comparten borrador; se puede descartar; adjuntos no recuperables se señalan. | Corregido; ver tercera iteración |
| P1 | UX-02 | Navegación y comparación en URL: volver y recuperar contexto | 2–4 días | Recarga abre sección/ID correctos; Atrás/Adelante funcionan; ID inválido tiene salida clara; no aparece información de otra cuenta. | Corregido; ver tercera iteración |
| P1 | UX-09 | Cabecera adaptable: acceso a todas las acciones | 0,5–1 día | A 390, 768, 887 y 1024 px no hay overflow global causado por cabecera; perfil/historial operables con teclado. | Corregido y verificado en navegador |
| P2 | UX-08, UX-14 | Mensajes específicos de dataset y anotación: corregir con certeza | 0,5–1 día | Duplicado indica ID/filas; confirmación distingue observación/diferencia; error conserva foco y contexto útil. | UX-14 y UX-08 corregidos; ver tercera iteración |
| P2 | UX-04 | Comparación de prompts con datos compartidos por defecto | 2–3 días | Entrada única para dos prompts; modo independiente explícito; resumen de variables que cambian; no pierde borrador al alternar. | Pendiente |
| P2 | UX-05, UX-06 | Resultados/campañas con información progresiva | 2–4 días | Primer bloque muestra estado y respuestas/métricas relevantes; detalles metodológicos accesibles sin repetición; acciones de campaña no retrasan lectura del resultado. | Pendiente |
| P2 | UX-07 | Selección de biblioteca persistente frente a filtros | 1 día | Cambiar filtro conserva selección; chips permiten quitar fichas ocultas; límite de dos y compatibilidad siguen claros. | Corregido; ver tercera iteración |
| P2 | UX-11 | Traza legible y salida por teclado | 1–2 días | Escape cierra y devuelve foco; resumen en español; eventos técnicos quedan disponibles; controles tienen nombres accesibles. | Corregido; ver tercera iteración |
| P3 | UX-10, UX-12, UX-13 | Inicio compacto, ejemplo visible y estado de worker contextual | 1–3 días | Ejemplo simulado descubrible antes de rellenar formulario; distingue simulador/modelo; worker visible junto a ejecución; móvil mantiene acceso a acciones principales. | Pendiente |

## Las tres primeras mejoras recomendadas

1. **Estados coherentes (UX-03).** Afecta directamente a cómo se interpreta la evidencia del TFG; requiere corregir una contradicción observada.
2. **Borradores (UX-01).** Evita rehacer entradas y perder preparación experimental antes de ejecutar.
3. **Rutas y recuperación de selección (UX-02).** Facilita volver a un resultado, alternar secciones y compartir una referencia dentro de la instalación local.

Para una primera iteración pequeña también son adecuados UX-09 y UX-14: tienen alcance acotado y resultado verificable.

## Hipótesis que requieren pruebas adicionales

- La ausencia de cancelación global podría resultar costosa con muchos casos; comprobar con trabajos largos y usuarios antes de decidir el diseño.
- El selector «Últimos 50» podría dificultar recuperar comparaciones antiguas; no se probaron más de cinco experimentos.
- Las cancelaciones durante inferencia, fallos de red y recargas con peticiones pendientes necesitan recorridos específicos; no se infiere su comportamiento del caso en cola.
- La selección y los paneles extensos podrían confundir a usuarios nuevos; validar con tareas de revisión de resultados, no solo inspección experta.

## Funciones nuevas para explorar (opcionales)

Estas propuestas no son condiciones para corregir los fallos anteriores ni presuponen una pregunta experimental definitiva.

- **Biblioteca local de datasets versionados.** Guardar nombre, hash y vista previa; seleccionar dataset al crear una prueba y localizar qué campañas lo usan. Evita importar repetidamente el mismo archivo.
- **Duplicar comparación como borrador.** Desde Resultados, cargar datos/prompts/condiciones y destacar lo cambiado antes de crear un experimento nuevo. Mantener el origen intacto.
- **Revisión humana ciega por caso.** Respuestas sin identidad A/B al puntuar con rúbrica simple, empate y comentario; revelar identidad después. Útil para respuestas abiertas, separada de evaluación automática.
- **Cuaderno experimental.** Campos opcionales de pregunta, objetivo, variables, observaciones y limitaciones; exportarlos con el informe. Permitir «exploración» mientras se decide la pregunta del TFG.
- **Comparador de cambios de diseño.** Antes de contrastar dos experimentos, mostrar diferencias de datos, prompts, modelo y parámetros en una tabla breve, con enlaces a evidencia.
- **Paquete de evidencia local.** Exportación ZIP con informe, CSV, snapshot y trazas seleccionadas, más un índice. No requiere cuentas externas.
- **Ejecutar solo casos seleccionados como experimento derivado.** Desde errores/incorrecciones, elegir casos y abrir un nuevo borrador; registrar procedencia y advertir que no representa el dataset completo.

Mantener el producto local y minimalista: priorizar recuperación y revisión de evidencia antes de proveedores externos, rankings globales o asistentes que elijan ganadores automáticamente.

## Registro de implementación y pruebas posteriores

### Primera iteración, 13 de octubre

Implementada después de guardar esta auditoría y recibir autorización para empezar a corregir.

- **UX-09 corregido:** entre 761 y 1024 px, la cabecera permite una segunda fila para las secciones. Perfil e historial permanecen en la primera. No se ocultan acciones ni se recorta la página para encubrir el desbordamiento.
- **UX-14 corregido:** la confirmación usa el tipo de anotación enviado, no una advertencia genérica. Observación: «Esta anotación no cambia la compatibilidad del intento»; diferencia: «Este intento queda excluido del análisis compatible».
- **UX-03 parcialmente corregido:** el historial usa «finalizadas» para el número de ejecuciones terminales. **Sigue pendiente** separar cancelaciones de errores en los resúmenes y exportaciones; no se han cambiado denominadores ni clasificación de métricas.

Verificación:

- `npm.cmd --prefix frontend test`: 30 tests existentes aprobados.
- `npm.cmd --prefix frontend run build`: compilación correcta.
- Navegador a 390, 768, 887, 1024 y 1280 px: ancho del documento 382, 760, 879, 1016 y 1272 px respectivamente (el espacio restante corresponde a la barra de desplazamiento). El borde derecho del perfil permanece dentro del viewport en todos ellos. A 887 px, antes era 908 px de documento y el perfil quedaba fuera.
- Observación guardada en intento 2: confirmación correcta y compatibilidad conservada. Diferencia ficticia guardada en intento 1: confirmación correcta y análisis con **1/2 intentos incluidos**, con motivo de exclusión visible.
- Historial: sus cinco entradas muestran «finalizadas»; Enter abre y Escape cierra devolviendo el foco al resumen.
- Worker detenido: Campañas muestra «Sin señal reciente del worker»; no se han ejecutado modelos reales.

Capturas posteriores: `runtime/ux-review-evidence/cabecera-corregida.jpg` y `runtime/ux-review-evidence/anotacion-corregida.jpg`.

### Nueva observación al continuar las pruebas

**UX-15 · Modelos, estado vacío por filtros.** Con solo resultados simulados, seleccionar «Modelos reales» muestra «No hay resultados para estos filtros», sin una acción directa para restablecerlos. La salida existe en el selector, pero obliga a descubrir qué filtro bloquea la lista. Propuesta opcional P3: botón «Restablecer filtros» junto al mensaje; conservar una indicación del filtro activo. Criterio: un clic vuelve a mostrar las fichas sin perder selección. Esfuerzo estimado: 0,5 día.

Las observaciones originales se mantienen como evidencia histórica. No se hizo commit/push ni se borraron datos; los nuevos registros pertenecen únicamente a la SQLite ficticia de la auditoría.

### Segunda iteración: cancelaciones separadas de errores

**UX-03 corregido.** `outcome()` devuelve `cancelled` para una ejecución cancelada, incluso si conserva un error técnico o una respuesta tardía. Los resúmenes añaden el contador `cancelled` y ya no lo suman a `execution_errors`. Las cancelaciones siguen siendo terminales para progreso, no respuestas evaluadas, y no aportan tiempos medios ni pares válidos de latencia. Los denominadores de casos programados con referencia se mantienen: cancelar no elimina un caso del plan experimental.

Resultados, biblioteca, evolución de campañas, análisis por tarea y series muestran canceladas por separado. El filtro «Con errores de ejecución» ya no incluye cancelaciones; se añade «Con cancelaciones». CSV por ejecución conserva `status=cancelled` y ahora `outcome=cancelled`; CSV de campaña y por tarea, JSON e informes incluyen el nuevo contador. La versión del análisis por tarea pasa a `arena-task-analysis-v3` para distinguir estas nuevas categorías; se siguen exportando fuentes y hashes.

No hay migración ni reescritura de resultados almacenados: los resúmenes se calculan a partir de estados existentes. Los archivos exportados previamente se conservan; una exportación nueva usa la clasificación corregida. Timeouts, límites, interrupciones y fallos técnicos siguen siendo errores de ejecución.

Verificación añadida:

- Casos de cancelación sin resultado, con motivo técnico y con respuesta tardía: sin puntuación ni tiempo medio.
- Recorrido API en SQLite temporal: consistencia entre resultados, protocolo, biblioteca, Markdown, CSV, campaña, análisis por tarea y JSON; cobertura cero y calidad sin evaluar en casos cancelados.
- Análisis de cambios entre intentos: cancelación y timeout son categorías distintas, sin imputar calidad.
- E2E de cancelación durante ejecución, con adaptador controlado y worker real: aprobado en Chromium escritorio y móvil (2 pruebas). Ningún modelo ni servidor Ollama interviene.
- Tests del frontend: 30 aprobados; compilación y comprobación TypeScript de E2E correctas.
- Suite completa del backend: 254 pruebas aprobadas. Se actualizaron dos expectativas antiguas que contabilizaban una cancelación como error. Solo queda un aviso de deprecación de Starlette/AnyIO, ajeno a esta corrección.
- Navegador manual sobre el intento ficticio original: rama B con **0 errores de ejecución y 1 cancelada**, tanto en Resultados como en evolución de campaña. Captura: `runtime/ux-review-evidence/cancelacion-corregida.jpg`.

El prompt de continuidad está en `docs/prompt-continuar-auditoria-ux.md`; prioriza borradores y navegación con contexto, preservando las correcciones y los cambios sin commit.


### Tercera iteración: borradores, navegación y revisión por teclado

Continuación del 13 de octubre de 2026. Se leyeron README y este registro antes de implementar. Se conservaron los cambios sin commit anteriores, incluidas las garantías de UX-03, UX-09 y UX-14. No se definió pregunta experimental, dominio, ranking ni método nuevo.

**UX-01 corregido y verificado.** Un borrador por cuenta en el almacenamiento local de este navegador conserva nombre, modos, modelos, prompts, parámetros, fase, evaluación, entradas A/B/compartida y referencias. Incluye el dataset ya validado y normalizado, aunque el selector de archivo esté vacío. El guardado local se realiza después de actualizar el campo, sin esperar al guardado remoto de preferencias. Se anuncia qué se guarda y cuándo falla el almacenamiento. Tras recargar o volver a entrar se ofrecen «Recuperar borrador» y «Descartar borrador»; el formulario espera esa decisión. Descartar elimina los datos preparados y mantiene las preferencias del formulario, como indica la confirmación.

Los adjuntos conservan solo sus nombres y su entrada de origen en el borrador, no sus bytes. Tras recuperar se pide reseleccionarlos o elegir «Omitir» para cada archivo. No se permite ejecutar una entrada que tenga adjuntos pendientes sin resolver. Los adjuntos disponibles siguen en memoria al cambiar de sección. El dataset normalizado no necesita reselección. Se utiliza una clave con el ID de cuenta y se comprueba también el propietario dentro del contenido; ninguna pantalla ofrece el borrador ajeno. Editar o descartar un borrador no modifica una comparación ejecutada.

**UX-02 corregido y verificado.** La sección y la selección de comparación se reflejan en rutas de fragmento, por ejemplo `#/results?comparison=<id>` o `#/models?comparison=<id>`. No requieren configurar rutas adicionales en el servidor local. Recarga y Atrás/Adelante recuperan contexto; la selección de la URL prevalece sobre el primer elemento del historial. Un ID inexistente o ajeno no muestra resultados: ofrece un mensaje, reintento, historial y «Volver a Comparar». El enlace de salto al contenido enfoca el área principal sin cambiar la ruta.

Se conservan las comprobaciones de versión de las peticiones: un resultado anterior no sustituye una selección nueva y navegar fuera de Resultados cierra la traza. Las validaciones de dataset posteriores al descarte o a la destrucción del formulario se ignoran. Las lecturas tardías de adjuntos no repueblan una entrada descartada. El interceptor comprueba la generación de sesión: un 401 de una petición antigua no cierra una sesión iniciada después. Si una creación termina tras navegar a otra sección, se actualiza el historial sin forzar el regreso a Resultados. El borrador registra un envío pendiente de confirmar y pide revisar el historial antes de repetir; recuperarlo nunca reenvía automáticamente la comparación.

Después de verificar los recorridos principales se completaron:

- **UX-08:** el error de importación incluye nombre del archivo, ID duplicado y líneas en conflicto; permanece junto al selector con `aria-invalid` y `aria-describedby`, y enlaza la ayuda de formato. En CSV con entradas multilínea se informa de las líneas físicas al final de cada registro; en JSONL se conserva la numeración aunque haya líneas vacías. El mensaje lo explica como líneas del archivo.
- **UX-07:** filtrar por modelo, ejecución o tipo conserva las fichas seleccionadas. Los botones con nombre de modelo y tipo permiten quitar fichas ocultas; se muestra cuántas están fuera del filtro. Se mantienen el límite de dos y las advertencias de compatibilidad, sin declarar ganador.
- **UX-11:** la traza es una sección no modal. Escape y «Cerrar traza» devuelven el foco al botón que la abrió; no se roba Escape a un diálogo abierto ni al historial. Los eventos y estados habituales tienen etiquetas y resúmenes en español. El JSON técnico original permanece en un desplegable independiente. Se traducen los mensajes conocidos de cancelación e interrupción sin reescribir la evidencia.

#### Criterios de aceptación comprobados

| Mejora | Recorrido y resultado observado |
| --- | --- |
| UX-01 | Texto, nombre, prompt personalizado y semilla 321 → adjuntos TXT → recarga → recuperación con Enter: se recuperan textos/configuración y aparece reselección. La ejecución se bloquea hasta omitir o reseleccionar; se probaron ambas acciones. Dataset en modo dos modelos, con dos casos → recarga → recuperación: conserva casos y referencias. Cuenta B no ve el borrador A; al volver a A recupera la última entrada. Descartar y recargar no ofrece el borrador eliminado. El snapshot de la comparación ya ejecutada es idéntico después de editar el siguiente borrador. |
| UX-02 | Crear dos comparaciones → Modelos → Guía → Atrás/Adelante → recarga → cambiar selección en historial: sección e ID coinciden. ID inexistente y de otra cuenta: mensaje y salida operables, sin mostrar título ni detalle ajenos. Una respuesta demorada no cambia la selección actual. |
| Sesión y peticiones | Dataset A demorado → cerrar sesión → registrar B → entregar respuesta 200 o 401 de A: no aparecen datos de A ni se cierra B; recarga de B no ofrece borrador ajeno. Creación guardada con respuesta de red perdida → recarga/recuperación: aviso de confirmación pendiente y una sola comparación en historial, sin envío automático. Descarte mientras valida dataset: la respuesta tardía no restaura el dataset ni recrea el borrador. |
| UX-08 | CSV con `repetido` en líneas 2 y 3: archivo, ID y filas visibles; ejecutar desactivado; enlace abre ayuda y Escape la cierra. Pruebas del parser añaden CSV multilínea y JSONL con línea vacía. |
| UX-07 | Dos fichas simuladas seleccionadas → filtrar por `simulated-a:latest`: 2/2 seleccionadas, una fuera del filtro y la visible marcada. Quitar la oculta deja 1/2. Filtrar por modelos reales conserva la selección oculta. |
| UX-11 | Abrir traza con Enter → título enfocado → Escape: panel cerrado y foco en el mismo botón. Repetido en Chromium de escritorio, móvil emulado y navegador integrado. Resumen de entrada en español y JSON técnico plegado comprobados visualmente. |

#### Entorno, pruebas y evidencias

- `npm.cmd --prefix frontend test`: **33 aprobadas**. Incluye fallo de almacenamiento local, comprobación de propietario y descarte durante validación pendiente.
- `npm.cmd --prefix frontend run build`: **correcta**, sin errores ni advertencias de presupuesto.
- `npm.cmd --prefix frontend run e2e:typecheck`: **correcta**.
- `.venv/Scripts/python.exe -m pytest -q`: **257 aprobadas**. Continúa el aviso de deprecación Starlette/AnyIO ya registrado; no se cambió la clasificación de cancelaciones.
- `npm.cmd --prefix frontend run e2e`: **32 aprobadas, 16 en escritorio y 16 en móvil**, en 2,1 minutos. La suite completa incluye cancelación durante ejecución con adaptador controlado, fallos, selección durante cargas, anotaciones, campañas y coherencia CSV/JSON/Markdown. Las expectativas antiguas de borrado de selección y regreso fijo a Comparar se actualizaron a los criterios de esta iteración. Los fallos iniciales de localizadores y del arnés se corrigieron antes de esta ejecución completa.
- Comprobación adicional de aceptación, tras ampliar las aserciones: **4 pruebas E2E aprobadas** (borrador y dataset en ambos viewports). Verifican explícitamente prompt personalizado, semilla 321, modo de dos modelos, omisión de un adjunto y reselección del otro. No hubo más cambios de implementación.
- Cada ejecución E2E asigna dos puertos propios y una SQLite nueva bajo `arena-e2e-*`. API y worker real comparten esa base; el simulador y `ControlledAdapter` evitan toda dependencia de Ollama o modelos descargados.
- Recorrido adicional en el navegador integrado: API/worker en **63356**, frontend en **63357**, SQLite nueva en `runtime/arena-e2e-ux-d6493c7e53d64111a84819ab9934ddf0/arena.sqlite`. Cuenta y entradas ficticias; recuperación, navegación, comparación simulada, traza con teclado y salida de ID inválido. A **390 × 844** el documento mide **382 px**, sin overflow global. El viewport se restableció y la pestaña temporal se cerró al terminar. Se detuvieron los servicios propios; la base ficticia aislada se conserva para poder revisar la evidencia.
- `git diff --check`: sin errores de espacios. No se hizo commit ni push; no se abrió ni modificó `runtime/arena.sqlite`, ni se borró historial real.

Capturas nuevas, en `runtime/ux-review-evidence/`: `borrador-recuperado-{chromium,mobile}.png`, `dataset-error-detallado-{chromium,mobile}.png`, `ruta-invalida-{chromium,mobile}.png`, `biblioteca-seleccion-{chromium,mobile}.png`, `borrador-movil-manual.png`, `traza-movil-manual.png` y `traza-resumen-espanol.png`. Son evidencia de datos ficticios; este directorio está excluido de Git.

![Borrador recuperado en móvil](../runtime/ux-review-evidence/borrador-movil-manual.png)

#### Límites y pendientes

El borrador pertenece a la cuenta **en este navegador y origen local**; no se sincroniza entre navegadores, equipos o puertos. Limpiar el almacenamiento del navegador lo elimina. Se conserva un borrador por cuenta; no se implementó resolución de ediciones simultáneas entre pestañas. El fallo de cuota/almacenamiento se verificó con una prueba controlada, no llenando el disco del usuario. La selección de biblioteca se conserva al filtrar durante la estancia en esa sección, no se promete persistencia tras recargar.

El aviso de envío sin confirmación no hace idempotente la creación: repetir deliberadamente puede crear otra comparación. Se probó una respuesta perdida después de guardar y la recuperación posterior, no un corte eléctrico del equipo ni todos los momentos posibles de recarga durante POST. No se verificaron modelos reales, lector de pantalla ni dispositivo táctil físico. El simulador y los sensores ficticios verifican el circuito, no calidad o rendimiento científico de modelos.

Siguen pendientes **UX-04, UX-05, UX-06, UX-10, UX-12 y UX-13**. UX-15 y las funciones nuevas continúan como propuestas opcionales; no se han convertido en requisitos ni en una metodología experimental. UX-03, UX-09 y UX-14 permanecen corregidos.


### Petición adicional: lanzador de desarrollo local

Añadidos `scripts/dev.ps1` y su worker con parada cooperativa, `scripts/dev_worker.py`. El comando inicia API, worker y Angular, genera un proxy para los puertos elegidos, espera a que respondan y abre el navegador habitual. Con `-NoBrowser` no abre otra ventana; `-Setup` instala las dependencias fijadas; `-Check` comprueba arranque y detiene sus servicios. Por defecto conserva datos de desarrollo en `runtime/dev/arena.sqlite`, separada de la base del arranque manual. README y operación local documentan comandos, logs, puertos y parada.

Verificación sobre una base ficticia explícita, `runtime/arena-e2e-launcher-35096e2485e34e02958e04f839d698a1/arena.sqlite`, con API **54843** e interfaz **54844**:

- Análisis sintáctico de PowerShell y compilación de Python: correctos.
- `-Check`: API, frontend, proxy y worker listos; parada cooperativa, señal `stopped` y ambos puertos liberados.
- Puerto ocupado por un listener de prueba: salida explicativa; no se creó la base solicitada ni se detuvo ese listener.
- Arranque con `-NoBrowser` y navegador integrado: registro ficticio, comparación simulada «Prueba del lanzador local», **2/2 finalizadas**, ambas `completed` sin evaluación de calidad. Esto confirma que API y worker comparten la base indicada. Captura: `runtime/ux-review-evidence/lanzador-comparacion.png`.
- Ctrl+C desde una terminal interactiva (PTY): se ejecutó la limpieza, el último worker registró `stopped` y los puertos quedaron libres. La terminación forzada del árbol desde una terminal sin PTY no permite asegurar limpieza; no equivale a la prueba de Ctrl+C interactivo.

La instalación `-Setup` no se repitió sobre dependencias ya instaladas ni se descargaron modelos. Se verificó la interfaz mediante el navegador integrado con `-NoBrowser`; no se comprobó visualmente el navegador predeterminado de Windows. Las bases ficticias se conservan, los servicios propios quedan detenidos y la base real continúa intacta.
