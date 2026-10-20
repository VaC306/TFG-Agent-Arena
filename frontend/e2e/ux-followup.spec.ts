import {test,expect,register,detail} from './helpers';
import {Page} from '@playwright/test';
import path from 'node:path';
const {checkContrast}=require('../tests/browser-colors.cjs');
const evidence=(name:string,project:string)=>path.resolve('..','runtime','ux-followup-evidence',`${name}-${project}.png`);
async function send(page:Page) {
  const pending=page.waitForResponse(r=>r.url().endsWith('/api/comparisons')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Ejecutar comparación',exact:true}).click();
  const response=await pending;expect(response.status()).toBe(201);
  const id=(await response.json()).id;
  await expect.poll(async()=>(await detail(page,id)).runs.every((r:any)=>!['queued','running'].includes(r.status))).toBe(true);
  await page.getByRole('button',{name:'↻ Actualizar',exact:true}).click();return id as string;
}
async function logout(page:Page) {
  await page.getByRole('button',{name:'Perfil de Prueba E2E'}).click();
  await page.getByRole('button',{name:'Cerrar sesión',exact:true}).click();
  await expect(page.getByLabel('Usuario',{exact:true})).toBeVisible();
  await expect(page).toHaveURL(/#\/compose$/);
}

test('entrada de cada caso y repetición desde snapshot, evaluación accesible y borrador independiente',async({page},info)=>{
  await page.emulateMedia({reducedMotion:'reduce'});await register(page);
  await page.getByLabel('Datos de la prueba').selectOption('dataset');
  await page.getByLabel('Seleccionar dataset').setInputFiles({name:'contexto.csv',mimeType:'text/csv',buffer:Buffer.from('id,input,expected_answer\nprimero,Entrada del primer caso,\nsegundo,Entrada del segundo caso,\n')});
  await expect(page.locator('.dataset-summary')).toContainText('2 casos');
  await page.locator('.protocol-settings > summary').press('Enter');
  await expect(page.locator('.advanced-settings')).not.toHaveAttribute('open');
  await page.getByLabel('Repeticiones (1–10)').fill('2');
  await page.getByLabel('Cómo evaluar las respuestas').selectOption('none');
  await expect(page.getByLabel('Calentamiento',{exact:true})).not.toBeVisible();
  const id=await send(page),snapshot=(await detail(page,id)).snapshot;
  await page.getByRole('button',{name:'Ver los 4 casos y repeticiones',exact:true}).press('Enter');
  await expect(page.locator('.case-result')).toHaveCount(4);
  for(const card of await page.locator('.case-result').all()) {
    const title=await card.locator('h3').innerText();
    await card.locator('.case-input > summary').press('Enter');
    await expect(card.locator('.case-input')).toContainText(title.startsWith('primero')?'Entrada del primer caso':'Entrada del segundo caso');
    await expect(card.locator('.case-input')).toContainText('Entrada compartida por A y B');
  }
  for(const theme of ['light','dark']) {
    await page.getByLabel('Tema',{exact:true}).selectOption(theme);await checkContrast(page);
    await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    await page.screenshot({path:evidence(`entradas-${theme}`,info.project.name),fullPage:true});
  }
  await page.getByRole('button',{name:'Comparar',exact:true}).click();
  await page.getByLabel('Datos de la prueba').selectOption('manual');
  await page.getByLabel('Entradas independientes',{exact:true}).check();
  await page.getByLabel('Entrada A',{exact:true}).fill('Petición independiente A');
  await page.getByLabel('Entrada B',{exact:true}).fill('Petición independiente B');
  const independent=await send(page);
  const card=page.locator('.case-result').first();await card.locator('.case-input > summary').press('Enter');
  await expect(card.locator('.case-input')).toContainText('Entrada A');await expect(card.locator('.case-input')).toContainText('Petición independiente A');
  await expect(card.locator('.case-input')).toContainText('Entrada B');await expect(card.locator('.case-input')).toContainText('Petición independiente B');
  expect((await detail(page,id)).snapshot).toEqual(snapshot);expect((await detail(page,independent)).snapshot.branch_tasks).toBeTruthy();
});

test('cierre explícito limpia ruta, conserva borrador por cuenta y respeta enlaces profundos',async({page},info)=>{
  const first=await register(page);await page.getByLabel('Entrada compartida',{exact:true}).fill('Borrador privado de primera cuenta');
  const pending=page.waitForResponse(r=>r.url().endsWith('/api/experiments')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Probar recorrido simulado de pedidos',exact:true}).click();const id=(await(await pending).json()).id;
  await expect(page).toHaveURL(new RegExp(id));await logout(page);
  await register(page);await page.getByRole('button',{name:'Modelos',exact:true}).click();
  await expect(page.locator('main')).toContainText('Aquí aparecerán tus modelos.');
  await expect(page.getByRole('alert')).toHaveCount(0);await expect(page.getByRole('button',{name:'Recuperar borrador'})).toHaveCount(0);
  await page.screenshot({path:evidence('cuenta-limpia',info.project.name),fullPage:true});
  await logout(page);
  // A deliberately supplied link at login must still survive authentication.
  await page.goto('/#/results?comparison='+id);
  if(await page.getByRole('button',{name:'Ya tengo cuenta. Iniciar sesión'}).isVisible())await page.getByRole('button',{name:'Ya tengo cuenta. Iniciar sesión'}).click();
  await page.getByLabel('Usuario',{exact:true}).fill(first);await page.getByLabel('Contraseña',{exact:true}).fill('Fixture-password-42');
  await page.getByRole('button',{name:'Entrar',exact:true}).click();await expect(page.locator('#results-title')).toContainText('prompts-pedidos-v1');
  await page.getByRole('button',{name:'Comparar',exact:true}).click();await page.getByRole('button',{name:'Recuperar borrador',exact:true}).press('Enter');
  await expect(page.getByLabel('Entrada compartida',{exact:true})).toHaveValue('Borrador privado de primera cuenta');
});

test('campañas vacías continúan a preparación o resultado y los avisos no siguen a otra sección',async({page})=>{
  await register(page);await page.getByRole('button',{name:'Campañas',exact:true}).click();
  await page.getByRole('button',{name:'Preparar comparación',exact:true}).press('Enter');await expect(page.locator('#page-title')).toBeFocused();
  await page.getByLabel('Entrada compartida',{exact:true}).fill('Entrada de continuidad');await send(page);
  await expect(page.locator('main > .alert[role=status]')).toContainText('guardada');
  await page.getByRole('button',{name:'Campañas',exact:true}).click();await expect(page.locator('main > .alert[role=status]')).toHaveCount(0);
  await page.getByRole('button',{name:'Abrir resultados',exact:true}).press('Enter');await expect(page.locator('#collection-title')).toBeFocused();
  await expect(page.locator('.case-result').first()).toContainText('Completada · sin evaluar');
});
