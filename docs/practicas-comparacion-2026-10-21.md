# Prácticas de interfaces de comparación aplicadas a Arena

Revisión de documentación oficial el 21/10/2026. Se revisan funciones documentadas;
no se ha realizado una prueba con usuarios de estas herramientas.

| Herramienta | Práctica observada | Aplicación en Arena |
| --- | --- | --- |
| [Promptfoo: web viewer](https://www.promptfoo.dev/docs/usage/web-ui/) | Selección de columnas, filtros por resultados, detalle de la evidencia y exportación CSV/JSON. | Selector de métricas que se aplica a gráficos, tabla y CSV. Se conserva el detalle de barras y el resultado original. |
| [Braintrust: compare experiments](https://www.braintrust.dev/docs/evaluate/compare-experiments) | Tabla resumen de experimentos, ordenación para encontrar diferencias y comparación con una referencia explícita. | Vista de tabla compacta con muestras, ordenación común de modelos y botón para abrir la evidencia. |
| [LangSmith: compare experiment results](https://docs.langchain.com/langsmith/compare-experiment-results) | Controles para mostrar/ocultar métricas, vistas compactas, dirección de las métricas y acceso al detalle. | Cambio Gráficos/Tabla, dirección y unidad en los encabezados, navegación desde cada fila al experimento. |

Estas adaptaciones son decisiones de diseño de Arena, no recomendaciones
textuales de los fabricantes ni resultados de investigación UX.

## Implementado

- **Vista Gráficos/Tabla** sobre las mismas fichas, sin solicitar nuevas inferencias.
- **Ordenar modelos** por nombre, aciertos, tiempo medio o coste estimado. El mismo
  orden se aplica a todos los gráficos y a la tabla. Los datos ausentes van al final
  y los empates conservan el orden anterior. Ordenar no establece una superioridad
  general ni elimina diferencias entre pruebas.
- **Métricas visibles**: al menos una de las ocho métricas; el selector controla
  gráficos, columnas y CSV. Cambiar de vista conserva la elección mientras la
  biblioteca permanezca abierta.
- **Tabla con muestras**: valor y denominador o número de respuestas medidas,
  proveedor y variante. La columna de modelo permanece visible al desplazar la
  tabla horizontalmente. El enlace abre respuestas, referencias y trazas originales.
- **CSV de la comparativa visible**: mismas fichas, métricas y orden. Conserva
  precisión numérica, unidades, ausencia de datos, identificación de la fuente,
  fase y tarifas configuradas. Etiqueta el coste como estimado y los valores como
  descriptivos. Las cadenas que podrían ejecutarse como fórmulas se neutralizan.

Se mantienen barras verticales, colores por proveedor, etiquetas independientes del
color, detalles con hover/teclado/toque, escalas desde cero y advertencias de
comparabilidad. No se agregan resultados de condiciones diferentes.

## Prácticas que merecen una siguiente iteración

1. **Filtrar casos por fallos y diferencias**, como Promptfoo, para pasar del
   resumen al caso que explica la diferencia. Una respuesta distinta no implica
   por sí sola un resultado incorrecto.
2. **Referencia explícita y deltas**, como Braintrust y LangSmith. Deben controlar
   datos, evaluador, repeticiones y condiciones antes de presentar regresiones
   o mejoras; las comparaciones remotas sin digest requieren un tratamiento
   descriptivo explícito.
3. **Guardar vistas por cuenta**: conservar filtros, columnas y orden sin mezclar
   preferencias ni tarifas de usuarios distintos.

No se han instalado servicios de terceros ni enviado los benchmarks a esas
plataformas. Los resultados reales previos siguen intactos.
