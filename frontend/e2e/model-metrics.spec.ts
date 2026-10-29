import {test,expect,register,compare,finished,download} from './helpers';
import path from 'node:path';

test('modelos: gráficos medidos, coste configurable, filtros y selección',async({page},info)=>{
  await register(page);
  const id=await compare(page,'Métricas visuales');
  await finished(page,id);
  await page.getByRole('button',{name:'Modelos',exact:true}).click();
  const dashboard=page.locator('arena-model-comparison');
  await expect(dashboard.getByRole('heading',{name:'Calidad, rendimiento y coste'})).toBeVisible();
  await expect(dashboard.locator('.metric-chart')).toHaveCount(8);
  await expect(dashboard.locator('[data-metric="quality"] .metric-row').first()).toContainText('100 %');
  await expect(dashboard.locator('[data-metric="tokens"] .metric-row').first()).toContainText('13 tok');
  await expect(dashboard.locator('[data-metric="cost"] .metric-row').first()).toContainText('Sin datos');
  const qualityBar=dashboard.locator('[data-metric="quality"] .metric-bar').first();
  const fill=await qualityBar.locator('.metric-fill').boundingBox();
  expect(fill!.height).toBeGreaterThan(fill!.width);
  await qualityBar.focus();
  await expect(dashboard.getByRole('tooltip')).toContainText('1/1 con referencia');
  await expect(dashboard.getByRole('tooltip')).toContainText('Ollama · local');
  await qualityBar.press('Escape');
  await expect(dashboard.getByRole('tooltip')).toHaveCount(0);
  if(info.project.name==='chromium') {
    await page.mouse.move(0,0); await qualityBar.hover();
    await expect(dashboard.getByRole('tooltip')).toContainText('Aciertos: 100 %');
    await dashboard.getByRole('tooltip').hover();
    await expect(dashboard.getByRole('tooltip')).toBeVisible();
    await page.mouse.move(0,0);
    await expect(dashboard.getByRole('tooltip')).toHaveCount(0);
  }
  const missing=dashboard.locator('[data-metric="cost"] .metric-bar').first();
  await missing.click();
  await expect(dashboard.getByRole('tooltip')).toContainText('Sin datos');
  await expect(missing.locator('.metric-fill')).toHaveCount(0);
  await missing.press('Escape');
  await dashboard.locator('.cost-settings > summary').press('Enter');
  await dashboard.getByLabel('Base del coste').selectOption('tokens');
  await dashboard.getByLabel('Entrada (€/millón de tokens)').fill('2');
  await dashboard.getByLabel('Salida (€/millón de tokens)').fill('4');
  await expect(dashboard.locator('[data-metric="cost"] .metric-row').first()).toContainText('0.00003 €');
  await dashboard.getByLabel('Entrada (€/millón de tokens)').fill('0');
  await dashboard.getByLabel('Salida (€/millón de tokens)').fill('0');
  await expect(dashboard.locator('[data-metric="cost"] .metric-row').first()).toContainText('0.00 €');
  await dashboard.getByLabel('Entrada (€/millón de tokens)').fill('');
  await expect(dashboard.locator('[data-metric="cost"] .metric-row').first()).toContainText('Sin datos');
  await dashboard.getByLabel('Mostrar en los gráficos').selectOption({label:'Fichas seleccionadas'});
  await expect(dashboard).toContainText('Selecciona fichas en la biblioteca');
  await page.locator('.library-card input[type="checkbox"]').first().check();
  await expect(dashboard.locator('[data-metric="quality"] .metric-row')).toHaveCount(1);
  await dashboard.getByLabel('Mostrar en los gráficos').selectOption({label:'Resultados del filtro'});
  await page.locator('.model-library').getByLabel('Ejecución',{exact:true}).selectOption('simulated');
  await expect(dashboard).toContainText('No hay resultados para estos filtros');
  await page.locator('.model-library').getByLabel('Ejecución',{exact:true}).selectOption('ollama');
  await expect(dashboard.locator('.metric-chart')).toHaveCount(8);
  await page.emulateMedia({colorScheme:'dark'});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await dashboard.screenshot({path:path.resolve('..','runtime','model-metrics-evidence',`models-${info.project.name}.png`)});
});

