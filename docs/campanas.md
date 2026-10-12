# Campañas experimentales

Una campaña conserva el diseño de una comparación terminada y permite ejecutarlo
de nuevo. Cada intento tiene UUID, ejecuciones, métricas y trazas independientes.
La comparación original se incorpora como intento 1 sin reescribir su snapshot.

## Uso desde Angular

1. Configura y termina una comparación, personalizada o de un preset existente.
2. En **Resultados**, escribe el nombre y pulsa **Crear campaña**.
3. En **Campañas**, revisa los datos, prompts, parámetros y condiciones fijados.
4. Pulsa **Repetir diseño**. El worker habitual procesará el intento nuevo.
5. Consulta la evolución por intento; abre cualquiera de ellos para ver respuestas,
   referencias, cancelaciones y trazas. Descarga CSV, Markdown o JSON de la campaña.

No se modifica el diseño dentro de una campaña. Para cambiar dataset, referencia,
prompt, parámetros, fase o repeticiones, crea otra comparación y otra campaña.
El selector conserva todas las campañas de la cuenta, aunque sus comparaciones
ya no aparezcan entre las últimas 50 del historial.

## Qué se conserva y qué se observa de nuevo

Se fijan configuración, endpoint de Ollama, tareas, referencias, adjuntos, entornos,
fase, evaluación, límites, repeticiones, semilla de orden y condiciones declaradas.
La variable `ARENA_OLLAMA_URL` no sustituye el endpoint al repetir una campaña.
El SHA-256 del diseño identifica esos campos; las identidades observadas de los
modelos se conservan por separado en `expected_models`.

Para campañas reales se requieren identidades verificadas y estables en todas las
ejecuciones de la comparación inicial. Se fija la huella que incluye identificador,
digest, versión de Ollama y configuración declarada por el servidor. Antes de
cada nueva ejecución se comprueba esa huella; si cambia, se registra un error y
no se envía la entrada al modelo. Cambiar el modelo requiere una campaña nueva.
El adaptador no descarga modelos ni sustituye inferencia real por simulación.

Cada intento captura el código, fuentes/hashes, host y dependencias actuales.
Se indican cambios respecto al origen; esos intentos permanecen visibles y
exportables, pero no se presentan como condiciones coincidentes. El hardware
registrado es el del host de la API; con Ollama remoto no identifica necesariamente
el servidor de inferencia. GPU/NVML pueden no estar disponibles. Carga externa,
estado térmico y actividad de otros programas necesitan registro del operador.
Una semilla fija no garantiza respuestas idénticas ni latencias idénticas.

## Lectura de la evolución

La tabla conserva aciertos/casos con referencia evaluable, respuestas evaluadas,
incorrectas, formatos inválidos, errores de ejecución, respuestas sin evaluar,
pendientes, tiempo medio y número de mediciones. Se usa el mismo resumen que
Resultados y la biblioteca. Sin referencias o mediciones, muestra «—».
Los resultados parciales se identifican; los errores no cuentan como respuestas
evaluadas y no entran en el tiempo medio de respuestas.

**Condiciones** compara cada intento con el diseño de origen y sus condiciones
registradas; no demuestra que A y B tengan instrucciones o entradas equivalentes.
Las diferencias de prompts, entradas o parámetros entre ramas se advierten.
Una campaña puede repetir una comparación de configuraciones.

El [análisis por tarea](analisis-por-tarea.md) agrega solo intentos terminados
compatibles, separa calidad y cobertura y muestra cambios de estados. Incluye
diferencias emparejadas descriptivas e incertidumbre exploratoria bajo condiciones
conservadoras; no declara rankings ni ganadores.
Las repeticiones del mismo caso no son muestras independientes.
La política de calentamiento heredada se mantiene; esta versión no introduce
warmup ni ejecución simultánea. El muestreo de recursos sigue siendo discontinuo.

## Persistencia, solicitudes y borrado

SQLite añade `campaigns` y `campaign_attempts` sin borrar ni modificar experimentos
existentes. Las campañas, sus intentos y sus exportaciones están restringidos a
la cuenta propietaria. Vaciar el historial también elimina las campañas y sus
copias de entradas, adjuntos y fuentes; la confirmación lo indica. Sigue estando
bloqueado cuando hay ejecuciones pendientes.

