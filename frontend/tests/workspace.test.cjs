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
  const core = {Component:() => target => target, Output:() => () => {}, EventEmitter:class {emit(){}}, signal, input:signal, computed:fn => fn, output:() => ({emit(){}}), DestroyRef,
    inject:token => token === ArenaService ? api : token === AuthService ? {user:signal({id:'test'})} : {onDestroy:fn=>destroy.push(fn)}};
  const module = {exports:{}};
  const source = fs.readFileSync(path.resolve(__dirname,'../src/app/',filename),'utf8');
  vm.runInNewContext(ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,experimentalDecorators:true}}).outputText,
    {module,exports:module.exports, require:name => name === '@angular/core' ? core : name === './arena.service' ? {ArenaService,defaultSettings:()=>({}),terminal:r=>!['queued','running'].includes(r.status)} : name === './auth.service' ? {AuthService,accountError:error=>error.message} : name === './validation' ? {modelIdentity:m=>m,textError:()=>''} : {},
      document:{title:'',getElementById:()=>null,activeElement:null}, HTMLElement:class {},crypto:require('node:crypto'), requestAnimationFrame:fn=>fn(),setInterval:()=>1,clearInterval(){},setTimeout:()=>1,clearTimeout(){}});
  return {exports:module.exports,destroy:()=>destroy.forEach(fn=>fn())};
}
async function workspace(api={}) {
  const f = fixture('app.component.ts',{presets:async()=>[],experiments:async()=>[],...api});
  const app = new f.exports.AppComponent();
  await new Promise(resolve=>setImmediate(resolve));
  return {app,...f};
}
const responseDetail = name => ({snapshot:{config:{name}},runs:[],name});
test('latency planning enables warmup and balances repetitions without reducing the sample',()=>{
  const f=fixture('composer.component.ts',{prompts:async()=>[]}),component=new f.exports.ComposerComponent();
  component.settings={warmup:'none',order_policy:'random'};component.repetitions=3;
  component.setLatencyStudy(true);
  assert.equal(component.settings.warmup,'per_run');assert.equal(component.settings.order_policy,'balanced');assert.equal(component.repetitions,4);
  component.setLatencyStudy(false);assert.equal(component.repetitions,4);
});
test('completed planned campaign cannot silently extend the sample',async()=>{
  let calls=0;const f=fixture('campaigns.component.ts',{repeatCampaign:async()=>calls++});
  const component=new f.exports.CampaignsComponent();component.selectedId.set('c');
  component.detail.set({id:'c',design:{config:{latency_study:true,planned_attempts:2}},attempts:[{},{}]});
  assert.equal(component.planFinished(),true);await component.repeat();assert.equal(calls,0);assert.equal(component.busy(),false);
  component.detail.set({id:'c',design:{config:{latency_study:false}},attempts:[{},{}]});assert.equal(component.planFinished(),false);
});
test('worker checks coalesce, discard stale status on failure and recover',async()=>{
  const request=deferred();let calls=0;
  const api={workerStatus:()=>{calls++;return request.promise;}};
  const f=fixture('campaigns.component.ts',api),component=new f.exports.CampaignsComponent();
  component.worker.set({state:'active'});
  const checking=component.checkWorker();await component.checkWorker();assert.equal(calls,1);
  request.reject(new Error('Offline'));await checking;
  assert.equal(component.worker(),null);assert.ok(component.workerError());
  api.workerStatus=async()=>({state:'no_recent_signal'});
  await component.checkWorker();assert.equal(component.worker().state,'no_recent_signal');assert.equal(component.workerError(),'');
});
test('uncertain annotation refresh retries with same key and preserves draft',async()=>{
  const keys=[];let fail=true;
  const f=fixture('campaigns.component.ts',{annotateAttempt:async(_c,_e,body)=>keys.push(body.request_id),campaign:async()=>{
    if(fail)throw new Error('Offline');return {id:'c',attempts:[{experiment_id:'e'}]};
  }}),component=new f.exports.CampaignsComponent();
  component.detail.set({id:'c',attempts:[{experiment_id:'e'}]});component.noteAttempt='e';component.noteText='Different load';
  await component.saveNote();assert.equal(component.savingNote(),false);assert.ok(component.noteError());assert.equal(component.noteText,'Different load');
  fail=false;await component.saveNote();assert.equal(keys[0],keys[1]);assert.equal(component.noteText,'');assert.ok(component.noteNotice());
});
test('late annotation completion cannot replace the newly selected campaign',async()=>{
  const request=deferred();
  const f=fixture('campaigns.component.ts',{annotateAttempt:()=>request.promise,campaign:async id=>({id,attempts:[]})});
  const component=new f.exports.CampaignsComponent();component.detail.set({id:'old',attempts:[{experiment_id:'e'}]});
  component.noteAttempt='e';component.noteText='Old conditions';const saving=component.saveNote();
  await component.select('new');component.noteText='New draft';request.resolve({id:'note'});await saving;
  assert.equal(component.detail().id,'new');assert.equal(component.noteText,'New draft');assert.equal(component.noteNotice(),'');
});
test('library rejects declared external deviations despite matching model cohorts',()=>{
  const f=fixture('model-library.component.ts',{modelResults:async()=>({entries:[]})}),component=new f.exports.ModelLibraryComponent();
  const base={adapter:'ollama',verified:true,cohort_key:'same',kind:'text',model:'model'};
  component.entries.set([{...base,id:'a',digest:'aaa',external_deviation:true},{...base,id:'b',digest:'bbb'}]);
  component.selected.set(['a','b']);assert.equal(component.compatible(),false);
});
test('task filters distinguish correctness variation, coverage, errors and changes',()=>{
  const f=fixture('campaigns.component.ts',{}), component=new f.exports.CampaignsComponent();
  const branch=(extra={})=>({reference_evaluable:true,quality_stability:'always_correct',coverage:1,between_attempt_changes:0,summary:{execution_errors:0},...extra});
  const task=(id,extra)=>({task_id:id,branches:{A:branch(extra),B:branch()}});
  component.detail.set({analysis:{tasks:[task('stable',{}),task('variable',{quality_stability:'variable'}),task('errors',{summary:{execution_errors:1},coverage:.5}),task('changed',{between_attempt_changes:1}),task('unreferenced',{reference_evaluable:false,coverage:null})]}});
  assert.equal(component.visibleTasks().length,5);
  for(const [filter,expected] of [['variable','variable'],['errors','errors'],['coverage','errors'],['changed','changed']]) {
    component.taskFilter.set(filter); assert.deepEqual(Array.from(component.visibleTasks(),t=>t.task_id),[expected]);
  }
  component.detail.set(null); assert.equal(component.visibleTasks().length,0);
});
test('changing campaign resets task filter and cannot retain previous analysis',async()=>{
  const response=deferred(), f=fixture('campaigns.component.ts',{campaign:()=>response.promise});
  const component=new f.exports.CampaignsComponent();
  component.detail.set({analysis:{tasks:[{}]}});component.taskFilter.set('errors');
  const selecting=component.select('new');
  assert.equal(component.taskFilter(),'all');assert.equal(component.visibleTasks().length,0);
  response.resolve({id:'new',attempts:[],analysis:{tasks:[]}}); await selecting;
  assert.equal(component.detail().id,'new');assert.equal(component.loading(),false);
});
test('new selection wins over late detail, failed requests release loading',async()=>{
  const old=deferred(),fresh=deferred();
  const {app}=await workspace({detail:id=>id==='old'?old.promise:fresh.promise});
  const first=app.select('old'), second=app.select('new');
  old.resolve(responseDetail('old')); await first;
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
  refresh.resolve(responseDetail('old')); await updating;
  assert.equal(app.detail(),null); assert.equal(app.loading(),true);
  fresh.resolve(responseDetail('new')); await selecting;
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
  detail.resolve(responseDetail('chosen')); await selecting; assert.equal(app.loading(),false);
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
  response.resolve(responseDetail('chosen')); await loading;
  assert.equal(app.view(),'models'); assert.equal(app.selectedId(),'chosen');assert.equal(app.loading(),false);
});
test('campaign selection discards late responses and terminates failed loading',async()=>{
  const old=deferred(),fresh=deferred();
  const f=fixture('campaigns.component.ts',{campaign:id=>id==='old'?old.promise:fresh.promise});
  const campaigns=new f.exports.CampaignsComponent();
  const first=campaigns.select('old'),second=campaigns.select('new');
  old.resolve({id:'old'}); await first;
  assert.equal(campaigns.detail(),null); assert.equal(campaigns.loading(),true);
  fresh.reject(new Error('Offline'));await second;
  assert.equal(campaigns.detail(),null);assert.equal(campaigns.loading(),false);assert.ok(campaigns.error());
});
test('campaign retry keeps its idempotency key after an uncertain response',async()=>{
  const keys=[];let calls=0;
  const f=fixture('campaigns.component.ts',{repeatCampaign:async(id,key)=>{keys.push(key);if(++calls===1)throw new Error('Lost response');return {id:'attempt'};},campaigns:async()=>[],campaign:async()=>({id:'campaign',pending:0,attempts:[]})});
  const campaigns=new f.exports.CampaignsComponent();campaigns.selectedId.set('campaign');campaigns.detail.set({id:'campaign',pending:0});
  await campaigns.repeat();assert.equal(campaigns.busy(),false);assert.ok(campaigns.error());
  await campaigns.refresh();await campaigns.repeat();
  assert.equal(keys.length,2);assert.equal(keys[0],keys[1]);assert.equal(campaigns.busy(),false);
});
test('campaign refresh recognises a saved attempt after a lost response',async()=>{
  let key;let calls=0;
  const f=fixture('campaigns.component.ts',{repeatCampaign:async(id,request)=>{key=request;calls++;throw new Error('Lost response');},campaigns:async()=>[],campaign:async()=>({id:'campaign',pending:2,attempts:[{request_id:key}]})});
  const campaigns=new f.exports.CampaignsComponent();campaigns.selectedId.set('campaign');campaigns.detail.set({id:'campaign',pending:0});
  await campaigns.repeat();await campaigns.refresh();await campaigns.repeat();
  assert.equal(calls,1);assert.match(campaigns.notice(),/ya estaba guardada/);assert.equal(campaigns.error(),'');
});
test('campaign pending attempts cannot be repeated and destroy discards late detail',async()=>{
  let calls=0;const late=deferred();
  const f=fixture('campaigns.component.ts',{repeatCampaign:async()=>{calls++;},campaign:()=>late.promise});
  const campaigns=new f.exports.CampaignsComponent();campaigns.selectedId.set('campaign');campaigns.detail.set({pending:2});
  await campaigns.repeat();assert.equal(calls,0);
  const selecting=campaigns.select('other');f.destroy();late.resolve({id:'other'});await selecting;
  assert.equal(campaigns.detail(),null);
});
test('campaign creation finishing after navigation does not override the new view',async()=>{
  const response=deferred();const {app}=await workspace({createCampaign:()=>response.promise});
  app.selectedId.set('source');app.detail.set(responseDetail('source'));app.campaignName.set('Valid campaign');app.navigate('results');
  const creating=app.createCampaign();app.navigate('profile');response.resolve({id:'campaign'});await creating;
  assert.equal(app.view(),'profile');assert.equal(app.campaignBusy(),false);
});
