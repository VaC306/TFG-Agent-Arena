# Continuación UX autorizada, 20/10/2026

La exploración inicial se realizó antes de leer auditorías, explicaciones del diseño, E2E o componentes. Se cerraron sus notas antes del contraste. Es una aproximación de un agente: no hubo participantes ni resultados de investigación con personas. El usuario aprobó implementar los bloques A–F del plan y pidió revisar después cómo usar Claude con una suscripción, sin API key.

Inicio en `main`, HEAD `55da3b3f9bd8dbdaccd38af7c67c34fad4097de8`, Git limpio. No se encontraron AGENTS.md aplicables en las ubicaciones comprobadas. No se hicieron commits, pushes, publicaciones o cambios al lanzador.

## Cambios

| Bloque | Implementación y aceptación |
| --- | --- |
| A | «Entrada de este caso» junto al título del par A/B. Se lee el caso correspondiente del snapshot ejecutado; se separan ramas independientes incluso si tienen el mismo texto. Una entrada no exportada se declara ausente. No se consulta ni modifica el borrador. |
| B | La evaluación pendiente se reserva a estados en cola/en curso. Cancelaciones terminales indican que no tienen evaluación por cancelación. Un motivo original conservado sigue accesible. Sin cambios en categorías, denominadores, informes o mediciones ausentes. |
| C | Tras cierre de sesión confirmado se reemplaza la ruta activa por Comparar sin IDs. No se borran borradores ni historial; el login ordinario y los enlaces profundos deliberados conservan su funcionamiento. |
| D | El botón inicial y el de ayuda anticipan «recorrido simulado de pedidos». El aviso existente aclara que el simulador no genera respuestas a instrucciones personalizadas. Se mantiene el preset y su evidencia. |
| E | Etiquetas «Instrucciones (prompt) A/B»; dentro de condiciones, evaluación/repeticiones antes de un desplegable de parámetros avanzados. Mismos valores, controles, validación y cuerpo enviado. «Modelos» conserva su nombre. |
| F | Campañas vacías ofrece continuar a resultados válidos o preparar comparación. Cambiar de sección limpia avisos anteriores. Las confirmaciones tardías se conservan sin redirigir; cancelar identifica caso y variante. |

No se añadieron dependencias, gráficos ni proveedores de inferencia. Demo local comparte presentación y sigue siendo solo consulta. Se mantienen temas, foco, snapshots, rutas, borradores por cuenta y cancelaciones separadas de errores. E responde a una hipótesis de comprensión aprobada: una verificación técnica no demuestra mejora con personas.

## Pruebas

- Frontend: **52 pruebas aprobadas**. Tres nuevas sobre entrada por caso, separación/ausencia por rama y evaluación según estado; otra sobre avisos y confirmación tardía. Se prueban funciones reales de presentación, sin mutar los snapshots.
- Compilaciones local y demo: correctas, sin advertencias de presupuesto. TypeScript de E2E correcto.
- Backend: **261 pruebas aprobadas**, en 65,52 s. Permanece el aviso previo de deprecación Starlette/AnyIO.
- Demo compilada: escritorio 1440 × 1000 y móvil 390 × 844; primer pintado, temas, navegación, filtros, descargas, ausencia de datos, error/reintento y recuperación parcial aprobados. Se añadieron entrada del caso y cancelación histórica sin evaluación pendiente. El registro de peticiones rechaza cualquier API/servicio externo. No se montan controles de ejecución.
- Suite completa E2E final: **64 aprobadas**, 32 en Chromium de escritorio y 32 en móvil emulado, en 4,6 minutos, sin reintentos. Incluye los recorridos de respuestas tardías 200/401 y las regresiones previas.

La primera pasada E2E tuvo **60 aprobadas y 4 fallidas**: la misma expectativa histórica de volver a Perfil tras registrar otra cuenta, en 200/401 tardíos y ambos viewports. La nueva ruta deliberadamente vuelve a Comparar. Se actualizó esa expectativa para comprobar título y foco en Comparar, conservando todas las comprobaciones de datos ajenos, sesión nueva y recarga. No se añadieron reintentos ni se relajaron las verificaciones de aislamiento. La repetición completa usa otra base/puertos.

Seis recorridos nuevos de navegador (tres por viewport) verifican entradas compartidas de dos casos/dos repeticiones, entradas independientes A/B, snapshot anterior inmutable, evaluación sin abrir avanzados, contraste en ambos temas, cierre de sesión, borrador por cuenta y enlace profundo válido, vacíos de campaña y avisos contextuales. Las pruebas existentes de cancelación real con adaptador controlado comprueban ahora también la etiqueta terminal.

## Entorno y comprobación visual

E2E crea una SQLite nueva en `arena-e2e-*` bajo la carpeta temporal, con dos puertos reservados y API/worker en la misma base. API de primera pasada: 49705; repetición final: 61840. Adaptador de inferencia y sensores controlados, identificados como tales; no Ollama ni mediciones de hardware reales.

Navegador integrado adicional con lanzador original: API 8140, UI 4340, base nueva `runtime/ux-implementation-20261020-a/arena.sqlite`. Cuenta ficticia `revision-final`, entrada ficticia de ayuda para comparar instrucciones. Se comprobó el atajo de campaña, preparación con teclado, evaluación antes de parámetros avanzados y entrada del resultado. Inspección en escritorio oscuro y móvil 390 × 844 claro.

Demo de producción existente después de recompilar, servida en 4341 sin API/proxy: recorrido guardado, cancelación histórica y «Sin evaluación: ejecución cancelada» con mediciones ausentes. No se alteró la evidencia histórica para producir la captura.

Capturas manuales: `runtime/ux-followup-evidence/entrada-local-manual.jpg`, `entrada-movil-claro-manual.jpg`, `demo-cancelacion-corregida-manual.jpg`. E2E: `entradas-{light,dark}-{chromium,mobile}.png` y `cuenta-limpia-{chromium,mobile}.png` en el mismo directorio. Demo automatizada: `frontend/dist/demo-review/{desktop,mobile}-cancelled-context.png`. Artefactos locales excluidos de Git.

No se abrió ni modificó `runtime/arena.sqlite`, no se borró historial real ni se descargaron modelos. Pestañas temporales cerradas y viewport restablecido. Worker manual detenido mediante su señal cooperativa; el lanzador detecta esa salida y ejecuta su limpieza (salida 1 esperada en esta forma de parada). Base y logs ficticios conservados.

## Límites y continuación

No se han realizado pruebas de comprensión con personas, lector de pantalla, dispositivo móvil físico, Firefox/Safari o inferencia real. Las comprobaciones de contraste y teclado no son una certificación completa. El resultado acredita comportamiento técnico y visual en los recorridos descritos.

La investigación de Claude está en [integracion-claude-suscripcion.md](integracion-claude-suscripcion.md). Se revisaron fuentes oficiales vigentes y el encaje con los contratos de Arena. No se instaló cliente, conectó cuenta o consumió cuota. El adaptador propuesto para una fase siguiente todavía no existe; «Próximamente» en Perfil no representa una conexión.
