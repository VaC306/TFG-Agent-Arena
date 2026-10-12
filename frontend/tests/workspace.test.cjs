// Exercise the actual component methods with deferred HTTP responses.
// Angular rendering and browser accessibility are checked separately in the UI.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
function deferred() {
  let resolve, reject;
  const promise = new Promise((a,b) => {resolve=a; reject=b;});
  return {promise,resolve,reject};
}
function fixture(filename, api) {
  const destroy = [];
  const signal = value => Object.assign(() => value, {set:next => {value=next;}, update:fn => {value=fn(value);}});
  class ArenaService {} class AuthService {} class DestroyRef {}
  const core = {Component:() => target => target, Output:() => () => {}, EventEmitter:class {emit(){}}, signal, computed:fn => fn, output:() => ({emit(){}}), DestroyRef,
    inject:token => token === ArenaService ? api : token === AuthService ? {user:signal({id:'test'})} : {onDestroy:fn=>destroy.push(fn)}};
  const module = {exports:{}};
  const source = fs.readFileSync(path.resolve(__dirname,'../src/app/',filename),'utf8');
  vm.runInNewContext(ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,experimentalDecorators:true}}).outputText,
    {module,exports:module.exports, require:name => name === '@angular/core' ? core : name === './arena.service' ? {ArenaService,defaultSettings:()=>({}),terminal:r=>!['queued','running'].includes(r.status)} : name === './auth.service' ? {AuthService} : name === './validation' ? {modelIdentity:m=>m} : {},
      document:{title:'',getElementById:()=>null,activeElement:null}, HTMLElement:class {}, requestAnimationFrame:fn=>fn(),setInterval:()=>1,clearInterval(){},setTimeout:()=>1,clearTimeout(){}});
  return {exports:module.exports,destroy:()=>destroy.forEach(fn=>fn())};
}
async function workspace(api={}) {
  const f = fixture('app.component.ts',{presets:async()=>[],experiments:async()=>[],...api});
  const app = new f.exports.AppComponent();
  await new Promise(resolve=>setImmediate(resolve));
  return {app,...f};
}
test('new selection wins over late detail, failed requests release loading',async()=>{
  const old=deferred(),fresh=deferred();
  const {app}=await workspace({detail:id=>id==='old'?old.promise:fresh.promise});
  const first=app.select('old'), second=app.select('new');
  old.resolve({runs:[],name:'old'}); await first;
  assert.equal(app.detail(),null); assert.equal(app.loading(),true);
  fresh.reject(new Error('Backend offline')); await second;
  assert.equal(app.selectedId(),'new'); assert.equal(app.detail(),null);
  assert.equal(app.loading(),false); assert.ok(app.error());
});
test('background refresh cannot replace a new selection; duplicate refresh coalesces',async()=>{
  const refresh=deferred(),fresh=deferred(); let calls=0;
  const {app}=await workspace({detail:id=>{calls++;return id==='old'?refresh.promise:fresh.promise;}});
  app.presets.set([{}]); app.selectedId.set('old');
  const updating=app.refresh(); await app.refresh();
  const selecting=app.select('new');
  refresh.resolve({runs:[],name:'old'}); await updating;
  assert.equal(app.detail(),null); assert.equal(app.loading(),true);
  fresh.resolve({runs:[],name:'new'}); await selecting;
  assert.equal(app.detail().name,'new'); assert.equal(calls,2);
});
test('closing a trace invalidates late events and clears its indicator',async()=>{
  const events=deferred(); const {app}=await workspace({events:()=>events.promise});
  const opening=app.showTrace({id:'run',status:'running'});
  app.closeTrace(); events.resolve([{seq:1}]); await opening;
  assert.equal(app.selectedRun(),null); assert.deepEqual(Array.from(app.events()),[]);
  assert.equal(app.traceLoading(),false);
});
test('initialization cannot override selection or end its loading early',async()=>{
  const initial=deferred(),detail=deferred();
  const f=fixture('app.component.ts',{presets:async()=>[],experiments:()=>initial.promise,detail:()=>detail.promise});
  const app=new f.exports.AppComponent();
  const selecting=app.select('chosen'); initial.resolve([{id:'old'}]);
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(app.selectedId(),'chosen'); assert.equal(app.loading(),true);
  detail.resolve({runs:[]}); await selecting; assert.equal(app.loading(),false);
});
test('model library coalesces requests, releases errors, and blocks stale comparison',async()=>{
  const request=deferred();let calls=0;
  const f=fixture('model-library.component.ts',{modelResults:()=>{calls++;return request.promise;}});
  const library=new f.exports.ModelLibraryComponent(); await library.refresh();
  assert.equal(calls,1); request.reject(new Error('Offline'));
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(library.loading(),false); assert.ok(library.error()); assert.equal(library.compatible(),false);
});
test('Ollama outage preserves model selections for recovery and ends loading',async()=>{
  const f=fixture('composer.component.ts',{prompts:async()=>[],models:async()=>({available:false,models:[]})});
  const composer=new f.exports.ComposerComponent();
  composer.adapter='ollama'; composer.mode='different_models';
  composer.modelA='qwen2.5:3b';composer.modelB='qwen2.5:7b';
  await composer.loadModels();
  assert.equal(composer.modelsBusy(),false); assert.equal(composer.validModels(),false);
  assert.equal(composer.modelA,'qwen2.5:3b');assert.equal(composer.modelB,'qwen2.5:7b');
});
test('navigation during detail loading keeps the new view and releases loading',async()=>{
  const response=deferred(); const {app}=await workspace({detail:()=>response.promise});
  const loading=app.select('chosen'); app.navigate('models');
  response.resolve({runs:[],name:'chosen'}); await loading;
  assert.equal(app.view(),'models'); assert.equal(app.selectedId(),'chosen');assert.equal(app.loading(),false);
});
