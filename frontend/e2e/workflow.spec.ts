import { test, expect, register, compare, finished, idle, download, csvRows } from './helpers';

test('registro, teclado, modal, sesión y recarga', async ({page}) => {
  const username = await register(page);
  const trigger = page.getByRole('button',{name:'Ayuda para configurar la prueba'});
  await trigger.focus(); await page.keyboard.press('Enter');
  const dialog = page.getByRole('dialog',{name:'Una comparación, dos variantes'});
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('heading',{name:'Una comparación, dos variantes'})).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(dialog.getByRole('button',{name:'Cerrar',exact:true})).toBeFocused();
  await page.keyboard.press('Shift+Tab');
  await expect(dialog.getByRole('button',{name:'Cerrar',exact:true})).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(dialog).not.toBeVisible(); await expect(trigger).toBeFocused();
  await page.getByRole('button',{name:'Perfil de Prueba E2E'}).click();
  await page.getByRole('button',{name:'Cerrar sesión',exact:true}).click();
  await page.getByRole('button',{name:'Ya tengo cuenta. Iniciar sesión'}).click();
  await expect(page.getByRole('heading',{name:'Qué bueno verte'})).toBeFocused();
  await page.getByLabel('Usuario',{exact:true}).fill(username);
  await page.getByLabel('Contraseña',{exact:true}).fill('Fixture-password-42');
  await expect(page.getByLabel('Usuario',{exact:true})).toHaveValue(username);
  await page.getByLabel('Contraseña',{exact:true}).press('Enter');
  await expect(page.getByRole('heading',{name:'Perfil',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Comparar',exact:true}).click();
  await page.reload();
  await expect(page.getByRole('heading',{name:'Una nueva comparación'})).toBeVisible();
  await idle(page);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
});

test('dataset, comparación, métricas, biblioteca, campaña e informes coherentes', async ({page}) => {
  await register(page);
  const id = await compare(page,'Comparación de fixture');
  const result = await finished(page,id);
  expect(result.runs.map((run:any)=>run.status)).toEqual(['succeeded','succeeded']);
  for (const branch of ['A','B']) {
    expect(result.overviews[branch]).toMatchObject({total:1,correct:1,evaluated:1,execution_errors:0,pending:0});
  }
  await expect(page.locator('.agent-card')).toHaveCount(2);
  for (const card of await page.locator('.agent-card').all()) await expect(card).toContainText('1 respuestas evaluadas');
  const rows = csvRows(await download(page,page.getByRole('link',{name:'↓ CSV',exact:true})));
  expect(rows).toHaveLength(2);
  for (const row of rows) {
    const run = result.runs.find((r:any)=>r.id===row.id);
    expect(row.status).toBe(run.status); expect(row.quality_evaluated).toBe('True');
    expect(Number(row.input_tokens)).toBe(run.result.input_tokens);
    expect(Number(row.agent_s)).toBe(run.result.agent_s);
    expect(JSON.parse(row.agent_config).seed).toBe(17);
    expect(JSON.parse(row.conditions)).toEqual(result.snapshot.conditions);
    expect(row.data_sha256).toBe(result.snapshot.data_sha256);
  }
  const markdown = await download(page,page.getByRole('link',{name:'↓ Informe',exact:true}));
  expect(markdown).toContain('Aciertos: 1/1 casos con referencia');
  expect(markdown).toContain('"seed": 17');
  expect(markdown).toContain(result.snapshot.data_sha256);
  await page.getByText('Evaluación y condiciones de esta prueba',{exact:true}).click();
  const report = JSON.parse(await download(page,page.getByRole('link',{name:'↓ Descargar informe reproducible'})));
  expect(report.snapshot.conditions).toEqual(result.snapshot.conditions);
  expect(report.overviews).toEqual(result.overviews);
  expect(report.runs).toEqual(result.runs);
  await page.getByRole('button',{name:'Modelos',exact:true}).click();
  await expect(page.getByRole('heading',{name:'fixture:latest',exact:true})).toBeVisible();
  await expect(page.locator('.library-card')).toContainText('1 respuestas evaluadas');
  await page.getByRole('checkbox',{name:/Seleccionar fixture:latest/}).check();
  await expect(page.getByRole('status').filter({hasText:'1/2 seleccionados'})).toBeVisible();
  const library=page.locator('.model-library');
  await library.getByRole('combobox',{name:/^Ejecución/}).selectOption('simulated');
  await expect(page.locator('.library-card')).toHaveCount(0);
  await expect(page.getByRole('status').filter({hasText:'1/2 seleccionados'})).toBeVisible();
  await expect(page.getByRole('status').filter({hasText:'1 seleccionados fuera del filtro'})).toBeVisible();
  await library.getByRole('combobox',{name:/^Ejecución/}).selectOption('ollama');
  await page.getByRole('button',{name:'Ver respuestas y referencia'}).click();
  await expect(page.getByRole('heading',{name:'Comparación de fixture',exact:true})).toBeVisible();
  await page.getByLabel('Nombre de campaña').fill('Campaña de fixture');
  await page.getByRole('button',{name:'Crear campaña',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Campaña de fixture',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Repetir diseño',exact:true}).click();
  await expect(page.getByRole('button',{name:'Repetir diseño',exact:true})).toBeEnabled();
  await expect(page.getByRole('region',{name:'Evolución de la campaña, tabla desplazable'}).getByRole('row')).toHaveCount(5);
  await page.getByLabel('Intento',{exact:true}).selectOption(id);
  await page.getByLabel('Condiciones observadas').fill('Carga controlada E2E');
  await page.getByLabel('Tipo de anotación').selectOption('observation');
  await page.getByRole('button',{name:'Guardar anotación',exact:true}).click();
  await expect(page.getByRole('status').filter({hasText:'Anotación'})).toBeVisible();
  const campaign = JSON.parse(await download(page,page.getByRole('link',{name:'↓ JSON reproducible'})));
  expect(campaign.attempts).toHaveLength(2);
  for (const attempt of campaign.attempts) {
    expect(attempt.complete).toBe(true);
    for (const branch of ['A','B']) expect(attempt.overviews[branch].correct).toBe(1);
  }
  const campaignCSV=csvRows(await download(page,page.getByRole('link',{name:'↓ CSV de evolución'})));
  expect(campaignCSV).toHaveLength(4);
  for (const row of campaignCSV) {
    const attempt=campaign.attempts.find((a:any)=>a.experiment_id===row.experiment_id);
    expect(row.design_sha256).toBe(campaign.design_sha256);
    expect(JSON.parse(row.annotations)).toEqual(attempt.annotations);
    expect(Number(row.correct)).toBe(attempt.overviews[row.branch].correct);
    expect(Number(row.evaluated)).toBe(attempt.overviews[row.branch].evaluated);
    expect(Number(row.mean_answer_s)).toBe(attempt.overviews[row.branch].mean_answer_s);
  }
  const campaignMD=await download(page,page.getByRole('link',{name:'↓ Informe',exact:true}));
  expect(campaignMD).toContain('Campaña de fixture'); expect(campaignMD).toContain('Carga controlada E2E');
  await page.reload();
  await page.getByRole('button',{name:'Campañas',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Campaña de fixture',exact:true})).toBeVisible();
  await idle(page);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
});
