# Demo estática de Agent Arena para Sites

## Revisión de legibilidad — 13/10/2026

La guía de consulta separa los cinco pasos en bloques con numeración lateral,
divisores, ancho de lectura limitado y párrafos con interlineado amplio. Se
ajustaron también márgenes de títulos/párrafos, separación de tarjetas, bloques
de JSON, arquitectura y textos de Campañas/Contacto en demo. Los estilos se
encapsulan en los componentes demo y `frontend/src/demo-layout.css`, incluido
exclusivamente por la configuración Angular `demo`; no cambia el CSS operativo
del backend. Se revisaron capturas completas de guía en escritorio y móvil y
pasaron los recorridos de demo y los dos E2E de aislamiento del modo local.

## Ampliación exclusiva de demo — 13/10/2026

La portada de demo abre un recorrido de cinco casos comentados, resumen visual
de las ocho suites con filtros de fase/modelo, diagnósticos en cuatro pasos,
reproducción manual de 20 eventos seleccionados de un simulador histórico,
explorador de tareas y siete archivos sintéticos, y una presentación de la
arquitectura/método/estado del TFG. Guía explica el modo consulta; Campañas
explica la capacidad local sin inventar resultados longitudinales.

La configuración Angular `demo` reemplaza `demo-overview.component.ts` y
`demo-guide.component.ts` por sus versiones `.demo.ts`. Sus versiones normales
están vacías, y solo se montan desde las ramas `demo` del workspace. El build con
backend no incluye el recorrido, su código de reproducción ni sus archivos JSON.
La guía operativa local original no se ha modificado. Una futura publicación con
backend debe usar la configuración habitual, no la configuración `demo`.

`scripts/demo_showcase.py`, llamado por el generador existente, prepara
`showcase.json`, `fixtures.json` y `replay.json`. Comprueba la procedencia de los
fixtures contra el manifiesto del benchmark y omite entornos completos, fuentes,
recursos y metadatos de host de la traza. La reproducción es estática, claramente
etiquetada como simulador; no ejecuta modelos ni reproduce razonamiento interno.
La selección de comparaciones permanece en 72 ejecuciones originales; la traza
histórica adicional no se incorpora a métricas de modelos ni a campañas.

Validación de la ampliación: compilan demo y backend; pasan 34 pruebas de
frontend, tres pruebas de selección/procedencia/regeneración, los recorridos de
demo en escritorio y móvil, recuperación de carga parcial y seis E2E locales,
incluidos dos que verifican que el backend no monta ni solicita contenido demo.
Se verificó también que el bundle normal excluye `showcase.json`, `replay.json`
y el texto del recorrido, y que no contiene el directorio de datos demo.
El paquete estático revisado contiene ahora 41 archivos, más el manifiesto
añadido por el empaquetador nativo de Sites. Los identificadores vigentes de la
publicación se conservan en `frontend/sites/publication.json`.

## Publicación autorizada — 13/10/2026

Demo publicada en https://agent-arena-demo-tfg.blush-cocoa-5254.chatgpt.site.
Sites confirmó despliegue correcto y acceso personalizado limitado al propietario,
sin editores, grupos ni visitantes externos. Las solicitudes HTTP anónimas a la
página, catálogo JSON y una descarga CSV recibieron 403. Queda por comprobar el
uso con una sesión de propietario y, cuando se autoricen, los visitantes invitados.

Los identificadores reales y la URL están en `frontend/sites/publication.json`.
El checkout separado está en `frontend/dist/sites-publication`; solo contiene los
38 archivos estáticos revisados y el manifiesto de hosting. La publicación nativa
añade ese manifiesto al archivo tar (39 archivos). El helper hizo el commit/push
en el repositorio independiente del Site; no hizo commits/pushes en el TFG.
No se guardaron credenciales. Para actualizar, recuperar el mismo Site mediante
el ID registrado, regenerar/revisar la demo y sincronizar esa copia separada.
En Windows el helper necesita Git Bash en PATH y `TAR_OPTIONS=--force-local`.

