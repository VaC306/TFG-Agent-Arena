# Agent Arena — batería v1

## Contenido y procedencia

Todos los casos son sintéticos y fueron preparados para Agent Arena. Los pedidos
proceden del entorno de ejemplo del repositorio. Los casos de desarrollo de texto
y JSON proceden de `data/examples/`. No es un benchmark externo validado.

| Suite | Desarrollo | Evaluación | Criterio |
| --- | ---: | ---: | --- |
| `text` | 3 | 6 | Texto exacto; acentos y mayúsculas cuentan |
| `json` | 3 | 6 | Igualdad estructural JSON estricta |
| `attachments` | 2 | 2 | JSON estricto a partir de archivos TXT, CSV y JSON |
| `orders` | 4 | 4 | Importe en céntimos, conjunto de pedidos y herramientas permitidas |

Son 12 casos de desarrollo y 18 de evaluación; una repetición con dos ramas
produce 24 y 36 ejecuciones, respectivamente. `diagnostics/tool-calls.json` es
otra prueba de desarrollo: tres llamadas sencillas, con una herramienta o con
todas disponibles. Se comprueba también si el modelo conserva el resultado de
la herramienta al responder; esa segunda comprobación es distinta de llamarla bien.

`datasets/text-*.csv` y `datasets/json-*.jsonl` se pueden importar directamente
desde la interfaz. En JSONL la respuesta esperada es una cadena que contiene JSON.
Las suites de herramientas y adjuntos usan formatos internos, para incluir
entornos y fixtures; se ejecutan mediante la CLI.

## Repetir desde la raíz del proyecto

Primero prepara el entorno Python según el README general. Arranca Ollama y
descarga los dos modelos explícitamente:

```powershell
ollama pull qwen2.5:3b
ollama pull qwen2.5:7b
```

Si usas la distribución portátil ya preparada en esta máquina, sustituye
`ollama` por `.\runtime\ollama\bin\ollama.exe`. El README general explica cómo
arrancar el servicio portátil y localizar sus modelos.

Validar datos, referencias de pedidos, hashes y separación de fases, sin inferencia:

```powershell
.\.venv\Scripts\python.exe -c "from arena.benchmarks import validate_bundle; print(validate_bundle('benchmarks/v1')['version'])"
```

Aislar herramientas con ambos modelos y conservar las peticiones reales:

```powershell
.\.venv\Scripts\python.exe -m arena.cli diagnose-tools --output runtime/diagnostico-mi-prueba
```

Ejecutar desarrollo y, una vez fijadas las decisiones, evaluación:

```powershell
.\.venv\Scripts\python.exe -m arena.cli benchmark --split dev --output runtime/benchmark-dev-mi-prueba
.\.venv\Scripts\python.exe -m arena.cli benchmark --split eval --output runtime/benchmark-eval-mi-prueba
```

Para seleccionar una suite o repetir con otro par:

```powershell
.\.venv\Scripts\python.exe -m arena.cli benchmark --split dev --suites orders --model-a qwen2.5:3b --model-b qwen2.5:7b --repetitions 2 --output runtime/pedidos-mi-prueba
```

Los directorios de salida deben ser nuevos. Nunca se sobrescriben resultados.
La batería usa una base SQLite propia dentro de esa salida y ejecuta su propio
worker; no requiere API ni Angular y no consume la cola o el historial personal.
Ejecuta cada batería secuencialmente, sin inferencias simultáneas de otros procesos.
En Linux/macOS utiliza `.venv/bin/python` en lugar de `.\.venv\Scripts\python.exe`.

## Evidencias y auditoría

Cada suite exporta `metrics.csv`, `summary.json`, `runs.json`, `snapshot.json`,
`events.jsonl` y `audit.json`. La salida general incluye `report.json`, el
manifiesto utilizado y SQLite. Las trazas de Ollama incluyen el cuerpo real de
la petición: modelo, mensajes, herramientas, parámetros, límites y `keep_alive`.
No se guarda el campo privado de razonamiento del modelo.

La auditoría recalcula evaluaciones desde las respuestas, referencias y llamadas
registradas; reproduce los resultados de herramientas; contrasta contadores de
herramientas, errores, tokens, duración de generación, CSV y resúmenes. Una respuesta
incorrecta del modelo puede pasar la auditoría: significa que se contabilizó de
forma coherente, no que fuera correcta. La ejecución termina con error si detecta
incoherencias. Los resultados parciales se conservan si el proceso se interrumpe.

El snapshot incluye datos, archivos, fuentes de backend, paquetes, hardware,
identidades de modelos, commit y estado de cambios locales. Antes de cada ejecución
se fija la primera identidad observada de cada modelo. La semilla no garantiza
reproducción bit a bit. Para volver a ejecutar se necesitan el mismo entorno,
modelo/digest, configuración y datos; comparar también los hashes de fuentes.

Los hashes cubren los bytes exactos. `.gitattributes` evita que Git convierta
automáticamente los saltos de línea de esta carpeta. No regeneres el manifiesto
de v1 para ocultar modificaciones: crea v2 y revisa sus referencias.

## Qué conclusiones permite

Los resultados describen estos casos sintéticos y estas condiciones. No prueban
un ganador general. Usa `dev` para ajustar; no cambies prompts tras ver `eval` y
presentes el resultado como reservado. La publicación del conjunto y los casos
similares limitan cualquier afirmación de generalización.

Presenta juntos los aciertos, el denominador de respuestas evaluadas, los errores
y las ejecuciones programadas. El porcentaje de calidad excluye errores de
ejecución; puede subir artificialmente si un modelo termina pocos casos. No se
calcula McNemar con pares incompletos, entradas independientes o repeticiones.
Una repetición y muestras pequeñas sirven para diagnóstico, no para conclusiones
estadísticas fuertes. Comparar múltiples suites introduce además comparaciones múltiples.

El tiempo incluye carga de modelo, metadatos e instrumentación y, en pedidos,
varias llamadas y herramientas. No hay warmup; `keep_alive=0` se aplica a cada
llamada. Las mediciones no aíslan el host y no demuestran diferencias de velocidad
intrínseca entre modelos. Los resultados publicados de una ejecución deben
identificar su versión, condiciones, hashes y limitaciones.
