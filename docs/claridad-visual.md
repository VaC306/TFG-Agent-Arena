# Interfaz y lectura visual

La interfaz se organiza en una vista breve y detalles que se abren cuando hacen
falta. Se mantienen la evidencia ejecutada, la navegación, los borradores por
cuenta y la apariencia Sistema / Claro / Oscuro.

## Preparar una comparación

1. Elige un modelo con dos prompts o dos modelos, el nombre y el motor.
2. **Datos de entrada**: escribe la entrada compartida o importa el dataset.
   Adjuntos, referencia opcional y vista previa de casos tienen desplegables
   propios. Entradas independientes conserva su advertencia visible.
3. **Variantes A/B**: elige los modelos y tipos de prompt. Las instrucciones
   completas se pueden editar en cada rama.
4. **Condiciones de ejecución**: abre este bloque para cambiar repeticiones,
   evaluación y, dentro de **Parámetros avanzados**, fase y parámetros. Son los
   mismos controles y valores previos.
5. **Revisar y ejecutar**: comprueba motor, datos, repeticiones, evaluación y
   variables que cambian antes de ejecutar. Los errores y los adjuntos que hay
   que reseleccionar permanecen visibles.

## Leer los resultados

El resumen muestra finalizadas, pendientes, errores de ejecución y canceladas.
La banda de progreso distingue los estados; finalizar no equivale a acertar.
Cada caso ofrece **Entrada de este caso** junto a sus respuestas. Lee el snapshot
ejecutado: una entrada compartida o entradas A/B separadas, sin recurrir al
borrador actual. Si la evidencia exportada no contiene una entrada, se indica
su ausencia. La cancelación terminal muestra «Sin evaluación: ejecución
cancelada»; el motivo original, si existe, sigue disponible.
Primero aparecen las respuestas A/B. Se muestran los tres primeros pares de
caso/repetición; el botón para ver todos indica el total y lleva el foco al primer
par recién revelado. Al reducir, el foco vuelve al primer par. No se eliminan ni
reescriben resultados.

Las dos barras de estados usan el total de ejecuciones programadas como
denominador. Separan correctas, incorrectas, formato inválido, error de ejecución,
cancelación, sin evaluar y pendientes. Las leyendas tienen nombres y números;
el gráfico expone el recuento completo mediante su nombre accesible. La fracción
de aciertos sobre casos con referencia y el número de respuestas evaluadas se
muestran por separado. Una respuesta sin referencia no se representa como fallo.

**Ver análisis de tiempos y métricas** abre los puntos A/B y las métricas
detalladas. Ambos puntos comparten una escala desde cero hasta el mayor tiempo
medio disponible. El tiempo procede del resumen guardado, incluye preparación
y puede incluir carga, calentamiento y muestreo. No es latencia pura de generación.
Una medición de cero se dibuja en cero; un valor ausente o sin respuestas medidas
se indica como «Sin mediciones» y no se dibuja. Se explican las condiciones y la
limitación de la ejecución secuencial, sin declarar ganadores.

## Biblioteca, campañas y trazas

La biblioteca incluye ocho gráficos de barras verticales: aciertos sobre ejecuciones con
referencia, cobertura de evaluación, errores, tiempo medio, P95, velocidad de
generación del servidor, tokens y coste estimado por ejecución. Se pueden mostrar
las fichas del filtro o solo las seleccionadas. Cada métrica comparte escala desde
cero entre las fichas; los porcentajes usan 0–100 %. La vista no mezcla resultados
ni declara ganadores si las condiciones difieren. Las simulaciones no representan
mediciones de modelos reales.

Los colores identifican el proveedor: OpenAI en turquesa, Ollama local en violeta
y simulaciones en ámbar, con variantes para claro y oscuro. Los modelos de un
mismo proveedor comparten color y mantienen sus nombres bajo las barras. Una
leyenda identifica los proveedores visibles. Al pasar el cursor, enfocar con Tab
o tocar una barra aparece su valor, muestras, tipo de prueba, variante, experimento,
fecha y fase. Escape cierra el detalle. El panel permanece visible al pasar el
cursor sobre él. Un cero conserva una marca en la base; los valores ausentes
usan un marcador discontinuo con «Sin datos», sin una altura que simule medición.
Con muchas fichas se desplaza el área de modelos dentro del gráfico.

