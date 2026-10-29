import type { ModelResult } from './arena.service';

export interface CostRate { basis:'tokens'|'hour'; input:number|null; output:number|null; hour:number|null }
export const rateKey = (entry:ModelResult) => `${entry.adapter}:${entry.model}`;
export function modelProvider(entry:ModelResult) {
  if (entry.adapter === 'codex') return {key:'openai',label:'OpenAI'};
  if (entry.adapter === 'ollama') return {key:'ollama',label:'Ollama · local'};
  return {key:'simulated',label:'Simulación'};
}
const valid = (n:unknown):n is number => typeof n === 'number' && Number.isFinite(n) && n >= 0;
const percent = (n:number,d:number) => d > 0 ? 100*n/d : null;
function kindLabel(kind:string) {
  const [evaluation,modality]=kind.split(':');
  const name=({exact_match:'Texto exacto',json_match:'JSON',none:'Respuesta abierta',order_benchmark:'Pedidos con herramientas'} as Record<string,string>)[evaluation]??evaluation;
  return name+(modality==='images'?' · imágenes':modality==='files'?' · archivos':'');
}

export function estimatedCost(entry:ModelResult, rate?:CostRate):number|null {
  const m=entry.metrics;
  if (!rate || !m || entry.adapter === 'simulated' || entry.summary.total <= 0) return null;
  if (rate.basis === 'hour') return valid(rate.hour) && valid(m.total_run_s)
    ? m.total_run_s / 3600 * rate.hour / entry.summary.total : null;
  return m.usage_samples === entry.summary.total && valid(m.input_tokens) && valid(m.output_tokens)
    && valid(rate.input) && valid(rate.output)
    ? (m.input_tokens * rate.input + m.output_tokens * rate.output) / 1e6 / entry.summary.total : null;
}

export function modelComparisonCharts(entries:ModelResult[], rates:Record<string,CostRate>) {
  const definitions:{key:string;title:string;unit:string;direction:string;note:string;fixed?:number;value:(e:ModelResult)=>number|null;sample:(e:ModelResult)=>string}[] = [
    {key:'quality',title:'Aciertos',unit:'%',direction:'Más es mejor',fixed:100,
      note:'Correctas / ejecuciones con referencia. Los errores y cancelaciones no cuentan como aciertos.',
      value:e=>percent(e.summary.correct,e.summary.planned_evaluable),sample:e=>`${e.summary.correct}/${e.summary.planned_evaluable} con referencia`},
    {key:'coverage',title:'Cobertura de evaluación',unit:'%',direction:'Más es mejor',fixed:100,
      note:'Respuestas evaluadas / ejecuciones con referencia. Lee la calidad junto a su cobertura.',
      value:e=>percent(e.summary.evaluated,e.summary.planned_evaluable),sample:e=>`${e.summary.evaluated}/${e.summary.planned_evaluable} con referencia`},
    {key:'errors',title:'Errores de ejecución',unit:'%',direction:'Menos es mejor',fixed:100,
      note:'Errores / ejecuciones programadas. Las cancelaciones se muestran en la distribución de cada ficha.',
      value:e=>percent(e.summary.execution_errors,e.summary.total),sample:e=>`${e.summary.execution_errors}/${e.summary.total} ejecuciones`},
    {key:'latency',title:'Tiempo medio de respuesta',unit:'s',direction:'Menos es mejor',
      note:'Tiempo total de respuestas sin error; incluye preparación, carga y calentamiento si se solicitó.',
      value:e=>e.summary.timed_answers>0?e.summary.mean_answer_s:null,sample:e=>`${e.summary.timed_answers} respuestas medidas`},
    {key:'p95',title:'Tiempo de respuesta · P95',unit:'s',direction:'Menos es mejor',
      note:'El 95 % de los tiempos medidos queda en este valor o por debajo (rango más próximo). Con pocas muestras es orientativo.',
      value:e=>e.metrics?.p95_answer_s??null,sample:e=>`${e.metrics?.latency_samples??0} respuestas medidas`},
    {key:'speed',title:'Velocidad de generación',unit:'tok/s',direction:'Más es mejor',
      note:'Media de tokens/s del servidor en respuestas sin error con uso completo. No mide toda la ejecución.',
      value:e=>e.metrics?.mean_server_tps??null,sample:e=>`${e.metrics?.speed_samples??0} respuestas medidas`},
    {key:'tokens',title:'Tokens por ejecución',unit:'tok',direction:'Según la tarea',
      note:'Entrada + salida, incluyendo ejecuciones con error. Solo disponible con uso completo de todas las ejecuciones.',
      value:e=>e.metrics?.usage_samples===e.summary.total && e.summary.total>0 && valid(e.metrics.input_tokens) && valid(e.metrics.output_tokens)
        ? (e.metrics.input_tokens+e.metrics.output_tokens)/e.summary.total:null,
      sample:e=>`${e.metrics?.usage_samples??0}/${e.summary.total} con uso completo`},
    {key:'cost',title:'Coste estimado por ejecución',unit:'€',direction:'Menos es mejor',
      note:'Estimación según tus tarifas; incluye errores y cancelaciones con mediciones completas. No es un importe facturado.',
      value:e=>estimatedCost(e,rates[rateKey(e)]),sample:e=>rates[rateKey(e)]?.basis==='hour'?'Tiempo × €/hora':'Tokens × tarifa de entrada y salida'},
  ];
  return definitions.map(def=>{
    const rows=entries.map(entry=>{
      const raw=def.value(entry);
      const value=entry.adapter==='simulated'||!valid(raw)?null:raw;
      return {id:entry.id,model:entry.model,branch:entry.branch,kind:kindLabel(entry.kind),value,sample:def.sample(entry),
        provider:modelProvider(entry),adapter:entry.adapter,experiment:entry.experiment_name,experimentId:entry.experiment_id,updatedAt:entry.updated_at,split:entry.split};
    });
    const maximum=def.fixed??Math.max(0,...rows.map(r=>r.value??0));
    return {...def,maximum,rows:rows.map(row=>({...row,height:row.value!==null && maximum>0?100*row.value/maximum:0}))};
  });
}