Las invitaciones externas están disponibles en este Site. No se han enviado ni
añadido visitantes; para el desarrollador y tutor se necesitan sus cuentas/correos
y autorización para añadirlos como visitantes de solo lectura.

## Registro de preparación local (anterior a la publicación)

Preparación local del 13/10/2026. No se ha creado un Site, publicado, invitado a
nadie ni cambiado permisos. No se han hecho commits ni pushes desde esta tarea.
Los registros originales se conservan; los cambios previos del proyecto se han
respetado. No hay dependencias nuevas.

## Resultado y alcance

Se reutiliza Angular, su diseño, navegación por hash y vistas de resultados y
biblioteca. La compilación `demo` sustituye mediante DI `ArenaService` por
`DemoArenaService`. La compilación normal mantiene FastAPI y las cuentas locales.
La demo abre directamente los resultados: no crea un usuario ni simula un login.
El acceso real corresponde a Sites cuando se publique; el servidor de revisión
local no protege los archivos.
Los JSON se solicitan al mismo origen con el comportamiento normal del navegador,
para conservar el acceso de Sites también en los recursos. La app no lee, guarda
ni exporta cookies, sesiones o credenciales.

La demo ofrece historial de diez comparaciones, filtros por rama, modelo,
adaptador y tipo de prueba, comparación de dos fichas, prompts, referencias,
respuestas, métricas disponibles y descargas CSV/Markdown/JSON revisadas. La
biblioteca de demo muestra todas las fichas seleccionadas, no solo la última.
No equipara automáticamente cohortes de exports diferentes tras omitir los
metadatos de infraestructura.

No se ejecutan modelos, benchmarks, cancelaciones ni reproducciones. Registro,
perfil, preferencias, borrado, creación/repetición de campañas y anotaciones
persistentes requieren el backend local. Los formularios de ejecución y perfil
no se montan en demo. El proveedor rechaza las operaciones de escritura y el
interceptor bloquea llamadas HTTP a API. No se configura un proxy en demo.

## Evidencia seleccionada y limitaciones

| Fuente | Selección |
| --- | --- |
| `benchmarks/v1/results/2026-10-12/{dev,eval}/{text,json,orders,attachments}.json` | Ocho comparaciones reales, 60 ejecuciones; tareas y referencias de los datasets correspondientes |
| `experiments/local-flow-2026-10-12/reproducibility.json` | Prueba funcional real, seis inferencias |
| `experiments/local-flow-2026-10-12/simulated-reproducibility.json` | Simulación de plataforma, seis registros, incluida una cancelación |
| `benchmarks/v1/results/2026-10-12/tool-diagnostics.json` | Doce diagnósticos: mensajes guardados y evaluación de llamadas/continuación |

Los diagnósticos son inferencias reales sobre fixtures sintéticos de desarrollo,
con una observación por condición. Son distintos de la simulación de plataforma.
No se fabrican eventos del worker: los exports seleccionados no contienen esas
trazas. La vista de ejecución lo explica y remite a los diagnósticos en Comparar.
No hay exports de campañas suficientes: Campañas muestra un estado vacío
explicativo, sin inventar intentos, análisis longitudinales o intervalos.

Los resúmenes se reconstruyen con `arena.model_results.summarize`. Esto aplica
el criterio actual: separa la cancelación de errores de ejecución. El export
histórico de la simulación contaba una cancelación entre los errores; los
resultados individuales originales no se cambian. No se rellenan tiempos,
recursos o métricas ausentes. `—` representa ausencia, no cero.

Los adjuntos binarios y entornos completos se omiten. Las pruebas de adjuntos
incluyen una advertencia: la entrada visible no reproduce todo el contexto.
Se mantienen warnings del protocolo y límites metodológicos: muestras pequeñas,
A/B secuenciales, tiempo con preparación/carga, host sin aislamiento y ausencia
de garantía de determinismo. No se presenta un ranking ni superioridad general.
Los datos de pedidos, nombres y clientes de los fixtures son sintéticos, según
el manifiesto del benchmark. La demo no descarga las bases de datos locales.

