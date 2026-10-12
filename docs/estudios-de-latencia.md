# Estudios de tiempo de tarea fijados

## Preparar el protocolo

1. Revisa un dataset compartido con referencia en todos los casos. Usa desarrollo
   para comprobar el flujo; reserva casos distintos para la evaluación final.
2. En **Comparar → Condiciones de ejecución**, activa **Fijar estudio de tiempo de
   tarea**. El control activa calentamiento por ejecución y orden equilibrado,
   y aumenta una repetición impar al siguiente par. Revisa los valores antes de lanzar.
3. Fija de 2 a 20 intentos previstos. El original cuenta como intento 1. Los casos,
   referencias, prompts, modelos, parámetros, repeticiones y fase se registran
   antes de ejecutar; la pregunta y medida principal quedan en `latency_plan`.
4. Termina el original y crea su campaña desde Resultados. Completa exactamente
   los intentos previstos. Documenta condiciones externas e incidencias.
5. Consulta **Tiempo de tarea y orden de ejecución** y conserva CSV, Markdown y
   JSON. No selecciones solo intentos favorables ni cambies el criterio después.

La misma validación de tareas compartidas con referencia se aplica a la API y CLI.
El objetivo fijado es la diferencia media emparejada **B−A en segundos de `task_s`**,
con igual peso por tarea. No es un registro externo ni una certificación de que
el operador desconocía resultados previos. El snapshot y la fecha local permiten
inspeccionar qué se fijó, sin certificar un preregistro público independiente.

## Orden y tamaño de muestra

`balanced` exige repeticiones pares. Una semilla fija el primer orden A/B de cada
caso y se invierte en la siguiente repetición: cada rama ejecuta primero la mitad
por caso e intento. Los intentos repiten ese mismo programa fijado. `random` sigue
siendo la opción predeterminada para comparaciones normales.

El límite de intentos se aplica dentro de la transacción SQLite: solicitudes
simultáneas no pueden ampliar la muestra. Una clave de solicitud repetida devuelve
el intento ya creado, también después de llegar al límite. La interfaz desactiva
repetir al guardar todos los previstos. Un intento fallido no se reemplaza por
otro favorable; su evidencia se conserva. Una ampliación requiere diseño nuevo
con su propia justificación, sin combinarla automáticamente con el anterior.

Equilibrar orden no elimina caché, estado térmico, carga de otros programas o
interferencia entre casos. El informe muestra quién ejecutó primero y comprueba
con timestamps que cada pareja fue secuencial. La ejecución global sigue siendo
secuencial. Un reloj de pared inconsistente puede impedir verificar este requisito.

## Lectura del análisis

Se usan solo intentos terminados con condiciones compatibles. Cada par identifica
tarea, intento y repetición; conserva tiempos A/B, orden, estado y calidad. Se
muestran pares previstos en esa cohorte, temporizados, ausentes, incorrectos y
sin calidad verificada. Los excluidos siguen en la evolución y evidencia original.

Tiempo válido requiere respuesta sin error y `task_s`/`agent_s` finitos y no
negativos, con tarea no mayor que total. No se sustituye una ausencia por cero,
por el tiempo total o por total menos calentamiento. Si falta un tiempo emparejado,
la media global queda `null`, mostrada como «—». La media de una tarea se muestra
solo cuando todos sus pares incluidos tienen tiempo válido.

La diferencia promedia primero las repeticiones/intentos dentro de cada tarea y
luego los casos con igual peso. Incluye respuestas incorrectas cuando tienen
tiempo válido, para no ocultar selectivamente resultados; su conteo se muestra.
Un valor negativo describe menor tiempo observado de B, no un ganador. El alcance
se identifica como modelos, configuraciones o repetibilidad según el protocolo.
El diagnóstico por orden usa solo pares temporizados y muestra su denominador;
no aplica una corrección causal automática del efecto de ejecutar primero.

## Incertidumbre exploratoria

BCa del 95 % mediante [SciPy 1.15.3](https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.stats.bootstrap.html),
4.000 remuestreos, semilla 42, unidad **tarea completa**. Todas sus repeticiones e
intentos permanecen agrupados. El método y las versiones Python/NumPy/SciPy,
medida fijada y SHA-256 del vector de entrada se conservan. Añadir repeticiones
idénticas no aumenta las tareas ni estrecha artificialmente el intervalo.

El intervalo requiere plan compatible previo, todos los intentos previstos,
inferencia real, fase `eval`, al menos 10 tareas sin entradas duplicadas, tiempos
completos, calidad correcta verificada en todos los pares, calentamiento registrado,
orden equilibrado observado, secuencia verificable y diferencias no constantes.
Los límites deben ser finitos. Cualquier fallo se explica; no se declara un ganador.
También se suprime la inferencia de calidad intermedia si el estudio no está completo.

