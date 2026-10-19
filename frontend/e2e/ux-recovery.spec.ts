import { test, expect, register, compare, finished, detail } from './helpers';
import { Page } from '@playwright/test';
import path from 'node:path';
import { randomUUID } from 'node:crypto';

async function logout(page:Page) {
  await page.getByRole('button',{name:'Perfil de Prueba E2E'}).click();
  await page.getByRole('button',{name:'Cerrar sesión',exact:true}).click();
  await expect(page.getByLabel('Usuario',{exact:true})).toBeVisible();
}
async function login(page:Page, username:string) {
  await page.goto('/');
  await page.getByLabel('Usuario',{exact:true}).fill(username);
  await page.getByLabel('Contraseña',{exact:true}).fill('Fixture-password-42');
  await page.getByRole('button',{name:'Entrar',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Una nueva comparación'})).toBeVisible();
}
async function evidence(page:Page, name:string, project:string) {
  await page.screenshot({path:path.resolve('..','runtime','ux-review-evidence',`${name}-${project}.png`),fullPage:true});
}

test('borrador por cuenta: teclado, recarga, adjuntos, descarte y resultado inmutable', async ({page},info) => {
  const first=await register(page);
  await page.getByLabel('Entradas independientes',{exact:true}).check();
  await page.getByLabel('Nombre',{exact:true}).fill('Borrador ficticio A');
  await page.getByLabel('Entrada A',{exact:true}).fill('Texto privado A');
  await page.getByLabel('Entrada B',{exact:true}).fill('Texto privado B');
  await page.getByText('Editar instrucciones A',{exact:true}).click();
  await page.locator('#prompt-a').fill('Prompt ficticio conservado.');
  await page.getByText('Condiciones de ejecución',{exact:true}).click();
  await page.getByLabel('Semilla (0–2147483647)',{exact:true}).fill('321');
  await page.locator('#a-files').setInputFiles({name:'nota.txt',mimeType:'text/plain',buffer:Buffer.from('Adjunto ficticio')});
  await page.locator('#b-files').setInputFiles({name:'otra-nota.txt',mimeType:'text/plain',buffer:Buffer.from('Segundo adjunto ficticio')});
  await expect(page.getByText('nota.txt',{exact:false}).first()).toBeVisible();
  await expect(page.getByRole('status').filter({hasText:'Borrador guardado'})).toBeVisible();
  await page.reload();
  const recover=page.getByRole('button',{name:'Recuperar borrador'});
  await expect(recover).toBeVisible(); await recover.focus(); await page.keyboard.press('Enter');
  await expect(page.getByLabel('Entrada A',{exact:true})).toHaveValue('Texto privado A');
  await expect(page.getByLabel('Nombre',{exact:true})).toHaveValue('Borrador ficticio A');
  await expect(page.locator('#prompt-a')).toHaveValue('Prompt ficticio conservado.');
  await expect(page.locator('#seed')).toHaveValue('321');
  await expect(page.getByText('Reselecciona nota.txt en Entrada A.')).toBeVisible();
  await page.getByRole('button',{name:'Ejecutar comparación'}).click();
  await expect(page.getByRole('alert')).toContainText('Reselecciona');
  await evidence(page,'borrador-recuperado',info.project.name);
  await page.getByRole('button',{name:'Omitir nota.txt'}).click();
  await page.locator('#b-files').setInputFiles({name:'otra-nota.txt',mimeType:'text/plain',buffer:Buffer.from('Segundo adjunto ficticio')});
  await expect(page.getByText('Reselecciona otra-nota.txt en Entrada B.')).toHaveCount(0);
  const created=page.waitForResponse(r=>r.url().endsWith('/api/comparisons') && r.request().method()==='POST');
  await page.getByRole('button',{name:'Ejecutar comparación'}).click();
  const id=(await (await created).json()).id;
  await expect(page.getByRole('heading',{name:'Borrador ficticio A',exact:true})).toBeVisible();
  const original=await detail(page,id);
  await page.getByRole('button',{name:'Comparar',exact:true}).click();
  await page.getByLabel('Entrada A',{exact:true}).fill('Preparación siguiente');
  await logout(page);
  await register(page);
  await page.getByLabel('Entradas independientes',{exact:true}).check();
  await expect(page.getByRole('button',{name:'Recuperar borrador'})).toHaveCount(0);
  await expect(page.getByLabel('Entrada A',{exact:true})).toHaveValue('');
  await page.getByLabel('Entrada A',{exact:true}).fill('Cuenta diferente');
  await logout(page); await login(page,first);
  await page.getByRole('button',{name:'Recuperar borrador'}).click();
  await expect(page.getByLabel('Entrada A',{exact:true})).toHaveValue('Preparación siguiente');
  expect((await detail(page,id)).snapshot).toEqual(original.snapshot);
  await page.getByRole('button',{name:'Descartar borrador'}).click();
  await page.reload();
  await expect(page.getByRole('heading',{name:'Una nueva comparación'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Recuperar borrador'})).toHaveCount(0);
  // Profile preferences save separately from the local draft. Select the editor
  // explicitly: this assertion verifies discarded data, not preference timing.
  const shared = page.getByLabel('Entrada compartida',{exact:true});
  if (await shared.isVisible()) await expect(shared).toHaveValue('');
  await page.getByLabel('Entradas independientes',{exact:true}).check();
  await expect(page.getByLabel('Entrada A',{exact:true})).toHaveValue('');
  await expect(page.getByLabel('Entrada B',{exact:true})).toHaveValue('');
});

test('dataset normalizado recuperable y error con ID, archivo y filas', async ({page},info)=>{
  await register(page);
  await page.getByRole('button',{name:'Dos modelos',exact:false}).click();
  await page.getByLabel('Datos de la prueba').selectOption('dataset');
  await page.getByLabel('Seleccionar dataset').setInputFiles({name:'casos.csv',mimeType:'text/csv',buffer:Buffer.from('id,input,expected_answer\na,hola,hola\nb,adiós,adiós')});
  await expect(page.getByRole('status').filter({hasText:'casos.csv'})).toContainText('2 casos');
  await page.reload(); await page.getByRole('button',{name:'Recuperar borrador'}).click();
  await expect(page.getByRole('button',{name:'Dos modelos',exact:false})).toHaveAttribute('aria-pressed','true');
  await expect(page.getByRole('status').filter({hasText:'casos.csv'})).toContainText('2 casos');
  await page.locator('.dataset-cases > summary').press('Enter');
  await expect(page.getByRole('cell',{name:'adiós',exact:true})).toHaveCount(2);
  await page.getByLabel('Seleccionar dataset').setInputFiles({name:'duplicados.csv',mimeType:'text/csv',buffer:Buffer.from('id,input\nrepetido,uno\nrepetido,dos')});
  await expect(page.getByRole('alert')).toContainText('duplicados.csv: ID duplicado «repetido»: filas 2 y 3');
  await expect(page.getByRole('button',{name:'Ejecutar comparación'})).toBeDisabled();
  await expect(page.getByLabel('Seleccionar dataset')).toHaveAttribute('aria-describedby','dataset-error');
  await evidence(page,'dataset-error-detallado',info.project.name);
  await page.getByRole('link',{name:'Ver formato y ejemplo',exact:true}).click();
  await expect(page.getByRole('dialog',{name:'Prepara tu dataset'})).toBeVisible();
  await page.keyboard.press('Escape');
});

test('URL: recarga, Atrás/Adelante, selección, ID inválido y cuenta ajena', async ({page},info)=>{
  await register(page);
  const a=await compare(page,'Primera ruta'); await finished(page,a);
  await expect(page).toHaveURL(new RegExp(`#/results\\?comparison=${a}`));
  await page.getByRole('button',{name:'Modelos',exact:true}).click();
  if (await page.locator('.secondary-menu').isVisible()) await page.locator('.secondary-menu > summary').click();
  await page.getByRole('button',{name:'Guía',exact:true}).click();
  await page.goBack(); await expect(page.getByRole('heading',{name:'Tus modelos, de un vistazo.'})).toBeVisible();
  await page.goBack(); await expect(page.getByRole('heading',{name:'Primera ruta',exact:true})).toBeVisible();
  await page.goForward(); await expect(page.getByRole('heading',{name:'Tus modelos, de un vistazo.'})).toBeVisible();
  await page.reload(); await expect(page.getByRole('heading',{name:'Tus modelos, de un vistazo.'})).toBeVisible();
  await page.getByRole('button',{name:'Comparar',exact:true}).click();
  const b=await compare(page,'Segunda ruta'); await finished(page,b);
  await page.reload(); await expect(page.getByRole('heading',{name:'Segunda ruta',exact:true})).toBeVisible();
  await page.getByText('Historial',{exact:false}).first().click();
  await page.getByRole('button',{name:/Primera ruta.*finalizadas/}).click();
  await expect(page).toHaveURL(new RegExp(`comparison=${a}`));
  await expect(page.getByRole('heading',{name:'Primera ruta',exact:true})).toBeVisible();
  await page.goto('/#/results?comparison=inexistente');
  await expect(page.getByRole('alert')).toContainText('Puede no existir o no pertenecer a tu cuenta');
  await evidence(page,'ruta-invalida',info.project.name);
  await page.getByRole('button',{name:'Volver a Comparar',exact:true}).click();
  await expect(page).toHaveURL(/#\/compose$/);
  await logout(page); await register(page);
  await page.goto(`/#/results?comparison=${a}`);
  await expect(page.getByRole('alert')).toContainText('Puede no existir o no pertenecer a tu cuenta');
  await expect(page.getByRole('heading',{name:'Primera ruta',exact:true})).toHaveCount(0);
});

test('biblioteca conserva fichas ocultas y traza cierra con Escape y devuelve foco', async ({page},info)=>{
  await register(page);
  await page.getByRole('button',{name:'Dos modelos',exact:false}).click();
  await page.getByLabel('Entrada compartida',{exact:true}).fill('Caso ficticio compartido');
  await page.getByLabel('Nombre',{exact:true}).fill('Selección persistente');
  const created=page.waitForResponse(r=>r.url().endsWith('/api/comparisons') && r.request().method()==='POST');
  await page.getByRole('button',{name:'Ejecutar comparación'}).click();
  const id=(await (await created).json()).id; await finished(page,id);
  const trigger=page.getByRole('button',{name:/Ver traza de .*rama A/}).first();
  await trigger.focus(); await page.keyboard.press('Enter');
  await expect(page.locator('#trace-title')).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button',{name:'Cerrar traza'})).toHaveCount(0); await expect(trigger).toBeFocused();
  await page.getByRole('button',{name:'Modelos',exact:true}).click();
  const checks=page.getByRole('checkbox',{name:/Seleccionar simulated-/});
  await checks.nth(0).check(); await checks.nth(1).check();
  await page.getByRole('combobox',{name:'Modelo',exact:true}).selectOption('simulated-a:latest');
  await expect(page.getByRole('status').filter({hasText:'2/2 seleccionados'})).toBeVisible();
  await expect(page.getByRole('status').filter({hasText:'1 seleccionados fuera del filtro'})).toBeVisible();
  await expect(checks).toHaveCount(1); await expect(checks).toBeChecked();
  await evidence(page,'biblioteca-seleccion',info.project.name);
  await page.getByRole('button',{name:/Quitar selección de simulated-b/}).click();
  await expect(page.getByRole('status').filter({hasText:'1/2 seleccionados'})).toBeVisible();
  await page.getByRole('combobox',{name:'Ejecución',exact:true}).selectOption('ollama');
  await expect(page.getByRole('status').filter({hasText:'1 seleccionados fuera del filtro'})).toBeVisible();
});

for (const status of [200,401]) test(`validación tardía ${status} no recupera datos ni cierra la nueva sesión`, async ({page})=>{
  await register(page);
  let release!:()=>void, started!:()=>void, handled!:()=>void;
  const gate=new Promise<void>(resolve=>release=resolve), requested=new Promise<void>(resolve=>started=resolve);
  const completed=new Promise<void>(resolve=>handled=resolve);
  await page.route('**/api/datasets/validate',async route=>{
    const response=await route.fetch(); started(); await gate; await route.fulfill({response,status}); handled();
  });
  await page.getByLabel('Datos de la prueba').selectOption('dataset');
  await page.getByLabel('Seleccionar dataset').setInputFiles({name:'privado.csv',mimeType:'text/csv',buffer:Buffer.from('id,input\na,Secreto de cuenta A')});
  await requested; await logout(page);
  if (await page.getByRole('button',{name:'¿Primera vez? Crear una cuenta'}).isVisible()) await page.getByRole('button',{name:'¿Primera vez? Crear una cuenta'}).click();
  await page.getByLabel('Tu nombre',{exact:true}).fill('Prueba E2E');
  await page.getByLabel('Usuario',{exact:true}).fill(`ux_${randomUUID().replaceAll('-','').slice(0,24)}`);
  await page.getByLabel('Contraseña',{exact:true}).fill('Fixture-password-42');
  await page.getByRole('button',{name:'Crear cuenta',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Perfil',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Comparar',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Una nueva comparación'})).toBeVisible();
  release(); await completed; await page.unroute('**/api/datasets/validate');
  await expect(page.getByRole('button',{name:'Recuperar borrador'})).toHaveCount(0);
  await expect(page.getByText('Secreto de cuenta A',{exact:true})).toHaveCount(0);
  await page.reload(); await expect(page.getByRole('button',{name:'Recuperar borrador'})).toHaveCount(0);
});

test('envío sin confirmación: recuperar no crea otra comparación', async ({page})=>{
  await register(page);
  await page.getByLabel('Entradas independientes',{exact:true}).check();
  await page.getByLabel('Entrada A',{exact:true}).fill('Caso ficticio A');
  await page.getByLabel('Entrada B',{exact:true}).fill('Caso ficticio B');
  let savedId='';
  await page.route('**/api/comparisons',async route=>{
    const response=await route.fetch();
    savedId=(await response.json()).id;
    await route.abort('connectionreset');
  });
  await page.getByRole('button',{name:'Ejecutar comparación'}).click();
  await expect(page.getByRole('alert')).toContainText('No se pudo confirmar');
  expect(savedId).not.toBe('');
  await page.reload();
  await expect(page.getByRole('status').filter({hasText:'Hay un envío pendiente de confirmar'})).toBeVisible();
  await page.getByRole('button',{name:'Recuperar borrador'}).click();
  await expect(page.getByLabel('Entrada A',{exact:true})).toHaveValue('Caso ficticio A');
  const experiments=await (await page.request.get('/api/experiments')).json();
  expect(experiments).toHaveLength(1);expect(experiments[0].id).toBe(savedId);
});
