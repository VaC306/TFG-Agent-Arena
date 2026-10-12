# Evidencia del flujo completo — 12 de octubre de 2026

Prueba funcional aislada; no es un benchmark de superioridad entre modelos.
Consulta [la validación y sus límites](../../docs/validacion-integral-2026-10-12.md).

- `metrics.csv`, `report.md`, `reproducibility.json`: descargados desde Angular
  tras seis inferencias reales con qwen2.5:3b/7b y el CSV de tres ejemplos.
- `simulated-*`: comparación de plataforma con cinco respuestas y una cancelación;
  no aporta evidencia de calidad real.
- `verified-summary.json`: contadores reconstruidos y comprobación entre formatos.
- `library.json`: fichas de la cuenta aislada; coinciden con el JSON real.
- `manifest.json`: SHA-256 de los archivos de evidencia (excluye esta nota).
- `library-desktop.jpg`: captura de las fichas comparadas, sin ranking ni ganador.

Mantén estos archivos como registro de la ejecución original. Los snapshots
identifican las fuentes efectivamente ejecutadas, aunque la app se corrija después.
