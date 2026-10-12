# Agent Arena — informe de resultados

```
Auditoría UI simulada 2026-10-12
```

Adaptador: simulated · Fase: dev · Repeticiones: 1

Aciertos sobre casos con referencia incluye los fallos y errores de esos casos en el denominador. La calidad entre respuestas evaluadas excluye errores de ejecución.

## Variante A

```
simulated-a
```

Aciertos: 0/3 casos con referencia. Respuestas evaluadas: 3. Ejecuciones programadas: 3.

Incorrectas: 3. Formatos inválidos: 0. Errores de ejecución: 0. Sin evaluar: 0. Pendientes: 0.

Tiempo medio de respuestas sin error: 0.022 s (3 mediciones).

### Configuración guardada

```
{
  "model": "simulated-a",
  "system_prompt": "Responde a la solicitud usando el contenido proporcionado. Distingue hechos de suposiciones y señala la información que falta.",
  "temperature": 0.0,
  "seed": 42,
  "num_ctx": 16384,
  "limits": {
    "timeout_s": 120.0,
    "max_calls": 12,
    "max_tool_calls": 30,
    "max_output_tokens": 4096
  },
  "prompt_template": "general",
  "tools_enabled": false
}
```

### Caso

```
capital
```

Repetición 1 · Respuesta incorrecta

Respuesta recibida:

```
SIMULACIÓN — modelo simulated-a. Entrada recibida:
Capital de Francia. Responde únicamente el nombre de la ciudad.
Imágenes recibidas: 0. El simulador no interpreta imágenes ni mide calidad del modelo.
```

Referencia:

```
París
```

```
Comparación exacta con la respuesta esperada (sin espacios en los extremos)
```

### Caso

```
cuenta
```

Repetición 1 · Respuesta incorrecta

Respuesta recibida:

```
SIMULACIÓN — modelo simulated-a. Entrada recibida:
Calcula 17 + 25. Responde únicamente el número.
Imágenes recibidas: 0. El simulador no interpreta imágenes ni mide calidad del modelo.
```

Referencia:

```
42
```

```
Comparación exacta con la respuesta esperada (sin espacios en los extremos)
```

### Caso

```
lectura
```

Repetición 1 · Respuesta incorrecta

Respuesta recibida:

```
SIMULACIÓN — modelo simulated-a. Entrada recibida:
Texto: La reunión comienza a las 10:30 y termina a las 11:15. ¿A qué hora termina? Responde solo HH:MM.
Imágenes recibidas: 0. El simulador no interpreta imágenes ni mide calidad del modelo.
```

Referencia:

```
11:15
```

```
Comparación exacta con la respuesta esperada (sin espacios en los extremos)
```

## Variante B

```
simulated-a
```

Aciertos: 0/3 casos con referencia. Respuestas evaluadas: 2. Ejecuciones programadas: 3.

Incorrectas: 2. Formatos inválidos: 0. Errores de ejecución: 1. Sin evaluar: 0. Pendientes: 0.

Tiempo medio de respuestas sin error: 0.020 s (2 mediciones).

### Configuración guardada

```
{
  "model": "simulated-a",
  "system_prompt": "Analiza los datos proporcionados. Identifica patrones, inconsistencias y limitaciones. Explica los resultados con claridad y no inventes cifras.",
  "temperature": 0.0,
  "seed": 42,
  "num_ctx": 16384,
  "limits": {
    "timeout_s": 120.0,
    "max_calls": 12,
    "max_tool_calls": 30,
    "max_output_tokens": 4096
  },
  "prompt_template": "analyst",
  "tools_enabled": false
}
```

### Caso

```
capital
```

Repetición 1 · Error de ejecución

Respuesta recibida:

```
No hay respuesta final.
```

Referencia:

```
París
```

```
Cancelled before execution
```

### Caso

```
cuenta
```

Repetición 1 · Respuesta incorrecta

Respuesta recibida:

```
SIMULACIÓN — modelo simulated-a. Entrada recibida:
Calcula 17 + 25. Responde únicamente el número.
Imágenes recibidas: 0. El simulador no interpreta imágenes ni mide calidad del modelo.
```

Referencia:

```
42
```

```
Comparación exacta con la respuesta esperada (sin espacios en los extremos)
```

### Caso

```
lectura
```

Repetición 1 · Respuesta incorrecta

Respuesta recibida:

