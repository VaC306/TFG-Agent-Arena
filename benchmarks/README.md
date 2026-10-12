# Datasets y pruebas reproducibles

`v1/` contiene casos sintéticos, fixtures TXT/JSON/CSV, tareas con herramientas,
prompts, parámetros y un manifiesto SHA-256. No contiene datos personales,
credenciales, modelos descargados ni resultados presentados como universales.

La batería inicial separa desarrollo (`dev`) y evaluación (`eval`). Los ejemplos
permiten comprobar la plataforma y explorar limitaciones; no representan todos
los usos de un modelo. Las versiones publicadas son inmutables: para cambiar
referencias, entradas, fixtures o parámetros, crea una nueva versión.

Consulta [las instrucciones de v1](v1/README.md),
[el protocolo de evaluación](../docs/protocolo-evaluacion.md) y
[la investigación de herramientas](../docs/diagnostico-herramientas.md).
