const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const ts=require('typescript');
const mod={exports:{}};
vm.runInNewContext(ts.transpileModule(fs.readFileSync(path.join(__dirname,'../src/app/result-presentation.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,{module:mod,exports:mod.exports});
const {caseInputs,evaluationStatus}=mod.exports;

test('case input uses the matching executed case without changing its snapshot',()=>{
  const snapshot={tasks:[{id:'first',input:'First input'},{id:'second',input:'Second input'}]};
  const before=JSON.stringify(snapshot);
  assert.equal(caseInputs(snapshot,'second')[0].text,'Second input');
  assert.equal(caseInputs(snapshot,'unknown')[0].text,null);
  assert.equal(caseInputs(undefined,'first')[0].text,null);
  assert.equal(JSON.stringify(snapshot),before);
});
test('independent inputs remain separate even with identical text or incomplete exports',()=>{
  const snapshot={tasks:[{id:'case',input:'Do not substitute shared data'}],branch_tasks:{A:{id:'case',input:'Same'},B:{id:'case',input:'Same'}}};
  const entries=caseInputs(snapshot,'case');
  assert.equal(entries.length,2);assert.equal(entries[0].label,'Entrada A');assert.equal(entries[1].label,'Entrada B');
  delete snapshot.branch_tasks.B;
  assert.equal(caseInputs(snapshot,'case')[1].text,null);
  snapshot.branch_tasks.A.id='another';assert.equal(caseInputs(snapshot,'case')[0].text,null);
  assert.ok(caseInputs({conditions:{inputs_shared:false}},'case').every(e=>e.text===null));
});
test('only pending runs imply a pending evaluation; terminal categories stay distinct',()=>{
  for(const status of ['queued','running'])assert.match(evaluationStatus({status,result:null}),/pendiente/);
  for(const status of ['cancelled','completed','succeeded','failed','timeout','limit','interrupted'])
    assert.doesNotMatch(evaluationStatus({status,result:null}),/pendiente/);
  const cancelled={status:'cancelled',result:{answer:'partial',reason:'Original evidence'}};
  assert.match(evaluationStatus(cancelled),/cancelada/);assert.equal(cancelled.result.reason,'Original evidence');
  assert.match(evaluationStatus({status:'completed',result:null}),/sin evaluar/i);
  assert.match(evaluationStatus({status:'failed',result:{answer:'bad',format_ok:false}}),/formato/);
  assert.match(evaluationStatus({status:'failed',result:{answer:'bad'}}),/criterio/);
  assert.match(evaluationStatus({status:'failed',result:{error:'offline'}}),/no se completó/);
  assert.equal(evaluationStatus({status:'failed',result:{reason:'Recorded reason'}}),'Recorded reason');
});