```
SIMULACIÓN — modelo simulated-a. Entrada recibida:
Texto: La reunión comienza a las 10:30 y termina a las 11:15. ¿A qué hora termina? Responde solo HH:MM.
Imágenes recibidas: 0. El simulador no interpreta imágenes ni mide calidad del modelo.
```

Referencia:

```
11:15
```

```
Comparación exacta con la respuesta esperada (sin espacios en los extremos)
```

## Condiciones y limitaciones

```
{
  "version": "arena-protocol-v1",
  "evaluator_version": "arena-evaluation-v2",
  "comparison_scope": "configurations",
  "inputs_shared": true,
  "prompts_equal": false,
  "parameters_equal": true,
  "evaluations": [
    "exact_match"
  ],
  "models": {
    "A": {
      "identifier": "simulated-a:latest",
      "adapter": "simulated-v1",
      "digest": null,
      "server_version": null,
      "quantization": null,
      "verified": false,
      "fingerprint": "d2d4a1c9c1c1a2e7fd433243aaba2fdd6960c693cdd387b1874b1bc30ac4b014"
    },
    "B": {
      "identifier": "simulated-a:latest",
      "adapter": "simulated-v1",
      "digest": null,
      "server_version": null,
      "quantization": null,
      "verified": false,
      "fingerprint": "d2d4a1c9c1c1a2e7fd433243aaba2fdd6960c693cdd387b1874b1bc30ac4b014"
    }
  },
  "branches": {
    "A": {
      "total": 3,
      "finished": 3,
      "evaluated": 3,
      "planned_evaluable": 3,
      "correct": 0,
      "incorrect": 3,
      "invalid_format": 0,
      "execution_errors": 0,
      "unscored": 0,
      "pending": 0,
      "mean_answer_s": 0.022069099999498576,
      "timed_answers": 3,
      "answers": 3
    },
    "B": {
      "total": 3,
      "finished": 3,
      "evaluated": 2,
      "planned_evaluable": 3,
      "correct": 0,
      "incorrect": 2,
      "invalid_format": 0,
      "execution_errors": 1,
      "unscored": 0,
      "pending": 0,
      "mean_answer_s": 0.020241549995262176,
      "timed_answers": 2,
      "answers": 2
    }
  },
  "warnings": [
    "Simulación: tokens y tiempo de generación sintéticos. El tiempo del agente mide el simulador, no un modelo real; no aporta evidencia sobre calidad de modelos reales.",
    "Los prompts son distintos: se comparan configuraciones, no solo modelos.",
    "Había cambios sin commit al guardar. Para identificar el código, usa también las fuentes y hashes del informe.",
    "Sin calentamiento previo. El tiempo del agente incluye consulta de metadatos y puede incluir carga del modelo.",
    "Política de memoria del modelo (keep_alive): 0. No se garantiza un inicio en frío si otro programa lo tiene cargado.",
    "Semilla fija no garantiza respuestas idénticas. La carga de otros programas no está aislada."
  ]
}
```

### Evidencia de reproducibilidad

