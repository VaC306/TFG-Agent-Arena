const net = require('node:net');
const { spawn } = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');

async function port() {
  const server = net.createServer();
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  return server;
}
(async () => {
  // Reserve both ports together. Never attach to a developer's existing server.
  const api = await port(), ui = await port();
  const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'arena-e2e-'));
  const env = {...process.env, ARENA_E2E_DB_DIRECTORY:temporary, ARENA_E2E_API_PORT:String(api.address().port), ARENA_E2E_UI_PORT:String(ui.address().port)};
  await Promise.all([api,ui].map(server => new Promise(resolve => server.close(resolve))));
  const cli = path.join(path.dirname(require.resolve('@playwright/test/package.json')), 'cli.js');
  const child = spawn(process.execPath, [cli, 'test', ...process.argv.slice(2)], {stdio:'inherit', env});
  child.on('exit', code => {
    process.exitCode = code ?? 1;
    // Playwright force-stops webServer on Windows. The parent owns cleanup.
    for (const suffix of ['', '-wal', '-shm', '-journal']) {
      const file=path.join(temporary,`arena.sqlite${suffix}`);
      try { fs.unlinkSync(file); } catch (error) { if (error.code!=='ENOENT') throw error; }
    }
    fs.rmdirSync(temporary);
  });
})().catch(error => { console.error(error); process.exitCode = 1; });
