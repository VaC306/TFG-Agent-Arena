# Ampliación de la demo: revisión del 13/10/2026

Revisión del código y los datos del artefacto publicado, los exports de
`benchmarks/v1/results/2026-10-12`, los experimentos versionados y documentación.
No se ha modificado ni vuelto a publicar el Site. No se ha inspeccionado una
sesión autenticada del tutor. Las propuestas no necesitan inferencias nuevas.

## Hallazgos

Hay contenido suficiente para una demo más rica sin aumentar artificialmente
el número de resultados. La sección Comparar ofrece una lista de diez exports
y doce diagnósticos en JSON técnico. Resultados y Modelos ya permiten inspección
y comparación, pero falta un recorrido que destaque preguntas y casos concretos.
La Guía conserva instrucciones para ejecutar/configurar la app local, incluido
el botón «Crear una comparación». Campañas permanece vacía por falta de exports.

## Propuestas ordenadas

| Prioridad | Adición | Evidencia y alcance | Criterio de aceptación |
| --- | --- | --- | --- |
| 1 | Recorrido para el tutor de cinco minutos | Enlaces a ejemplos existentes: acierto simple, JSON inválido, error de ejecución y diferencia entre simulación e inferencia real | Desde el inicio se llega a cada caso y se entiende qué enseña; ningún botón aparenta iniciar inferencia |
| 1 | Galería de casos comentados | Respuestas/referencias originales y condiciones, con comparación A/B | Cada explicación enlaza al registro y separa observación de interpretación; no deduce capacidad general del modelo |
| 1 | Resumen por suite y fase | Ocho suites reales: texto, JSON, adjuntos y pedidos, dev/eval, separadas de la prueba funcional y simulación | Tabla/gráficos de aciertos, respuestas evaluadas, errores y formatos inválidos; denominadores visibles, sin ranking ni promedio global de suites incompatibles |
| 1 | Visor visual de diagnósticos | Doce probes del 12/10: solicitud, llamada de herramienta, resultado, continuación y evaluación | Mensajes legibles por paso, JSON opcional, selección modelo/caso/condición y aviso de fixture sintético; no inventar tiempos por paso a partir del único tiempo total |
| 2 | Reproducción de una traza del simulador | `experiments/simulated-dev-final-2026-10-08/events.jsonl`: 16 ejecuciones con eventos de inferencia y herramientas | Publicar solo una selección saneada; avanzar/retroceder por eventos reales; etiqueta permanente «Reproducción de traza guardada · simulador» y tokens sintéticos |
| 2 | Explorador de datasets y archivos sintéticos | Datasets y fixtures de benchmark versionados, incluidos catálogo, cantidades y nota | Mostrar pregunta, referencia, tipo de evaluación y contexto revisado; comprobar hashes contra manifiesto antes de añadir archivos al paquete |
| 2 | El TFG: arquitectura, método y estado | README, decisiones, protocolo y validaciones | Diagrama Angular → API → SQLite/worker → Ollama, además de ruta demo → JSON; diferenciar implementado, validado con simulador, validado con inferencia real y pendiente, con fecha |

El recorrido puede reutilizar componentes y deep links por hash. Los gráficos
se pueden hacer con SVG/HTML en Angular, sin una biblioteca nueva. El contenido
del TFG debe resumirse y actualizarse; no publicar documentación interna en bruto
con rutas privadas o estados históricos que contradigan validaciones posteriores.

## Tres ejemplos especialmente útiles

1. **Criterio exacto:** en la prueba funcional real, la rama A responde `Paris`
   y la referencia es `París`. Mostrar ambas y el criterio explica por qué una
   respuesta aparentemente válida puede fallar; no implica peor razonamiento.
2. **Calidad y cobertura:** pedidos dev, rama B, tiene una respuesta evaluada
   correcta y tres errores de ejecución. Mostrar 1/1 evaluadas correctas junto a
   1/4 ejecuciones programadas correctas evita que el 100 % oculte los fallos.
3. **Llamar y conservar datos:** en los diagnósticos, cada modelo tiene 6/6
   llamadas iniciales correctas y 4/6 continuaciones correctas. Mostrar el
   listado truncado de 3B y la clave envolvente añadida por 7B permite explicar
   dos fallos diferentes. Son observaciones sobre fixtures concretos, no un
   benchmark estadístico ni una generalización sobre esos modelos.

## Evidencia adicional localizada

Las cuatro carpetas del 08/10 son exclusivamente simulaciones, según
`experiments/README.md`. `simulated-dev` y `simulated-dev-final` no deben tratarse
como repeticiones equivalentes: la primera conserva una versión anterior.
`simulated-dev-final` tiene dos repeticiones por rama y caso; no son dos intentos
de campaña. `ui-smoke` conserva una cancelación intencionada y 15 éxitos; su
resumen histórico la incluía entre resultados negativos. Al adaptarlo se debe
separar cancelación con el criterio vigente, conservando los datos originales.

No hay motivos para añadir todas las simulaciones por volumen. Una traza
representativa basta para enseñar el ciclo de herramientas. Los payloads de
recursos y metadatos de infraestructura se deben excluir de la selección.

## Qué requiere evidencia nueva

- Campañas y evolución entre intentos: hace falta un export saneado con diseño,
  intentos, condiciones y análisis. No reconstruir una campaña a partir de
  carpetas históricas ni presentar repeticiones como intentos.
- Estudios de latencia: hacen falta ejecuciones bajo un protocolo adecuado,
  warmup, orden y muestra suficientes. Las duraciones existentes se pueden
  explorar descriptivamente; no sustentan un ranking de velocidad.
- Más modelos o nuevas tareas: requieren inferencias nuevas fuera de Sites,
  seguidas de revisión/exportación. No son necesarias para esta ampliación.

## Primera ampliación sugerida

Una versión centrada en recorrido, galería, resumen por suite y diagnósticos
visuales aportaría más que cargar más registros. Adaptar la Guía al modo de
consulta y convertir la sección vacía de Campañas en una explicación breve de
la capacidad local completaría esa versión. Añadir después una traza simulada
y el explorador de fixtures, tras revisar su exportación.

Mantener el mismo Site, acceso privado y proceso reproducible. Cualquier dato
nuevo debe entrar por la allowlist, manifiesto, tests y revisión del inventario;
conservar las pruebas de red y navegador para escritorio/móvil. Actualizar la
publicación solo cuando se solicite implementar estas propuestas.
