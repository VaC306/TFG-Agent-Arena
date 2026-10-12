# Comprobación con inferencia local real

Prueba realizada el 11 de octubre de 2026 desde la API de la aplicación, con
sesión local, SQLite, worker secuencial, evaluación, trazas y exportación CSV.
No se sustituyó el modelo por el simulador.

## Entorno

- Ollama 0.40.3, distribución portátil oficial con SHA-256 verificado.
- `qwen2.5:3b`, Q4_K_M, digest
  `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`.
- RTX 4060 Laptop: Ollama detectó 8 GiB de VRAM y CUDA; RAM del sistema: 31,6 GiB.
- Temperatura 0, semilla 42, sin calentamiento, `keep_alive=0` en cada llamada.
- Texto, JSON y adjuntos: contexto 4096, salida máxima 512, timeout 120 s.
  Preset inicial de herramientas: contexto 8192 y límites guardados en el snapshot.
  Prueba con instrucciones explícitas: contexto 4096.
- Mismo modelo en ambas ramas, con prompts distintos. Son comparaciones de
  configuraciones, no evidencia de superioridad entre modelos.

## Resultados observados

| Prueba | Resultado A | Resultado B | Observación |
| --- | --- | --- | --- |
| Respuestas concretas, tres casos | 2/3 | 2/3 | `42` y `11:15` correctos. Ambas respuestas `Paris` fallan frente a `París` con texto exacto. |
| Extracción JSON, tres casos | 3/3 | 3/3 | Nombre y precio, booleano y teléfono ausente (`null`) correctos. El formato e indentación distintos no penalizan. |
| Pedidos con herramientas, cuatro casos | 0/3 evaluables; un límite de llamadas | 0/4 | Argumentos inventados, herramientas rechazadas por validación y respuestas finales que no cumplen JSON. |
| Pedidos con instrucciones explícitas, dos casos | 0/2 | 0/2 | Explicar los argumentos y pasos no resolvió la limitación en esta prueba. |
| Adjuntos TXT, JSON y CSV; un caso | 0/1 | 0/1 | Total esperado: `2×10 + 3×5 = 35`. Respuestas: 25 y 45. |
| Mismos adjuntos con contenido legible, un caso | 0/1 | 0/1 | Respuestas: 25 y 75. La mejora de presentación no demuestra mejora de precisión. |

Son 28 ejecuciones reales, con 27 respuestas evaluables y una ejecución que
alcanzó el límite de llamadas. Esta muestra pequeña de desarrollo verifica el
funcionamiento y descubre limitaciones; no es un benchmark representativo.
No se alteraron las referencias ni se relajó el evaluador para dar por correctas
respuestas incorrectas.

La primera consulta tardó unos 35 s; las siguientes consultas simples, unos 3 s.
El tiempo incluye carga del modelo e instrumentación. No se puede atribuir esa
diferencia al prompt ni usar estos tiempos como una comparación de rendimiento
controlada. `keep_alive=0` también puede provocar recargas entre llamadas a herramientas.

## Cambios y comprobaciones

Las respuestas desplegadas muestran ahora su estado, la referencia y el motivo
de evaluación. Así se puede distinguir un fallo literal, como `Paris`/`París`,
de una respuesta numérica incorrecta.

El contenido de los adjuntos se envía como texto con sus saltos de línea originales,
acompañado del nombre y tipo del archivo, en lugar de anidarlo en una cadena JSON
con comillas y saltos escapados. Esto facilita su lectura; no garantiza aciertos
del modelo. Las referencias siguen fuera de los mensajes de inferencia.

Se revisaron respuestas, argumentos y resultados de herramientas, identidad del
modelo y contadores de evaluación/errores. Los fallos de herramientas quedan en
las trazas; alcanzar un límite se contabiliza aparte de la puntuación de calidad.
Los modelos y binarios se guardan en `runtime/ollama`, excluido de Git.

Las seis comparaciones quedan en el historial de la cuenta local `test`:

- Texto: `297b2dca-e062-4d9c-bcb6-312fce4c8ed4`.
- JSON: `45c6b0a0-8d51-4af9-8123-0613b9aa0322`.
- Pedidos inicial: `bd888f45-3270-459c-95eb-2136e9004b28`.
- Adjuntos inicial: `02d70572-a01c-409d-80fb-6f3cf78aeb7e`.
- Pedidos explícito: `50ec7dc2-56bb-4a9e-b148-9b8e9c7875dc`.
- Adjuntos legibles: `7044a0b8-b944-411e-bad4-a1cd00c77cb0`.

Desde cada resultado se puede descargar el CSV y el informe con entradas,
configuración y respuestas. Los UUID corresponden a esta base local; no se crean
automáticamente al clonar el repositorio. Los resultados completos de esta sesión
también están en `runtime/real-comparison-results.json`,
`runtime/real-followup-results.json` y `runtime/real-readable-files.json`.

Fuentes de descarga: [Ollama para Windows](https://docs.ollama.com/windows),
[release 0.40.3](https://github.com/ollama/ollama/releases/tag/v0.40.3),
[modelo Qwen 2.5 3B](https://ollama.com/library/qwen2.5:3b).
