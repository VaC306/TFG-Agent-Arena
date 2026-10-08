# Evidencia experimental

Las carpetas fechadas el 8 de octubre de 2026 contienen exclusivamente
ejecuciones del adaptador simulado. No hay resultados de inferencia real.

| Carpeta | Alcance |
| --- | --- |
| simulated-dev-2026-10-08 | Primera ejecución de desarrollo; conserva la versión previa a los ajustes finales |
| simulated-dev-final-2026-10-08 | Desarrollo con el motor final: cuatro tareas, dos ramas, dos repeticiones |
| simulated-eval-2026-10-08 | Evaluación con el motor final: cuatro tareas, dos ramas, una repetición |
| ui-smoke-2026-10-08 | Prueba funcional Angular: 16 ejecuciones, una cancelación B intencionada y 15 éxitos |

Cada carpeta conserva configuración y entorno en snapshot.json, resultados
individuales en runs.json, trazas en events.jsonl, métricas en metrics.csv y
resumen emparejado en summary.json. Los snapshots finales incluyen el texto y
hash de las fuentes Python del motor; el snapshot inicial solo incluye hashes.

Los tiempos del runner son mediciones de la plataforma; los tokens y duraciones
de generación que devuelve el simulador son valores sintéticos. La semilla de
orden es 42. No se ha realizado warmup. Los datos de pedidos son ficticios.

El commit base registrado corresponde al repositorio antes de estos cambios;
las fuentes y hashes del snapshot identifican la implementación efectiva.
Cada nueva repetición debe guardarse en una carpeta nueva. No modifiques las
exportaciones originales para actualizar la documentación.