La comparativa permite alternar **Gráficos/Tabla**, ordenar las fichas por nombre
o valores observados y elegir qué métricas mostrar. Las columnas de la tabla y el
CSV siguen la misma selección y orden. La tabla mantiene visibles las muestras y
permite abrir la evidencia de origen. **Descargar comparativa CSV** exporta las
fichas del ámbito mostrado, con unidades y tarifas asignadas; un dato ausente no
se convierte en cero. Los controles permanecen durante la visita a la biblioteca.
La [revisión de prácticas de otras herramientas](practicas-comparacion-2026-10-21.md)
documenta las fuentes y los límites de esta adaptación.

El P95 utiliza el rango más próximo sobre tiempos de respuestas sin error; la
velocidad muestra la media de tokens/s del servidor con uso completo. Se indica
el número de muestras. La ausencia de medidas aparece como «Sin datos», también
en exports antiguos que todavía no incluyen las nuevas métricas.

En **Configurar tarifas para estimar el coste** se introducen euros por hora de
ejecución o euros por millón de tokens de entrada y salida, por modelo y motor.
Las tarifas se mantienen mientras la vista esté abierta. La estimación por hora
usa la suma de tiempos registrados; la de tokens exige uso completo de todas las
ejecuciones. Ambas incluyen errores y cancelaciones con mediciones completas y
dividen por el número de ejecuciones programadas. Son costes asignados por el
usuario, no facturación ni precios de catálogo; los tokens son los de tarea y
excluyen el calentamiento. No incluyen tiempos de cola ni
inactividad del equipo. No se presupone que una suscripción o ejecución local sea
gratuita. Los valores cero explícitos se distinguen de los datos ausentes.

- **Biblioteca**: fichas compactas con tipo, fecha y distribución visual. Métricas,
  parámetros, identidad y evidencia completa están en «Ver métricas y condiciones».
  La selección se conserva frente a filtros; «Restablecer filtros» facilita salir
  de un resultado vacío. Las diferencias declaradas continúan visibles.
- **Campañas**: la evolución muestra, por intento, A y B en una escala fija
  de 0–100 % de aciertos sobre casos con referencia. Cada punto conserva sus
  recuentos; las ramas no se fusionan ni se calcula una clasificación. Solo se
  dibujan intentos completos, compatibles e incluidos por el análisis existente.
  Los excluidos y los parciales siguen en la lista con su razón, sin puntos;
  «Intentos» abre la tabla completa y las anotaciones. «Exportar evidencia» reúne
  las descargas. No se reconstruyen campañas en la demo sin evidencia exportada.
- **Trazas**: una secuencia numerada muestra los eventos realmente registrados.
  Cada paso se abre para consultar su explicación y su JSON. Los números indican
  orden de presentación; se conserva también el identificador original del evento.
  Escape cierra la traza y devuelve el foco al control de origen.

Los gráficos se construyen con HTML y CSS, sin librerías nuevas ni peticiones
adicionales. Las variantes local y demo comparten la presentación; la demo sigue
utilizando exclusivamente sus archivos estáticos. Se mantienen los cálculos,
clasificaciones, informes y condiciones del backend.

## Verificación

Las reglas de recuento, denominadores, valores ausentes y exclusiones están
cubiertas en `frontend/tests/visual-data.test.cjs`. Los recorridos de teclado,
orden visual, despliegue de casos, conservación del snapshot y exclusión de
intentos están en `frontend/e2e/visual-hierarchy.spec.ts`. Las suites anteriores
conservan sus aserciones y abren explícitamente los nuevos desplegables para
revisar tablas y exportaciones. No se han añadido reintentos.

Resultados de ejecución, capturas y límites: [registro de la auditoría UX](auditoria-ux-2026-10-13.md).

## Orientación para principiantes (20 de octubre de 2026)

