# Mediciones y calentamiento

## Política fijada

En **Comparar → Condiciones de ejecución**, elige sin calentamiento (por defecto)
o una petición neutra antes de cada ejecución. Se aplica a ambas ramas, se guarda
en preferencias y queda fijada en configuración, condiciones y campañas.

`per_run` envía `Reply OK.`, con máximo un token, sin herramientas, instrucciones
originales, referencia, adjuntos ni conversación de la tarea. Conserva modelo,
contexto, temperatura y semilla elegidos. Su respuesta no se evalúa ni reutiliza.
La identidad se verifica antes y después; una diferencia bloquea la entrada real.

Los tokens de calentamiento no se suman a los de tarea. Sus contadores, petición,
duración y estado se registran por separado. Fallos, timeout, cancelación e
interrupción terminan la ejecución sin enviar la tarea y quedan como errores,
no como respuestas de calidad incorrecta.

Se usa `keep_alive=5m` durante calentamiento y tarea, según el control documentado
por [Ollama](https://docs.ollama.com/api/chat). Sin calentamiento, las comparaciones
nuevas mantienen `0`. No se descargan modelos. El servidor puede desalojarlos;
no se garantiza residencia, arranque en frío o estabilización térmica. Una petición
corta prepara carga/generación, no todas las rutas de herramientas o visión.

## Tiempos

- `agent_s`: tiempo total desde el inicio del runner hasta capturas finales,
  incluyendo preparación, calentamiento y muestreo. Las medias existentes siguen
  usando este valor de respuestas sin error, etiquetado **tiempo total medio**.
- `preparation_s`: consulta inicial y validación de identidad.
- `warmup.duration_s`: petición neutra y verificación posterior.
- `task_s`: ciclo de tarea, incluyendo HTTP, inferencia, herramientas y evaluación;
  es `null` si la tarea no empezó.
- `queue_s`: espera previa a que el worker reclame la ejecución.

El límite incluye metadatos, calentamiento y tarea. Capturas inicial/final y
persistencia pueden añadir tiempo al total. Las fases no suman necesariamente el
total: hay otras operaciones y muestreo concurrente. `failure_phase` identifica
preparación, calentamiento o tarea cuando falla. No es latencia pura de generación.

## Recursos

Las comparaciones nuevas solicitan capturas cada segundo, además de inicio y
final. Se hacen fuera del bucle asíncrono; al terminar/cancelar se espera la captura
en curso, sin escrituras posteriores al cierre. Captura y persistencia pueden
añadir demora: no es medición sin coste ni una garantía de tiempo real.

Cada muestra registra timestamp, tiempo relativo y fase. El intervalo efectivo
incluye captura y planificación; se conserva el mayor hueco observado. El resumen
incluye número de muestras, duración observada, máximo RSS del worker, mínima RAM
disponible del host y máximo uso GPU por dispositivo cuando NVML está disponible.
La diferencia de CPU usa tiempos acumulados del proceso de [psutil](https://psutil.io/),
no un porcentaje instantáneo.

RSS/CPU del worker **no incluye Ollama**. RAM/GPU del host incluye otros programas;
con Ollama remoto no representa su máquina. Los máximos son valores observados
entre muestras, **no picos garantizados**. Sin sensor se conserva `null` y el
motivo, sin sustituirlo por cero ni fallar una respuesta válida. No se mide energía,
temperatura ni utilización GPU. `sampling_overhead_s` es la duración acumulada de
capturas/escrituras; no un incremento causal de latencia ni un valor que deba restarse.

Campañas antiguas sin intervalo conservan capturas de extremos al usar el runner
actual. El historial no se reescribe y cambios de código/política/configuración
siguen impidiendo mezclar evidencia incompatible.

## Exportaciones

Resultados muestra fases por ejecución y permite descargar
`GET /experiments/{id}/resources.csv`: una fila por muestra con identificación,
fase, tiempos y valores. Requiere propiedad del experimento y puede ser parcial.
CSV de ejecuciones, Markdown y JSON conservan tiempos, calentamiento y resumen.
La biblioteca conserva los mismos registros y muestra la política; campañas añade
`measurements` por intento/rama en sus informes. CLI añade `resources.csv` y las
trazas conservan todas las muestras. Calentar no aumenta las tareas evaluadas.

## Verificación del 13 de octubre de 2026

Regresión completa: **218 pruebas Python**. Después se añadió y verificó el bloqueo
por cambio de identidad tras calentar: **9 pruebas de mediciones** correctas,
incluyendo las ocho ya presentes en la batería completa. También pasaron **28 pruebas
frontend**, compilación de producción, `compileall`, `pip check` y `git diff --check`.
TestClient mantiene una advertencia de deprecación de AnyIO.

Pruebas controladas: pico intermedio ausente en extremos, separación de tokens,
petición neutra, fases, cancelación/timeout/interrupción, errores de adaptador/sensor,
fin del sampler, política antigua, conservación en campañas/biblioteca/informes y
acceso por cuenta. Estos resultados controlados no son inferencia real.

Se inició el Ollama portátil existente **0.40.3**, sin cloud ni descargas. En una
copia aislada `runtime/measurement-smoke/arena.sqlite` se ejecutó el caso `capital`
de `data/dataset-ejemplo.csv`, referencia exacta `París`, con **Qwen 2.5 3B**:
mismo prompt A/B, desarrollo, una repetición, contexto 1.024, máximo 32 tokens,
semilla 42, temperatura 0 y límite 120 s. Ambas identidades/digests se verificaron.
El historial original no se modificó.

Experimento: `46efb508-8ea9-45d7-84d7-5b3b7daa1c43`.

| Rama / orden | Respuesta | Total (s) | Tarea (s) | Calentamiento y verificación (s) | Muestras |
|---|---|---:|---:|---:|---:|
| B / primera | París | 4,166 | 0,211 | 3,724 | 6 |
| A / segunda | París | 0,671 | 0,175 | 0,308 | 2 |

Ambas fueron correctas (2/2), con ocho muestras. NVML no estaba instalado: GPU
`null`, motivo `ModuleNotFoundError`. CSV y JSON coincidieron en contadores, tiempos,
uso de calentamiento y resúmenes. Artefactos locales ignorados: `real-report.{json,md}`,
`real-metrics.csv`, `real-resources.csv` y `measurement-desktop.png` en la carpeta aislada.

En navegador se verificaron selector nativo con ayuda accesible, detalles con
teclado y valores del desglose. A 320/390 px no hubo desbordamiento horizontal.
Estos dos tiempos no prueban efecto causal del calentamiento ni ventaja de A:
es un caso único, con orden secuencial y estados previos distintos. La auditoría
completa de accesibilidad sigue pendiente.

Queda diseñar una campaña real con casos reservados, repeticiones y orden adecuados,
condiciones externas registradas e hipótesis de latencia concreta. Estas mediciones
permiten auditarla; no demuestran por sí solas rendimiento general.