test('colores por proveedor estables y etiquetas visibles con varios modelos',async({page})=>{
  await register(page);
  const id=await compare(page,'Proveedores de prueba'); await finished(page,id);
  await page.route('**/api/model-results',async route=>{
    const response=await route.fetch(); const body=await response.json(); const source=body.entries[0];
    await route.fulfill({json:{entries:[
      {...source,id:'local',adapter:'ollama',model:'local-fixture',summary:{...source.summary,mean_answer_s:2}},
      {...source,id:'remote',adapter:'codex',model:'openai-fixture',summary:{...source.summary,correct:0,incorrect:1,mean_answer_s:4}},
      {...source,id:'simulation',adapter:'simulated',model:'simulated-fixture'},
    ]}});
  });
  await page.getByRole('button',{name:'Modelos',exact:true}).click();
  await page.locator('.model-library').getByLabel('Ejecución',{exact:true}).selectOption('all');
  const dashboard=page.locator('arena-model-comparison'),quality=dashboard.locator('[data-metric="quality"]');
  await expect(dashboard.locator('.provider-legend span')).toHaveCount(3);
  const colors=await quality.locator('.metric-row').evaluateAll(rows=>rows.map(row=>getComputedStyle(row).getPropertyValue('--provider-color').trim()));
  expect(new Set(colors).size).toBe(3);
  await expect(quality.locator('[data-provider="simulated"] .metric-value')).toHaveText('Sin datos');
  await quality.locator('[data-provider="openai"] .metric-bar').click();
  await expect(quality.getByRole('tooltip')).toContainText('OpenAI');
  await expect(quality.getByRole('tooltip')).toContainText('openai-fixture');
  await quality.locator('[data-provider="openai"] .metric-bar').press('Escape');
  await page.emulateMedia({colorScheme:'dark'});
  const darkColors=await quality.locator('.metric-row').evaluateAll(rows=>rows.map(row=>getComputedStyle(row).getPropertyValue('--provider-color').trim()));
  expect(new Set(darkColors).size).toBe(3);
  await dashboard.getByLabel('Ordenar modelos por').selectOption('latency');
  await expect(quality.locator('.metric-model').first()).toContainText('local-fixture');
  await expect(quality.locator('.metric-model').last()).toContainText('simulated-fixture');
  await dashboard.getByRole('button',{name:'Tabla',exact:true}).click();
  await expect(dashboard.getByRole('button',{name:'Tabla',exact:true})).toHaveAttribute('aria-pressed','true');
  await expect(dashboard.locator('.comparison-table tbody tr')).toHaveCount(3);
  await expect(dashboard.locator('.comparison-table tbody tr').first()).toContainText('2 s');
  await dashboard.locator('.metric-settings > summary').click();
  for(const title of ['Cobertura de evaluación','Errores de ejecución','Tiempo de respuesta · P95','Velocidad de generación','Tokens por ejecución','Coste estimado por ejecución']) {
    await dashboard.getByRole('checkbox',{name:title,exact:true}).uncheck();
  }
  await expect(dashboard.locator('.comparison-table thead th')).toHaveCount(3);
  const exported=await download(page,dashboard.getByRole('button',{name:'Descargar comparativa CSV'}));
  expect(exported).toContain('Aciertos (%)'); expect(exported).toContain('Tiempo medio de respuesta (s)');
  expect(exported).not.toContain('Tiempo de respuesta · P95'); expect(exported).toContain('Sin datos');
  expect(exported.indexOf('"local-fixture"')).toBeLessThan(exported.indexOf('"openai-fixture"'));
  await dashboard.getByRole('checkbox',{name:'Tiempo medio de respuesta',exact:true}).uncheck();
  await expect(dashboard.getByRole('checkbox',{name:'Aciertos',exact:true})).toBeDisabled();
  await dashboard.getByRole('button',{name:'Gráficos',exact:true}).click();
  await expect(dashboard.locator('.metric-chart')).toHaveCount(1);
  await dashboard.getByRole('button',{name:'Tabla',exact:true}).click();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await dashboard.locator('.comparison-table tbody tr').first().getByRole('button',{name:/Abrir evidencia/}).click();
  await expect(page.getByRole('heading',{name:'Proveedores de prueba',exact:true})).toBeVisible();
});
