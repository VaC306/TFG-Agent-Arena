# Claude con cuenta de suscripción: revisión de viabilidad

Revisado el **20/10/2026**. Investigación posterior a la implementación UX autorizada. No se ha instalado Claude Code, iniciado sesión, consumido cuota ni implementado un proveedor nuevo.

Actualización de contexto: el usuario aclaró que todavía no tiene una suscripción Claude y decidió comenzar por ChatGPT. Se implementó y verificó esa conexión por separado; véase [ChatGPT mediante Codex](integracion-openai-suscripcion.md). Claude continúa pendiente, sin conexión funcional ni suscripción contratada en esta tarea. El estado técnico descrito abajo corresponde al momento de esta revisión, anterior a la integración de ChatGPT.

## Conclusión

La vía concreta para este proyecto local es ejecutar **el binario oficial de Claude Code, sin modificar, autenticado por su propio flujo con la cuenta del usuario**. Arena coordinaría un proceso local y recogería sus resultados; no guardaría cookies, contraseñas o tokens de Claude ni ofrecería un OAuth propio para invocar directamente Messages API. Es una propuesta técnica para una siguiente fase, pendiente de probar con el plan real.

El centro de ayuda confirma, en su actualización del 7/10/2026, que Agent SDK, `claude -p` y aplicaciones de terceros pueden seguir consumiendo los límites de suscripción. La actualización del 15/6 había dejado en pausa el cambio de facturación anunciado. No se debe tratar una noticia anterior como la regla actual. [Uso del SDK con un plan Claude](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan).

## Límite entre integración y login propio

