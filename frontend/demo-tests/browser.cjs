// Exercise the production demo with a plain file server. No API/proxy/worker.
const { chromium, expect } = require('@playwright/test');
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../dist/sites/browser');
const output = path.resolve(__dirname, '../dist/demo-review');
fs.mkdirSync(output, {recursive:true});
const mime = {'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.ttf':'font/ttf','.csv':'text/csv','.md':'text/plain'};
const server = http.createServer((req,res) => {
  const relative = decodeURIComponent(new URL(req.url,'http://preview').pathname).replace(/^\/preview\//,'');
  const file = path.resolve(root, relative || 'index.html');
  if (!file.startsWith(root + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) {res.writeHead(404);res.end();return;}
  res.writeHead(200, {'Content-Type':mime[path.extname(file)] || 'application/octet-stream'}); fs.createReadStream(file).pipe(res);
});
(async()=>{
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const base = `http://127.0.0.1:${server.address().port}/preview/`;
  const browser = await chromium.launch(process.env.ARENA_DEMO_BROWSER ? {executablePath:process.env.ARENA_DEMO_BROWSER} : {});
  try {
    for (const [name,viewport] of [['desktop',{width:1440,height:1000}],['mobile',{width:390,height:844}]]) {
      const context = await browser.newContext({viewport,acceptDownloads:true});
      const page = await context.newPage(), bad = [], errors = [];
      page.on('pageerror', e=>errors.push(e.message));
      page.on('request', req=> { const u = new URL(req.url()); if (u.origin !== new URL(base).origin || !u.pathname.startsWith('/preview/') || u.pathname.includes('/api')) bad.push(req.url()); });
      await page.goto(base);
      await expect(page.locator('.demo-case')).toHaveCount(5);
      await expect(page.locator('.demo-case').nth(1)).toContainText('Paris frente a París');
      await page.screenshot({path:path.join(output,`${name}-tour.png`),fullPage:true,animations:'disabled'});
      await page.locator('.demo-case').nth(1).getByRole('button',{name:'Abrir evidencia'}).click();
      await expect(page.locator('#results-title')).toContainText('Auditoría real');
      await page.goto(base+'#/results?comparison=f9376f27-eeb5-416e-a3a7-eca838fdff56');
      await expect(page.locator('#results-title')).toContainText('text dev');
      await expect(page.getByRole('button',{name:'Lanzar comparación',exact:true})).toHaveCount(0);
      await expect(page.locator('.profile-button')).toHaveCount(0);
      await expect(page.locator('.campaign-create')).toHaveCount(0);
      await page.getByText('Tabla de ejecuciones y métricas técnicas',{exact:true}).click();
      await page.getByRole('combobox',{name:'Filtrar por rama'}).selectOption('A');
      await expect(page.locator('.runs-panel tbody tr')).toHaveCount(3);
      await page.getByRole('button',{name:/Ver traza de/}).first().click();
      await expect(page.locator('.trace-panel')).toContainText('No se exportaron eventos');
      await page.locator('.result-downloads a').first().click();
      // Check every selected export resolves and is a real payload, not SPA fallback.
      const catalog = JSON.parse(fs.readFileSync(path.join(root,'demo/catalog.json'),'utf8'));
      for (const experiment of catalog.experiments) for (const file of ['metrics.csv','report.md','reproducibility.json']) {
        const response = await context.request.get(base+`demo/exports/${experiment.id}/${file}`); assert.equal(response.status(),200); assert.ok((await response.body()).length>40);
      }
      await page.screenshot({path:path.join(output,`${name}-results.png`),fullPage:true,animations:'disabled'});
      await page.getByRole('button',{name:'Modelos',exact:true}).click();
      await expect(page.locator('.library-card')).toHaveCount(18);
      await page.locator('.library-card input').nth(0).check(); await page.locator('.library-card input').nth(1).check();
      await expect(page.locator('.library-comparison')).toBeVisible();
      await page.getByRole('button',{name:'Comparar',exact:true}).click();
      await page.getByRole('button',{name:'Resumen',exact:true}).click();
      await expect(page.locator('.demo-summary-card')).toHaveCount(8);
      await page.getByRole('combobox',{name:'Fase del resumen'}).selectOption('dev');
      await page.getByRole('combobox',{name:'Modelo del resumen'}).selectOption('qwen2.5:7b');
      await expect(page.locator('.demo-summary-card')).toHaveCount(4);
      const orders = page.locator('.demo-summary-card').filter({has:page.getByRole('heading',{name:'Pedidos',exact:true})});
      await expect(orders).toContainText('1/4');await expect(orders).toContainText('1/1 evaluadas correctas');await expect(orders).toContainText('3 errores');
      await page.screenshot({path:path.join(output,`${name}-summary.png`),fullPage:true,animations:'disabled'});
      await page.getByRole('button',{name:'Diagnósticos',exact:true}).click();
      await expect(page.locator('.demo-timeline > li')).toHaveCount(4);
      await page.getByRole('combobox',{name:'Modelo del diagnóstico',exact:true}).selectOption('qwen2.5:7b');
      await expect(page.getByRole('combobox',{name:'Registro del diagnóstico'}).locator('option')).toHaveCount(6);
      await page.screenshot({path:path.join(output,`${name}-diagnostics.png`),fullPage:true,animations:'disabled'});
      await page.getByRole('button',{name:'Reproducción',exact:true}).click();
      await expect(page.locator('.demo-section')).toContainText('simulador');
      await expect(page.getByRole('button',{name:'← Anterior'})).toBeDisabled();
      await page.getByRole('button',{name:'Siguiente →'}).click();
      await expect(page.locator('.demo-replay-event')).toContainText('Solicitud al simulador');
      const replay = JSON.parse(fs.readFileSync(path.join(root,'demo/replay.json'),'utf8'));
      for(let i=1;i<replay.events.length-1;i++) await page.getByRole('button',{name:'Siguiente →'}).click();
      await expect(page.getByRole('button',{name:'Siguiente →'})).toBeDisabled();
      await expect(page.locator('.demo-replay-event')).toContainText('Resultado final');
      await expect(page.locator('.demo-replay-event')).toContainText('3500');
      await page.getByRole('button',{name:'Volver al inicio',exact:true}).click();
      await expect(page.getByRole('button',{name:'← Anterior'})).toBeDisabled();
      await page.getByRole('button',{name:'Datos',exact:true}).click();
      await expect(page.locator('.demo-fixture')).toHaveCount(7);
      await page.getByRole('combobox',{name:'Dataset de la demo'}).selectOption(catalog.experiments[7].id);
      await expect(page.locator('.demo-data-grid article')).toHaveCount(2);
      await page.getByRole('button',{name:'El proyecto',exact:true}).click();
      await expect(page.getByRole('list',{name:'Arquitectura local'})).toBeVisible();
      expect(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      await page.getByRole('button',{name:'Campañas',exact:true}).click();
      await expect(page.locator('main')).toContainText('No hay campañas');
      await page.getByRole('button',{name:'Contacto',exact:true}).click();
      await expect(page.locator('main')).not.toContainText('@ucm.es');
      await page.getByRole('button',{name:'Guía',exact:true}).click();
      await expect(page.getByRole('heading',{name:'Explora sin ejecutar.'})).toBeVisible();
      await expect(page.getByRole('button',{name:'Crear una comparación'})).toHaveCount(0);
      await page.screenshot({path:path.join(output,`${name}-guide.png`),fullPage:true,animations:'disabled'});
      await page.goto(base+'#/results?comparison=missing');
      await expect(page.locator('[role=alert]').first()).toContainText('No se ha podido cargar');
      await page.goto(base+'#/results?comparison='+catalog.experiments[9].id);
      await expect(page.locator('.experiment-meta')).toContainText('SIMULACIÓN');
      await page.reload(); await expect(page.locator('.experiment-meta')).toContainText('SIMULACIÓN');
      assert.deepEqual(bad,[],'No backend, localhost service, or external requests'); assert.deepEqual(errors,[]);
      await context.close(); console.log(`${name}: navigation, branch filter, comparison, diagnostics, downloads, missing data, reload and request isolation passed`);
    }
    const context = await browser.newContext();
    const page = await context.newPage();
    await page.route('**/demo/catalog.json',route=>route.fulfill({status:503,body:'Unavailable'}));
    await page.goto(base); await expect(page.getByRole('alert').first()).toContainText('No se pudieron cargar');
    await page.unroute('**/demo/catalog.json');
    await page.getByRole('button',{name:'Resultados',exact:true}).click();
    await page.getByRole('button',{name:/Actualizar/}).click();
    await expect(page.locator('#results-title')).toBeVisible();
    await context.close(); console.log('Load failure and retry passed');
    const recovery = await browser.newContext(); const retryPage = await recovery.newPage();
    await retryPage.route('**/demo/replay.json',route=>route.fulfill({status:503,body:'Unavailable'}));
    await retryPage.goto(base);await expect(retryPage.locator('arena-demo-overview [role=alert]')).toContainText('No se pudo cargar todo el recorrido');
    await retryPage.unroute('**/demo/replay.json');await retryPage.getByRole('button',{name:'Reintentar recorrido'}).click();
    await expect(retryPage.locator('.demo-case')).toHaveCount(5);await recovery.close();console.log('Showcase partial-load recovery passed');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;}).finally(()=>server.close());
