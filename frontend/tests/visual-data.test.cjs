const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const ts=require('typescript');
const mod={exports:{}};
vm.runInNewContext(ts.transpileModule(fs.readFileSync(path.join(__dirname,'../src/app/visual-data.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,{module:mod,exports:mod.exports});
const {outcomeSegments,outcomeDescription,timePoints,campaignPoints}=mod.exports;
const summary=(extra={})=>({total:0,finished:0,evaluated:0,planned_evaluable:0,correct:0,incorrect:0,invalid_format:0,execution_errors:0,cancelled:0,unscored:0,pending:0,mean_answer_s:null,timed_answers:0,...extra});

test('outcome chart keeps cancellations, errors, unscored and pending separate',()=>{
  const s=summary({total:7,finished:6,evaluated:3,planned_evaluable:5,correct:1,incorrect:1,invalid_format:1,execution_errors:1,cancelled:1,unscored:1,pending:1});
  const segments=outcomeSegments(s);
  assert.equal(segments.reduce((n,s)=>n+s.count,0),7);
  assert.ok(Math.abs(segments.reduce((n,s)=>n+s.width,0)-100)<1e-10);
  assert.equal(segments.find(s=>s.key==='cancelled').count,1);
  assert.match(outcomeDescription(s),/1 canceladas/);assert.match(outcomeDescription(s),/1 errores de ejecución/);
});
test('distribution uses all scheduled runs rather than the evaluated denominator',()=>{
  const parts=outcomeSegments(summary({total:4,correct:1,evaluated:1,planned_evaluable:2,unscored:1,cancelled:2}));
  assert.equal(parts[0].width,25);assert.equal(parts.find(p=>p.key==='cancelled').width,50);
  assert.ok(outcomeSegments(summary()).every(p=>p.width===0));
});
test('time graph distinguishes measured zero from missing measurements',()=>{
  const rows=timePoints([{branch:'A',mean_answer_s:0,timed_answers:1},{branch:'B',mean_answer_s:null,timed_answers:0}]);
  assert.equal(rows[0].available,true);assert.equal(rows[0].position,0);assert.equal(rows[1].available,false);
  assert.equal(timePoints([{branch:'A',mean_answer_s:2,timed_answers:0}])[0].available,false);
});
test('time dots share a zero-based scale and exclude invalid measurements',()=>{
  const rows=timePoints([{branch:'A',mean_answer_s:2,timed_answers:3},{branch:'B',mean_answer_s:4,timed_answers:3}]);
  assert.equal(rows[0].position,50);assert.equal(rows[1].position,100);assert.equal(rows[0].maximum,4);
  assert.equal(timePoints([{branch:'A',mean_answer_s:NaN,timed_answers:2}])[0].available,false);
});
test('campaign plot preserves reference denominators and does not plot excluded or partial attempts',()=>{
  const attempt=(id,seq,extra={})=>({experiment_id:id,sequence:seq,compatible:true,complete:true,overviews:{A:summary({correct:1,planned_evaluable:4,evaluated:2}),B:summary()},...extra});
  const campaign={attempts:[attempt('partial',3,{complete:false}),attempt('excluded',2),attempt('included',1)],analysis:{included_attempts:[{experiment_id:'included'}],excluded_attempts:[{experiment_id:'excluded',reasons:['Carga distinta']}]} };
  const before=JSON.stringify(campaign),points=campaignPoints(campaign);
  assert.equal(points[0].sequence,1);assert.equal(points[0].branches[0].position,25);assert.equal(points[0].branches[1].position,null);
  assert.equal(points[0].included,true);assert.equal(points[1].included,false);assert.match(points[1].reason,/Carga distinta/);
  assert.equal(points[2].included,false);assert.match(points[2].reason,/En curso/);
  assert.equal(JSON.stringify(campaign),before);
});

test('execution orientation describes only observed states and separates incorrect answers from execution failures',()=>{
  const guide=mod.exports.executionGuidance;
  assert.match(guide([]).title,/Sin ejecuciones/);
  const queued=guide([{status:'queued'},{status:'cancelled'}]);
  assert.equal(queued.queued,1);assert.equal(queued.running,0);assert.match(queued.title,/En espera/);
  assert.match(guide([{status:'running'},{status:'queued'}]).title,/Procesando/);
  assert.match(guide([{status:'failed',result:{answer:'no',success:false}}]).next,/Revisa una respuesta/);
  assert.match(guide([{status:'failed',result:{error:'offline'}}]).next,/si hay un error/);
  assert.match(guide([{status:'cancelled',result:{error:'cancelled'}}]).next,/Revisa una respuesta/);
  assert.match(guide([{status:'timeout'}]).next,/si hay un error/);
});

test('partial answers retain their category without treating an incorrect evaluated answer as interrupted',()=>{
  const partial=mod.exports.partialAnswer;
  assert.equal(partial({status:'cancelled',result:{answer:'late answer'}}),true);
  assert.equal(partial({status:'failed',result:{answer:'partial',error:'offline'}}),true);
  assert.equal(partial({status:'timeout',result:{answer:'partial'}}),true);
  assert.equal(partial({status:'failed',result:{answer:'wrong'}}),false);
  assert.equal(partial({status:'completed',result:{answer:'unscored'}}),false);
  assert.equal(partial({status:'cancelled',result:null}),false);
});