La documentación legal diferencia ejecutar Claude Code publicado por Anthropic de ofrecer acceso a Claude desde un producto propio. Permite que cada usuario se autentique en el binario original con su suscripción, incluso alojado en otra plataforma, sujeto a las condiciones comerciales aplicables. Prohíbe que el desarrollador recoja/intermedie credenciales y que ofrezca su propio login de Claude.ai o enrute solicitudes con credenciales de usuarios fuera de ese marco. El SDK mantiene una advertencia específica para productos de terceros. Por ello, la propuesta es una integración con el cliente oficial y su autenticación, no un proveedor HTTP que copie tokens. No equivale a una autorización general para redistribuir una aplicación con login propio. [Condiciones de Claude Code](https://code.claude.com/docs/en/legal-and-compliance), [aviso del Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview).

## Qué significa «incluido»

| Modalidad | Autenticación / consumo documentado | Encaje con esta petición |
| --- | --- | --- |
| Claude Code oficial con cuenta Claude | Login propio de Claude Code; el uso con Pro/Max y otros planes admitidos puede ir contra los límites del plan. | Ruta preferente para probar sin API key. No se promete uso ilimitado ni disponibilidad permanente. |
| Créditos mensuales de API en Max/Team | Bolsa separada en una organización de Console vinculada; no es la cuota del chat. | Alternativa si se quisiera la API más adelante; no es la ruta elegida para esta petición. |
| API de un proyecto / cloud provider | Credenciales y facturación correspondientes a la plataforma. | No sustituye automáticamente la cuota del plan Claude. |

La autenticación oficial permite Pro/Max mediante cuenta Claude y Team/Enterprise mediante la cuenta invitada. Las credenciales de API, proveedores y perfiles pueden tener precedencia sobre el login de suscripción; debe comprobarse el método realmente activo. La documentación advierte además que `--bare` no lee la credencial OAuth de suscripción: **no usarlo como supuesto modo de aislamiento para este prototipo**. [Autenticación de Claude Code](https://code.claude.com/docs/en/authentication).

Para Max/Team hay créditos API mensuales: Max 5x $100, Max 20x $200; Team tiene importes por asiento y un tope de bolsa de $500. Pro no figura como elegible. Requieren vincular una organización y son distintos de los límites del plan. Agotarlos puede pasar a créditos comprados o recarga si existen; sin otros fondos se detienen las solicitudes. Son datos a verificar en la cuenta, no un saldo del usuario observado aquí. [Créditos API mensuales](https://support.claude.com/en/articles/17154008-monthly-api-credits-for-max-and-team-plans).

## Comprobación local realizada

- `claude` no está en el PATH de esta sesión; tampoco se encontró en las ubicaciones habituales de CLI local/npm comprobadas. No se afirma haber inspeccionado todo el disco.
- En el entorno del proceso no están presentes `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN` ni `CLAUDE_CODE_OAUTH_TOKEN`. Se comprobaron solo booleanos de presencia; no se leyeron ni imprimieron secretos.
- En la revisión inicial no se conocía el plan. Después, el usuario aclaró que no tiene suscripción Claude; no se ha verificado ninguna cuenta Claude.
- Antes de la integración de ChatGPT, Arena implementaba únicamente `simulated` y `ollama`. `arena/adapters.py` usa el contrato de chat de Ollama. «Claude / Próximamente» en Perfil sigue siendo información, no una conexión funcional.

## Cómo continuar: prueba mínima y después adaptador

Estas decisiones son de diseño propuestas para Arena, no afirmaciones de capacidades ya implementadas.

1. **Preparación del cliente oficial.** Instalar Claude Code desde su distribución oficial y ejecutar `claude auth login` con la cuenta del usuario, en el flujo de Anthropic. El usuario completa el acceso. Verificar con `claude auth status` y `/status` que se usa el método de suscripción esperado, sin exponer email/tokens en registros. La referencia CLI documenta estos comandos y `claude -p` con salida JSON. [Referencia CLI](https://code.claude.com/docs/en/cli-reference).
2. **Prueba de una sola tarea ficticia.** Una ejecución explícita, sin referencias privadas, adjuntos ni acceso al repositorio. Recoger respuesta y metadatos documentados. Comprobar en la cuenta que el consumo corresponde al plan elegido. No afirmar «sin coste adicional» solo porque el comando haya respondido; no activar extra usage, recargas ni cambiar a API si se agota la cuota.
3. **Primer adaptador de texto.** Backend local → subproceso oficial → JSON/stream-json → resultado guardado. Usar argumentos estructurados y stdin, sin shell ni interpolación de prompts. Un directorio de trabajo por intento, separado de este repositorio. Sesión nueva por variante/repetición; ninguna conversación o caché de contexto se comparte implícitamente entre A y B. La ejecución no interactiva y sus eventos de modelo/sesión están documentados. [Uso programático](https://code.claude.com/docs/en/headless).
4. **Permisos y configuración reproducible.** Para el primer alcance, no dar herramientas del equipo, lectura/escritura de archivos, shell, navegador o MCP. Verificar las opciones de la versión instalada para limitar herramientas, carga de configuración y persistencia; registrar qué queda activo, incluidos ajustes administrados. No usar `--dangerously-skip-permissions`. No usar `--bare` por el problema de autenticación señalado. Un tool loop de Claude Code no se presenta como el mismo motor/herramientas de Ollama.
5. **Integración en Arena.** Añadir un motor diferenciado al contrato, worker y formulario. Detectar cliente/autenticación; si falta, explicar el siguiente paso. No mostrar «Conectado» por la mera existencia del ejecutable. Mantener credenciales solo en el cliente oficial y explicar el alcance local: el perfil del SO no proporciona automáticamente una cuenta Claude distinta a cada cuenta interna de Arena.
6. **Persistencia honesta.** Guardar instrucciones, entrada, versión del cliente, modelo informado, configuración de herramientas y eventos disponibles. La referencia de evaluación sigue sin enviarse. No registrar razonamiento privado ni secretos. No inventar temperatura/semilla/contexto, digest, TPS o métricas ausentes; marcar controles no aplicables y compatibilidad no verificada. Medir el tiempo de proceso como tal, sin equipararlo a generación pura o a la inferencia local.
7. **Cancelación y errores.** Cancelar solo el proceso/grupo creado para ese intento, con timeout y limpieza en Windows. Conservar salida parcial y distinguir cancelación, cuota agotada, acceso ausente y fallo técnico. Nunca convertir un fallo de autenticación en fallback silencioso a API o en un reintento que duplique consumo.

## Pruebas para decidir si el adaptador está listo

- Pruebas con un ejecutable ficticio: stdin/Unicode, JSON inválido, errores, salida parcial, bloqueo, timeout/cancelación y limpieza; ninguna credencial real ni consumo en CI.
- Smoke real de una tarea autorizado por el usuario, con cliente oficial y plan comprobado. Ese paso sigue pendiente.
- Navegador: cliente ausente, sesión ausente, método de facturación distinto, cuota agotada y resultado; escritorio/móvil, temas, teclado y borrador por cuenta.
- A/B recibe la misma entrada cuando corresponde; referencias no se transmiten; snapshots se conservan. No forzar verificación de identidad o compatibilidad de campañas si el cliente no aporta evidencia suficiente.
- Demo sigue siendo consulta estática, sin montar conexión, ejecutar el cliente ni consultar API.

El siguiente entregable razonable sería la prueba mínima del cliente y un adaptador local de texto. El conector completo con herramientas, adjuntos y campañas necesitaría ampliar y verificar ese alcance después. No se ha creado un botón de conexión ficticio ni una promesa de cuota garantizada.
