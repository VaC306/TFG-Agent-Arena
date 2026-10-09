# Cuentas locales y conexiones futuras

El registro crea una cuenta en SQLite con usuario único (3–40 caracteres ASCII entre
letras, números, punto, guion y guion bajo), nombre visible y contraseña de 10–128 caracteres.
Los nombres de usuario no distinguen mayúsculas. El usuario puede editar el nombre visible
en Perfil y cerrar sesión. Todavía no hay recuperación ni cambio de contraseña desde la interfaz.

Las contraseñas se almacenan con scrypt y sal aleatoria, nunca en texto plano. Las sesiones
usan tokens aleatorios de 256 bits; SQLite guarda su hash SHA-256. La cookie es HttpOnly,
SameSite=Strict, caduca a los siete días y se revoca al salir. Usa Secure si la API se sirve
por HTTPS; el desarrollo actual usa HTTP en loopback. Las escrituras requieren una cabecera
personalizada y se rechazan peticiones de navegador marcadas cross-site. El inicio de sesión
y registro se limitan conjuntamente a diez intentos por minuto y dirección de cliente.

El historial, detalle, CSV, trazas y cancelaciones comprueban el propietario del experimento.
Una consulta a un recurso de otro usuario devuelve 404. La primera cuenta registrada reclama
los experimentos preexistentes sin propietario; las siguientes solo ven los propios.
Los experimentos creados posteriormente por CLI sin propietario permanecen fuera de la interfaz.
La CLI y el acceso directo a los archivos son herramientas del propietario de la máquina:
estas cuentas no constituyen aislamiento frente a alguien con acceso al sistema operativo.

Las preferencias guardan la última configuración del formulario: modo, adaptador, modelos,
prompts, nombre, repeticiones y origen de datos. Los cambios se guardan automáticamente.
Los archivos, entradas y datasets se guardan al ejecutar dentro del experimento; no se guardan
como borradores del perfil. La navegación interna conserva el formulario abierto, pero una
recarga o cierre de sesión requiere volver a introducir los datos todavía no ejecutados.

## Cuenta de pruebas

Por petición explícita del usuario existe un comando de desarrollo:
`python -m arena.cli create-test-user`. Crea `test` / `test`; no se ejecuta automáticamente
y no modifica una cuenta preexistente con otra contraseña. El formulario de registro normal
no admite esa contraseña corta. Esta instalación sigue destinada a uso local, no a publicación
en Internet. No hay usuarios o contraseñas reales incluidos en el repositorio.

## Conexiones a proveedores (investigación, sin integración aún)

El perfil muestra Ollama como proveedor local y ChatGPT/Claude como próximos proveedores.
No se solicitan ni almacenan credenciales externas en esta versión.

Fuentes oficiales consultadas el 9 de octubre de 2026:

- [Sign in with ChatGPT](https://developers.openai.com/siwc/quickstart): diferencia identidad
  de permisos para inferencia. Documenta integración abierta para clientes open source y
  disponibilidad condicionada para otros clientes. Requiere registro de cliente, PKCE y
  autorización de los scopes correspondientes; el acceso depende de elegibilidad y límites.
- [Claude Agent SDK con suscripción](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan):
  documenta uso con planes y actualizaciones de límites/créditos. No equivale a un login
  genérico de terceros que permita reutilizar cualquier cookie de Claude.
- [Autenticación de la API de Claude](https://platform.claude.com/docs/en/manage-claude/authentication).
- [Autenticación de la API de OpenAI](https://developers.openai.com/api/reference/overview).

La próxima implementación debe asociar cada conexión al ID interno de usuario, verificar
el retorno OAuth con state/PKCE, almacenar secretos en un almacén protegido del servidor,
permitir desconexión/revocación y cargar solo las credenciales del propietario de cada ejecución.
No incluir tokens ni claves en snapshots, exportaciones, preferencias, trazas o almacenamiento
del navegador. La concesión de identidad y el acceso a modelos deben tratarse por separado.