## Regeneración y ejecución (PowerShell, raíz del repositorio)

Con el entorno Python y las dependencias Angular del README ya instalados:

```powershell
.\.venv\Scripts\python.exe scripts/build_demo_data.py
npm.cmd --prefix frontend run start:demo
```

Abre la dirección que imprime Angular (normalmente `http://127.0.0.1:4200`). Solo
el servidor estático/de desarrollo debe estar encendido para revisión local.

Compilar y preparar el artefacto estático:

```powershell
npm.cmd --prefix frontend run build:demo
.\.venv\Scripts\python.exe scripts/package_demo.py
```

Salida web: `frontend/dist/sites/browser/index.html`, recursos relativos,
fuente local y `demo/`. Paquete de revisión: `frontend/dist/arena-demo-static.zip`
con `dist/index.html` y recursos; inventario externo con tamaño y SHA-256:
`frontend/dist/arena-demo-inventory.json`. El ZIP es un artefacto estático local,
no una versión registrada de Sites. No incluye un ID o credenciales.

El generador usa una lista explícita de campos, registra hashes de las fuentes,
y rechaza patrones de contenido privado en campos libres. No lee `runtime/`,
SQLite, `.env`, cuentas o sesiones. El empaquetador acepta únicamente archivos
esperados de la compilación demo: bundles, licencia/fuente y datos seleccionados.
No empaquetar el repositorio entero. La detección automática complementa la
revisión humana; revisar cualquier nueva respuesta o traza antes de añadirla.

Modo local original:

```powershell
.\scripts\dev.ps1
# O iniciar API/worker según README y:
npm.cmd --prefix frontend start
npm.cmd --prefix frontend run build
```

Para actualizar: modificar la selección/allowlist del generador si cambia la
evidencia, regenerar, revisar el diff de `frontend/demo-assets`, compilar, repetir
las comprobaciones y generar un nuevo inventario. Los cambios de interfaz se
hacen en los componentes existentes; datos y UI se publican juntos tras revisión.

## Capacidad de Sites y acceso privado

Verificación documental del 13/10/2026:

