# Prompt para continuar la auditoría UX

Trabaja en Agent Arena Local, en `C:\Users\rishi\Desktop\UNI 2026\TFG`. Lee README y `docs/auditoria-ux-2026-10-13.md`, incluida la cuarta iteración y sus límites. Inspecciona Git y conserva cambios de otras sesiones.

UX-01 a UX-14 están corregidos y verificados según el registro. Preserva borradores por cuenta, rutas y selección, entrada compartida por defecto con opción independiente, snapshots ejecutados, selección de biblioteca frente a filtros, trazas con Escape y retorno de foco, lectura progresiva de resultados/campañas, navegación móvil, distinción entre simulador y modelo configurado y señal contextual del worker. Las cancelaciones son terminales y cuentan aparte: no puntúan calidad, no son errores ni entran en tiempos medios. Conserva el lanzador `scripts/dev.ps1` y el aislamiento de la demo estática.

No quedan mejoras obligatorias del backlog original. UX-15 (restablecer filtros en el estado vacío de Modelos) y las hipótesis/funciones nuevas son propuestas opcionales: acuerda su alcance antes de convertirlas en requisitos. La pregunta experimental del TFG de la Universidad Complutense de Madrid sigue sin decidirse; no fijes dominio, ranking ni metodología por tu cuenta.

Para nuevos cambios completa tareas reales de navegador, teclado, móvil, recarga y cambio de cuenta/selección. Usa SQLite temporal nueva, datos ficticios, API y worker en la misma base aislada y puertos propios. No abras ni modifiques `runtime/arena.sqlite`, no borres historial real, no descargues modelos ni dependas de Ollama. Usa simulador o adaptadores controlados.

Ejecuta pruebas relevantes y compilación; registra criterios, resultados, límites y capturas. No declares corregida una mejora solo porque cambió el código. No hagas commit ni push salvo autorización explícita del usuario en esa sesión. Entrega resultados y pendientes.
