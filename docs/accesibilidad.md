# Accesibilidad de la interfaz

La interfaz toma WCAG 2.2 AA como objetivo. Esta documentación describe la
implementación y las comprobaciones realizadas; no constituye una certificación
completa de conformidad.

## Comportamiento implementado

- Formularios con etiquetas, instrucciones y errores asociados al campo mediante
  `aria-describedby` y `aria-invalid`. Al enviar datos incompletos, el foco pasa al
  primer campo que necesita corregirse. Los prompts plegados se abren si contienen
  el error.
- Modales de ayuda mediante `dialog.showModal()`, con nombre accesible, fondo
  inerte, foco inicial en el título y ciclo de Tab/Shift+Tab dentro del diálogo.
  Escape y el botón Cerrar devuelven el foco al botón de ayuda.
- Enlace para saltar al contenido, navegación con `aria-current`, títulos de
  página y foco en el encabezado al cambiar de sección. Cerrar una traza devuelve
  el foco a su botón de apertura. Escape cierra el historial.
- Estados identificados por texto, encabezados jerárquicos, tablas con caption y
  encabezados de columna. Las tablas desplazables tienen nombre y acceso con
  teclado; su desplazamiento queda dentro del contenedor.
- Controles principales con zonas pulsables de al menos 44 píxeles de altura,
  foco visible y colores con contraste suficiente. La información no depende
  únicamente del color.
- Animaciones breves de entrada y transiciones de controles. Se desactivan con
  `prefers-reduced-motion: reduce`, incluido el desplazamiento suave. Se incluyen
  ajustes para colores forzados.
- Apartado Guía con seis pasos, índice de enlaces y encabezados enfocables. Los
  ejemplos siguen el orden de lectura y el contenido permanece disponible sin
  animaciones. Las apariciones al hacer scroll se reproducen una vez por paso y
  se omiten cuando se solicita movimiento reducido.

## Comprobaciones del 10 de octubre de 2026

- Compilación Angular de producción satisfactoria.
- En navegador: ayudas de configuración, datasets y métricas; foco inicial,
  Tab/Shift+Tab, cierre con Escape y con botón, y retorno del foco.
- En navegador: error de entrada compartida vacía, identificación del campo y
  foco; salto al contenido; navegación a resultados y perfil; apertura y cierre
  de trazas; cierre y reapertura de sesión con la cuenta de prueba existente.
- Vista a 390 píxeles: formulario y modal del dataset. Vista a 320 píxeles:
  resultados, perfil, historial y formulario. Sin desbordamiento horizontal de la
  página en estas comprobaciones. Las tablas mantienen desplazamiento propio.
- Guía: navegación y salto al paso de datos con teclado, activación de la
  animación al entrar en pantalla, adaptación a 320 y 390 píxeles y botón final
  para volver a Comparar. Compilación satisfactoria y sin errores de consola.
- Contraste calculado con luminancia relativa: texto secundario sobre la superficie
  gris 4,64:1; bordes de campos sobre blanco 3,72:1; foco sobre el fondo 7,53:1;
  texto de error 5,46:1; estados de fallo y éxito 5,25:1 y 5,40:1.

## Revisión pendiente

La [validación del 12 de octubre](validacion-integral-2026-10-12.md) añade la
biblioteca y los informes: revisión móvil a 320/390 píxeles, modal con teclado,
avisos de API/Ollama inaccesibles y comprobación básica de contraste. Las pruebas
automatizadas de carga y selección sustituyen HTTP/Angular; no constituyen una
auditoría con lector de pantalla.

Los selectores conservan el control nativo y permiten personalizar la lista y
animación con `appearance: base-select` cuando el navegador lo soporta.
Sin ese soporte se mantiene la lista del sistema operativo. Las animaciones
respetan movimiento reducido y los estados se adaptan a colores forzados.
La confirmación de vaciar historial contiene el foco, permite Escape antes de
iniciar la eliminación y devuelve el foco al botón que la abrió.

Antes de declarar conformidad completa, realizar una revisión independiente con
NVDA o VoiceOver, zoom del navegador al 200 % y 400 %, espaciado de texto
personalizado y preferencias reales de movimiento reducido y colores forzados.
Comprobar también los flujos completos con distintas combinaciones de errores,
archivos, datasets grandes y respuestas largas. Las pruebas anteriores no
sustituyen esa evaluación.

Referencias: [WCAG 2.2](https://www.w3.org/WAI/WCAG22/quickref/) y
[patrón de diálogo modal de WAI-ARIA](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/).
