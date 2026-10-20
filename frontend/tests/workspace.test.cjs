// Exercise the actual component methods with deferred HTTP responses.
// Angular rendering and browser accessibility are checked separately in the UI.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const validationModule={exports:{}};
vm.runInNewContext(ts.transpileModule(fs.readFileSync(path.resolve(__dirname,'../src/app/validation.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,{module:validationModule,exports:validationModule.exports});
function deferred() {
  let resolve, reject;
  const promise = new Promise((a,b) => {resolve=a; reject=b;});
  return {promise,resolve,reject};
}
function fixture(filename, api, options={}) {
  const destroy = [];
  const signal = value => Object.assign(() => value, {set:next => {value=next;}, update:fn => {value=fn(value);}});
  class ArenaService {} class AuthService {} class DestroyRef {}
  const core = {Component:() => target => target, Input:() => () => {}, Output:() => () => {}, HostListener:() => () => {}, EventEmitter:class {emit(){}}, signal, input:signal, computed:fn => fn, output:() => ({emit(){}}), DestroyRef,
    inject:token => token === ArenaService ? api : token === AuthService ? auth : {onDestroy:fn=>destroy.push(fn),begin:()=>()=>{}}};
  const auth = {user:signal(options.user ?? {id:'test'}),savePreferences:async()=>{}};
  const storage = options.storage ?? {getItem:()=>null,setItem(){},removeItem(){}};
  const module = {exports:{}};
  const source = fs.readFileSync(path.resolve(__dirname,'../src/app/',filename),'utf8');
  vm.runInNewContext(ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,experimentalDecorators:true}}).outputText,
    {module,exports:module.exports, require:name => name === '@angular/core' ? core : name === './arena.service' ? {ArenaService,defaultSettings:()=>({}),terminal:r=>!['queued','running'].includes(r.status)} : name === './auth.service' ? {AuthService,accountError:error=>error.message} : name === './validation' ? options.realValidation ? validationModule.exports : {modelIdentity:m=>m,textError:()=>'',filenameError:()=>''} : {},
      window:{location:{hash:''},history:{pushState(){},replaceState(){}}}, URLSearchParams, queueMicrotask, TextDecoder, localStorage:storage, document:{querySelector:()=>null,title:'',getElementById:()=>null,activeElement:null}, HTMLElement:class {},crypto:require('node:crypto'), requestAnimationFrame:fn=>fn(),setInterval:()=>1,clearInterval(){},setTimeout:()=>1,clearTimeout(){}});
  return {exports:module.exports,auth,destroy:()=>destroy.forEach(fn=>fn())};
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


test('draft storage failure is visible and never claims a successful save',async()=>{
  const f=fixture('composer.component.ts',{prompts:async()=>[]},{storage:{getItem:()=>null,setItem(){throw new Error('quota');},removeItem(){}}});
  const composer=new f.exports.ComposerComponent();composer.inputA.text='Keep this input';composer.queueSave();
  await new Promise(resolve=>setImmediate(resolve));
  assert.match(composer.draftNotice(),/No se pudo guardar/);assert.equal(composer.inputA.text,'Keep this input');
});

test('account identity scopes draft writes and rejects a foreign owner',async()=>{
  let key,stored;
  const storage={getItem:()=>null,setItem:(k,value)=>{key=k;stored=value;},removeItem(){}};
  const f=fixture('composer.component.ts',{prompts:async()=>[]},{storage});
  const composer=new f.exports.ComposerComponent();composer.inputA.text='Private A';composer.queueSave();
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(key,'arena.composer.v1.test');assert.equal(JSON.parse(stored).inputs.inputA.text,'Private A');
  const foreign=fixture('composer.component.ts',{prompts:async()=>[]},{user:{id:'other'},storage:{...storage,getItem:()=>stored}});
  const other=new foreign.exports.ComposerComponent();assert.equal(other.pendingDraft(),null);assert.equal(other.inputA.text,'');
  f.auth.user.set({id:'other'});composer.inputA.text='Late A';composer.queueSave();
  await new Promise(resolve=>setImmediate(resolve));assert.equal(JSON.parse(stored).inputs.inputA.text,'Private A');
});

test('discard invalidates an in-flight normalized dataset without recreating its draft',async()=>{
  const response=deferred();let calls=0;
  const f=fixture('composer.component.ts',{prompts:async()=>[],validateDataset:()=>{calls++;return response.promise;}});
  const composer=new f.exports.ComposerComponent();
  const input={files:[{name:'private.csv',size:16,arrayBuffer:async()=>new TextEncoder().encode('id,input\na,hola').buffer}],value:'private.csv'};
  const importing=composer.importDataset({target:input});
  await new Promise(resolve=>setImmediate(resolve));assert.equal(calls,1);
  composer.discardDraft();response.resolve({cases:[{id:'a',input:'hola',expected_answer:null}],count:1,scored:0});await importing;
  assert.equal(composer.dataset(),null);assert.equal(composer.datasetBusy(),false);assert.match(composer.draftNotice(),/descartado/);
});

test('preparation review and submit use the same real validators, active inputs and references',async()=>{
  let posts=0;
  const f=fixture('composer.component.ts',{prompts:async()=>[{id:'general',text:'Instrucciones'},{id:'analyst',text:'Otras instrucciones'}],compare:async()=>{posts++;return {id:'new'};}},{realValidation:true});
  const c=new f.exports.ComposerComponent();await new Promise(resolve=>setImmediate(resolve));
  c.settings={temperature:0,seed:42,num_ctx:16384,max_output_tokens:4096,timeout_s:120,warmup:'none',order_policy:'random',latency_study:false,planned_attempts:2};
  assert.equal(c.preparationIssues()[0].id,'shared-input');
  await c.submit();assert.equal(posts,0);assert.match(c.error(),/obligatorio/);
  c.shared.text='saludo';c.shared.expected_answer='{invalid';c.evaluation='json_match';
  assert.equal(c.preparationIssues()[0].id,'shared-reference');await c.submit();assert.equal(c.invalidField(),'shared-reference');
  c.shared.expected_answer='"hola"';c.missingFiles.set({inputA:['inactive.txt'],shared:['active.txt']});
  assert.equal(c.preparationIssues().length,1);assert.equal(c.preparationIssues()[0].id,'shared-files');
  c.missingFiles.set({inputA:['inactive.txt']});assert.equal(c.preparationIssues().length,0);
  c.settings.order_policy='balanced';assert.equal(c.preparationIssues()[0].id,'repetitions');
  c.repetitions=2;assert.equal(c.plannedRuns(),4);assert.equal(c.preparationIssues().length,0);
  c.settings.max_output_tokens=16384;assert.equal(c.preparationIssues()[0].id,'output-limit');
  c.settings.max_output_tokens=4096;await c.submit();assert.equal(posts,1);
});

test('map model equality uses actual identities and ignores inactive B in one-model mode',()=>{
  const f=fixture('composer.component.ts',{prompts:async()=>[]},{realValidation:true}),c=new f.exports.ComposerComponent();
  c.modelA='example';c.modelB='example:latest';c.mode='different_models';assert.equal(c.modelsEqual(),true);
  c.modelB='other';assert.equal(c.modelsEqual(),false);c.mode='same_model';assert.equal(c.modelsEqual(),true);
});

test('navigation clears old notices but keeps late creation confirmation without redirecting',async()=>{
  const request=deferred();const {app}=await workspace({create:()=>request.promise});
  app.notice.set('Old cancellation');app.navigate('models');assert.equal(app.notice(),'');
  app.navigate('compose');const creating=app.create();app.navigate('profile');request.resolve({id:'saved'});await creating;
  assert.equal(app.view(),'profile');assert.match(app.notice(),/guardada.*historial/);
});


test('ChatGPT catalog discards stale adapter responses and ends loading after destroy',async()=>{
  const request=deferred();
  const f=fixture('composer.component.ts',{prompts:async()=>[],openaiModels:()=>request.promise});
  const c=new f.exports.ComposerComponent();
  c.adapter='codex';const loading=c.loadModels();
  c.adapter='simulated';c.changeAdapter();
  request.resolve({models:[{name:'stale-gpt'}]});await loading;
  assert.equal(c.models().length,0);assert.equal(c.modelsBusy(),false);
});

test('ChatGPT connection ignores completion after account change',async()=>{
  const request=deferred();let calls=0;
  const f=fixture('openai-connection.component.ts',{openaiStatus:async()=>({linked:false}),openaiConnect:()=>{calls++;return request.promise;}});
  const c=new f.exports.OpenaiConnectionComponent();await new Promise(r=>setImmediate(r));
  const connecting=c.act(true);f.auth.user.set({id:'other'});
  request.resolve({linked:true});await connecting;
  assert.equal(calls,1);assert.equal(c.linked(),false);assert.equal(c.message(),'');
});

test('ChatGPT does not send invalid hidden Ollama settings after switching provider',async()=>{
  let sent;
  const f=fixture('composer.component.ts',{prompts:async()=>[],compare:async body=>{sent=body;return {id:'controlled'};}});
  const c=new f.exports.ComposerComponent();c.adapter='codex';c.modelA='fixture-gpt';c.models.set(['fixture-gpt']);
  c.templates.set([{id:'general'}]);c.promptA.text=c.promptB.text='Brief';c.shared.text='Hello';
  c.settings={temperature:NaN,seed:-1,num_ctx:NaN,max_output_tokens:NaN,timeout_s:120,order_policy:'balanced',latency_study:false};
  await c.submit();assert.equal(sent.adapter,'codex');assert.equal(sent.settings.timeout_s,120);
  assert.equal(sent.settings.order_policy,'random');assert.notEqual(sent.settings.seed,-1);
});
