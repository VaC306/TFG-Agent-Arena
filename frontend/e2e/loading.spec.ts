import { test, expect, register, idle } from './helpers';

test('dataset inválido, reimportación JSONL y recuperación tras fallo de API', async ({page})=>{
  await register(page);
  await page.getByLabel('Datos de la prueba').selectOption('dataset');
  await page.getByLabel('Seleccionar dataset').setInputFiles({name:'invalid.csv',mimeType:'text/csv',buffer:Buffer.from('wrong,header\nx,y\n')});
  await expect(page.getByRole('alert')).toBeVisible();
  await expect(page.getByRole('button',{name:'Ejecutar comparación'})).toBeDisabled();
  await idle(page);
  await page.route('**/api/datasets/validate',route=>route.abort('connectionrefused'));
  const file={name:'cases.jsonl',mimeType:'application/x-ndjson',buffer:Buffer.from('{"id":"json-case","input":"saludo","expected_answer":"hola"}\n')};
  await page.getByLabel('Seleccionar dataset').setInputFiles(file);
  await expect(page.getByRole('alert')).toContainText('No se pudo validar');
  await idle(page);
  await page.unroute('**/api/datasets/validate');
  await page.getByLabel('Seleccionar dataset').setInputFiles(file);
  await expect(page.getByRole('status').filter({hasText:'cases.jsonl'})).toContainText('1 casos');
  await expect(page.getByRole('alert')).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Ejecutar comparación'})).toBeEnabled();
  await idle(page);
});

test('salir de biblioteca durante carga y volver tras error libera indicadores', async ({page})=>{
  await register(page);
  let release!:()=>void, entered!:()=>void, fulfilled!:()=>void;
  const gate=new Promise<void>(resolve=>{release=resolve;});
  const observed=new Promise<void>(resolve=>{entered=resolve;});
  const drained=new Promise<void>(resolve=>{fulfilled=resolve;});
  await page.route('**/api/model-results',async route=>{
    const response=await route.fetch(); entered(); await gate;
    await route.fulfill({response}); fulfilled();
  });
  await page.getByRole('button',{name:'Modelos',exact:true}).click(); await observed;
  await expect(page.getByRole('heading',{name:'Tus modelos, de un vistazo.'})).toBeFocused();
  await page.getByRole('button',{name:'Guía',exact:true}).click();
  const delivered=page.waitForResponse(response=>response.url().endsWith('/api/model-results'));
  release(); await drained; await delivered; await page.unroute('**/api/model-results');
  await expect(page.getByRole('heading',{name:'Tus modelos, de un vistazo.'})).toHaveCount(0);
  await idle(page);
  await page.route('**/api/model-results',route=>route.abort('connectionrefused'));
  await page.getByRole('button',{name:'Modelos',exact:true}).click();
  await expect(page.getByRole('alert')).toBeVisible(); await idle(page);
  await page.unroute('**/api/model-results');
  await page.getByRole('button',{name:'Actualizar',exact:true}).click();
  await expect(page.getByRole('alert')).toHaveCount(0); await idle(page);
});
