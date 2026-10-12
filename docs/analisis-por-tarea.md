# Análisis por tarea y estabilidad

En **Campañas**, «Qué cambia en cada tarea» agrupa las repeticiones de los
intentos terminados con condiciones compatibles con el origen. Los intentos
parciales, con cambios de código/equipo/modelo o con un plan de ejecuciones
incompleto permanecen en la evolución y se muestran como excluidos del análisis.
No se modifica el historial ni se declara un ganador.

## Contadores y lectura

Cada fila corresponde a una tarea y una rama. Conserva los mismos contadores
que Resultados y la biblioteca: aciertos, referencias evaluables, evaluadas,
incorrectas, formatos inválidos, errores, sin evaluar, pendientes y tiempos.
Calidad es aciertos/evaluadas; cobertura es evaluadas/referencias evaluables.
Un error de ejecución no se convierte en respuesta incorrecta. Sin denominador,
las tasas son `null` y la interfaz muestra «—».

«Evaluadas siempre correctas/incorrectas» describe únicamente respuestas
puntuadas y requiere al menos dos. Una mezcla indica calidad variable; menos de
dos indica evidencia insuficiente. No demuestra respuestas idénticas. La serie
desplegable muestra el estado de cada repetición e incluye enlaces al intento.
«Entre intentos» compara los vectores de estados entre intentos consecutivos
incluidos; detecta también cambios de formato o error aunque no cambien los
aciertos. Cero cambios no implica texto idéntico. Los filtros muestran tareas
con calidad variable, cambios, errores o cobertura incompleta.

## Diferencia emparejada e incertidumbre

Se emparejan A y B por tarea compartida, intento y repetición. Con entradas
independientes no se emparejan IDs coincidentes. Las tareas sin referencia
quedan fuera. Se muestran ambos correctos, solo A/B correcta, ambos incorrectos
y pares sin puntuación. Si falta una puntuación se suprime la diferencia media;
no se imputan errores como calidad incorrecta.

La diferencia B−A es la media de las diferencias de cada tarea, dando el mismo
peso a cada caso. Cada diferencia de tarea promedia todas sus repeticiones e
intentos incluidos. El alcance distingue modelos, configuraciones y
repetibilidad según el protocolo; prompts o parámetros diferentes no justifican
atribuir la diferencia exclusivamente al modelo.

El intervalo exploratorio del 95 % usa BCa mediante
[SciPy 1.15.3 `bootstrap`](https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.stats.bootstrap.html),
con 4.000 remuestreos y semilla 42. La unidad remuestreada es la tarea completa:
sus repeticiones e intentos permanecen agrupados. Repetir más un caso no aumenta
el número de tareas independientes. Se necesitan tareas independientes y
representativas para interpretar el intervalo; la aplicación no puede probar
ese supuesto mediante IDs diferentes.

La política conservadora de esta versión exige:

- Inferencia real, fase `eval`, al menos 10 tareas compartidas con referencia y
  dos intentos terminados compatibles.
- Todos los pares puntuados y ningún intento excluido o pendiente.
- Ausencia de entradas duplicadas bajo distintos IDs, considerando también
  entorno y adjuntos; esta comprobación no detecta todas las dependencias.
- Diferencias por tarea no constantes y límites finitos del remuestreo.

Estos mínimos son una política de la herramienta, no una garantía estadística.
Se explica cada motivo de indisponibilidad. El intervalo describe sensibilidad
al conjunto de tareas bajo las condiciones registradas; no caracteriza toda la
variación entre máquinas, tiempos o futuras ejecuciones. No se calcula un
valor p, ranking o ganador, ni se generaliza a otros datasets. Revisar referencias,
representatividad y posibles dependencias sigue siendo responsabilidad del
diseño experimental del TFG.

## Exportación y reproducción

- `GET /campaigns/{id}/analysis.csv`: una fila por tarea y rama, contadores,
  tasas, series JSON y cantidades de intentos incluidos/excluidos. Las celdas
  que podrían interpretarse como fórmulas se neutralizan con apóstrofo.
- El CSV de evolución sigue mostrando cada intento por separado.
- Markdown añade el análisis, exclusiones, diferencias y método.
- JSON incluye la misma estructura `analysis`, evidencia original y
  `analysis_sources`: fuentes exactas de `task_analysis.py`, `model_results.py`,
  `protocol.py` y `latency_analysis.py` usadas por el proceso para calcularlo, con SHA-256. Estas
  fuentes son distintas de las históricas que ejecutaron cada intento.

El método registra versión del análisis, semilla, número de remuestreos,
unidad, política, versiones Python/NumPy/SciPy y huella de diferencias de entrada.
Se conserva el diseño, snapshots, fuentes e identidades originales. Los informes
leen cada intento una sola vez y comparten esa evidencia con los contadores.
Las descargas separadas pueden reflejar momentos diferentes si hay un worker
activo. Reproducir el cálculo sobre evidencia guardada no garantiza respuestas
idénticas de un modelo en otra máquina. Cambiar el backend antes de repetir
puede excluir ese intento por cambio de código; para una nueva campaña homogénea,
termina una comparación con la versión actual y fija su diseño.

## Verificación del 12 de octubre de 2026

Controles: 205 pruebas Python, 24 del frontend, compilación Angular de producción
y `pip check`, todos correctos. Hay una advertencia de deprecación de AnyIO en
TestClient. Las 17 pruebas nuevas de Python cubren denominadores, formatos,
errores, series, planes incompletos/duplicados, entradas independientes,
exclusiones, cada condición del intervalo y remuestreo determinista. La prueba
de integración cruza informes y CSV, verifica fuentes, aislamiento entre cuentas
y supresión del intervalo cuando aparece un intento pendiente. Las dos pruebas
nuevas del componente comprueban filtros y eliminación de análisis anterior al
cambiar selección; el harness sustituye Angular/HTTP, no es un navegador.

La elegibilidad del intervalo y los errores se verifican con resultados
controlados, sin llamadas a Ollama. En navegador se utilizó exclusivamente
`runtime/campaign-smoke/arena.sqlite`, con los dos intentos simulados existentes:
cuatro tareas, dos repeticiones, 32 ejecuciones guardadas. Se comprobaron 2/2
intentos incluidos, ocho filas tarea/rama con 4/4 por fila, 16/16 pares y diferencia
descriptiva cero. El intervalo se suprime por simulación, desarrollo, tamaño
insuficiente y diferencias constantes.

Se verificaron filtro vacío, detalles con Enter, desplazamiento de tabla con
flechas/foco, recarga y regreso a Campañas. A 320 y 390 px no hay desbordamiento
horizontal de página. Se corrigió una solapación de las entradas largas. No hubo
errores de consola durante el flujo conectado. Al detener la API, la actualización
advierte que los datos visibles pueden estar desactualizados, bloquea repetir y
termina los indicadores. Tras reiniciar y reintentar, desaparece el aviso y se
recuperan los controles. Las descargas por navegador CSV/Markdown/JSON coinciden en
contadores/series y se comprobaron las huellas de las fuentes. Artefactos locales:
`runtime/campaign-smoke/task-analysis.{csv,md,json}` y
`runtime/campaign-smoke/task-analysis-desktop.png` (ignorados por Git).

No se ejecutó un modelo real ni se descargaron modelos en este hito; la comprobación
de navegador valida presentación y persistencia de simulación existente. No es
una auditoría completa de accesibilidad ni evidencia empírica de calidad de modelos.
Queda preparar casos de evaluación revisados y una campaña real homogénea, registrar
condiciones externas y mejorar observación del worker/calentamiento para latencias.
