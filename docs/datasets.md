# Datasets propios

En la comparación personalizada, selecciona **Datos de la prueba → Importar dataset CSV / JSONL**.
Descarga la plantilla, sustituye los ejemplos e importa el archivo. La app valida el documento
y muestra todos los casos, cuántos tienen referencia y el número de ejecuciones antes de lanzar.
El botón de ejecución requiere un dataset válido; una nueva importación inválida descarta la selección anterior.

## Estructura v1

| Campo | Obligatorio | Contenido |
| --- | --- | --- |
| `id` | Sí | Identificador único, 1–80 caracteres. Empieza con letra ASCII o número; después admite también punto, guion y guion bajo. |
| `input` | Sí | Entrada de texto, 1–6.000 caracteres; no puede estar en blanco. |
| `expected_answer` | No | Respuesta de referencia, hasta 6.000 caracteres. Vacío o `null` significa sin evaluación. |

CSV usa cabecera y comas. Las celdas que contienen comas, comillas o saltos de línea deben
seguir el entrecomillado CSV. JSONL contiene un objeto por línea; se ignoran líneas vacías.
Ambos formatos usan UTF-8, con BOM opcional. Se rechazan columnas desconocidas, IDs repetidos,
tipos incorrectos, entradas vacías y archivos de más de 1 MiB o 100 casos.

Ejemplos completos: `data/dataset-ejemplo.csv` y `data/dataset-ejemplo.jsonl`.
Esta primera versión importa casos de texto. Los adjuntos TXT, CSV, JSON e imágenes continúan
disponibles en la entrada manual; el dataset no interpreta rutas de archivos ni URLs.

## Ejecución y evaluación

Cada caso se ejecuta en A y B con exactamente la misma entrada. Puedes usar un único modelo
con dos prompts, o dos modelos distintos. No se pueden combinar un dataset y entradas manuales
en el mismo envío. El modo manual de un solo modelo conserva las entradas A/B independientes.
Total de ejecuciones: casos × repeticiones × 2 (máximo 2.000).

La referencia nunca se envía al modelo. La evaluación es coincidencia exacta de texto después
de quitar espacios al principio y al final; no ignora mayúsculas, acentos ni formato JSON.
Para preguntas abiertas conviene omitirla: completar una ejecución no demuestra calidad.
El simulador verifica el circuito, pero no responde preguntas reales ni mide calidad de modelos.

Los casos normalizados y referencias quedan guardados en el snapshot del experimento, con
el hash de datos existente, prompts y parámetros. No se conserva el nombre ni el archivo original
del dataset. La configuración guardada muestra todos los casos; resultados y CSV identifican cada
ejecución por `task_id`. No existe todavía una biblioteca de datasets independientes del experimento.

## API

- `GET /datasets/template.csv`: plantilla descargable.
- `POST /datasets/validate`: `{ "filename": "datos.csv", "content": "id,input\nuno,Hola" }`.
  Devuelve `cases`, `count` y `scored`; no encola ejecuciones.
- `POST /comparisons`: configuración habitual con `dataset: [{"id":"uno","input":"Hola"}]`
  en lugar de `shared_input` o `branch_inputs`. El servidor vuelve a validar los casos.

El parser indica la línea y campo del primer error. En CSV multilineal, la línea indicada es
la última línea física del registro. La aplicación no hace una inferencia hasta lanzar la comparación.
