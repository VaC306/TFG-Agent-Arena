import { test,expect,register,compare,finished,detail } from './helpers';
import path from 'node:path';

test('prompts con datos compartidos: alternar modos, recuperar y ejecutar sin cambiar el diseño anterior',async({page},info)=>{
  await register(page);
  await expect(page.getByLabel('Entradas independientes',{exact:true})).not.toBeChecked();
  await page.getByLabel('Entrada compartida',{exact:true}).fill('Texto compartido ficticio');
  await page.getByLabel('Entradas independientes',{exact:true}).check();
  await page.getByLabel('Entrada A',{exact:true}).fill('Texto independiente A');
  await page.getByLabel('Entrada B',{exact:true}).fill('Texto independiente B');
  await expect(page.locator('.design-changes')).toContainText('datos o referencias');
  await page.getByLabel('Entradas independientes',{exact:true}).uncheck();
  await expect(page.getByLabel('Entrada compartida',{exact:true})).toHaveValue('Texto compartido ficticio');
  await page.getByRole('button',{name:'Dos modelos',exact:false}).click();
  await expect(page.getByLabel('Entrada compartida',{exact:true})).toHaveValue('Texto compartido ficticio');
  await expect(page.locator('.design-changes')).toContainText('modelo');
  await page.getByRole('button',{name:'Un modelo',exact:false}).click();
  await page.reload(); await page.getByRole('button',{name:'Recuperar borrador'}).click();
  await expect(page.getByLabel('Entradas independientes',{exact:true})).not.toBeChecked();
  await expect(page.getByLabel('Entrada compartida',{exact:true})).toHaveValue('Texto compartido ficticio');
  await page.getByLabel('Entradas independientes',{exact:true}).check();
  await expect(page.getByLabel('Entrada A',{exact:true})).toHaveValue('Texto independiente A');
  await expect(page.getByLabel('Entrada B',{exact:true})).toHaveValue('Texto independiente B');
  await page.getByLabel('Entradas independientes',{exact:true}).uncheck();
  const created=page.waitForResponse(r=>r.url().endsWith('/api/comparisons')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Ejecutar comparación'}).click();
  const response=await created, id=(await response.json()).id;
  expect(response.request().postDataJSON()).toMatchObject({comparison:'same_model',shared_input:{text:'Texto compartido ficticio'}});
  const original=await finished(page,id);
  expect(original.snapshot.conditions.inputs_shared).toBe(true);expect(original.snapshot.branch_tasks).toBeNull();
  await expect(page.locator('.case-answer')).toHaveCount(2);
  await expect(page.locator('.case-answer').first()).toContainText('Texto compartido ficticio');
  await expect(page.locator('.run-details')).not.toHaveAttribute('open');
  await page.screenshot({path:path.resolve('..','runtime','ux-review-evidence',`respuestas-por-caso-${info.project.name}.png`),fullPage:true});
  await page.getByRole('button',{name:'Comparar',exact:true}).click();
  await page.getByLabel('Entrada compartida',{exact:true}).fill('Siguiente borrador');
  expect((await detail(page,id)).snapshot).toEqual(original.snapshot);
});

test('borrador anterior conserva su elección de entradas independientes',async({page})=>{
  await register(page); await page.getByLabel('Entradas independientes',{exact:true}).check();
  await page.getByLabel('Entrada A',{exact:true}).fill('Entrada anterior A');
  await page.getByLabel('Entrada B',{exact:true}).fill('Entrada anterior B');
  await page.evaluate(()=>{
    const key=Object.keys(localStorage).find(k=>k.startsWith('arena.composer.v1.'))!;
    const draft=JSON.parse(localStorage.getItem(key)!);delete draft.config.independentInputs;
    localStorage.setItem(key,JSON.stringify(draft));
  });
  await page.reload();await page.getByRole('button',{name:'Recuperar borrador'}).click();
  await expect(page.getByLabel('Entradas independientes',{exact:true})).toBeChecked();
  await expect(page.getByLabel('Entrada A',{exact:true})).toHaveValue('Entrada anterior A');
  await expect(page.getByLabel('Entrada B',{exact:true})).toHaveValue('Entrada anterior B');
});

test('respuestas primero, campaña secundaria e intentos/tareas/método por teclado',async({page},info)=>{
  await register(page);const id=await compare(page,'Revisión por caso');await finished(page,id);
  await expect(page.locator('.case-answer')).toHaveCount(2);
  await expect(page.locator('.case-answer').first()).toHaveText('hola');
  const answer=await page.locator('.case-result').boundingBox(), action=await page.locator('.campaign-action').boundingBox();
  expect(answer!.y).toBeLessThan(action!.y);
  await expect(page.getByLabel('Nombre de campaña')).not.toBeVisible();
  await page.getByText('Campaña y repetición del diseño',{exact:true}).press('Enter');
  await page.getByLabel('Nombre de campaña').fill('Campaña progresiva');
  await page.getByRole('button',{name:'Crear campaña',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Campaña progresiva',exact:true})).toBeVisible();
  await expect(page.locator('.campaign-attempts')).toHaveAttribute('open','');
  await expect(page.getByLabel('Mostrar tareas',{exact:true})).not.toBeVisible();
  await page.getByText('Por tarea',{exact:true}).press('Enter');
  await expect(page.getByLabel('Mostrar tareas',{exact:true})).toBeVisible();
  await page.getByText('Método y condiciones',{exact:true}).press('Enter');
  await expect(page.getByRole('heading',{name:'Diferencias e incertidumbre',exact:true})).toBeVisible();
  await page.getByText('Registrar condiciones externas',{exact:true}).press('Enter');
  await page.getByLabel('Intento',{exact:true}).selectOption(id);
  await page.getByLabel('Tipo de anotación').selectOption('observation');
  await page.getByLabel('Condiciones observadas').fill('Observación ficticia de la revisión UX');
  await page.getByRole('button',{name:'Guardar anotación',exact:true}).click();
  await expect(page.getByRole('status').filter({hasText:'Observación guardada'})).toContainText('no cambia la compatibilidad');
  await page.screenshot({path:path.resolve('..','runtime','ux-review-evidence',`campana-progresiva-${info.project.name}.png`),fullPage:true});
});

test('ejemplo simulado, worker contextual y navegación compacta sin overflow',async({page},info)=>{
  const modelRequests:string[]=[];
  page.on('request',r=>{if(r.url().endsWith('/api/models')||r.url().includes(':11434'))modelRequests.push(r.url());});
  await register(page);
  await page.getByLabel('Entrada compartida',{exact:true}).fill('Conservar mi preparación');
  await expect(page.locator('arena-composer arena-worker-status')).toContainText('Worker disponible');
  const created=page.waitForResponse(r=>r.url().endsWith('/api/experiments')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Probar ejemplo simulado',exact:true}).press('Enter');
  const id=(await(await created).json()).id;
  await expect.poll(async()=> (await detail(page,id)).runs.every((r:any)=>!['queued','running'].includes(r.status))).toBe(true);
  await page.getByRole('button',{name:'↻ Actualizar',exact:true}).click();
  await expect(page.locator('.experiment-meta')).toContainText('Motor: simulador');
  await expect(page.locator('.experiment-meta')).toContainText('Configurado A: qwen2.5:3b');
  await expect(page.locator('.agent-card').first()).toContainText('este modelo no se ejecutó');
  await page.getByRole('button',{name:'Comparar',exact:true}).click();
  await expect(page.getByLabel('Entrada compartida',{exact:true})).toHaveValue('Conservar mi preparación');
  for(const width of [390,768,887,1024]) {
    await page.setViewportSize({width,height:844});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  }
  await page.setViewportSize({width:390,height:844});
  await page.locator('.secondary-menu > summary').press('Enter');
  await page.getByRole('button',{name:'Guía',exact:true}).press('Enter');
  await expect(page.locator('arena-guide')).toBeVisible();
  await page.goBack();await expect(page.getByRole('heading',{name:'Compara con tus datos.',exact:true})).toBeVisible();
  await page.route('**/api/worker/status',r=>r.fulfill({json:{state:'no_recent_signal',queued:0,running:0}}));
  await page.locator('arena-composer').getByRole('button',{name:'Comprobar worker',exact:true}).click();
  await expect(page.locator('arena-composer arena-worker-status')).toContainText('Sin señal reciente');
  await page.screenshot({path:path.resolve('..','runtime','ux-review-evidence',`inicio-compacto-${info.project.name}.png`),fullPage:true});
  await page.getByRole('button',{name:'Perfil de Prueba E2E'}).click();
  await expect(page.getByText('ChatGPT',{exact:true})).not.toBeVisible();
  await page.getByText('Conexiones futuras',{exact:true}).press('Enter');
  await expect(page.getByText('ChatGPT',{exact:true})).toBeVisible();
  expect(modelRequests).toEqual([]);
});
