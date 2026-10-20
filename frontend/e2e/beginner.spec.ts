import {test,expect,register,detail} from './helpers';
import path from 'node:path';
const {checkContrast}=require('../tests/browser-colors.cjs');
const evidence=(name:string,project:string)=>path.resolve('..','runtime','beginner-evidence',`${name}-${project}.png`);

test('mapa fiel al borrador, navegación por teclado y revisión con las validaciones del envío',async({page},info)=>{
  await page.emulateMedia({reducedMotion:'reduce'});await register(page);
  const map=page.getByRole('navigation',{name:'Mapa de la comparación preparada'});
  await expect(map).toContainText('Datos compartidos A/B');await expect(map).toContainText('= Mismo modelo');
  await map.getByRole('button',{name:/Entrada/}).press('Enter');await expect(page.locator('#shared-input')).toBeFocused();
  await page.locator('#shared-input').fill('Entrada ficticia');
  await map.getByRole('button',{name:/Prompts diferentes/}).press('Enter');await expect(page.locator('#prompt-b')).toBeFocused();
  const promptA=await page.locator('#prompt-a').inputValue();await page.locator('#prompt-b').fill(promptA);
  await expect(map).toContainText('= Mismo prompt');
  await page.getByLabel('Entradas independientes',{exact:true}).check();await expect(map).toContainText('Datos independientes A/B');
  await map.getByRole('button',{name:/Entrada/}).press('Enter');await expect(page.locator('#a-input')).toBeFocused();
  await page.getByRole('button',{name:'Dos modelos',exact:false}).click();await expect(map).toContainText('↔ Modelos distintos');await expect(map).toContainText('Datos compartidos A/B');
  await map.getByRole('button',{name:/Variante B/}).press('Enter');await expect(page.locator('#model-b')).toBeFocused();
  await page.getByRole('button',{name:'Un modelo',exact:false}).click();await page.getByLabel('Entradas independientes',{exact:true}).uncheck();
  await map.getByRole('button',{name:/Evaluación/}).press('Enter');await expect(page.locator('#evaluation-mode')).toBeFocused();
  await page.locator('#evaluation-mode').selectOption('json_match');
  await page.locator('.reference-input > summary').press('Enter');await page.locator('#shared-reference').fill('no es JSON');
  await page.locator('.reference-input > summary').press('Enter');
  await expect(page.getByLabel('Estado de preparación')).toContainText('Revisa los datos');
  await page.locator('.preparation-problems > summary').press('Enter');
  await page.locator('.preparation-problems').getByRole('button',{name:/JSON válido/}).press('Enter');await expect(page.locator('#shared-reference')).toBeFocused();
  await page.getByRole('button',{name:'Ejecutar comparación'}).click();await expect(page.locator('#shared-reference')).toBeFocused();await expect(page.locator('#composer-error')).toContainText('JSON válido');
  await page.locator('#shared-reference').fill('"hola"');await expect(page.getByLabel('Estado de preparación')).toContainText('Datos preparados');
  for (const theme of ['light','dark']) {
    await page.getByRole('combobox',{name:'Tema',exact:true}).selectOption(theme);await expect(page.locator('html')).toHaveAttribute('data-theme',theme);await checkContrast(page);
    await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.locator('.protocol-settings > summary').click();
    await page.screenshot({path:evidence(`mapa-${theme}`,info.project.name),fullPage:true});
    await map.screenshot({path:evidence(`esquema-${theme}`,info.project.name)});
  }
});

test('ayuda opcional ejecuta ejemplo separado y conserva texto, archivos, dataset y snapshot',async({page},info)=>{
  await page.emulateMedia({colorScheme:'dark',reducedMotion:'reduce'});await register(page);
  await page.locator('#shared-input').fill('Borrador propio ficticio');
  await page.locator('.upload-zone > summary').click();await page.locator('#shared-files').setInputFiles({name:'nota.txt',mimeType:'text/plain',buffer:Buffer.from('Adjunto ficticio')});
  await expect(page.locator('.file-list')).toContainText('nota.txt');
  await page.getByLabel('Datos de la prueba').selectOption('dataset');await page.getByLabel('Seleccionar dataset').setInputFiles({name:'propio.csv',mimeType:'text/csv',buffer:Buffer.from('id,input,expected_answer\ncaso,Di hola,hola\n')});
  await expect(page.locator('.dataset-summary')).toContainText('propio.csv');
  await page.locator('.getting-started > summary').press('Enter');
  const created=page.waitForResponse(r=>r.url().endsWith('/api/experiments')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Abrir ejemplo guiado'}).press('Enter');const response=await created;expect(response.status()).toBe(201);const id=(await response.json()).id;
  await expect(page.getByLabel('Orientación de la ejecución')).toBeVisible();
  await expect.poll(async()=>(await detail(page,id)).runs.every((r:any)=>!['queued','running'].includes(r.status))).toBe(true);
  await page.getByRole('button',{name:'↻ Actualizar',exact:true}).click();
  await expect(page.getByLabel('Orientación de la ejecución')).toContainText('Recorrido finalizado');
  await page.getByText('Cómo leer los estados',{exact:true}).press('Enter');await checkContrast(page);
  await page.screenshot({path:evidence('resultados',info.project.name),fullPage:true});
  const snapshot=(await detail(page,id)).snapshot;
  await page.getByRole('button',{name:'Comparar',exact:true}).click();await expect(page.locator('.dataset-summary')).toContainText('propio.csv');
  await page.getByLabel('Datos de la prueba').selectOption('manual');await expect(page.locator('#shared-input')).toHaveValue('Borrador propio ficticio');await expect(page.locator('.file-list')).toContainText('nota.txt');
  await page.locator('#shared-input').fill('Nuevo borrador');expect((await detail(page,id)).snapshot).toEqual(snapshot);
});