```
{
  "conditions": {
    "mode": "sequential",
    "inputs_shared": true,
    "warmup": "none",
    "keep_alive": "0",
    "resource_scope": "host_and_worker",
    "seed_determinism": "not guaranteed"
  },
  "data_sha256": "ac797c76fe08f99dc6f295a85a2c657a3e1f78e8db667124210fd2bffd639705",
  "source_sha256": {
    "accounts.py": "142cbf2c7571877a37197f1e111a3c4fb047c2fd92f9074ec1f289919fb529d3",
    "adapters.py": "2bd17ebeff6c88e448cd9a6c34121d5fba97f4eefa30bff68d94cada183c4f4e",
    "api.py": "0325b87d4bb06c6920a25847094129b82b96496cb0171961d1e085157e60c3db",
    "attachments.py": "db1ade58c249baa6c1415752705dd8816e3127db588ef7240ce93fd475d79e2b",
    "benchmarks.py": "c549f7dc25acc9c91a833bd7eb232f1aec70ca2554cd253f20c7c3457f9d36ca",
    "cli.py": "7a341cdb5f13a256037c187fb7eca0c650df142ad00077823eea18c3720413bf",
    "comparisons.py": "37463e6855548d7ec066f411cc09a53f511d9a269fabaae6359aa24a27f7aa9f",
    "contracts.py": "d6622773221f28745c85c0cb72159676dbda1b8f33f22e90d05f4c5a4d21ce90",
    "datasets.py": "f979a9e355cef883b022238404d7f27fa666a6b485ec44fdf42a2ea271e249aa",
    "diagnostics.py": "47868b2f88fb02b00c2d814f784a3a23f2804bf632705b71290eba3359aee1aa",
    "evaluator.py": "a1d1c0a91d5cf3727910965337d956c018d65cde9c6dacb03bb216dc63af1b13",
    "export.py": "5731f15c4b0769da17a752a39879995ea8ea37d0300a21295d0ba03320080c4d",
    "json_input.py": "d955862c26c26b026f7ad8ce08e8efae850269bfccd6ca8c55beac8429756624",
    "model_results.py": "c9361fb5f64570b32922b89615763aefb8212b99092d845ecea9f49b208480c6",
    "protocol.py": "cbd0be9eab4371847c1af7138aea978955d6e7dc34849a987ddb0268960d99dd",
    "resources.py": "5fa55346518460f6ddc169cf26eb071b0531e082f628baccd127b6b07f3da488",
    "result_report.py": "4060f4b41557b2d705eaf6e3a1301c5027346977cd60178e5ba41884ddd14ee5",
    "runner.py": "876753094771dae89eeee0f557ff4631f881987357be262bdffa0f5121b0e4a1",
    "scheduler.py": "fcf6644f32ef8616ddc6cbbc9671b68fc17683d4a17dbeb80c6f345c76160976",
    "store.py": "cede412b34e42ed019ce4da566f7bf244c8c716f1b8026ce4093d279547b6d61",
    "tools.py": "12a3c582510b2bb070c8a0b1ee4f706db80f4810da7a6be4968619a4a7b6f172",
    "worker.py": "e593043ba6f5f1500056ef009723f87bacc4683c43484ca24b84b939ddb24a8a",
    "__init__.py": "91447944015cec709e8aa7655f7e9d64e1e4508e7023a57fe3746911c0fc6fed"
  },
  "git_commit": "e367b9a104cc8a924a5c5838114c8b7e3c4c250c",
  "git_worktree_dirty": true,
  "host": {
    "platform": "Windows-10-10.0.26300-SP0",
    "python": "3.11.9",
    "cpu": "Intel64 Family 6 Model 183 Stepping 1, GenuineIntel",
    "logical_cpus": 32,
    "ram_total_bytes": 33959383040,
    "packages": {
      "agent-arena-local": "0.1.0",
      "annotated-types": "0.8.0",
      "anyio": "4.15.1",
      "certifi": "2026.7.22",
      "click": "8.5.0",
      "colorama": "0.4.6",
      "fastapi": "0.115.12",
      "h11": "0.16.0",
      "httpcore": "1.0.9",
      "httpx": "0.28.1",
      "idna": "3.20",
      "iniconfig": "2.3.1",
      "numpy": "2.4.6",
      "packaging": "26.3",
      "pandas": "2.2.3",
      "pillow": "11.3.0",
      "pip": "24.0",
      "pluggy": "1.6.0",
      "psutil": "7.0.0",
      "pydantic": "2.11.5",
      "pydantic_core": "2.33.2",
      "pytest": "8.3.5",
      "python-dateutil": "2.9.0.post0",
      "pytz": "2026.5",
      "scipy": "1.15.3",
      "setuptools": "80.9.0",
      "six": "1.17.0",
      "starlette": "0.46.2",
      "typing_extensions": "4.16.0",
      "typing-inspection": "0.4.4",
      "tzdata": "2026.5",
      "uvicorn": "0.34.2",
      "wheel": "0.45.1"
    },
    "resources": {
      "at": 1791821680.4523423,
      "scope": "host_and_worker",
      "ram_available_bytes": 15426383872,
      "worker_rss_bytes": 151261184,
      "gpu": null,
      "unavailable": [
        "NVML: ModuleNotFoundError"
      ]
    }
  },
  "protocol": {
    "version": "arena-protocol-v1",
    "evaluator_version": "arena-evaluation-v2",
    "identity_capture": "before each run; first observed identity pinned per model",
    "order": "seeded random A/B within each case and repetition",
    "reference_sent_to_model": false
  },
  "order_seed": 42
}
```

El tiempo incluye preparación y puede incluir carga del modelo. No es latencia pura. Las simulaciones no miden modelos reales. El informe es parcial mientras haya ejecuciones pendientes. El JSON reproducible conserva entradas, archivos, fuentes y hashes completos.
