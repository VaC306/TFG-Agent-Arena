# Evidencia de la ejecución del 12 de octubre de 2026

Esta selección contiene peticiones/respuestas del diagnóstico y, por cada suite,
CSV, respuestas, configuración, identidad de modelos, hashes y auditorías.
`manifest.json` identifica los datos y parámetros usados. A corresponde a Qwen
2.5 3B y B a Qwen 2.5 7B en las suites; el diagnóstico identifica cada modelo
explícitamente. La ejecución fue real mediante Ollama 0.40.3.

Los archivos son evidencia de una ejecución, no resultados esperados de futuras
ejecuciones. El evaluador usa las referencias en `../../datasets/`; no compara
contra estas respuestas. No se afirma determinismo entre máquinas o versiones.
`audit.passed=true` significa coherencia del registro, incluso cuando la respuesta
es incorrecta. Las fuentes completas y trazas del worker están en los exports
locales y se pueden generar con los comandos de la batería.

El diagnóstico distingue llamada correcta y conservación posterior del JSON.
Un modelo puede llamar correctamente y después perder datos o cambiar el formato.
Los porcentajes de calidad de los informes se calculan sobre respuestas evaluadas;
consulta también total programado y errores. Los p-valores quedan ausentes en
pedidos por pares incompletos. Cualquier contraste de suites pequeñas es exploratorio.

Los hashes de fuentes del desarrollo pueden variar respecto a evaluación porque
la auditoría se amplió durante desarrollo; no se modificó el protocolo ni los datos
antes o durante evaluación. Se recalcularon todas las auditorías con la versión final.
Para reproducir la inferencia, conserva datos, modelo, prompt y opciones; para
comparar código, usa los hashes junto con el commit.

Consulta [el análisis y sus limitaciones](../../../../docs/diagnostico-herramientas.md).
