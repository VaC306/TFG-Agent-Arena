const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const ts=require('typescript');
const mod={exports:{}};
vm.runInNewContext(ts.transpileModule(fs.readFileSync(path.join(__dirname,'../src/app/model-comparison-data.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,{module:mod,exports:mod.exports});
const {estimatedCost,modelComparisonCharts,rateKey}=mod.exports;
const entry=(extra={})=>({id:'a',model:'example',adapter:'ollama',kind:'exact_match:text',branch:'A',
  summary:{total:4,correct:1,planned_evaluable:2,evaluated:1,execution_errors:1,mean_answer_s:2,timed_answers:2},
  metrics:{input_tokens:1000000,output_tokens:500000,usage_samples:4,total_run_s:3600,p95_answer_s:3,latency_samples:2,mean_server_tps:20,speed_samples:2},...extra});

test('cost estimates use all executions and require explicit finite rates and complete usage',()=>{
  const e=entry();
  assert.equal(estimatedCost(e),null);
  assert.equal(estimatedCost(e,{basis:'hour',hour:2}),.5);
  assert.equal(estimatedCost(e,{basis:'tokens',input:2,output:4}),1);
  assert.equal(estimatedCost(e,{basis:'tokens',input:0,output:0}),0);
  assert.equal(estimatedCost(e,{basis:'tokens',input:null,output:4}),null);
  assert.equal(estimatedCost(entry({metrics:{...e.metrics,usage_samples:3}}),{basis:'tokens',input:2,output:4}),null);
  assert.equal(estimatedCost(entry({metrics:{...e.metrics,total_run_s:null}}),{basis:'hour',hour:2}),null);
  assert.equal(estimatedCost(entry({adapter:'simulated'}),{basis:'hour',hour:2}),null);
  for(const hour of [-1,NaN,Infinity]) assert.equal(estimatedCost(e,{basis:'hour',hour}),null);
});

test('charts use explicit denominators, common zero scales and distinguish zero from missing',()=>{
  const e=entry(),charts=modelComparisonCharts([e,entry({id:'b',metrics:undefined})],{[rateKey(e)]:{basis:'hour',hour:2}});
  assert.equal(charts.find(c=>c.key==='quality').rows[0].value,50);
  assert.equal(charts.find(c=>c.key==='coverage').rows[0].value,50);
  assert.equal(charts.find(c=>c.key==='errors').rows[0].value,25);
  assert.equal(charts.find(c=>c.key==='quality').maximum,100);
  assert.equal(charts.find(c=>c.key==='p95').rows[1].value,null);
  const rows=modelComparisonCharts([entry({summary:{...e.summary,execution_errors:0,mean_answer_s:0}})],{});
  assert.equal(rows.find(c=>c.key==='errors').rows[0].value,0);
  assert.equal(rows.find(c=>c.key==='latency').rows[0].value,0);
  assert.ok(modelComparisonCharts([entry({adapter:'simulated'})],{}).every(c=>c.rows[0].value===null));
});
