const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

test('static provider covers every API method and rejects all writes without a request',async()=>{
  const local = ts.createSourceFile('arena.service.ts',fs.readFileSync(path.join(__dirname,'../src/app/arena.service.ts'),'utf8'),ts.ScriptTarget.Latest,true);
  const declaration = local.statements.find(s=>ts.isClassDeclaration(s) && s.name.text==='ArenaService');
  const methods = declaration.members.filter(s=>ts.isMethodDeclaration(s) && !s.modifiers?.some(m=>m.kind===ts.SyntaxKind.PrivateKeyword)).map(s=>s.name.text);
  class ArenaService {}
  let requests = 0;
  const module = {exports:{}};
  const catalog = {experiments:[],entries:[],campaigns:[],details:{}};
  vm.runInNewContext(ts.transpileModule(fs.readFileSync(path.join(__dirname,'../src/app/demo-arena.service.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,experimentalDecorators:true}}).outputText,
    {module,exports:module.exports, require:name=>name==='@angular/core'?{Injectable:()=>c=>c}:{ArenaService},URL,document:{baseURI:'https://demo.example/preview/'},fetch:async url=>{requests++;assert.equal(url.href,'https://demo.example/preview/demo/catalog.json');return {ok:true,json:async()=>catalog};}});
  const service = new module.exports.DemoArenaService();
  for(const method of methods) assert.ok(Object.hasOwn(module.exports.DemoArenaService.prototype,method),`API method ${method} needs a static implementation`);
  for(const method of ['annotateAttempt','createCampaign','repeatCampaign','clearHistory','validateDataset','compare','create','cancel']) await assert.rejects(service[method](),/requiere la aplicaci/);
  assert.equal(requests,0);
  await service.experiments(); await service.modelResults(); await service.campaigns();
  assert.equal(requests,1,'Read requests share one immutable catalog');
  await assert.rejects(service.detail('absent'),/no incluida/);
});