Solo se permite un intento pendiente por campaña. La inserción del experimento,
sus ejecuciones y su enlace se realiza en una transacción. La secuencia no se
duplica si dos solicitudes llegan a la vez. Crear una campaña desde el mismo
experimento devuelve la existente. Repetir utiliza un UUID de solicitud:
reintentar con la misma clave devuelve el mismo experimento, incluso después
de terminar. Tras una respuesta perdida, la interfaz exige actualizar y reconoce
si el intento ya se guardó. Conserva la clave mientras vive ese componente;
tras recargar o navegar, revisa los intentos antes de repetir una solicitud dudosa.

## API y exportaciones

- `POST /campaigns`: `{name, experiment_id}`; requiere comparación terminada.
- `GET /campaigns`: campañas y progreso de la cuenta.
- `GET /campaigns/{id}`: diseño fijado y evolución de todos los intentos.
- `POST /campaigns/{id}/attempts`: `{request_id}` con UUID; no acepta cambios de diseño.
- `GET /campaigns/{id}/export.csv`: una fila por intento y rama.
- `GET /campaigns/{id}/analysis.csv`: una fila por tarea y rama con series y cobertura.
- `GET /campaigns/{id}/export.md`: diseño, modelos fijados, contadores y advertencias.
- `GET /campaigns/{id}/export.json`: snapshot de origen, snapshots/fuentes y resultados
  de cada intento, además de los mismos resúmenes. No incluye las trazas completas;
  se consultan en las comparaciones o se exportan con la CLI.

Se aplican la sesión local y `X-Arena-Request: 1` habituales. El JSON lee las
ejecuciones una sola vez por intento para que los contadores y los resultados
incluidos no describan estados diferentes si el worker termina durante la descarga.
Todas las exportaciones pueden ser parciales mientras queden trabajos pendientes.

## Verificación del 12 de octubre de 2026

Base aislada `runtime/campaign-smoke/arena.sqlite`; API 8011 y Angular 4201.
Se lanzó desde navegador el preset simulado de pedidos: cuatro casos de desarrollo,
dos ramas, dos repeticiones por caso. Se fijó una campaña y se repitió el diseño.
Los dos intentos terminaron con 8/8 aciertos por rama, 32 ejecuciones simuladas
en total. Estos resultados prueban la plataforma, no modelos reales.

Campaña: `f3eebe5a-ab79-48b7-9b63-65474a5dff49`.
Origen: `562999da-d980-42a0-918b-3c53dd22371e`.
Segundo intento: `ecd483c6-693e-49cd-870c-a2b614093c29`.

Se descargaron los tres formatos desde Angular y se comprobaron cuatro filas A/B,
contadores, igualdad de configuración y hash de datos entre los intentos.
Los artefactos locales están en `runtime/campaign-smoke/campaign.*` y la captura
en `runtime/campaign-smoke/campaign-desktop.jpg`; no son evidencia de inferencia real.
Se comprobó apertura del segundo intento, retorno a la campaña, persistencia tras
recarga, error/recuperación de API y ausencia de errores de consola. A 320/390 px
no hubo desbordamiento horizontal de la página; la tabla responde a las flechas
con teclado y la navegación enfoca el título.

Las pruebas de integración cubren aislamiento de cuentas, referencias/adjuntos
de ramas independientes, diseño inmutable, peticiones concurrentes, idempotencia,
borrado coherente, informes parciales y cambios de código/equipo/condiciones.
Los cambios de digest y versión del servidor se verifican con un adaptador
controlado, comprobando que no recibe ninguna llamada de chat del nuevo intento.
No se volvió a ejecutar un modelo real para esta funcionalidad.

Controles: 188 pruebas Python y 22 del frontend, compilación Angular de producción
y `pip check`. Las pruebas de componentes sustituyen Angular/HTTP y se complementan
con la comprobación manual de navegador. No equivalen a una auditoría completa
de accesibilidad. La verificación posterior del análisis por tarea está documentada
en [su metodología y resultados](analisis-por-tarea.md). Siguientes mejoras:
campañas con anotaciones de condiciones externas y estado del worker.
