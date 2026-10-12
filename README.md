# Agent Arena Local

Plataforma local para comparar modelos y prompts con datos propios y conservar
resultados, condiciones y trazas. Proyecto desarrollado como **Trabajo de Fin de
Grado (TFG) para la Universidad Complutense de Madrid (UCM)**.

## About

Agent Arena Local permite estudiar el comportamiento de agentes con herramientas
mediante experimentos documentados. El frontend utiliza **Angular, TypeScript,
HTML y CSS**; el backend, **Python y FastAPI**, con un worker independiente y
persistencia en **SQLite**. La inferencia se realiza con modelos locales de
**Ollama**; el simulador permite verificar la plataforma sin modelos.

Los informes facilitan reproducir el análisis de la evidencia guardada.
Reproducibilidad no significa garantizar respuestas idénticas en cualquier máquina.

## Funcionalidades

- Comparaciones A/B de modelos o configuraciones de prompt.
- Entradas, adjuntos y datasets CSV/JSONL con evaluación automática.
- Resultados, biblioteca de modelos y campañas con diseño fijado.
- Análisis por tarea, cobertura, errores y estabilidad; incertidumbre exploratoria
  solo cuando la evidencia cumple las condiciones del método.
- Anotaciones de condiciones externas, estado del worker y exportación CSV,
  Markdown y JSON. Las diferencias incompatibles se advierten sin elegir ganadores.

## Inicio rápido

Requisitos: **Python 3.11** y **Node.js 22.12 o posterior de la rama 22**.
Ejecuta desde la raíz de tu copia del repositorio. Los ejemplos usan PowerShell.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .
npm.cmd --prefix frontend ci
```

Mantén estas tres terminales abiertas, todas desde la raíz del repositorio:

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

## Comprobaciones

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
```

Las pruebas usan bases aisladas. La simulación valida la plataforma; las
conclusiones sobre modelos requieren experimentos reales y casos revisados.

## Documentación

- [Operación local y CLI](docs/operacion-local.md).
- [Datasets y evaluación](docs/datasets.md) · [Protocolo reproducible](docs/protocolo-evaluacion.md).
- [Campañas](docs/campanas.md) · [Análisis por tarea](docs/analisis-por-tarea.md) · [Estudios de latencia](docs/estudios-de-latencia.md).
- [Condiciones externas y worker](docs/condiciones-y-worker.md) · [Mediciones y calentamiento](docs/mediciones-y-calentamiento.md).
- [Validación integral](docs/validacion-integral-2026-10-12.md) · [Pruebas reales](docs/diagnostico-herramientas.md).
- [Memoria del TFG](docs/memoria.md) · [Accesibilidad](docs/accesibilidad.md).