El mínimo de diez tareas es una política conservadora de la herramienta, no una
garantía de potencia o validez estadística. El remuestreo presupone tareas
independientes y representativas: IDs distintos no lo prueban. Un intervalo sobre
estos casos no mide toda la variación entre máquinas, servidores, días o ejecuciones.
Referencias y representatividad necesitan revisión independiente para el TFG.

## Exportación

`GET /campaigns/{id}/latency.csv` conserva una fila por par de intentos incluidos,
con orden, estados, calidad, tiempos de tarea/total y calentamiento de ambas ramas,
así como cantidades de intentos incluidos/excluidos. Solo accede el propietario;
las celdas que podrían ser fórmulas se neutralizan. Los registros excluidos y los
motivos completos permanecen en JSON/Markdown/evolución. Las descargas separadas
pueden representar momentos distintos mientras exista actividad.

JSON/Markdown incorporan `analysis.latency`. `analysis_sources` incluye la fuente
exacta de `latency_analysis.py` y su huella; el análisis por tarea pasa a versión 2.
El diseño, fuentes originales e identidades de cada intento no se reescriben.

## Verificación del 13 de octubre de 2026

**240 pruebas Python**, **30 del frontend**, build de producción y `pip check`,
correctos; `git diff --check` sin errores. TestClient mantiene la advertencia de
AnyIO. Las 21 pruebas nuevas cubren orden equilibrado reproducible, validación,
agrupación por tarea, invariancia ante repeticiones idénticas, cada condición del
intervalo, tiempos negativos/no finitos/imposibles, calidad, idempotencia al llegar
al límite, exportaciones, cuenta ajena y exclusión por condiciones externas.
El requisito de referencias de la CLI se verificó después con esas mismas pruebas.
La disponibilidad del intervalo se prueba con datos controlados, sin inferencia real.

Piloto real: copia aislada `runtime/latency-smoke/arena.sqlite`, Ollama portátil
**0.40.3**, Qwen 2.5 **3B**, mismo modelo/prompt A/B, primeros dos casos del dataset
existente `benchmarks/v1/datasets/text-dev.csv`, fase desarrollo, dos repeticiones,
dos intentos, contexto 1.024, salida máxima 32 tokens, semilla 42, temperatura 0,
límite 120 s, calentamiento por ejecución. Sin cloud, descargas o limpieza de
modelos; se conservó el historial original. No es una evaluación con casos nuevos
reservados ni un estudio confirmatorio de velocidad.

Campaña: `feaea0c2-10d2-44de-a49b-a918be3d5565`.
Origen: `a17966d5-ead9-4d6a-bdfc-b1e525eecdea`.
Intento 2: `735a8df4-6cca-4510-85f1-9a9b172404d3`.

Se completaron **16 ejecuciones**, ocho pares con tiempos válidos, cuatro por cada
orden A/B. En `capital` el modelo respondió `Paris` frente a la referencia exacta
`París`: ocho respuestas incorrectas, que no son errores de ejecución. `cuenta`
respondió correctamente `42` en sus ocho ejecuciones. Hubo cuatro pares con
respuestas incorrectas; no se corrigió el prompt ni se repitió selectivamente.

Diferencia descriptiva global B−A: **+0,005428 s**. Con A primero: **−0,008311 s**
(cuatro pares); con B primero: **+0,019167 s** (cuatro pares). El cambio de signo
muestra sensibilidad observada al orden en este piloto, sin probar una causa.
El intervalo se suprime por desarrollo, dos casos y calidad incorrecta. NVML no
estaba disponible; los recursos GPU no se inventan. No demuestra una ventaja de
modelo: ambas ramas usan el mismo digest.

Un tercer intento devuelve 409; reintentar la clave del segundo devuelve el mismo
ID. CSV y JSON coinciden en tiempos, orden y calentamiento. En navegador se
comprobaron controles del plan, bloqueo al completarlo, motivos de falta de intervalo,
foco/desplazamiento de tabla con teclado y ausencia de desbordamiento a 320/390 px,
sin errores de consola. La auditoría completa de accesibilidad sigue pendiente.
Artefactos locales ignorados: `campaign.{json,md}`, `latency.csv`, `ids.json` y
`latency-desktop.png` en la carpeta aislada.

Queda elegir y revisar independientemente un conjunto representativo de casos
reservados, justificar la muestra para una hipótesis concreta, registrar las
condiciones externas y ejecutar el estudio final. La herramienta ya permite
fijarlo, completarlo y auditarlo; el piloto no sustituye esa evidencia del TFG.
