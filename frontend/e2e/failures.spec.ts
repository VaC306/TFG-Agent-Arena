import { test, expect, register, compare, detail, finished, idle } from './helpers';

test('cancelación real conserva trazas y libera el worker', async ({page}) => {
  await register(page);
  const id=await compare(page,'Cancelación','[block]');
  await expect.poll(async()=> (await detail(page,id)).runs.some((r:any)=>r.status==='running')).toBe(true);
  await page.getByRole('button',{name:'↻ Actualizar',exact:true}).click();
  await page.getByText('Tabla de ejecuciones y métricas técnicas',{exact:true}).click();
  const running=page.getByRole('row').filter({has:page.locator('[data-status="running"]')});
  await running.getByRole('button',{name:'Cancelar',exact:true}).click();
  await expect(page.getByRole('row').filter({has:page.locator('[data-status="cancelled"]')})).toHaveCount(1);
  // Cancel the other branch too, whether queued or already claimed.
  await page.getByRole('button',{name:'Cancelar',exact:true}).click();
  const result=await finished(page,id);
  for (const run of result.runs) {
    expect(run.status).toBe('cancelled'); expect(run.result?.quality_evaluated ?? false).toBe(false);
  }
  for (const branch of ['A','B']) {
    expect(result.overviews[branch]).toMatchObject({finished:1,cancelled:1,execution_errors:0,evaluated:0,timed_answers:0});
  }
  await expect(page.locator('.agent-card .result-breakdown').filter({hasText:'1 canceladas'})).toHaveCount(2);
  await expect(page.locator('.agent-card .result-breakdown').filter({hasText:'0 errores de ejecución'})).toHaveCount(2);
  await page.getByRole('button',{name:/Ver traza de case, rama/}).first().click();
  await expect(page.getByRole('heading',{name:'case',exact:true})).toBeFocused();
  await page.getByRole('button',{name:'Cerrar traza',exact:true}).click();
  await expect(page.getByRole('button',{name:/Ver traza de case, rama/}).first()).toBeFocused();
  const next=await compare(page,'Worker recuperado'); await finished(page,next); await idle(page);
});

for (const [input,status,name] of [['[block]','timeout','Timeout'],['[fail]','failed','Fallo controlado']]) {
  test(`${name}: sin calidad puntuada ni indicadores persistentes`, async ({page})=>{
    await register(page);
    const id=await compare(page,name,input,1);
    const result=await finished(page,id);
    for (const run of result.runs) {expect(run.status).toBe(status);expect(run.result.quality_evaluated).toBe(false);}
    for (const branch of ['A','B']) expect(result.overviews[branch]).toMatchObject({evaluated:0,execution_errors:1,pending:0});
    await expect(page.locator(`[data-status="${status}"]`)).toHaveCount(2); await idle(page);
  });
}

test('API inaccesible muestra error, permite reintento y limpia cargas', async ({page})=>{
  await page.route('**/api/**',route=>route.abort('connectionrefused'));
  await page.goto('/');
  await expect(page.getByRole('alert')).toContainText('conectar');
  await idle(page);
  await page.unroute('**/api/**');
  await page.getByRole('button',{name:'Reintentar conexión'}).click();
  await expect(page.getByRole('button',{name:'Entrar',exact:true})).toBeEnabled();
  await idle(page);
});

test('navegación y selección durante cargas descartan respuestas anteriores', async ({page})=>{
  await register(page);
  const first=await compare(page,'Anterior'); await finished(page,first);
  const second=await compare(page,'Actual'); await finished(page,second);
  let release!:()=>void;
  const gate=new Promise<void>(resolve=>{release=resolve;});
  let entered!:()=>void;
  const observed=new Promise<void>(resolve=>{entered=resolve;});
  let fulfilled!:()=>void;
  const drained=new Promise<void>(resolve=>{fulfilled=resolve;});
  await page.route(`**/api/experiments/${first}`,async route=>{
    const response=await route.fetch(); entered(); await gate; await route.fulfill({response}); fulfilled();
  });
  await page.locator('summary').filter({hasText:/^Historial/}).click();
  const history=page.getByRole('navigation',{name:'Historial de comparaciones'});
  await history.getByRole('button',{name:/Anterior/}).click(); await observed;
  await expect(page.getByRole('heading',{name:'Actual',exact:true})).toHaveCount(0);
  await page.getByRole('button',{name:'Modelos',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Tus modelos, de un vistazo.'})).toBeVisible();
  await page.locator('summary').filter({hasText:/^Historial/}).click();
  await history.getByRole('button',{name:/Actual/}).click();
  await expect(page.getByRole('heading',{name:'Actual',exact:true})).toBeVisible();
  const delivered=page.waitForResponse(response=>response.url().endsWith(`/api/experiments/${first}`));
  release(); await drained; await delivered; await page.unroute(`**/api/experiments/${first}`);
  await idle(page);
  await expect(page.getByRole('heading',{name:'Anterior',exact:true})).toHaveCount(0);
  await page.reload(); await page.getByRole('button',{name:'Resultados',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Actual',exact:true})).toBeVisible(); await idle(page);
});
