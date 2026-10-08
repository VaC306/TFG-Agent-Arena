# Decisiones técnicas

## D01. Arquitectura local y separación del worker

**Fecha:** 8 de octubre de 2026.

**Problema:** comparar agentes con trazabilidad en una máquina durante un TFG
de dos personas y aproximadamente tres meses.

**Alternativas:** infraestructura distribuida; API que ejecuta directamente;
API y worker independientes con almacenamiento local.

**Elección:** FastAPI, worker Python y SQLite. El planificador persiste la cola y
el worker reclama una ejecución mediante transacción. La API permanece disponible
durante la inferencia y no se necesitan Kubernetes ni OpenStack. SQLite utiliza
WAL y conexiones breves; solo se permite una ejecución activa globalmente en
el modo secuencial. PENDIENTE: estrategia explícita para concurrencia shadow.

## D02. Lenguajes e interfaz

**Fecha:** 8 de octubre de 2026.

**Problema:** equilibrar aprendizaje, experiencia del equipo y tiempo disponible.

**Alternativas:** FastAPI/Python; ASP.NET Core con worker Python; backend .NET
completo. Para interfaz: React, Angular o una interfaz Python.

**Elección vigente:** conservar Python para API, ejecución y análisis, con
contratos Pydantic. Se confirma Angular con TypeScript, HTML y CSS para el frontend,
aprovechando la experiencia del equipo y sustituyendo el React inicialmente
propuesto. La primera interfaz está implementada con componentes standalone,
signals y CSS propio, sin biblioteca de componentes externa. Una API .NET sería
posible por la separación de componentes, pero añadiría un segundo entorno al
primer hito.

## D03. Comparación secuencial del mismo modelo

**Fecha:** 8 de octubre de 2026.

**Problema:** no se conoce la VRAM disponible ni la capacidad para alojar modelos
simultáneos. La competencia por recursos alteraría las latencias.

**Alternativas:** dos modelos concurrentes; mismo modelo secuencial; cloud.

**Elección:** mismo modelo, prompts distintos, ramas secuenciales con orden A/B
aleatorizado mediante una semilla registrada. Cada rama reconstruye sus mensajes
y recibe una copia profunda del entorno. No se comparte una secuencia de acciones.
La inicialización actual no realiza warmup y utiliza keep_alive de cinco minutos.
Esto se registra, pero exige un protocolo de calentamiento para estudios reales.

## D04. Herramientas y evaluación

**Fecha:** 8 de octubre de 2026.

**Problema:** verificar el resultado sin premiar una trayectoria única ni ejecutar
código arbitrario propuesto por un modelo.

**Alternativas:** ejecutar Python generado; comparar texto libre con otro LLM;
herramientas acotadas y evaluación por resultado estructurado.

**Elección:** búsqueda de pedidos, consulta de líneas y cálculo con tres operaciones
predefinidas. Importes enteros en céntimos y argumentos validados. El evaluador
compara total e IDs y comprueba herramientas permitidas. Las devoluciones parciales
restan unidades; las totales excluyen el ID. Los criterios no se pasan al adaptador.

## D05. Trazabilidad, límites y recuperación

**Fecha:** 8 de octubre de 2026.

**Problema:** evitar que fallos o interrupciones desaparezcan del análisis.

**Alternativas:** reintentos transparentes; sobrescritura; nuevas ejecuciones
identificadas y estados explícitos.

**Elección:** UUID nuevos, snapshots, eventos ordenados, métricas acumuladas y
estados terminales separados. Las exportaciones exigen directorios nuevos.
Se limitan tiempo, llamadas al modelo, herramientas y tokens de salida. Las
cancelaciones se sondean durante las esperas asíncronas. Tras un cierre abrupto,
la recuperación requiere detener workers y una orden explícita; no se reintenta.
La transición final y su evento se guardan en una misma transacción.

## D06. Evidencia simulada y dependencias

**Fecha:** 8 de octubre de 2026.

**Problema:** validar la plataforma sin inferir resultados de un modelo no ejecutado.

**Alternativas:** depender desde el inicio de descargas; devolver directamente
respuestas de referencia; simulador que consulta las herramientas.

**Elección:** simulador determinista que usa entrada y resultados de herramientas,
con contadores sintéticos identificados. No representa capacidad de comprensión
de un LLM. Dependencias directas fijadas en pyproject y entorno completo fijado
en requirements.lock. El rango de Python admitido es 3.11–3.12; solo 3.11.9 se
ha verificado. Docker Compose está preparado, pendiente de ejecución.

## D07. Primera interfaz y comunicación con la API

**Fecha:** 8 de octubre de 2026.

**Problema:** explorar comparaciones sin depender de comandos, manteniendo una
interfaz pequeña y sin trasladar la ejecución del agente al navegador.

**Alternativas:** editor completo desde el inicio; dashboard desconectado con datos
de muestra; pantalla conectada a presets y resultados persistidos.

**Elección:** pantalla conectada con historial, lanzamiento, tarjetas A/B, progreso,
filtro de ramas, cancelación, trazas y CSV. El backend incorpora GET /experiments
con límite acotado y GET /presets. La interfaz consulta cada 2,5 segundos mientras
la comparación seleccionada tiene ejecuciones pendientes; las solicitudes no se
solapan y las respuestas de selecciones anteriores se descartan.

Angular 20.3.33 y TypeScript 5.9.3 son compatibles con Node 22.16.0 del equipo según
la [tabla oficial](https://angular.dev/reference/versions), consultada el 8 de octubre
de 2026. CLI/build 20.3.39, dependencias y lockfile quedan fijados. El desarrollo usa
un proxy de mismo origen `/api`, sin añadir CORS abierto. El build estático está
verificado; su despliegue en Compose es PENDIENTE.

La presentación diferencia ramas y estados por texto y color, permite navegación
con teclado y utiliza desplazamiento horizontal solo dentro de tablas e historial
móvil. El éxito incluye cancelaciones y fallos; las métricas ausentes no se sustituyen
por cero. La prueba de interfaz cancela intencionadamente una rama para verificarlo.
