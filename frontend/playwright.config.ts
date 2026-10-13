import { defineConfig, devices } from '@playwright/test';
import path from 'node:path';
import fs from 'node:fs';

const api = process.env.ARENA_E2E_API_PORT;
const ui = process.env.ARENA_E2E_UI_PORT;
if (!api || !ui) throw new Error('Use npm run e2e to allocate isolated ports');
const root = path.resolve(__dirname, '..');
const venv = path.join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const python = process.env.ARENA_TEST_PYTHON || (fs.existsSync(venv) ? venv : 'python');
export default defineConfig({
  testDir:'./e2e', fullyParallel:false, workers:1, retries:0,
  timeout:45_000, expect:{timeout:10_000},
  reporter:[['list'],['html',{open:'never'}]],
  use:{baseURL:`http://127.0.0.1:${ui}`, trace:'retain-on-failure'},
  projects:[
    {name:'chromium', use:{...devices['Desktop Chrome']}},
    {name:'mobile', use:{...devices['Pixel 7'], defaultBrowserType:'chromium'}},
  ],
  webServer:[
    {command:`"${python}" frontend/e2e/server.py`, cwd:root, url:`http://127.0.0.1:${api}/auth/session`, reuseExistingServer:false, timeout:60_000},
    {command:`node node_modules/@angular/cli/bin/ng.js serve --host 127.0.0.1 --port ${ui} --proxy-config e2e/proxy.cjs`, url:`http://127.0.0.1:${ui}`, reuseExistingServer:false, timeout:120_000},
  ],
});
