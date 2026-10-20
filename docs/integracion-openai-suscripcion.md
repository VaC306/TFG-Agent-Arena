# ChatGPT mediante la suscripción y el cliente oficial Codex

Implementación inicial local, 20 de octubre de 2026. No usa una API key ni copia
tokens de autenticación a Arena. Esta verificación no incluye un despliegue.

## Uso

1. Instala el [cliente oficial Codex](https://developers.openai.com/codex/cli),
   comprueba `codex --version` e inicia sesión con `codex login`, eligiendo ChatGPT.
   El acceso y las credenciales se gestionan en el cliente oficial.
2. Arranca Arena con el lanzador habitual. API y worker deben ejecutarse bajo el
   mismo usuario de Windows, con Codex accesible y la misma SQLite de Arena.
3. En Comparar, selecciona **ChatGPT · suscripción mediante Codex** y pulsa
   **Usar sesión de ChatGPT de este equipo**. También puedes vincularla en Perfil.
4. Elige un modelo del catálogo consultado al cliente, prepara la entrada y los
   prompts A/B y ejecuta. Cada rama inicia un hilo efímero independiente.
5. Revisa respuestas, referencias, condiciones y trazas en Resultados. La
   biblioteca conserva las fichas con la etiqueta ChatGPT · Codex.

La cuenta local de Arena y la cuenta ChatGPT son distintas. Solo vincula la sesión
de Windows si tienes permiso para usarla. Cada cuenta local debe vincularla
explícitamente. Desvincular de Arena conserva resultados y no hace `codex logout`.
Un cambio de cuenta en Codex requiere volver a vincularla.

Esta vía consume los límites compartidos de Codex. No ofrece uso ilimitado ni
créditos gratuitos de API. Según la configuración de la cuenta, pueden aplicarse
créditos adicionales; Arena no activa compras ni cambia esa configuración. El
catálogo no garantiza que todos los modelos estén habilitados para cada petición.
Ante un rechazo de acceso, cuota o conexión, se registra un error sin cambiar de
modelo, recurrir a otra cuenta o intentar una API key.

## Alcance y condiciones registradas

- Texto manual o casos CSV/JSONL, una o dos configuraciones/modelos del catálogo.
  Sin herramientas, imágenes ni otros adjuntos en esta primera conexión.
- Se mantienen evaluación exacta, JSON o sin evaluación, referencias locales,
  repeticiones, historial y borradores por cuenta. Las referencias nunca se envían.
- Se aplica el tiempo límite. Temperatura, semilla de inferencia, ventana de
  contexto y máximo de salida de Ollama no se trasladan a Codex. Los valores que
  conserva el contrato se identifican como **no aplicados** en las condiciones;
  no constituyen límites del proveedor. No hay calentamiento ni estudio de latencia
  para este adaptador. El orden de la cola sigue siendo local.
- Codex añade instrucciones internas, además del prompt de la rama y una
  instrucción de ejecución de texto. No es una llamada equivalente al chat web ni
  una comparación con parámetros idénticos a Ollama. Se registra esta diferencia.
- Los tokens se guardan cuando el cliente los comunica; si faltan quedan nulos.
  Incluyen el contexto del cliente y pueden incluir trabajo adicional del modelo.
  No se inventa tiempo de generación ni TPS del servidor remoto. Los recursos
  muestreados son del host y del worker, no del servidor remoto ni del proceso Codex.
- Se conserva el identificador solicitado y se comprueba que Codex lo acepte sin
  sustitución. No se dispone de digest verificable del modelo remoto; por ello no
  se habilita la creación de campañas que exigen identidad fijada por digest.

Cancelar o retirar la vinculación solicita interrumpir el turno y cierra el
proceso propiedad de esa ejecución. No equivale a demostrar que el servicio remoto
dejó de generar o consumir cuota instantáneamente. Cancelación, timeout y error
conservan categorías distintas. Un fallo al retirar un directorio temporal después
de recibir una respuesta completa se registra como aviso de limpieza, sin falsear
el resultado de inferencia.

## Implementación y límites de confianza

Se usa [Codex App Server](https://learn.chatgpt.com/docs/app-server) por stdio:
handshake, cuenta, catálogo, hilo efímero, turno, eventos finales y cancelación.
La [documentación de integración con ChatGPT](https://developers.openai.com/siwc/codex-app-server)
describe también esta vía oficial. Se mantiene la autenticación gestionada por el
cliente instalado; no se implementa un OAuth paralelo ni se leen archivos de auth.

Arena guarda únicamente una huella de la identidad por cuenta local y la fecha
de vinculación. Comprueba la identidad antes de enviar la entrada y exige cuenta
de tipo ChatGPT. No divulga el catálogo a cuentas locales sin vincular. Rechaza
proveedores alternativos y elimina API keys y URL base de OpenAI del entorno del
subproceso, sin modificar el entorno del usuario.

El proceso se inicia en un directorio temporal nuevo. Desactiva shell, navegación,
apps, hooks, imágenes, subagentes, plugins y servidores MCP mediante configuración
por proceso/hilo. Selecciona explícitamente cero entornos y herramientas dinámicas,
sandbox de lectura, cero documentos de proyecto y ninguna sustitución de modelo.
Rechaza instrucciones externas declaradas, solicitudes de permisos y eventos de
herramientas inesperadas. No persiste razonamiento privado ni eventos de cuenta.
Estas restricciones se han comprobado con el protocolo y cliente indicados abajo;
no constituyen una garantía sobre versiones futuras del cliente.

La instalación sigue siendo local y comparte la sesión del usuario del sistema
operativo; los perfiles de Arena no crean sesiones ChatGPT independientes. El
usuario puede revocar el acceso nativo con las herramientas oficiales. El modo
demo conserva un proveedor sin red: todas las nuevas operaciones están anuladas
o devuelven un estado local, sin heredar llamadas HTTP.

`ARENA_CODEX_COMMAND` es una opción de administración para indicar el comando local
como array JSON. No se acepta por HTTP ni se almacena en preferencias. Las pruebas
la usan para ejecutar `tests/fake_codex.py`; nunca representan inferencia real.

## Verificación y evidencia

Entorno: Windows, Python 3.11.9, Angular 20.3, Chromium de escritorio y Pixel 7
emulado. Cliente real: `codex-cli 0.163.0-alpha.10.2`, sesión de tipo ChatGPT con
plan `plus`. No se instalaron modelos, dependencias ni una suscripción nueva.

La prueba manual usa el lanzador existente sin cambios, puertos 58170/58171 y
`runtime/openai-manual-20261020-a/arena.sqlite`, creada para esta tarea. API y worker
comparten esa base. Solo se enviaron saludos ficticios. No se abrió ni modificó
`runtime/arena.sqlite` ni se eliminó historial.

Durante la verificación se corrigieron dos problemas detectados con el cliente
real: la ruta oficial `/backend-api/` rechazada por una validación demasiado
estricta y carreras/bloqueos de Windows al cerrar el proceso o retirar su directorio
temporal. Los intentos afectados permanecen en el historial ficticio como fallidos;
no se reescribieron para presentar un éxito.

Las pruebas controladas cubren protocolo, respuestas sin uso comunicado, referencias
no transmitidas, errores, permisos rechazados, timeout, cancelación, desvinculación,
cambio de identidad, aislamiento entre cuentas, notificaciones anteriores al ack,
endpoint alternativo y limpieza de Windows. Los recorridos de navegador verifican
vinculación, teclado, ambos temas, escritorio/móvil, resultados y demo sin API.

Las capturas se guardan en `runtime/openai-evidence/`. Son evidencia de una
verificación técnica por un agente, no una prueba con participantes ni resultados
de investigación UX. Las cuotas, acceso a todos los modelos, concurrencia elevada,
otros sistemas operativos y versiones futuras no se han validado exhaustivamente.

Resultado manual final: comparación `920affd3-9d59-4f8b-b9c4-3208065232d0`, modelo
`gpt-6-luna` en ambas ramas, respuesta `hola` en A y B, ambas `completed` sin
referencia, sin errores ni avisos de limpieza. Tokens comunicados: A 7417/5,
B 7422/5; incluyen contexto interno del cliente. No se deduce de ello el saldo
restante, coste monetario ni calidad del modelo. Evidencia visual:
[respuestas reales, tema claro](../runtime/openai-evidence/real-chatgpt-responses.jpg)
y [tema oscuro](../runtime/openai-evidence/real-chatgpt-responses-dark.jpg).

Comprobaciones ejecutadas:

- Regresión backend: 277 pruebas aprobadas. Tras ampliar la limpieza temporal,
  las 18 pruebas focales de esta integración volvieron a pasar; no se suman ambos
  números porque las suites se solapan. Un aviso previo de deprecación de
  Starlette/AnyIO, sin fallo.
- Frontend: 55 pruebas unitarias y compilaciones local/demo aprobadas.
- Navegador: pasada completa de 68 E2E aprobada, escritorio y móvil. Las cuatro
  de ChatGPT se repitieron tras el ajuste final de los parámetros no aplicados: cuatro aprobadas.
- Demo de producción: escritorio/móvil, navegación, descargas, recuperación y
  ausencia de solicitudes a la API aprobados. Typecheck E2E aprobado.

Los fallos intermedios de pruebas no se ocultaron con retries: se corrigieron un
selector/etiqueta de cancelación, la expectativa antigua de ChatGPT «futuro» y se
reinició el backend de pruebas al cambiar la validación de su ruta oficial.
