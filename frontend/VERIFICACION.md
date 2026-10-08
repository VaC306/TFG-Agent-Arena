# Verificación de la primera interfaz

Fecha: 8 de octubre de 2026. Node 22.16.0, npm 10.9.2, Angular 20.3.33,
CLI/build 20.3.39 y TypeScript 5.9.3. Navegador integrado de escritorio.

## Comprobaciones realizadas

| Comprobación | Resultado observado |
| --- | --- |
| Instalación npm y build de producción | Correctos; lockfile guardado |
| API desconectada / proxy incorrecto | Mensaje de error y opción de actualizar; proxy corregido y probado |
| Historial persistido | Tres experimentos previos cargados; nuevo experimento añadido tras lanzar |
| Lanzamiento simulado | 16 ejecuciones en cola creadas desde el formulario |
| Cancelación en cola | Una ejecución de B pasa a Cancelada y conserva su fila |
| Worker y actualización automática | Quince ejecuciones restantes correctas, progreso 16/16 |
| Resumen A/B | A: 8/8; B: 7/8, sin ocultar la cancelación |
| Filtro de rama | B muestra ocho filas |
| Traza | Respuesta final, evaluación y eventos de herramientas visibles |
| Exportar CSV | Descarga metrics.csv desde el proxy de Angular |
| Vista móvil de 390 px | Sin desbordamiento horizontal de la página; historial y tabla con scroll propio |

La evidencia del experimento se exportó a `experiments/ui-smoke-2026-10-08`.
La captura está en `docs/figuras/interfaz-angular.png`. Se mantienen las
exportaciones anteriores intactas. No se ha probado Ollama real ni despliegue
de frontend en Docker. Estas verificaciones de navegador fueron interactivas;
no se presenta una suite E2E automatizada como si se hubiese ejecutado.

## Repetir la comprobación

1. Arranca API y Angular según el README, inicialmente sin worker.
2. Selecciona Simulado, consulta el preset y pulsa Lanzar comparación.
3. Cancela una ejecución B en cola; sus métricas ausentes deben mostrar «—».
4. Arranca el worker y espera a que terminen las quince restantes.
5. Comprueba los porcentajes, filtra por B y abre la traza de una ejecución correcta.
6. Descarga el CSV, recarga la página y comprueba que el historial se conserva.
7. Comprueba un ancho móvil y navegación de teclado. Una auditoría completa de
   accesibilidad y pruebas E2E automatizadas quedan pendientes.
