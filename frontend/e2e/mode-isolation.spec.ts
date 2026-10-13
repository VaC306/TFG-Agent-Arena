import {test,expect,register} from './helpers';

test('backend mode never mounts demo content or requests its static evidence',async({page})=>{
  const demoRequests:string[]=[];
  page.on('request',request=>{if(new URL(request.url()).pathname.startsWith('/demo/')) demoRequests.push(request.url());});
  await register(page);
  await expect(page.locator('arena-demo-overview')).toHaveCount(0);
  await expect(page.locator('.demo-nav')).toHaveCount(0);
  await expect(page.getByRole('heading',{name:'Una nueva comparación'})).toBeVisible();
  if (await page.locator('.secondary-menu').isVisible()) await page.locator('.secondary-menu > summary').click();
  await page.getByRole('button',{name:'Guía',exact:true}).click();
  await expect(page.locator('arena-demo-guide')).toHaveCount(0);
  await expect(page.locator('arena-guide')).toBeVisible();
  await expect(page.getByRole('button',{name:'Crear una comparación'})).toBeVisible();
  await page.getByRole('button',{name:'Campañas',exact:true}).click();
  await expect(page.locator('arena-campaigns')).toBeVisible();
  expect(demoRequests).toEqual([]);
});
