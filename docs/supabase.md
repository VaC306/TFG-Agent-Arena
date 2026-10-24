# PostgreSQL en Supabase

SQLite sigue siendo la opción predeterminada. `ARENA_DATABASE_URL` selecciona
PostgreSQL y tiene prioridad sobre `ARENA_DB`. La API y el worker deben utilizar
el mismo destino. El esquema `arena` conserva las cuentas locales y no utiliza
Supabase Auth ni las claves del navegador. No añadas `arena` a los esquemas
expuestos por la Data API de Supabase.

## Crear el proyecto gratuito

1. Abre https://supabase.com/dashboard y crea una cuenta.
2. Crea un proyecto en una organización con plan Free y elige una región europea.
3. Guarda la contraseña de PostgreSQL en un gestor de contraseñas.
4. Cuando termine de crearse, abre **Connect → Session pooler** y copia la URI.
   Este modo admite IPv4. Usa el usuario y host exactos que muestra el panel;
   la contraseña debe estar codificada como parte de una URL si contiene
   caracteres especiales. No es la URL HTTP del proyecto ni la clave `anon`.
5. Guarda la URI completa en `runtime/supabase/database-url.txt`, en una sola
   línea, sin comillas. `runtime/` está excluido de Git. No pegues la URI en
   chats, capturas, archivos versionados o argumentos de comandos.

La conexión remota exige SSL. Se conserva `sslmode=verify-full` y `sslrootcert`
si los configuras con el certificado del proveedor; por defecto se exige cifrado
con `sslmode=require`.

## Instalar y arrancar

Con Python 3.11 o 3.12 y una versión de Node admitida por el frontend:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-postgres.lock
.\scripts\start_supabase.ps1
```

Si el entorno compatible está en otra carpeta:

```powershell
.\scripts\start_supabase.ps1 -Python runtime\dev\venv312\Scripts\python.exe
```

El lanzador lee la URI localmente y la transmite a los servicios por variable
de entorno, sin mostrarla ni incluirla en sus argumentos. No crea usuarios de
prueba ni importa el historial automáticamente. Para usar puertos distintos,
añade `-ApiPort 8010 -UiPort 4210`.

Para comprobar solo la conexión, desde una terminal local:

```powershell
$env:ARENA_DATABASE_URL = (Get-Content runtime\supabase\database-url.txt -Raw).Trim()
.\runtime\dev\venv312\Scripts\python.exe scripts\check_database.py
```

Esta comprobación crea el esquema y las tablas si no existen. No imprime la URI.
La API y el worker continúan procesando una sola ejecución activa globalmente;
PostgreSQL conserva esta condición mediante un bloqueo transaccional.

## Importar el historial local, opcional

Primero finaliza o cancela los trabajos y detén API y workers locales y remotos.
La importación exige un destino vacío y usa una transacción: si falla, revierte
las filas importadas. El origen se abre en modo de solo lectura y no se elimina.

```powershell
$env:ARENA_DATABASE_URL = (Get-Content runtime\supabase\database-url.txt -Raw).Trim()
.\runtime\dev\venv312\Scripts\python.exe scripts\migrate_sqlite_postgres.py --source runtime\dev\arena.sqlite
```

Importa usuarios con sus contraseñas cifradas mediante hash, experimentos,
ejecuciones, eventos, campañas y anotaciones. No copia sesiones, intentos de
autenticación, señales de workers ni vinculaciones locales de proveedores:
inicia sesión y vuelve a vincular proveedores desde el equipo correspondiente.
Las credenciales y hashes de cuentas siguen siendo datos sensibles.

## Consultar desde Supabase

En el SQL Editor:

```sql
SELECT id, snapshot::jsonb #>> '{config,name}' AS nombre
FROM arena.experiments
ORDER BY rowid DESC;

SELECT status, COUNT(*) FROM arena.runs GROUP BY status;
```

Para volver a SQLite, detén los servicios y elimina `ARENA_DATABASE_URL` de la
terminal antes de arrancar `scripts/dev.ps1`. Los cambios nuevos en PostgreSQL
no se sincronizan automáticamente con el archivo SQLite original.

## Límites

El plan gratuito tiene cuotas y puede pausar proyectos por inactividad. Vigila
el tamaño de trazas, snapshots y adjuntos. La base en la nube no aloja por sí
sola la interfaz, la API, el worker ni Ollama.

Referencias: https://supabase.com/docs/guides/database/connecting-to-postgres
y https://supabase.com/pricing.