export function orderComparisonCharts(charts:ReturnType<typeof modelComparisonCharts>,order:string) {
  const first=charts[0]?.rows??[];
  const metric=charts.find(c=>c.key===order);
  const rows=[...first].sort((a,b)=>{
    if (order==='model') return a.model.localeCompare(b.model);
    if (!metric) return 0;
    const av=metric.rows.find(r=>r.id===a.id)?.value??null;
    const bv=metric.rows.find(r=>r.id===b.id)?.value??null;
    if (av===null) return bv===null?0:1;
    if (bv===null) return -1;
    return order==='quality'?bv-av:av-bv;
  });
  const positions=new Map(rows.map((r,i)=>[r.id,i]));
  return charts.map(chart=>({...chart,rows:[...chart.rows].sort((a,b)=>positions.get(a.id)!-positions.get(b.id)!)}));
}

/** Export precisely the displayed scope and units, preserving missing values. */
export function comparisonCsv(charts:ReturnType<typeof modelComparisonCharts>,rates:Record<string,CostRate>={}) {
  const cell=(value:string|number|null)=>{
    let text=value===null?'Sin datos':String(value);
    if (typeof value==='string' && /^\s*[=+@-]/.test(text)) text="'"+text;
    return '"'+text.replace(/"/g,'""')+'"';
  };
  const header=['Ficha','Modelo','Proveedor','Variante','Prueba','Experimento','ID experimento','Fase',
    ...charts.flatMap(c=>[`${c.title} (${c.unit})`,`${c.title} · muestra`]),
    'Base del coste','Entrada (EUR/millón de tokens)','Salida (EUR/millón de tokens)','Coste asignado (EUR/hora)','Lectura'];
  const rows=(charts[0]?.rows??[]).map(row=>{
    const rate=rates[`${row.adapter}:${row.model}`];
    return [row.id,row.model,row.provider.label,row.branch,row.kind,row.experiment,row.experimentId,row.split,
      ...charts.flatMap(c=>{const point=c.rows.find(r=>r.id===row.id);return [point?.value??null,point?.sample??''];}),
      rate?.basis??'',rate?.input??null,rate?.output??null,rate?.hour??null,
      'Valores descriptivos; revisar condiciones y evidencia de origen. Coste estimado, no facturado.'];
  });
  return [header,...rows].map(row=>row.map(cell).join(',')).join('\r\n')+'\r\n';
}