El mapa **Entrada → A/B → Respuestas → Evaluación** representa el borrador actual.
Indica los datos compartidos o independientes, identidad de modelos (incluido el
alias `:latest`), igualdad exacta de prompts y parámetros comunes. Cada bloque
es un botón de teclado: abre los detalles necesarios y enfoca el campo que se
puede editar. Las respuestas del mapa son ejecuciones previstas, no resultados.
El modo de simulación se explica junto al mapa.

**Cómo empezar** es opcional. Describe el recorrido y abre el preset simulado de
pedidos como comparación separada mediante el flujo existente. No reemplaza ni
envía el formulario preparado. Texto, dataset y adjuntos se mantienen durante la
visita; tras recargar se aplica la recuperación del borrador por cuenta y la
reselección habitual de adjuntos. El ejemplo no se presenta como evidencia de
calidad o velocidad de modelos.

Las ayudas compartidas «Qué es…» definen modelo, prompt, dataset, referencia,
ejecución y campaña junto a sus controles. Cada explicación se abre a petición.
«Revisar y ejecutar» agrupa datos, variantes y condiciones y enlaza sus problemas
con el campo correspondiente. Reutiliza la función de validación del envío,
incluidos límites, referencias JSON, archivos pendientes y condiciones de orden
y estudio de tiempos. El servidor conserva sus propias validaciones definitivas.
La preparación correcta no garantiza que Ollama o el worker estén disponibles.

En resultados, la orientación usa únicamente estados observados: en cola, en
curso o finalizados. No estima duraciones ni inventa pasos. La leyenda ampliable
separa completada, evaluada, sin evaluar, cancelación y error. Las respuestas
conservadas con error, cancelación, interrupción, timeout o límite se señalan como
parciales tanto en el caso como en la traza; una respuesta incorrecta evaluada no
se reclasifica como parcial. La demo explica que su evidencia es guardada y no
ofrece acciones de ejecución. Las barras añaden símbolos y una lectura breve con
recuentos; mantienen denominadores y datos ausentes. Biblioteca y campañas
conservan sus advertencias y exclusiones junto a la evidencia, con ayuda opcional
sobre lo que contiene una ficha o una campaña. La traza explica su recorrido de
eventos registrados y mantiene el JSON técnico ampliable.

Componentes nuevos: `ComparisonMapComponent`, `TermHelpComponent` y
`ExecutionGuideComponent`, con HTML/CSS y variables semánticas. Sin dependencias
nuevas, cambios en cálculos del backend, metodología, rankings ni causalidad.
Pruebas nuevas: `beginner.spec.ts`, validación real en `workspace.test.cjs`,
estados y respuestas parciales en `visual-data.test.cjs`, orientación de consulta
en `demo-tests/browser.cjs`. Resultados y límites en el registro de auditoría.

## Continuación tras exploración sin documentación previa (20/10/2026)

«Probar recorrido simulado de pedidos» anticipa el contenido del ejemplo. El
aviso del formulario aclara que el simulador confirma recepción y no genera
respuestas a instrucciones personalizadas. Las etiquetas editables usan
«Instrucciones (prompt) A/B». La evaluación y las repeticiones quedan antes del
desplegable avanzado, sin cambiar valores, validaciones ni payloads.

Al cerrar sesión explícitamente se limpia la selección de comparación/campaña
de la ruta activa, conservando borradores e historial. Los enlaces profundos
introducidos para iniciar sesión siguen funcionando. Cambiar de sección retira
avisos anteriores; las confirmaciones de operaciones que terminan después de
navegar siguen apareciendo sin forzar el regreso. La cancelación nombra caso y
variante. Campañas vacías ofrece «Abrir resultados» con selección válida o
«Preparar comparación» en su ausencia. La demo conserva solo consulta.

La autorización abarcó A–F del plan de esta exploración. La reorganización de
instrucciones/condiciones es una propuesta aprobada basada en una hipótesis;
su implementación y verificación técnica no prueban mejora de comprensión
con personas usuarias. Registro y límites en la auditoría UX.
