# Prompt para continuar la auditoría UX

Copia el siguiente texto en otra sesión:

---

Trabaja en Agent Arena Local, en `C:\Users\rishi\Desktop\UNI 2026\TFG`. Lee primero el README y `docs/auditoria-ux-2026-10-13.md`, incluido su registro de implementación. Inspecciona el estado de Git y conserva los cambios sin commit de sesiones anteriores.

El objetivo es implementar las mejoras pendientes de la auditoría con un diseño minimalista, manteniendo el carácter local y el contexto del TFG de la Universidad Complutense de Madrid. La pregunta experimental aún no está decidida; no fijes un dominio, un ranking o una metodología experimental por tu cuenta.

Ya están corregidos: cabecera en anchos intermedios (UX-09), confirmación de anotaciones (UX-14), historial con «finalizadas» y separación de cancelaciones respecto a errores (UX-03). Esta última incluye contador `cancelled` en resúmenes/CSV/JSON, resultado `cancelled` por ejecución, informes y pantallas; las cancelaciones no puntúan calidad ni entran en tiempos medios. No reviertas estas garantías.

Empieza por UX-01: borradores recuperables por cuenta. Conserva texto, configuración y dataset normalizado cuando sea apropiado; indica qué se ha guardado, permite recuperar y descartar, y explica qué adjuntos necesitan reselección. Evita que otra cuenta recupere un borrador ajeno. No alteres comparaciones ya ejecutadas. Después aborda UX-02: sección y comparación en la URL, recarga que recupera contexto, Atrás/Adelante e ID inválido con salida clara. Revisa cómo interactúan navegación, borradores, sesión y peticiones pendientes.

Si esas dos mejoras quedan verificadas, sigue con UX-08 (ID y filas en errores de dataset), UX-07 (conservar selección de biblioteca al filtrar) y UX-11 (Escape y retorno de foco en trazas). Revisa las observaciones en el documento antes de implementarlas; trata las hipótesis y funciones nuevas como propuestas opcionales.

Completa tareas reales en un navegador, incluidos teclado, móvil, recarga y cambio de cuenta/selección. Usa una SQLite temporal nueva y datos ficticios, con API y worker apuntando a la misma base aislada y puertos propios. No abras ni modifiques `runtime/arena.sqlite`, no borres historial real, no descargues modelos y no dependas de Ollama. Usa simulador o adaptadores de prueba controlados.

Implementa y verifica cada mejora. Ejecuta pruebas relevantes y compilación; registra criterios de aceptación, resultados, límites y capturas útiles en la auditoría. No marques algo corregido solo porque cambió el código. No hagas commit ni push. Al terminar, entrega qué se corrigió, qué se probó y qué sigue pendiente.
