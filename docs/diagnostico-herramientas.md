# Diagnóstico local y batería reproducible

Comprobación del 12 de octubre de 2026: Ollama 0.40.3, Qwen 2.5 3B y 7B,
cuantización Q4_K_M, RTX 4060 Laptop con 8 GiB de VRAM y 31,6 GiB de RAM.
Ollama se ejecutó en loopback, con uso de cloud deshabilitado.

## Aislamiento de herramientas

Se pidieron explícitamente `search_orders(C1)`, `order_lines(O1)` y
`calculate(sum,[100,200])`. Cada caso se ejecutó con una sola herramienta y
con las tres disponibles, usando los esquemas reales del adaptador.

Ambos modelos produjeron **6/6 llamadas correctas**, con nombres y argumentos
válidos. Los resultados de las herramientas se incorporaron usando el formato
`role=tool`, `tool_name` y `content`, descrito por
[Ollama](https://docs.ollama.com/capabilities/tool-calling).

La segunda petición exigía devolver íntegro el resultado como JSON. Cada modelo
pasó 4/6: 3B eliminó dos pedidos al copiar el listado; 7B añadió una clave
`order_lines` alrededor de una lista. No son fallos de la llamada inicial.
Se conservaron los cuerpos de petición, respuestas y argumentos observados.

Esto demuestra que las tres herramientas funcionan en peticiones sencillas con
esta integración. No demuestra que el encadenamiento completo sea fiable ni
descarta efectos de la plantilla o el parser de esta versión de Ollama.

## Comparación con condiciones fijadas

La batería [v1](../benchmarks/v1/README.md) compara modelos con los mismos datos,
prompts y parámetros, usando temperatura 0, semilla 42, contexto 4096, salida
máxima 1024, timeout 90 s, ocho llamadas al modelo y veinte herramientas como
límites. El orden A/B se aleatoriza por caso con semilla 42. Una repetición.
Los prompts y datasets quedaron fijados antes de ejecutar la fase `eval`.

| Desarrollo | Qwen 3B: aciertos/programadas | Qwen 7B: aciertos/programadas | Errores de ejecución 3B / 7B |
| --- | ---: | ---: | ---: |
| Texto | 3/3 | 3/3 | 0 / 0 |
| JSON | 3/3 | 3/3 | 0 / 0 |
| Adjuntos | 1/2 | 0/2 | 0 / 0 |
| Pedidos | 0/4 | 1/4 | 0 / 3 |

| Evaluación reservada | Qwen 3B: aciertos/programadas | Qwen 7B: aciertos/programadas | Errores de ejecución 3B / 7B |
| --- | ---: | ---: | ---: |
| Texto | 6/6 | 6/6 | 0 / 0 |
| JSON | 6/6 | 4/6 | 0 / 0 |
| Adjuntos | 1/2 | 0/2 | 0 / 0 |
| Pedidos | 0/4 | 0/4 | 0 / 3 |
| Total descriptivo | 13/18 | 10/18 | 0 / 3 |

Estas tablas usan las ejecuciones programadas como denominador para mostrar el
cumplimiento de extremo a extremo. El porcentaje de calidad de la aplicación
usa solo respuestas evaluables y puede diferir: en pedidos de desarrollo 7B
tiene 1/1 respuestas correctas, pero completa solo uno de cuatro casos.

Se observaron argumentos no permitidos, límites de llamadas y respuestas vacías.
En adjuntos, ambos modelos fallaron el cálculo que relaciona un catálogo y un
CSV; 7B también devolvió claves distintas de las solicitadas en consultas simples.
Los fallos se conservaron y no se relajaron referencias ni criterios para
convertirlos en aciertos.

## Correcciones y auditoría

- Las trazas registran ahora el cuerpo de petición real enviado a Ollama,
  incluidos herramientas, opciones y política de memoria, además de los mensajes.
- El contraste emparejado no se calcula si faltan puntuaciones en algún par,
  para evitar inferir sobre un subconjunto de respuestas que terminaron.
- Los datasets tienen manifiesto SHA-256, fases separadas y validación de
  referencias de pedidos mediante un cálculo independiente desde los fixtures.
- La CLI ejecuta en SQLite aislado y audita evaluaciones, resultados de
  herramientas, errores, contadores de tokens, duración de generación, CSV y
  resúmenes. Las **ocho auditorías de suites pasan**, incluyendo los fallos de modelos.
- El backend tiene 156 pruebas satisfactorias, con una advertencia de
  deprecación de Starlette/AnyIO.

Los informes completos están en `runtime/diagnostic-tools-20261012`,
`runtime/benchmark-v1-dev-20261012` y `runtime/benchmark-v1-eval-20261012`.
Una selección de evidencia sin detalles privados del host está publicada en
[benchmarks/v1/results/2026-10-12](../benchmarks/v1/results/2026-10-12).
Cada suite incluye respuestas, CSV, hashes de datos y código e identidad de modelos.
Las fuentes completas y trazas del worker se conservan en el exportador local.

## Alcance de las conclusiones

Es una comprobación funcional y una comparación descriptiva de casos sintéticos,
no un resultado estadístico general sobre modelos. Solo hay una observación por
modelo y caso; los conjuntos son pequeños, públicos y próximos entre sí. No se
ha demostrado que 3B sea mejor que 7B fuera de estas condiciones.

La calidad de llamadas simples y el cumplimiento de una tarea completa son
dimensiones distintas. El tamaño del modelo no garantiza seguir el esquema o
resolver operaciones entre archivos. Para sostener conclusiones más amplias hacen
falta más casos revisados independientemente, repeticiones agrupadas por tarea
y un análisis que tenga en cuenta errores, cobertura y comparaciones múltiples.

No se aisló la carga del host; parte de las verificaciones de software se ejecutó
durante la primera suite de evaluación. No hay warmup y `keep_alive=0` puede
recargar el modelo entre llamadas. Los tiempos son evidencia de esta ejecución,
no una comparación controlada de velocidad. Los snapshots indican cambios sin
commit y conservan hashes de fuentes: identificar la implementación con esos
hashes, no solo con el commit registrado.
