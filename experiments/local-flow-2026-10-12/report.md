# Agent Arena — informe de resultados

```
Auditoría real 3b frente a 7b 2026-10-12
```

Adaptador: ollama · Fase: dev · Repeticiones: 1

Aciertos sobre casos con referencia incluye los fallos y errores de esos casos en el denominador. La calidad entre respuestas evaluadas excluye errores de ejecución.

## Variante A

```
qwen2.5:3b
```

Aciertos: 2/3 casos con referencia. Respuestas evaluadas: 3. Ejecuciones programadas: 3.

Incorrectas: 1. Formatos inválidos: 0. Errores de ejecución: 0. Sin evaluar: 0. Pendientes: 0.

Tiempo medio de respuestas sin error: 3.032 s (3 mediciones).

### Configuración guardada

```
{
  "model": "qwen2.5:3b",
  "system_prompt": "Responde a la solicitud usando el contenido proporcionado. Distingue hechos de suposiciones y señala la información que falta.",
  "temperature": 0.0,
  "seed": 42,
  "num_ctx": 2048,
  "limits": {
    "timeout_s": 120.0,
    "max_calls": 12,
    "max_tool_calls": 30,
    "max_output_tokens": 64
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
Paris
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

Repetición 1 · Correcta

Respuesta recibida:

```
42
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

Repetición 1 · Correcta

Respuesta recibida:

```
11:15
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
qwen2.5:7b
```

Aciertos: 3/3 casos con referencia. Respuestas evaluadas: 3. Ejecuciones programadas: 3.

Incorrectas: 0. Formatos inválidos: 0. Errores de ejecución: 0. Sin evaluar: 0. Pendientes: 0.

Tiempo medio de respuestas sin error: 3.988 s (3 mediciones).

### Configuración guardada

```
{
  "model": "qwen2.5:7b",
  "system_prompt": "Responde a la solicitud usando el contenido proporcionado. Distingue hechos de suposiciones y señala la información que falta.",
  "temperature": 0.0,
  "seed": 42,
  "num_ctx": 2048,
  "limits": {
    "timeout_s": 120.0,
    "max_calls": 12,
    "max_tool_calls": 30,
    "max_output_tokens": 64
  },
  "prompt_template": "general",
  "tools_enabled": false
}
```

### Caso

```
capital
```

Repetición 1 · Correcta

Respuesta recibida:

```
París
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

Repetición 1 · Correcta

Respuesta recibida:

```
42
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

Repetición 1 · Correcta

Respuesta recibida:

```
11:15
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
  "comparison_scope": "models",
  "inputs_shared": true,
  "prompts_equal": true,
  "parameters_equal": true,
  "evaluations": [
    "exact_match"
  ],
  "models": {
    "B": {
      "identifier": "qwen2.5:7b",
      "adapter": "ollama",
      "digest": "845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e",
      "server_version": "0.40.3",
      "quantization": "Q4_K_M",
      "verified": true,
      "fingerprint": "9790b53a88dbd85dc7c7bdd749be79608c3d2c5ab49ca35d4ba108b50d4ebe7e"
    },
    "A": {
      "identifier": "qwen2.5:3b",
      "adapter": "ollama",
      "digest": "357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b",
      "server_version": "0.40.3",
      "quantization": "Q4_K_M",
      "verified": true,
      "fingerprint": "a2d1b0a541b6f4bf1f9ec6a1eaf7e00b9e75646b4f5b7cd4c881d8daae3f6420"
    }
  },
  "branches": {
    "A": {
      "total": 3,
      "finished": 3,
      "evaluated": 3,
      "planned_evaluable": 3,
      "correct": 2,
      "incorrect": 1,
      "invalid_format": 0,
      "execution_errors": 0,
      "unscored": 0,
      "pending": 0,
      "mean_answer_s": 3.031826166664056,
      "timed_answers": 3,
      "answers": 3
    },
    "B": {
      "total": 3,
      "finished": 3,
      "evaluated": 3,
      "planned_evaluable": 3,
      "correct": 3,
      "incorrect": 0,
      "invalid_format": 0,
      "execution_errors": 0,
      "unscored": 0,
      "pending": 0,
      "mean_answer_s": 3.988070733331066,
      "timed_answers": 3,
      "answers": 3
    }
  },
  "warnings": [
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
      "at": 1791821772.5709007,
      "scope": "host_and_worker",
      "ram_available_bytes": 14299377664,
      "worker_rss_bytes": 155279360,
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
