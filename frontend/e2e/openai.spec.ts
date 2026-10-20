import {test,expect,register,detail,finished} from './helpers';
import path from 'node:path';

test('ChatGPT controlado: vinculación explícita, teclado, respuestas, trazas y parámetros honestos',async({page},info)=>{
  await register(page);
  await page.getByLabel('Ejecución',{exact:true}).selectOption('codex');
  await expect(page.getByRole('button',{name:'Ejecutar comparación',exact:true})).toBeDisabled();
  const connect=page.getByRole('button',{name:'Usar sesión de ChatGPT de este equipo',exact:true});
  await expect(connect).toBeEnabled(); await connect.focus(); await connect.press('Enter');
  await expect(page.getByRole('button',{name:'Desvincular de Arena'})).toBeVisible();
  await expect(page.getByLabel('Modelo compartido A/B')).toHaveValue('fixture-gpt');
  await expect(page.getByRole('option',{name:'fixture-gpt',exact:true})).toHaveCount(1);
  await page.getByLabel('Entrada compartida',{exact:true}).fill('Saluda [no-usage]');
  await expect(page.locator('.upload-zone')).toHaveCount(0);
  await page.locator('.protocol-settings > summary').click();
  await page.locator('.advanced-settings > summary').click();
  await expect(page.getByLabel('Semilla (0–2147483647)',{exact:true})).toHaveCount(0);
  await expect(page.getByLabel('Tiempo límite (1–3600 segundos)',{exact:true})).toBeVisible();
  for (const theme of ['light','dark']) {
    await page.getByLabel('Tema',{exact:true}).selectOption(theme);
    await page.screenshot({path:path.resolve('..','runtime','openai-evidence',`controlled-prepared-${theme}-${info.project.name}.png`),fullPage:true});
  }
  const sent=page.waitForResponse(r=>r.url().endsWith('/api/comparisons')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Ejecutar comparación',exact:true}).click();
  const response=await sent;expect(response.status()).toBe(201);
  const id=(await response.json()).id;const result=await finished(page,id);
  expect(result.runs.every((r:any)=>r.status==='completed'&&r.result.input_tokens===null&&r.result.server_tps===null)).toBe(true);
  await expect(page.locator('.case-answer')).toHaveCount(2);
  await expect(page.locator('.case-answer').first()).toContainText('hola');
  await expect(page.locator('.experiment-meta')).toContainText('ChatGPT');
  const trace=await page.request.get(`/api/runs/${result.runs[0].id}/events`);
  expect(trace.ok()).toBeTruthy();expect(await trace.text()).not.toContain('PRIVATE_REASONING');
  await page.screenshot({path:path.resolve('..','runtime','openai-evidence',`controlled-result-${info.project.name}.png`),fullPage:true});
  await page.getByRole('button',{name:'Perfil de Prueba E2E'}).click();
  await page.getByRole('button',{name:'Desvincular de Arena'}).click();
  await expect(page.getByRole('button',{name:'Usar sesión de ChatGPT de este equipo'})).toBeVisible();
  expect((await detail(page,id)).runs).toHaveLength(2);
});

test('ChatGPT controlado: cancelación sin evaluación',async({page})=>{
  await register(page);
  await page.getByLabel('Ejecución',{exact:true}).selectOption('codex');
  await page.getByRole('button',{name:'Usar sesión de ChatGPT de este equipo'}).click();
  await expect(page.getByLabel('Modelo compartido A/B')).toHaveValue('fixture-gpt');
  await page.getByLabel('Entrada compartida',{exact:true}).fill('[block]');
  const sent=page.waitForResponse(r=>r.url().endsWith('/api/comparisons')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Ejecutar comparación',exact:true}).click();
  const id=(await (await sent).json()).id;
  await expect.poll(async()=>(await detail(page,id)).runs.some((r:any)=>r.status==='running')).toBe(true);
  const current=await detail(page,id);
  for(const run of current.runs) {
    const response=await page.request.post(`/api/runs/${run.id}/cancel`,{headers:{'X-Arena-Request':'1'}});
    expect(response.ok()).toBeTruthy();
  }
  const result=await finished(page,id);
  expect(result.runs.every((r:any)=>r.status==='cancelled')).toBe(true);
  await page.locator('.case-branch').first().getByText('Referencia y métricas de A',{exact:true}).click();
  await expect(page.locator('.case-branch').first()).toContainText('Sin evaluación: ejecución cancelada.');
});
