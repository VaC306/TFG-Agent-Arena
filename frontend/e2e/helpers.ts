import { test as base, expect, Page, Locator } from '@playwright/test';
import { randomUUID, createHash } from 'node:crypto';

export { expect };
export const test=base.extend<{clientIdentity:void}>({
  clientIdentity:[async ({context},use,info)=>{
    // Separate rate-limit buckets as well as browser sessions, including repetitions.
    // Only the test server trusts this loopback proxy; no production setting changes.
    const identity=createHash('sha256').update(`${info.testId}:${info.repeatEachIndex}`).digest('hex');
    await context.setExtraHTTPHeaders({'X-Forwarded-For':`2001:db8:${identity.match(/.{4}/g)!.slice(0,6).join(':')}`});
    await use();
  },{auto:true}],
});

export async function register(page:Page) {
  const username = `e2e_${randomUUID().replaceAll('-','').slice(0,24)}`;
  await page.goto('/');
  await page.getByRole('button',{name:'¿Primera vez? Crear una cuenta'}).click();
  await expect(page.getByRole('heading',{name:'Crea tu espacio'})).toBeFocused();
  await page.getByLabel('Tu nombre',{exact:true}).fill('Prueba E2E');
  await page.getByLabel('Usuario',{exact:true}).fill(username);
  await page.getByLabel('Contraseña',{exact:true}).fill('Fixture-password-42');
  await expect(page.getByLabel('Usuario',{exact:true})).toHaveValue(username);
  await page.getByRole('button',{name:'Crear cuenta',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Una nueva comparación'})).toBeVisible();
  return username;
}

export async function compare(page:Page, name:string, input='saludo', timeout=10) {
  await page.getByRole('button',{name:'Comparar',exact:true}).click();
  await page.getByLabel('Nombre',{exact:true}).fill(name);
  // The test server supplies ControlledAdapter for the Ollama contract. No model is loaded.
  await page.getByLabel('Ejecución',{exact:true}).selectOption('ollama');
  await page.getByLabel('Modelo compartido A/B').selectOption('fixture:latest');
  await page.getByLabel('Datos de la prueba').selectOption('dataset');
  await page.getByLabel('Seleccionar dataset').setInputFiles({
    name:'fixture.csv', mimeType:'text/csv', buffer:Buffer.from(`id,input,expected_answer\ncase,${input},hola\n`),
  });
  await expect(page.getByRole('status').filter({hasText:'fixture.csv'})).toContainText('1 casos · 1 con referencia · 2 ejecuciones');
  const conditions=page.locator('details').filter({has:page.getByText('Condiciones de ejecución',{exact:true})});
  if (await conditions.getAttribute('open') === null) await page.getByText('Condiciones de ejecución',{exact:true}).click();
  await page.getByLabel('Semilla (0–2147483647)',{exact:true}).fill('17');
  await page.getByLabel('Tiempo límite (1–3600 segundos)',{exact:true}).fill(String(timeout));
  const created = page.waitForResponse(response => response.url().endsWith('/api/comparisons') && response.request().method()==='POST');
  await page.getByRole('button',{name:'Ejecutar comparación'}).click();
  const response = await created;
  expect(response.status()).toBe(201);
  const {id} = await response.json();
  await expect(page.getByRole('heading',{name,exact:true})).toBeVisible();
  return id as string;
}

export async function detail(page:Page, id:string) {
  const response = await page.request.get(`/api/experiments/${id}`);
  expect(response.ok()).toBeTruthy();
  return response.json();
}
export async function finished(page:Page,id:string) {
  await expect.poll(async () => (await detail(page,id)).runs.every((run:any) => !['queued','running'].includes(run.status))).toBe(true);
  await page.getByRole('button',{name:'↻ Actualizar',exact:true}).click();
  await expect(page.getByRole('button',{name:'Cancelar',exact:true})).toHaveCount(0);
  await expect(page.getByRole('progressbar',{name:'Ejecuciones finalizadas'})).toHaveAttribute('value','2');
  return detail(page,id);
}
export async function idle(page:Page) {
  await expect(page.getByRole('progressbar',{name:'Procesando solicitudes'})).toHaveCount(0);
  await expect(page.locator('arena-loading')).toHaveCount(0);
}
export async function download(page:Page, link:Locator) {
  const pending = page.waitForEvent('download');
  await link.click();
  const file = await pending;
  expect(await file.failure()).toBeNull();
  const stream = await file.createReadStream();
  const chunks:Buffer[] = [];
  for await (const chunk of stream!) chunks.push(Buffer.from(chunk));
  return Buffer.concat(chunks).toString('utf8');
}
export function csvRows(text:string) {
  const rows:string[][] = []; let row:string[] = [], cell='', quoted=false;
  for (let i=0;i<text.length;i++) {
    const c=text[i];
    if (c==='"') { if (quoted && text[i+1]==='"') {cell+='"';i++;} else quoted=!quoted; }
    else if (c===',' && !quoted) {row.push(cell);cell='';}
    else if (c==='\n' && !quoted) {row.push(cell.replace(/\r$/,''));rows.push(row);row=[];cell='';}
    else cell+=c;
  }
  const header=rows.shift()!;
  return rows.map(values=>Object.fromEntries(header.map((key,i)=>[key,values[i]])));
}
