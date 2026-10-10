# Validación de entradas

El frontend detecta errores antes de enviar y enfoca el campo correspondiente.
El backend vuelve a validar cada solicitud; los controles HTML no son una barrera
de seguridad. Un error no debe guardar un experimento parcial. Los formularios
conservan el texto para poder corregirlo.

| Dato | Reglas |
| --- | --- |
| Usuario | 3–40 letras ASCII, números, punto, guion o guion bajo; se normaliza a minúsculas |
| Contraseña | Registro: 10–128 caracteres, no solo espacios. Acceso: 1–128 para permitir cuentas existentes |
| Nombre visible | 1–80 caracteres, no solo espacios |
| Comparación | Nombre 1–120; repeticiones enteras 1–10, sin conversión de cadenas, booleanos o decimales |
| Prompts y entradas | 1–6.000 caracteres, no solo espacios; referencia opcional de hasta 6.000 |
| Modelos | Identificadores limitados; A/B iguales en modo un modelo y distintos en modo dos modelos, considerando el alias `:latest` |
| Adjuntos | Hasta 4 por entrada, entre 1 byte y 1 MiB cada uno; nombres sin rutas ni controles |
| Texto adjunto | UTF-8, máximo conjunto de 20.000 caracteres; JSON y CSV válidos |
| Imágenes | PNG/JPEG/WebP, formato coherente con extensión, hasta 10 megapíxeles; el servidor verifica integridad y rechaza animación |
| Dataset | CSV/JSONL UTF-8, hasta 1 MiB y 100 casos; columnas `id,input,expected_answer`, última opcional; identificadores únicos |

Los textos rechazan caracteres nulos y Unicode inválido. El servidor rechaza
JSON con claves duplicadas, números no finitos o anidamiento excesivo. Los
errores de validación no devuelven el cuerpo enviado ni contraseñas.
Las preferencias admiten borradores vacíos; ejecutar una comparación exige
los campos obligatorios completos. Los límites siguen aplicándose al borrador.

El historial se elimina en una transacción y solo para la cuenta actual, tras
confirmación explícita. No se permite borrar si hay ejecuciones en cola o en
curso. La revisión del historial impide borrar comparaciones nuevas que no
figuraban en la confirmación. Se conservan cuenta, sesión y preferencias.

Pruebas: `python -m pytest -q` desde la raíz, con el entorno virtual activo;
`npm test` y `npm run build` desde `frontend`. Los casos de borrado usan bases
de datos temporales, sin modificar el historial de la instalación.
