import { Component, computed, inject, output, signal } from '@angular/core';
import { DecimalPipe, JsonPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ArenaService, ExperimentDetail, ExperimentSummary, ResultSummary, Run } from './arena.service';

type Section = 'tour' | 'summary' | 'diagnostics' | 'replay' | 'data' | 'project';
interface SavedCase { title:string; question:string; explanation:string; experiment_id:string; run_id:string; task_id:string; branch:'A'|'B' }
interface Suite { experiment_id:string; suite:string; split:string }
interface Showcase { cases:SavedCase[]; suites:Suite[] }
interface Message { role:string; content?:string; tool_calls?:unknown[]; tool_name?:string }
interface Probe { model:string; case:string; condition:string; elapsed_s?:number;
  assessment:{correct?:boolean;reason?:string;tool_result?:unknown}; continuation_correct?:boolean;
  request?:{messages?:Message[]}; response?:{message?:Message};
  continuation_request?:{messages?:Message[]}; continuation_response?:{message?:Message}; }
interface Fixture { name:string; split:string; content:string; source:string }
interface ReplayEvent { seq:number; kind:string; at:number; payload:Record<string,any> }
interface Replay { source:string; run_id:string; branch:string; task:{id:string;input:string;criteria:unknown}; system_prompt:string; events:ReplayEvent[]; note:string }

@Component({selector:'arena-demo-overview',standalone:true,imports:[JsonPipe,DecimalPipe,FormsModule],
  templateUrl:'./demo-overview.component.html',styleUrl:'./demo-overview.component.css'})
