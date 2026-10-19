import {test,expect,register,compare,finished,detail} from './helpers';
import path from 'node:path';
const {checkContrast}=require('../tests/browser-colors.cjs');
const evidence=(name:string,project:string)=>path.resolve('..','runtime','claridad-evidence',`${name}-${project}.png`);

test('entrada primero, parámetros opcionales y resumen fiel antes de ejecutar',async({page},info)=>{
  await page.emulateMedia({colorScheme:'dark',reducedMotion:'reduce'});await register(page);
  const input=await page.getByLabel('Entrada compartida',{exact:true}).boundingBox();
  const models=await page.locator('#variants-heading').boundingBox();expect(input!.y).toBeLessThan(models!.y);
  await expect(page.locator('.protocol-settings')).not.toHaveAttribute('open');
  await expect(page.locator('.upload-zone')).not.toHaveAttribute('open');
  await page.getByRole('button',{name:'Ejecutar comparación'}).click();
  await expect(page.getByLabel('Entrada compartida',{exact:true})).toBeFocused();
  await page.getByLabel('Entrada compartida',{exact:true}).fill('Entrada ficticia para revisar');
  await page.locator('.protocol-settings > summary').press('Enter');
  await page.getByLabel('Repeticiones (1–10)').fill('2');
  await page.getByLabel('Cómo evaluar las respuestas').selectOption('none');
  await page.locator('.protocol-settings > summary').press('Enter');
  await expect(page.locator('.compose-review')).toContainText('2 repeticiones');
  await expect(page.locator('.compose-review')).toContainText('Sin evaluación automática');
  await checkContrast(page);await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:evidence('comparar',info.project.name),fullPage:true,scale:'css'});
  const created=page.waitForResponse(r=>r.url().endsWith('/api/comparisons')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Ejecutar comparación'}).click();
  const response=await created;expect(response.status()).toBe(201);const body=response.request().postDataJSON();
  expect(body.repetitions).toBe(2);expect(body.evaluation).toBe('none');expect(body.shared_input.text).toBe('Entrada ficticia para revisar');
});

test('respuestas antes de gráficos, denominadores fieles y todos los casos accesibles',async({page},info)=>{
  await page.emulateMedia({reducedMotion:'reduce'});await register(page);
  await page.getByLabel('Ejecución',{exact:true}).selectOption('ollama');
  await page.getByLabel('Modelo compartido A/B').selectOption('fixture:latest');
  await page.getByLabel('Datos de la prueba').selectOption('dataset');
  await page.getByLabel('Seleccionar dataset').setInputFiles({name:'visuales.csv',mimeType:'text/csv',buffer:Buffer.from('id,input,expected_answer\na,saludo,hola\nb,saludo,adios\nc,saludo,\nd,saludo,\n')});
  await expect(page.locator('.dataset-summary')).toContainText('4 casos');
  const created=page.waitForResponse(r=>r.url().endsWith('/api/comparisons')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Ejecutar comparación'}).click();const id=(await(await created).json()).id;
  await expect.poll(async()=> (await detail(page,id)).runs.every((r:any)=>!['queued','running'].includes(r.status))).toBe(true);
  await page.getByRole('button',{name:'↻ Actualizar',exact:true}).click();
  const original=(await detail(page,id)).snapshot;
  await expect(page.locator('.case-result')).toHaveCount(3);
  await expect(page.locator('.case-responses')).toContainText('3 de 4');
  const answers=await page.locator('.case-responses').boundingBox(),chart=await page.locator('.visual-analysis').boundingBox();expect(answers!.y).toBeLessThan(chart!.y);
  await expect(page.locator('arena-outcome-chart .outcome-correct.outcome-segment').first()).toHaveAttribute('style',/width: 25%/);
  await expect(page.getByRole('img',{name:/4 ejecuciones programadas.*1 correctas.*1 incorrectas.*2 sin evaluar/})).toHaveCount(2);
  await expect(page.locator('.analysis-details')).not.toHaveAttribute('open');
  await page.getByRole('button',{name:'Ver los 4 casos y repeticiones'}).press('Enter');
  await expect(page.locator('.case-result')).toHaveCount(4);await expect(page.locator('#response-case-3')).toBeFocused();
  await page.locator('.analysis-details > summary').press('Enter');await expect(page.locator('arena-time-chart')).toBeVisible();
  await checkContrast(page);await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:evidence('resultados',info.project.name),fullPage:true,scale:'css'});
  expect((await detail(page,id)).snapshot).toEqual(original);
  await page.getByRole('button',{name:'Mostrar los primeros 3'}).press('Enter');await expect(page.locator('#response-case-0')).toBeFocused();
});

test('evolución distingue excluidos y conserva tabla y evidencia por teclado',async({page},info)=>{
  await page.emulateMedia({colorScheme:'dark',reducedMotion:'reduce'});await register(page);
  const id=await compare(page,'Evolución ficticia');await finished(page,id);
  await page.getByText('Campaña y repetición del diseño',{exact:true}).press('Enter');await page.getByLabel('Nombre de campaña').fill('Claridad visual');
  await page.getByRole('button',{name:'Crear campaña',exact:true}).click();
  await expect(page.locator('.campaign-visual .time-track i')).toHaveCount(2);
  await expect(page.locator('.campaign-attempts')).not.toHaveAttribute('open');
  await page.locator('.campaign-attempts > summary').press('Enter');await page.getByText('Registrar condiciones externas',{exact:true}).press('Enter');
  await page.getByLabel('Intento',{exact:true}).selectOption(id);await page.getByLabel('Tipo de anotación').selectOption('deviation');await page.getByLabel('Condiciones observadas').fill('Diferencia ficticia de carga');
  await page.getByRole('button',{name:'Guardar anotación',exact:true}).click();
  await expect(page.getByRole('status').filter({hasText:'Diferencia de condiciones guardada'})).toBeVisible();
  await expect(page.locator('.campaign-visual .time-track i')).toHaveCount(0);await expect(page.locator('.campaign-visual')).toContainText('Excluido');
  await expect(page.getByRole('region',{name:'Evolución de la campaña, tabla desplazable'})).toBeVisible();
  await page.locator('.campaign-attempts > summary').press('Enter');await checkContrast(page);
  await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:evidence('campana',info.project.name),fullPage:true,scale:'css'});
});
