# Condiciones externas y estado del worker

## Anotaciones por intento

En **Campañas**, selecciona un intento y registra las condiciones observadas.
Una anotación conserva UUID, texto, tipo y fecha de registro. Puede describir
carga externa, incidencias o estado térmico; es una declaración del operador,
no una medición automática. Si se añade después, el texto debe indicar cuándo
ocurrió. El timestamp identifica el registro, no necesariamente el suceso.

Hay dos tipos:

- **Diferencia de condiciones** (por defecto): el intento se excluye del análisis
  compatible y se suprime el intervalo de campaña. La biblioteca impide una
  comparación directa aunque coincidan las demás condiciones.
- **Observación**: conserva la compatibilidad registrada. No certifica que las
  condiciones externas fueran idénticas. Una diferencia conocida debe registrarse
  como diferencia, no ocultarse en una observación.

Las anotaciones son acumulativas: no se editan ni borran individualmente, y no
reescriben snapshots, métricas o el diseño congelado. Para aclarar un registro,
añade otro; una aclaración no elimina una exclusión previa. El vaciado explícito
del historial elimina también las anotaciones de esa cuenta.

`POST /campaigns/{id}/attempts/{experiment_id}/annotations` acepta
`{request_id, kind, text}`: UUID de solicitud, `observation` o `deviation`, y texto
no vacío de hasta 2.000 caracteres. Reintentar el mismo contenido con la misma
clave no duplica la nota, incluso con solicitudes simultáneas. Reutilizar la
clave con contenido distinto devuelve 409. El acceso se restringe al propietario.
Tras un fallo de red, el componente mantiene contenido y clave para reintentar;
tras navegar o recargar, revisa las anotaciones antes de reenviar.

Campañas incorpora las notas en JSON, Markdown y CSV de evolución. Resultados las
incluye en avisos de protocolo, JSON reproducible, Markdown y CSV de ejecuciones.
La biblioteca muestra las declaraciones junto a las condiciones. El paquete CLI
añade `operator-annotations.json` y las incluye en el resumen. Una diferencia
declarada suprime también el valor p del resumen CLI. Los informes históricos
descargados antes de registrar una nota no se actualizan automáticamente.

## Señal periódica del worker

Cada proceso nuevo registra un UUID y una señal al iniciar, cambiar entre reposo
y trabajo, y finalizar normalmente. Durante la ejecución actualiza la señal
cada dos segundos. Se mantiene en SQLite junto a la cola; API y worker deben
apuntar a la misma base. Workers de versiones anteriores no emiten esta señal.

`GET /worker/status` requiere sesión y devuelve:

- `active`: hay al menos una señal de un proceso no detenido de los últimos 15 s.
- `unobserved`: nunca se registró una señal en esta base.
- `no_recent_signal`: no hay una señal reciente de un proceso activo.

La interfaz consulta cada 2,5 s mientras Campañas está abierta. Ante un fallo de
API retira el estado anterior y muestra que no se pudo comprobar. Muestra número
de workers activos/ocupados, momento de comprobación y cola/antigüedad máxima
exclusivamente de la cuenta actual. No revela entradas, IDs ni colas de otras
cuentas. Los workers son compartidos: uno activo puede estar atendiendo otra
cuenta. La ejecución sigue siendo secuencial globalmente.

Una señal reciente acredita actividad del proceso, no progreso de una inferencia
ni disponibilidad de Ollama. La ausencia puede deberse a detención, bloqueo,
versión antigua o pérdida de acceso a SQLite. No demuestra por sí sola que sea
seguro recuperar un trabajo. Un cierre abrupto puede dejar `running`; no se
reencola ni cambia automáticamente. Detén todos los workers y usa la recuperación
manual descrita en [operación local](operacion-local.md). La tabla de señales
contiene datos operativos y no se incorpora como condición experimental medida.

## Verificación

Controles: **210 pruebas Python**, **28 del frontend**, compilación Angular y
`pip check`, correctos. TestClient mantiene una advertencia de deprecación de
AnyIO. Las cinco pruebas nuevas del backend cubren propiedad, validación,
idempotencia concurrente, conservación de snapshots, exclusión, exportaciones,
borrado por cuenta, señales múltiples/caducadas, señal durante una ejecución
bloqueada controlada, cancelación y excepciones. Las cuatro pruebas nuevas de
componentes cubren coalescencia/recuperación del estado, reintento de anotación
tras respuesta incierta, navegación durante guardado y bloqueo de comparación.

La comprobación de navegador usa una **copia** de la base simulada anterior,
`runtime/conditions-smoke/arena.sqlite`; el historial original no se modifica.
Se observó ausencia inicial de señal, proceso worker real activo en reposo y
posterior ausencia de señal reciente al detenerlo. No se llamó a modelos ni se
descargaron modelos. El heartbeat durante inferencia se verificó con una
ejecución bloqueada controlada, no con Ollama real.

Se guardó con teclado una diferencia explícitamente de prueba para el intento 2:
el análisis pasó de 2/2 a 1/2 intentos incluidos. Persistió tras recarga y las
descargas JSON/CSV coincidieron en notas y compatibilidad. A 320/390 px no hubo
desbordamiento horizontal. La accesibilidad completa sigue pendiente. Artefactos
locales ignorados: `runtime/conditions-smoke/campaign.{json,csv}` y capturas.

Quedan pendientes monitorización de recursos periódica, política de calentamiento
y experimentos reales amplios con casos reservados. Las declaraciones manuales
no reemplazan esos controles ni garantizan reproducibilidad entre máquinas.