export class DemoOverviewComponent {
  private api = inject(ArenaService);
  opened = output<string>();
  section = signal<Section>('tour');
  sections: {id:Section;label:string}[] = [{id:'tour',label:'Recorrido'},{id:'summary',label:'Resumen'},{id:'diagnostics',label:'Diagnósticos'},{id:'replay',label:'Reproducción'},{id:'data',label:'Datos'},{id:'project',label:'El proyecto'}];
  experiments = signal<ExperimentSummary[]>([]);
  details = signal<Record<string,ExperimentDetail>>({});
  showcase = signal<Showcase>({cases:[],suites:[]});
  probes = signal<Probe[]>([]);
  fixtures = signal<Fixture[]>([]);
  replay = signal<Replay|null>(null);
  loading = signal(false);
  error = signal('');
  private loadVersion = 0;
  split = signal('eval');
  model = signal('all');
  diagnosticModel = signal('all');
  diagnosticCase = signal('all');
  diagnosticCondition = signal('all');
  probeId = signal('');
  datasetId = signal('');
  step = signal(0);
  models = computed(() => [...new Set(this.experiments().filter(e=>e.adapter === 'ollama').flatMap(e=>Object.values(this.details()[e.id]?.snapshot.config.agents ?? {}).map(a=>a.model)))].sort());
  summaryRows = computed(() => this.showcase().suites.filter(s=>this.split() === 'all' || s.split === this.split()).flatMap(s => {
    const detail = this.details()[s.experiment_id];
    return detail ? (['A','B'] as const).filter(b=>this.model() === 'all' || detail.snapshot.config.agents[b].model === this.model()).map(b=>({
      ...s,branch:b,model:detail.snapshot.config.agents[b].model,summary:detail.overviews[b],
    })) : [];
  }));
  diagnosticModels = computed(() => [...new Set(this.probes().map(p=>p.model))].sort());
  diagnosticCases = computed(() => [...new Set(this.probes().map(p=>p.case))].sort());
  diagnosticConditions = computed(() => [...new Set(this.probes().map(p=>p.condition))].sort());
  visibleProbes = computed(() => this.probes().filter(p=>(this.diagnosticModel()==='all'||p.model===this.diagnosticModel()) && (this.diagnosticCase()==='all'||p.case===this.diagnosticCase()) && (this.diagnosticCondition()==='all'||p.condition===this.diagnosticCondition())));
  selectedProbe = computed(() => this.visibleProbes().find(p=>this.probeKey(p)===this.probeId()) ?? this.visibleProbes()[0] ?? null);
  diagnosticScores = computed(() => this.diagnosticModels().map(model=>{
    const probes = this.probes().filter(p=>p.model===model);
    return {model,total:probes.length,calls:probes.filter(p=>p.assessment.correct===true).length,continuations:probes.filter(p=>p.continuation_correct===true).length};
  }));
  dataset = computed(() => this.details()[this.datasetId()] ?? this.details()[this.experiments()[0]?.id] ?? null);
  replayEvent = computed(() => this.replay()?.events[this.step()] ?? null);
  constructor() { void this.load(); }
  async json<T>(file:string):Promise<T> {
    const response = await fetch(new URL('demo/'+file,document.baseURI));
    if (!response.ok) throw new Error('Carga incompleta');
    return response.json();
  }
  async load() {
    const version = ++this.loadVersion;
    this.error.set('');this.loading.set(true);
    try {
      const [experiments,showcase,diagnostics,fixtures,replay] = await Promise.all([
        this.api.experiments(),this.json<Showcase>('showcase.json'),this.json<{probes:Probe[]}>('diagnostics.json'),
        this.json<{files:Fixture[]}>('fixtures.json'),this.json<Replay>('replay.json'),
      ]);
      const details = Object.fromEntries(await Promise.all(experiments.map(async e=>[e.id,await this.api.detail(e.id)] as const)));
      if (version !== this.loadVersion) return;
      this.experiments.set(experiments);this.details.set(details);this.showcase.set(showcase);
      this.probes.set(diagnostics.probes);this.fixtures.set(fixtures.files);this.replay.set(replay);this.step.set(0);
    } catch { if(version === this.loadVersion) this.error.set('No se pudo cargar todo el recorrido de demo. Los datos visibles pueden estar incompletos; reintenta.'); }
    finally { if(version === this.loadVersion) this.loading.set(false); }
  }
  choose(section:Section) { this.section.set(section);requestAnimationFrame(()=>document.getElementById('demo-section-title')?.focus()); }
  probeKey(p:Probe) { return [p.model,p.case,p.condition].join('/'); }
  savedRun(c:SavedCase):Run|undefined { return this.details()[c.experiment_id]?.runs.find(r=>r.id===c.run_id); }
  reference(c:SavedCase) { const task=this.details()[c.experiment_id]?.snapshot.tasks?.find(t=>t.id===c.task_id);return task?.expected_answer ?? this.format(task?.criteria); }
  format(value:unknown) { return value == null ? 'No disponible' : typeof value === 'string' ? value : JSON.stringify(value,null,2); }
  formatMessage(value:string|undefined) { if(value == null) return 'No disponible';try{return JSON.stringify(JSON.parse(value),null,2);}catch{return value;} }
  suiteLabel(suite:string) { return ({text:'Texto',json:'JSON',orders:'Pedidos',attachments:'Adjuntos'} as Record<string,string>)[suite] ?? suite; }
  width(summary:ResultSummary,key:'correct'|'incorrect'|'invalid_format'|'execution_errors'|'cancelled'|'unscored'|'pending') { return summary.total ? 100*summary[key]/summary.total : 0; }
  conditionLabel(value:string) { return value === 'single_tool' ? 'Una herramienta' : value === 'all_tools' ? 'Todas las herramientas' : value; }
  toolMessages(p:Probe) { return (p.continuation_request?.messages ?? []).filter(m=>m.role==='tool'); }
  moveStep(delta:number) { const last=(this.replay()?.events.length??1)-1;this.step.update(i=>Math.max(0,Math.min(last,i+delta))); }
  eventLabel(kind:string) { return ({input:'Entrada preparada',inference_request:'Solicitud al simulador',inference_response:'Respuesta del simulador',tool_request:'Herramienta solicitada',tool_result:'Resultado de herramienta',finished:'Resultado final'} as Record<string,string>)[kind] ?? kind; }
  eventText(event:ReplayEvent) {
    const p=event.payload;
    if(event.kind==='input') return (p['messages'] as Message[])?.find(m=>m.role==='user')?.content ?? 'Entrada guardada';
    if(event.kind==='inference_request') return `Solicitud guardada con ${(p['messages'] as Message[])?.length ?? 0} mensajes. El historial se conserva en el JSON.`;
    if(event.kind==='inference_response') return p['response']?.message?.content || this.format(p['response']?.message?.tool_calls);
    if(event.kind==='tool_request') return p['name']+'\n'+this.format(p['arguments']);
    if(event.kind==='tool_result') return p['name']+'\n'+this.format(p['result']);
    return p['answer'] ?? 'Sin respuesta final';
  }
  elapsed(event:ReplayEvent) { return Math.max(0,event.at-(this.replay()?.events[0]?.at ?? event.at)); }
}
