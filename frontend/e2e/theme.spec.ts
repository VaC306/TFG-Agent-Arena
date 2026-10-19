import {test,expect,register,compare,finished} from './helpers';
import path from 'node:path';
const {checkContrast}=require('../tests/browser-colors.cjs');

test('tema antes de Angular, sistema dinámico, teclado y persistencia por navegador',async({page},info)=>{
  await page.emulateMedia({colorScheme:'dark',reducedMotion:'reduce'});
  let release!:()=>void;
  let gate=new Promise<void>(resolve=>release=resolve);
  await page.route('**/main.js',async route=>{await gate;await route.continue();});
  await page.goto('/',{waitUntil:'commit'});
  try {
    await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
    await expect(page.locator('arena-root')).toBeEmpty();
  } finally {release();}
  const picker=page.getByRole('combobox',{name:'Tema',exact:true});
  await expect(picker).toHaveValue('system');
  // Reach the picker through the real tab order, then operate its native popup.
  for(let i=0;i<20 && !await picker.evaluate(e=>e===document.activeElement);i++) await page.keyboard.press('Tab');
  await expect(picker).toBeFocused();await page.keyboard.press('Enter');
  await page.screenshot({path:path.resolve('..','runtime','ux-review-evidence',`tema-selector-${info.project.name}.png`),scale:'css'});
  await page.keyboard.press('ArrowDown');await page.keyboard.press('Enter');
  await expect(picker).toHaveValue('light');await expect(picker).toBeFocused();
  expect(await picker.evaluate(e=>getComputedStyle(e).outlineStyle)).not.toBe('none');
  await expect(page.locator('html')).toHaveAttribute('data-theme','light');
  gate=new Promise<void>(resolve=>release=resolve);
  await page.goto('/',{waitUntil:'commit'});
  try {
    await expect(page.locator('html')).toHaveAttribute('data-theme','light');
    await expect(page.locator('arena-root')).toBeEmpty();
  } finally {release();}
  await expect(picker).toHaveValue('light');
  await page.emulateMedia({colorScheme:'light'});await page.emulateMedia({colorScheme:'dark'});
  await expect(page.locator('html')).toHaveAttribute('data-theme','light');
  await picker.selectOption('dark');await page.reload();await expect(picker).toHaveValue('dark');
  await picker.selectOption('system');await page.emulateMedia({colorScheme:'light'});
  await expect(page.locator('html')).toHaveAttribute('data-theme','light');
  await page.emulateMedia({colorScheme:'dark'});await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
  expect(await page.evaluate(()=>localStorage.getItem('arena.theme.v1'))).toBeNull();
});

test('pantallas oscuras, foco de traza/diálogo y navegación adaptable',async({page},info)=>{
  await page.emulateMedia({colorScheme:'dark'});await register(page);
  await page.emulateMedia({reducedMotion:'reduce'});
  const shot=async(name:string)=>{await checkContrast(page);const picker=page.getByRole('combobox',{name:'Tema',exact:true});const previous=await picker.inputValue();await picker.selectOption('light');await checkContrast(page);await picker.selectOption(previous);await page.screenshot({path:path.resolve('..','runtime','ux-review-evidence',`tema-${name}-${info.project.name}.png`),fullPage:true});};
  const fits=async()=>expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  for(const width of [390,768,887,1024,1440]) {await page.setViewportSize({width,height:844});await fits();}
  await page.setViewportSize(info.project.name==='mobile'?{width:390,height:844}:{width:1440,height:1000});
  await shot('formulario');
  const help=page.locator('arena-composer .info-trigger').first();
  await help.press('Enter');await expect(page.getByRole('dialog')).toBeVisible();await shot('dialogo');
  await page.keyboard.press('Tab');await expect(page.getByRole('dialog').getByRole('button',{name:'Cerrar'})).toBeFocused();
  await page.keyboard.press('Escape');await expect(help).toBeFocused();
  const id=await compare(page,'Tema oscuro ficticio');await finished(page,id);
  await page.getByRole('button',{name:/Ver traza de/}).first().press('Enter');
  await expect(page.locator('.trace-panel')).toBeVisible();await shot('traza');
  await page.keyboard.press('Escape');await expect(page.getByRole('button',{name:/Ver traza de/}).first()).toBeFocused();
  await page.getByText('Campaña y repetición del diseño',{exact:true}).press('Enter');
  await page.getByLabel('Nombre de campaña').fill('Campaña tema ficticia');await page.getByRole('button',{name:'Crear campaña',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Campaña tema ficticia',exact:true})).toBeVisible();await shot('campana');
  await page.getByRole('button',{name:'Modelos',exact:true}).click();await expect(page.locator('.library-card').first()).toBeVisible();await shot('biblioteca');
  await page.getByRole('button',{name:'Perfil de Prueba E2E'}).click();await shot('perfil');
  await page.locator('.history-menu > summary').press('Enter');await shot('historial');await page.keyboard.press('Escape');await expect(page.locator('.history-menu > summary')).toBeFocused();
  await fits();await page.getByRole('combobox',{name:'Tema',exact:true}).selectOption('light');await shot('claro');
});

test('estados oscuros de carga, vacío y error conservan texto y contraste',async({page},info)=>{
  await page.emulateMedia({colorScheme:'dark',reducedMotion:'reduce'});await register(page);
  await page.getByRole('button',{name:'Resultados',exact:true}).click();
  await expect(page.locator('.empty')).toBeVisible();await checkContrast(page);
  let release!:()=>void;const gate=new Promise<void>(resolve=>release=resolve);
  await page.route('**/api/model-results*',async route=>{await gate;await route.fulfill({status:503,json:{detail:'Fallo ficticio'}});});
  await page.getByRole('button',{name:'Modelos',exact:true}).click();
  try {await expect(page.locator('arena-model-library arena-loading')).toBeVisible();await checkContrast(page);}
  finally {release();}
  await expect(page.locator('arena-model-library [role=alert]')).toBeVisible();await checkContrast(page);
  await page.screenshot({path:path.resolve('..','runtime','ux-review-evidence',`tema-error-${info.project.name}.png`),fullPage:true});
});
