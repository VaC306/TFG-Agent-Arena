# Apariencia de Agent Arena Local

El selector **Tema** de la cabecera ofrece **Sistema**, **Claro** y **Oscuro**.
Está disponible en el acceso a la cuenta, el espacio de trabajo y la demo
estática, también en móvil. Usa Tab para llegar al control; Enter abre la lista,
las flechas recorren las opciones y Enter confirma. Escape cierra la lista.

Sin elección previa se sigue `prefers-color-scheme`. Al seleccionar Sistema,
los cambios del sistema se aplican inmediatamente. Claro y Oscuro prevalecen
sobre el sistema y se guardan en `localStorage` (`arena.theme.v1`); Sistema
elimina ese valor. La preferencia es del navegador y origen, incluido el puerto,
independiente de cuentas y borradores. Otras pestañas del mismo origen reciben
el cambio. Borrar el almacenamiento restablece Sistema. Si el almacenamiento
está bloqueado o lleno, el tema funciona durante la visita y se muestra un aviso
sin afirmar que se guardó.

`assets/theme.js` se ejecuta de forma bloqueante en el `<head>`, antes de los
estilos y de Angular. Resuelve la elección, configura `data-theme`,
`color-scheme` y el color de la barra del navegador. Se incluye con ruta relativa
en ambas compilaciones, incluida la demo alojada bajo un subdirectorio.
Se desactiva `inlineCritical` en producción local/demo: Angular descartaba del
CSS crítico el selector oscuro activado dinámicamente y cargaba el resto después
del primer pintado. El CSS completo se carga con una hoja bloqueante, por lo que
el navegador espera a tener ambas paletas antes de pintar. La prueba de demo
demora esa hoja y verifica que no hay pintados antes de recibirla, tanto con
sistema oscuro como con una elección clara guardada.
No hace peticiones a la API. La paleta en `frontend/src/theme.css` conserva los
valores claros existentes y define colores oscuros por función: superficies,
texto, bordes de controles, foco, acciones, ramas A/B y estados. Las variantes
numeradas conservan matices previos del tema claro. No hay filtros de inversión.

Los controles nativos, formularios, tablas, historial, biblioteca, campañas,
respuestas, trazas, JSON, diálogos y estados de carga/error/vacío usan la misma
paleta. Los estados mantienen sus etiquetas; A/B conserva sus letras. El foco
tiene contorno visible y las preferencias de movimiento reducido y colores
forzados conservan sus reglas.

## Repetir las comprobaciones

Desde la raíz, con las dependencias ya instaladas:

```powershell
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
npm.cmd --prefix frontend run build:demo
npm.cmd --prefix frontend run e2e:typecheck
npm.cmd --prefix frontend run e2e:repeat
npm.cmd --prefix frontend run test:demo
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/check_reliability.py
```

Las pruebas de tema están en `frontend/tests/theme.test.cjs` y
`frontend/e2e/theme.spec.ts`. Cubren arranque antes de Angular (bloqueando su
carga), sistema dinámico, elección explícita, recarga, persistencia, teclado,
almacenamiento no disponible, valores inválidos y sincronización entre pestañas.
La suite E2E usa puertos propios y una SQLite nueva temporal; API y worker
comparten esa base y usan simulador/adaptador controlado. La suite de demo sirve
la compilación estática sin backend y rechaza cualquier petición externa o API.
GitHub Actions ejecuta también la compilación y los recorridos de la demo.

`browser-colors.cjs` calcula contraste de texto visible frente a los fondos
compuestos de los elementos renderizados, con umbral AA de 4,5:1 (3:1 para texto
grande). Se combina con capturas y pruebas de foco. Excluye controles desactivados;
no constituye una certificación de accesibilidad ni comprueba cada combinación
posible de contenido, pseudo-elementos o interfaz nativa del sistema operativo.

Resultados concretos, capturas y límites de esta implementación se registran en
la [auditoría UX](auditoria-ux-2026-10-13.md#modo-oscuro-completo-20-de-octubre-de-2026).
