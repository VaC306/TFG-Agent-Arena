# Grafana y referencias visuales

Consulta: 9 de octubre de 2026.

## Grafana

Grafana consulta fuentes de datos y las presenta en paneles; también permite alertas.
Es complementario a la API, el worker y la interfaz Angular. No sustituye la ejecución
de comparaciones ni la evaluación de respuestas.

Para Agent Arena podría mostrar tiempos por modelo, fallos, cola y consumo de recursos
a lo largo del tiempo. Dos caminos posibles:

- Un plugin SQLite sobre una base de resultados con acceso de lectura: menos infraestructura,
  pero dependencia de un plugin externo y de nuestro esquema.
- Instrumentación Prometheus más Grafana: apropiada para monitorización continua, requiere
  un endpoint de métricas, recolección y servicios adicionales. Evitar prompts, respuestas e IDs
  de ejecución como etiquetas de métricas para no aumentar cardinalidad ni exponer contenido.

Recomendación para esta fase del TFG: mantener los resultados de cada experimento en Angular/CSV
y plantear Grafana como extensión opcional cuando la observabilidad sea un objetivo concreto.
Al medir rendimiento en la misma máquina, los servicios de monitorización consumen recursos;
su presencia debe registrarse y mantenerse constante entre experimentos.
No se ha instalado Grafana ni se afirma que exista una integración actual.

Fuentes primarias:

- [Fuentes de datos en Grafana](https://grafana.com/docs/grafana/latest/datasources/).
- [Plugin SQLite de la comunidad](https://grafana.com/grafana/plugins/frser-sqlite-datasource/).
- [Grafana con Prometheus](https://prometheus.io/docs/visualization/grafana/).

## Referencias para elegir dirección

La valoración estética es una propuesta subjetiva. Son referencias para conversar sobre
tipografía, densidad y jerarquía; no plantillas para copiar ni activos para reutilizar.

| Referencia | Dirección propuesta para explorar |
| --- | --- |
| [Are.na](https://www.are.na/) | Herramienta sobria, contenido y tipografía en primer plano. |
| [Cosmos](https://www.cosmos.so/) | Colecciones visuales y más espacio para el contenido. |
| [Notion](https://www.notion.com/product) | Interfaz de trabajo discreta y organización clara. |

[Discusión de r/webdesign](https://www.reddit.com/r/webdesign/comments/1m2om61)
sobre la repetición de tarjetas, sombras y paletas en páginas generadas. Es una observación
de comunidad, no una regla universal ni un estudio de usabilidad.

Dirección sugerida para evaluar: reducir contenedores anidados y adornos, dar prioridad a una
tabla de casos legible, agrupar formularios por tarea y emplear color para estados y acciones.
El usuario eligió Cosmos. La interfaz toma como referencia su amplitud, tipografía destacada,
paleta neutra y navegación discreta: cabecera superior, historial desplegable, formularios
sin tarjetas anidadas, superficies suaves para datasets y respuestas y botones principales
oscuros. No se han copiado imágenes, fuentes ni código de Cosmos. Se mantienen los estados
visibles, foco por teclado y una composición de una columna en móvil.