- La [guía oficial de uso](https://help.openai.com/en/articles/20001339-creating-and-using-chatgpt-sites)
  describe disponibilidad beta en Plus y visitantes externos nominales con
  permiso de lectura. Las opciones dependen de plan, cuenta y despliegue gradual.
  No se ha verificado qué controles aparecen en esta cuenta concreta.
- La skill instalada `sites/1.0.1/skills/sites/SKILL.md`, sección Hosting manifest,
  admite artefactos estáticos con directorio `dist`, `dist/client`, `out`, `build`
  o `.output/public`. `frontend/sites/hosting.template.json` prepara
  `static.directory = dist`, sin inventar `project_id`. Es una plantilla, no un
  manifiesto registrado listo para desplegar.
- La referencia del plugin `references/identity-and-secrets.md` atribuye el
  acceso privado a Sites; no se añade OAuth, secretos ni autenticación ficticia.
  No usamos capacidades de servidor ni asumimos que Sites ejecute Python,
  Docker, SQLite local, Ollama o el worker.
- La skill indica Cloudflare Workers para código de servidor. Esta demo no lo
  necesita. La compatibilidad exacta del ZIP de revisión con una versión alojada
  no se declara validada: el flujo nativo de publicación prepara su propio
  archivo y metadatos de versión/source.
- La [documentación oficial](https://help.openai.com/en/articles/20001339-creating-and-using-chatgpt-sites)
  describe uso incluido hasta límites beta por plan. No se garantiza capacidad
  ilimitada ni una disponibilidad concreta sin consultar la cuenta al publicar.

Pasos futuros, **solo después de autorización expresa**:

1. Revisar web, datos y el inventario; comprobar límites y controles reales de
   la cuenta Plus. Crear un Site privado y guardar el ID real que devuelva Sites.
2. Preparar un checkout de publicación que contenga solo la selección revisada
   y la web, con `.openai/hosting.json`: ID real más `static.directory = dist`.
   Usar el flujo nativo del plugin para preparar/guardar la versión. Su helper
   de source sincroniza mediante commits/push; eso necesitará autorización
   aparte de la prohibición vigente en esta tarea. No utilizarlo sobre este
   checkout con otros cambios sin revisar.
3. Mantener al propietario como owner. Añadir al segundo desarrollador y tutor
   como visitantes `Can view` o visitantes externos nominales según la cuenta;
   no dar `Can edit`. Verificar que ambos aparecen en la lista de acceso y que
   no hay audiencia pública o acceso general al workspace.
4. Publicar mediante el flujo nativo para la audiencia seleccionada. El tutor
   abre el enlace con la identidad invitada y navega sin configurar hosting,
   editar código ni publicar versiones.
5. Probar con propietario, cada invitado, una cuenta no invitada y una sesión
   anónima. Comprobar también JSON, CSV, fuente y otros recursos directamente:
   deben estar protegidos por el mismo acceso. Probar revocación de un visitante.

Una URL difícil de adivinar no ofrece protección. La privacidad real y el acceso
por invitación quedan pendientes de un futuro despliegue autorizado.

## Archivos de esta adaptación

- Configuración: `frontend/angular.json`, `frontend/package.json`, `frontend/src/main.ts`,
  `frontend/sites/hosting.template.json`.
- Separación de datos: `runtime-mode{,.demo}.ts`, `data-providers{,.demo}.ts`,
  `demo-arena.service.ts` en `frontend/src/app/`.
- UI: `root.component.ts`, `app.component.{ts,html}`, `auth.service.ts`,
  `model-library.component.{ts,html}`, nuevos `demo-overview.component.ts` y
  `contact.component{,.demo}.ts`; ruta relativa de fuente en `frontend/src/styles.css`.
- Selección: `scripts/build_demo_data.py`, `frontend/demo-assets/demo/**`.
- Paquete: `scripts/package_demo.py`.
- Pruebas: `tests/test_demo_selection.py`, `frontend/tests/demo-service.test.cjs`,
  `frontend/demo-tests/browser.cjs`. Documentación: este archivo y enlace en README.

## Validación

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_demo_selection.py -q
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
npm.cmd --prefix frontend run build:demo
npm.cmd --prefix frontend run test:demo
npm.cmd --prefix frontend run e2e -- workflow.spec.ts
.\.venv\Scripts\python.exe scripts/package_demo.py
```

`test:demo` usa el Chromium instalado por Playwright; admite `ARENA_DEMO_BROWSER`
si se necesita un ejecutable alternativo. No instala un navegador. Sirve la web
compilada en una subruta, sin proxy ni API, y comprueba navegación, filtrado,
comparación, diagnósticos, las 30 descargas, recarga, datos ausentes, errores y
reintento. Rechaza requests a API, otros servicios o recursos fuera de la subruta.
Genera capturas en `frontend/dist/demo-review/` y cierra el servidor al terminar.
El E2E local usa su API/base/worker simulador aislados, sin tocar el historial real.
Las pruebas locales no validan autenticación de Sites ni inferencia real futura.

Resultado de esta revisión: compilan ambos modos; pasan 34 pruebas de frontend,
259 pruebas de Python (incluidas las dos de selección), los cuatro E2E del flujo
local en escritorio/móvil y los recorridos de demo estática en ambas resoluciones.
Se revisaron las capturas de resultados. El manifiesto histórico del flujo local
sigue coincidiendo con los hashes originales. El empaquetado revisado contiene
38 archivos. La suite general de Python se ejecutó fuera del sandbox tras no
progresar dentro; terminó correctamente, con un warning de deprecación de AnyIO.
