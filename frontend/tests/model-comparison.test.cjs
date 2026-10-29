const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const ts=require('typescript');
const mod={exports:{}};
vm.runInNewContext(ts.transpileModule(fs.readFileSync(path.join(__dirname,'../src/app/model-comparison-data.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,{module:mod,exports:mod.exports});
const {comparisonCsv,estimatedCost,modelComparisonCharts,modelProvider,orderComparisonCharts,rateKey}=mod.exports;
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

test('vertical heights share the metric scale and providers are explicit',()=>{
  const a=entry(),b=entry({id:'b',adapter:'codex',model:'remote',summary:{...a.summary,mean_answer_s:4}});
  const time=modelComparisonCharts([a,b],{}).find(c=>c.key==='latency');
  assert.equal(time.rows[0].height,50); assert.equal(time.rows[1].height,100);
  assert.equal(time.rows[0].provider.key,'ollama'); assert.equal(time.rows[1].provider.key,'openai');
  assert.equal(modelProvider(entry({adapter:'simulated'})).key,'simulated');
});

test('ordering keeps one common model order, missing last, and preserves source arrays',()=>{
  const a=entry({model:'zeta'}),b=entry({id:'b',model:'alpha',summary:{...a.summary,correct:2,mean_answer_s:4}}),c=entry({id:'c',adapter:'simulated'});
  const charts=modelComparisonCharts([a,b,c],{});
  const sorted=orderComparisonCharts(charts,'quality');
  assert.ok(sorted.every(c=>c.rows.map(r=>r.id).join(',')==='b,a,c'));
  assert.equal(orderComparisonCharts(charts,'latency')[0].rows.map(r=>r.id).join(','),'a,b,c');
  assert.equal(orderComparisonCharts(charts,'model')[0].rows[0].model,'alpha');
  assert.equal(charts[0].rows[0].id,'a');
});

test('CSV exports selected columns, exact observations, scope and safe quoted text',()=>{
  const e=entry({experiment_id:'experiment-1',experiment_name:'=UNTRUSTED("demo")'});
  const charts=modelComparisonCharts([e],{[rateKey(e)]:{basis:'hour',hour:2}}).filter(c=>['quality','cost'].includes(c.key));
  const csv=comparisonCsv(charts,{[rateKey(e)]:{basis:'hour',hour:2}});
  assert.ok(csv.includes('Aciertos (%)')); assert.ok(csv.includes('Coste estimado por ejecución (€)'));
  assert.ok(!csv.includes('Tiempo de respuesta · P95'));
  assert.ok(csv.includes('"50"')); assert.ok(csv.includes('"0.5"')); assert.ok(csv.includes('"hour"'));
  assert.ok(csv.includes('"\'=UNTRUSTED(""demo"")"'));
  assert.ok(csv.includes('experiment-1')); assert.ok(csv.includes('Sin datos'));
  const missing=comparisonCsv(modelComparisonCharts([entry({metrics:undefined})],{}).filter(c=>c.key==='p95'));
  assert.ok(missing.split('\r\n')[1].includes('Sin datos'));
});
