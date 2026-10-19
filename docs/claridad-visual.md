# Interfaz y lectura visual

La interfaz se organiza en una vista breve y detalles que se abren cuando hacen
falta. Se mantienen la evidencia ejecutada, la navegación, los borradores por
cuenta y la apariencia Sistema / Claro / Oscuro.

## Preparar una comparación

1. Elige un modelo con dos prompts o dos modelos, el nombre y el motor.
2. **Datos de entrada**: escribe la entrada compartida o importa el dataset.
   Adjuntos, referencia opcional y vista previa de casos tienen desplegables
   propios. Entradas independientes conserva su advertencia visible.
3. **Variantes A/B**: elige los modelos y tipos de prompt. Las instrucciones
   completas se pueden editar en cada rama.
4. **Condiciones de ejecución**: abre este bloque para cambiar repeticiones,
   evaluación, fase y parámetros. Son los mismos controles y valores previos.
5. **Revisar y ejecutar**: comprueba motor, datos, repeticiones, evaluación y
   variables que cambian antes de ejecutar. Los errores y los adjuntos que hay
   que reseleccionar permanecen visibles.

## Leer los resultados

El resumen muestra finalizadas, pendientes, errores de ejecución y canceladas.
La banda de progreso distingue los estados; finalizar no equivale a acertar.
Primero aparecen las respuestas A/B. Se muestran los tres primeros pares de
caso/repetición; el botón para ver todos indica el total y lleva el foco al primer
par recién revelado. Al reducir, el foco vuelve al primer par. No se eliminan ni
reescriben resultados.

Las dos barras de estados usan el total de ejecuciones programadas como
denominador. Separan correctas, incorrectas, formato inválido, error de ejecución,
cancelación, sin evaluar y pendientes. Las leyendas tienen nombres y números;
el gráfico expone el recuento completo mediante su nombre accesible. La fracción
de aciertos sobre casos con referencia y el número de respuestas evaluadas se
muestran por separado. Una respuesta sin referencia no se representa como fallo.

**Ver análisis de tiempos y métricas** abre los puntos A/B y las métricas
detalladas. Ambos puntos comparten una escala desde cero hasta el mayor tiempo
medio disponible. El tiempo procede del resumen guardado, incluye preparación
y puede incluir carga, calentamiento y muestreo. No es latencia pura de generación.
Una medición de cero se dibuja en cero; un valor ausente o sin respuestas medidas
se indica como «Sin mediciones» y no se dibuja. Se explican las condiciones y la
limitación de la ejecución secuencial, sin declarar ganadores.

## Biblioteca, campañas y trazas

- **Biblioteca**: fichas compactas con tipo, fecha y distribución visual. Métricas,
  parámetros, identidad y evidencia completa están en «Ver métricas y condiciones».
  La selección se conserva frente a filtros; «Restablecer filtros» facilita salir
  de un resultado vacío. Las diferencias declaradas continúan visibles.
- **Campañas**: la evolución muestra, por intento, A y B en una escala fija
  de 0–100 % de aciertos sobre casos con referencia. Cada punto conserva sus
  recuentos; las ramas no se fusionan ni se calcula una clasificación. Solo se
  dibujan intentos completos, compatibles e incluidos por el análisis existente.
  Los excluidos y los parciales siguen en la lista con su razón, sin puntos;
  «Intentos» abre la tabla completa y las anotaciones. «Exportar evidencia» reúne
  las descargas. No se reconstruyen campañas en la demo sin evidencia exportada.
- **Trazas**: una secuencia numerada muestra los eventos realmente registrados.
  Cada paso se abre para consultar su explicación y su JSON. Los números indican
  orden de presentación; se conserva también el identificador original del evento.
  Escape cierra la traza y devuelve el foco al control de origen.

Los gráficos se construyen con HTML y CSS, sin librerías nuevas ni peticiones
adicionales. Las variantes local y demo comparten la presentación; la demo sigue
utilizando exclusivamente sus archivos estáticos. Se mantienen los cálculos,
clasificaciones, informes y condiciones del backend.

## Verificación

Las reglas de recuento, denominadores, valores ausentes y exclusiones están
cubiertas en `frontend/tests/visual-data.test.cjs`. Los recorridos de teclado,
orden visual, despliegue de casos, conservación del snapshot y exclusión de
intentos están en `frontend/e2e/visual-hierarchy.spec.ts`. Las suites anteriores
conservan sus aserciones y abren explícitamente los nuevos desplegables para
revisar tablas y exportaciones. No se han añadido reintentos.

Resultados de ejecución, capturas y límites: [registro de la auditoría UX](auditoria-ux-2026-10-13.md).
