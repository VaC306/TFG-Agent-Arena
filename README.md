# Agent Arena Local

Plataforma local para comparar modelos y prompts con datos propios y conservar
resultados, condiciones y trazas. Proyecto desarrollado como **Trabajo de Fin de
Grado (TFG) para la Universidad Complutense de Madrid (UCM)**.

## About

Agent Arena Local permite estudiar el comportamiento de agentes con herramientas
mediante experimentos documentados. El frontend utiliza **Angular, TypeScript,
HTML y CSS**; el backend, **Python y FastAPI**, con un worker independiente y
persistencia en **SQLite**. La inferencia se realiza con modelos locales de
**Ollama**; el simulador permite verificar la plataforma sin modelos. También
incluye una conexión inicial de texto a **ChatGPT mediante la suscripción de Codex**,
sin API key, usando el cliente oficial instalado y sus límites compartidos.

Los informes facilitan reproducir el análisis de la evidencia guardada.
Reproducibilidad no significa garantizar respuestas idénticas en cualquier máquina.

## Funcionalidades

- Comparaciones A/B de modelos o configuraciones de prompt.
- Mapa navegable de la comparación, ayuda opcional para principiantes y revisión
  de datos, variantes y condiciones antes de ejecutar.
- Entradas, adjuntos y datasets CSV/JSONL con evaluación automática.
- Borradores por cuenta recuperables en el mismo navegador; los adjuntos requieren
  reselección tras recargar. Sección y comparación seleccionada en la URL.
- Respuestas A/B, gráficos de estados y tiempos y detalles desplegables.
- Biblioteca de modelos con gráficos de calidad, cobertura, errores, tiempos,
  tokens y coste estimado con tarifas configurables; evolución de campañas con diseño fijado.
- Análisis por tarea, cobertura, errores y estabilidad; incertidumbre exploratoria
  solo cuando la evidencia cumple las condiciones del método.
- Anotaciones de condiciones externas, estado del worker y exportación CSV,
  Markdown y JSON. Las diferencias incompatibles se advierten sin elegir ganadores.

## Inicio rápido

Para consultar evidencia sin API, worker ni Ollama, usa la
[demo estática preparada para Sites](docs/demo-sites.md). Incluye compilación
Angular independiente, datos revisados y pasos de publicación privada pendientes
de autorización.

Requisitos: **Python 3.11** y **Node.js 22.12 o posterior de la rama 22**.
Ejecuta desde la raíz de tu copia del repositorio. Los ejemplos usan PowerShell.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .
npm.cmd --prefix frontend ci
```

En Windows puedes iniciar API, worker e interfaz y abrir la aplicación con un comando:

```powershell
.\scripts\dev.ps1
```

Para instalar las dependencias y arrancar por primera vez, usa
`.\scripts\dev.ps1 -Setup` (Python y Node deben estar instalados). El lanzador usa
`runtime/dev/arena.sqlite`, una base de desarrollo separada; crea tu cuenta local
en ella. Mantén la terminal abierta y pulsa `Ctrl+C` para detener sus servicios.
No descarga modelos ni necesita Ollama para usar el simulador.

Si los puertos están ocupados, usa por ejemplo
`.\scripts\dev.ps1 -ApiPort 8010 -UiPort 4210`. Los logs quedan en
`runtime/dev/sessions/`. [Opciones del lanzador](docs/operacion-local.md#lanzador-de-desarrollo-en-windows).

También puedes mantener estas tres terminales abiertas, todas desde la raíz del repositorio:

```powershell
# Terminal 1: API
.\.venv\Scripts\python.exe -m uvicorn arena.api:app --host 127.0.0.1 --port 8000
```

```powershell
# Terminal 2: worker
.\.venv\Scripts\python.exe -m arena.cli worker
```

```powershell
# Terminal 3: interfaz
npm.cmd --prefix frontend start
```

Abre [la aplicación](http://127.0.0.1:4200/), crea una cuenta local y ejecuta una
comparación simulada o con modelos ya instalados en Ollama. Sin worker, los
trabajos quedan en cola. Detén los procesos con `Ctrl+C`.

En Linux/macOS usa `.venv/bin/python` y `npm` en lugar de las variantes Windows.
La API se documenta en [Swagger](http://127.0.0.1:8000/docs).

Para usar tu suscripción, selecciona **ChatGPT · suscripción mediante Codex** en
Comparar y vincula la sesión del cliente oficial de este equipo. Consulta
[preparación, alcance y verificación](docs/integracion-openai-suscripcion.md).

## Apariencia

El selector **Tema: Sistema / Claro / Oscuro** está en la cabecera, también antes
de entrar y en la demo estática. «Sistema» es el valor inicial y responde a los
cambios de apariencia del sistema. Claro y Oscuro se recuerdan en este navegador
para este origen (incluido el puerto), independientemente de la cuenta.
Volver a Sistema elimina la elección explícita. Si el navegador bloquea el
almacenamiento, el selector avisa y aplica el tema durante la visita.
[Detalles y verificación del tema](docs/tema.md).

## Comprobaciones

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
npm.cmd --prefix frontend run e2e:install
npm.cmd --prefix frontend run e2e
```

Para repetir: `npm.cmd --prefix frontend run e2e:repeat` y
`.\.venv\Scripts\python.exe scripts/check_reliability.py`.
[Cobertura E2E y límites](docs/pruebas-e2e.md).
Las pruebas usan bases y puertos aislados. La simulación valida la plataforma; las
conclusiones sobre modelos requieren experimentos reales y casos revisados.

## Documentación

- [PostgreSQL en Supabase: conexión e importación desde SQLite](docs/supabase.md).

- [Operación local y CLI](docs/operacion-local.md).
- [Datasets y evaluación](docs/datasets.md) · [Protocolo reproducible](docs/protocolo-evaluacion.md).
- [Campañas](docs/campanas.md) · [Análisis por tarea](docs/analisis-por-tarea.md) · [Estudios de latencia](docs/estudios-de-latencia.md).
- [Condiciones externas y worker](docs/condiciones-y-worker.md) · [Mediciones y calentamiento](docs/mediciones-y-calentamiento.md).
- [Validación integral](docs/validacion-integral-2026-10-12.md) · [Pruebas reales](docs/diagnostico-herramientas.md).
- [Interfaz y lectura visual](docs/claridad-visual.md).
- [Memoria del TFG](docs/memoria.md) · [Accesibilidad](docs/accesibilidad.md).
