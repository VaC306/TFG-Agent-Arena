# Protocolo inicial de evaluación

## Pregunta y alcance

La pregunta inicial es: ¿cómo cambian el cumplimiento de una tarea, los errores
y el tiempo al cambiar de modelo o de configuración en una misma máquina?
Los resultados describen esos casos y esas condiciones; no establecen un
ganador universal. El simulador valida la plataforma, no modelos reales.

Primera batería propuesta: respuestas concretas y extracción JSON. Los resúmenes
y las imágenes se exploran aparte, con revisión humana, hasta contar con una
rúbrica validada. No se asigna una nota semántica automática mediante coincidencia
de texto ni se incorpora todavía un LLM juez.

## Preparación, antes de ejecutar modelos reales

1. Elegir dos modelos locales cuya memoria y contexto sean compatibles con la
   máquina. Registrar nombre, digest, cuantización y versión de Ollama. La máquina
   de desarrollo tiene aproximadamente 32 GiB de RAM; esto no determina la VRAM
   ni garantiza que un modelo concreto quepa. La elección final requiere comprobar
   también la GPU y el tamaño de los modelos instalados.
2. Preparar casos de desarrollo para ajustar instrucciones y otro conjunto
   reservado para evaluación final. No cambiar instrucciones a partir de los
   resultados reservados. La etiqueta de fase registra esta decisión, pero la
   herramienta no detecta reutilización de casos.
3. Revisar referencias y elegir el criterio antes de ver respuestas. Los archivos
   de `data/examples/` ilustran el formato; son ejemplos, no un benchmark validado.
4. Para comparar modelos, usar mismos datos, prompts y parámetros. Si se cambian
   prompts o entradas, presentar la prueba como comparación de configuraciones.
5. Mantener las condiciones locales lo más estables posible y registrar cualquier
   cambio. No ejecutar otros trabajos pesados mientras se mide. La aplicación
   recoge muestras de recursos, pero no aísla procesos del sistema operativo.

## Criterios implementados

| Tarea | Criterio | Interpretación |
| --- | --- | --- |
| Respuesta concreta | `exact_match` | Texto idéntico, salvo espacios en los extremos. Mayúsculas, acentos y puntuación cuentan |
| Extracción estructurada | `json_match` | Mismos valores y estructura. Orden de claves irrelevante; orden de listas relevante. Booleanos distintos de números; 1 y 1.0 equivalentes |
| Resumen, imagen o respuesta abierta | `none` | Sin nota automática; conservar respuesta para revisión humana |
| Benchmark de pedidos existente | `order_benchmark` | Importe, IDs únicos y restricciones de herramientas del caso |

JSON exige una respuesta JSON completa, sin bloques Markdown, claves duplicadas
ni números no finitos. Sin referencia, un caso queda sin evaluar. Las referencias
no se envían al modelo. El criterio es común a A/B y a todos los casos de una
comparación, para que ambos se midan con la misma regla.

## Ejecución y registro

Temperatura, semilla, contexto, máximo de salida y tiempo límite son configurables
y comunes a A/B. Sus valores completos se guardan en el snapshot. El máximo de
salida debe dejar espacio para la entrada; esto no garantiza que toda entrada
quepa, porque la tokenización depende del modelo. Las ejecuciones son secuenciales
y el orden A/B se aleatoriza con una semilla de orden registrada, dentro de cada
caso y repetición. Las nuevas pruebas solicitan `keep_alive=0` en ambas ramas;
los experimentos anteriores conservan su política registrada.

No hay calentamiento previo. `agent_s` incluye preparación, metadatos, inferencia
y herramientas, si existen; puede incluir carga del modelo. No es latencia pura.
El CSV conserva también duración de evaluación del servidor y contadores de
tokens. Una semilla fija no garantiza determinismo entre hardware o versiones.
Las muestras RAM/GPU son del host y worker, no consumo exclusivo del modelo.

Antes de cada ejecución se registra la identidad observada del modelo y una
huella de digest, versión del servidor y configuración declarada. La primera
identidad observada de cada modelo se fija para ese experimento. Si cambia en una
ejecución posterior, esta se detiene antes de enviar la entrada. La identidad no
se fija al crear la comparación: puede cambiar hasta su primera ejecución.
Tampoco se impide que otro programa cambie Ollama durante una llamada en curso.
Las identidades antiguas o adaptadores sin digest se indican como no verificadas.

## Lectura de resultados

- Coincidencia/cumplimiento: respuestas correctas entre respuestas evaluadas;
  siempre mostrar el denominador y el número de casos sin puntuación.
- Errores de ejecución: conexión, cancelación, timeout, límites o interrupción;
  se muestran aparte y no reciben puntuación de calidad. Una respuesta incorrecta
  sí cuenta como fallo del criterio. No confundir un porcentaje alto entre pocas
  respuestas con una ejecución fiable de todos los casos.
- Tiempo medio de respuestas: solo respuestas sin error de ejecución. Para estudiar
  coste de los fallos, usar sus filas del CSV por separado.
- Los resultados emparejados solo usan pares evaluados con datos compartidos.
  No realizar inferencia emparejada con entradas independientes. Las repeticiones
  están agrupadas por caso y no se tratan como muestras independientes; el contraste
  existente no produce p-valor cuando hay repeticiones.
  Tampoco produce p-valor cuando faltan puntuaciones en alguno de los pares.

La batería inicial versionada está en [benchmarks/v1](../benchmarks/v1/README.md).
Incluye separación de fases, fixtures, parámetros, manifiesto y una CLI que
audita las respuestas y métricas antes de exportarlas. Su alcance sigue siendo
un conjunto pequeño de casos sintéticos.

## Informe reproducible

Resultados permite descargar `reproducibility.json`: snapshot inmutable de
configuración, tareas, archivos, entornos, fuentes y SHA-256; commit y estado de
cambios locales; hardware/paquetes al guardar; resultados e identidades observadas;
informe de condiciones y limitaciones. Durante una ejecución es parcial. Las
trazas completas siguen disponibles en la aplicación y en el exportador CLI.
No es un instalador ni una promesa de reproducción bit a bit: para repetir deben
estar disponibles los modelos, versiones y entorno correspondientes.

El CSV incluye respuesta, versión del evaluador y digest. Las cadenas que podrían
interpretarse como fórmulas de hoja de cálculo se prefijan con apóstrofo; el JSON
conserva el contenido original. Los experimentos históricos no se reevalúan ni se
reescriben. La nueva agregación separa sus errores de ejecución de la calidad.

Referencias: [elección de métricas según la tarea](https://huggingface.co/docs/evaluate/choosing_a_metric),
[metadatos de modelos Ollama](https://docs.ollama.com/api/tags) y
[parámetros y contadores de la API de chat](https://docs.ollama.com/api/chat).
