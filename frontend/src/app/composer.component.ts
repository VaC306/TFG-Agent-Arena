import { ComparisonMapComponent } from './comparison-map.component';
import { TermHelpComponent } from './term-help.component';
import { Component, DestroyRef, EventEmitter, inject, Input, Output, signal } from '@angular/core';
import { WorkerStatusComponent } from './worker-status.component';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { ArenaService, ComparisonBody, DatasetPreview, InputData, PresetId, PromptTemplate, EvaluationMode, defaultSettings } from './arena.service';
import { InputEditorComponent } from './input-editor.component';
import { InfoDialogComponent } from './info-dialog.component';
import { AuthService, Preferences } from './auth.service';
import { textError, filenameError, modelIdentity } from './validation';
import { LoadingIndicatorComponent } from './loading-indicator.component';
import { LoadingService } from './loading.service';

type DraftSlot = 'inputA' | 'inputB' | 'shared';
interface ComposerDraft {
  version: 1; owner: string; config: Preferences;
  inputs: Record<DraftSlot, Pick<InputData,'text'|'expected_answer'>>;
  dataset: DatasetPreview | null; datasetName: string;
  missingFiles: Record<DraftSlot,string[]>;
  submissionPending?: boolean;
}

function validDraft(value: unknown, owner: string | undefined): value is ComposerDraft {
  if (!value || typeof value !== 'object') return false;
  const d = value as ComposerDraft;
  const c = d.config;
  return d.version === 1 && !!owner && d.owner === owner && !!c &&
    ['simulated','ollama'].includes(c.adapter) && ['same_model','different_models'].includes(c.mode) && ['manual','dataset'].includes(c.source) &&
    (c.independentInputs === undefined || typeof c.independentInputs === 'boolean') &&
    [c.name,c.modelA,c.modelB,c.promptA?.template,c.promptA?.text,c.promptB?.template,c.promptB?.text].every(v => typeof v === 'string') &&
    typeof c.repetitions === 'number' && !!c.settings && typeof c.settings === 'object' &&
    !!d.inputs && !!d.missingFiles && (['inputA','inputB','shared'] as const).every(slot =>
      typeof d.inputs[slot]?.text === 'string' && typeof d.inputs[slot]?.expected_answer === 'string' &&
      Array.isArray(d.missingFiles[slot]) && d.missingFiles[slot].every(name => typeof name === 'string')) &&
    typeof d.datasetName === 'string' && (d.dataset === null || !!d.dataset && Array.isArray(d.dataset.cases) &&
      typeof d.dataset.count === 'number' && typeof d.dataset.scored === 'number' && d.dataset.cases.every(row =>
        typeof row.id === 'string' && typeof row.input === 'string' && (row.expected_answer === null || typeof row.expected_answer === 'string')));
}

@Component({
  selector: 'arena-composer', standalone: true, imports: [ComparisonMapComponent,TermHelpComponent,FormsModule, InputEditorComponent, InfoDialogComponent,LoadingIndicatorComponent,WorkerStatusComponent],
  templateUrl: './composer.component.html',
})
export class ComposerComponent {
  @Input() active = true;
  @Input() exampleBusy = false;
  @Output() example = new EventEmitter<void>();
  private api = inject(ArenaService);
  private auth = inject(AuthService);
  private activity = inject(LoadingService);
  private saveTimer?: ReturnType<typeof setTimeout>;
  private ownerId = this.auth.user()?.id;
  private destroyed = false;
  private datasetVersion = 0;
  private draftKey = `arena.composer.v1.${this.ownerId}`;
  pendingDraft = signal<ComposerDraft | null>(null);
  draftNotice = signal('');
  submissionPending = signal(false);
  missingFiles = signal<Record<string,string[]>>({});
  preferencesNotice = signal('');
  @Output() created = new EventEmitter<string>();
  mode: 'same_model' | 'different_models' = 'same_model';
  adapter: PresetId = 'simulated';
  name = 'Comparación personalizada';
  repetitions = 1;
  evaluation: EvaluationMode = 'exact_match';
  settings = defaultSettings();
  split: 'dev' | 'eval' = 'dev';
  modelA = 'simulated-a';
  modelB = 'simulated-b';
  promptA = {template:'general',text:''};
  promptB = {template:'analyst',text:''};
  inputA: InputData = {text:'',files:[],expected_answer:''};
  inputB: InputData = {text:'',files:[],expected_answer:''};
  shared: InputData = {text:'',files:[],expected_answer:''};
  templates = signal<PromptTemplate[]>([]);
  models = signal<string[]>([]);
  modelsBusy = signal(false);
  modelNotice = signal('');
  error = signal('');
  invalidField = signal('');
  busy = signal(false);
  readingA = false;
  readingB = false;
  readingShared = false;
  source: 'manual' | 'dataset' = 'manual';
  independentInputs = false;
  usesIndependentInputs() { return this.mode === 'same_model' && this.independentInputs; }
  modelsEqual() { return this.mode === 'same_model' || modelIdentity(this.modelA) === modelIdentity(this.modelB); }
  variablesChanged() {
    const changes = [];
    if (this.mode === 'different_models' && modelIdentity(this.modelA) !== modelIdentity(this.modelB)) changes.push('modelo');
    if (this.promptA.text !== this.promptB.text) changes.push('prompt');
    if (this.source === 'manual' && this.usesIndependentInputs() && JSON.stringify(this.pack(this.inputA)) !== JSON.stringify(this.pack(this.inputB))) changes.push('datos o referencias');
    return changes.length ? 'Cambia: ' + changes.join(' · ') : 'No cambian las variables configuradas entre A y B.';
  }
  dataset = signal<DatasetPreview | null>(null);
  datasetName = signal('');
  datasetBusy = signal(false);
  datasetError = signal('');

  async importDataset(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    const version = ++this.datasetVersion;
    this.dataset.set(null);
    this.datasetName.set('');
    this.datasetError.set('');
    this.datasetBusy.set(true);
    const endLoading = this.activity.begin();
    try {
      if (filenameError(file.name)) throw new Error(filenameError(file.name));
      if (!/\.(csv|jsonl)$/i.test(file.name)) throw new Error('Elige un dataset CSV o JSONL.');
      if (!file.size) throw new Error('El dataset está vacío.');
      if (file.size > 1024 * 1024) throw new Error('El dataset supera 1 MiB.');
      const content = new TextDecoder('utf-8', {fatal:true}).decode(await file.arrayBuffer());
      const result = await this.api.validateDataset(file.name, content);
      if (this.destroyed || version !== this.datasetVersion) return;
      this.dataset.set(result);
      this.datasetName.set(file.name);
    } catch (error) {
      if (this.destroyed || version !== this.datasetVersion) return;
      const detail = error instanceof HttpErrorResponse ? error.error?.detail : null;
      this.datasetError.set(file.name + ': ' + (typeof detail === 'string' ? detail : error instanceof HttpErrorResponse ? 'No se pudo validar el dataset. Comprueba la API y la estructura del archivo.' : error instanceof Error ? error.message : 'No se pudo leer el archivo UTF-8.'));
    } finally { endLoading(); if (!this.destroyed && version === this.datasetVersion) { this.datasetBusy.set(false); this.queueSave(); } input.value = ''; }
  }

  constructor() {
    const saved = this.auth.user()?.preferences;
    if (saved) {
      this.name = saved.name; this.adapter = saved.adapter; this.mode = saved.mode;
      this.source = saved.source; this.repetitions = saved.repetitions;
      this.independentInputs = saved.independentInputs ?? false;
      this.evaluation = saved.evaluation ?? 'exact_match'; this.settings = {...defaultSettings(), ...saved.settings};
      this.split = saved.split ?? 'dev';
      this.modelA = saved.modelA; this.modelB = saved.modelB;
      this.promptA = {...saved.promptA}; this.promptB = {...saved.promptB};
    }
    try {
      const raw = localStorage.getItem(this.draftKey);
      if (raw) {
        const draft = JSON.parse(raw);
        if (validDraft(draft, this.ownerId)) this.pendingDraft.set(draft);
        else this.draftNotice.set('El borrador guardado no es compatible. Puedes descartarlo.');
      }
    } catch { this.draftNotice.set('No se pudo leer el borrador local. Puedes descartarlo.'); }
    void this.loadTemplates();
    if (this.adapter === 'ollama') void this.loadModels();
    inject(DestroyRef).onDestroy(() => {
      this.destroyed = true;
      if (this.saveTimer) clearTimeout(this.saveTimer);
    });
  }

  private config(): Preferences {
    return {name:this.name, adapter:this.adapter, mode:this.mode, source:this.source,
      repetitions:this.repetitions, modelA:this.modelA, modelB:this.modelB,
      promptA:{...this.promptA}, promptB:{...this.promptB}, evaluation:this.evaluation, settings:{...this.settings}, split:this.split, independentInputs:this.independentInputs};
  }

  recoverDraft() {
    const draft = this.pendingDraft();
    if (!draft || draft.owner !== this.ownerId) return;
    ++this.datasetVersion;
    const config = draft.config;
    this.name = config.name; this.adapter = config.adapter; this.mode = config.mode; this.source = config.source;
    // Earlier drafts used independent manual inputs. Recover that choice without reinterpreting their data.
    this.independentInputs = config.independentInputs ?? true;
    this.repetitions = config.repetitions; this.modelA = config.modelA; this.modelB = config.modelB;
    this.promptA = {...config.promptA}; this.promptB = {...config.promptB};
    this.evaluation = config.evaluation ?? 'exact_match'; this.settings = {...defaultSettings(),...config.settings}; this.split = config.split ?? 'dev';
    for (const slot of ['inputA','inputB','shared'] as const) {
      this[slot] = {text:draft.inputs[slot].text, expected_answer:draft.inputs[slot].expected_answer, files:[]};
    }
    this.dataset.set(draft.dataset); this.datasetName.set(draft.datasetName);
    this.missingFiles.set(draft.missingFiles);
    this.submissionPending.set(draft.submissionPending === true);
    this.pendingDraft.set(null); this.datasetBusy.set(false); this.datasetError.set('');
    this.draftNotice.set('Borrador recuperado: texto, referencias, configuración y dataset normalizado.');
    if (this.adapter === 'ollama') void this.loadModels();
  }

  discardDraft() {
    try { localStorage.removeItem(this.draftKey); }
    catch { this.draftNotice.set('No se pudo descartar el borrador local.'); return; }
    ++this.datasetVersion;
    this.pendingDraft.set(null); this.missingFiles.set({});
    this.submissionPending.set(false);
    this.inputA = {text:'',files:[],expected_answer:''}; this.inputB = {text:'',files:[],expected_answer:''}; this.shared = {text:'',files:[],expected_answer:''};
    this.dataset.set(null); this.datasetName.set(''); this.datasetError.set(''); this.datasetBusy.set(false);
    this.error.set(''); this.invalidField.set('');
    this.draftNotice.set('Borrador descartado. Se mantienen las preferencias del formulario.');
  }

  missingAttachments() {
    return Object.entries(this.missingFiles()).flatMap(([slot,names]) => names.filter(name => !this[slot as 'inputA'|'inputB'|'shared'].files.some(file => file.name === name)).map(name => ({slot,name})));
  }
  omitAttachment(slot:string, name:string) {
    this.missingFiles.update(files => ({...files,[slot]:(files[slot] ?? []).filter(n => n !== name)})); this.queueSave();
  }
  private saveDraft() {
    if (this.destroyed || !this.ownerId || this.auth.user()?.id !== this.ownerId || this.pendingDraft()) return;
    const inputs = Object.fromEntries((['inputA','inputB','shared'] as const).map(slot => [slot,{text:this[slot].text,expected_answer:this[slot].expected_answer}]));
    const missingFiles = Object.fromEntries((['inputA','inputB','shared'] as const).map(slot => [slot,[...new Set([...(this.missingFiles()[slot] ?? []),...this[slot].files.map(f => f.name)])]]));
    try {
      localStorage.setItem(this.draftKey, JSON.stringify({version:1,owner:this.ownerId,config:this.config(),inputs,dataset:this.dataset(),datasetName:this.datasetName(),missingFiles,submissionPending:this.submissionPending()}));
      this.draftNotice.set('Borrador guardado en este navegador: texto, referencias, configuración y dataset normalizado. Los adjuntos requieren reselección tras recargar.');
    } catch { this.draftNotice.set('No se pudo guardar el borrador local. Conserva una copia antes de recargar.'); }
  }

  queueSave() {
    queueMicrotask(() => this.saveDraft());
    if (this.invalidField()) this.error.set('');
    this.invalidField.set('');
    if (this.saveTimer) clearTimeout(this.saveTimer);
    this.saveTimer = setTimeout(() => { this.saveTimer = undefined; void this.savePreferences(); }, 650);
  }
  setLatencyStudy(enabled:boolean) {
    if (enabled) {
      this.settings.warmup = 'per_run'; this.settings.order_policy = 'balanced';
      if (this.repetitions % 2) this.repetitions += 1;
    }
    this.queueSave();
  }

  private async savePreferences() {
    if (this.auth.user()?.id !== this.ownerId || this.modelsBusy()) return;
    if (!Number.isInteger(this.repetitions) || this.repetitions < 1 || this.repetitions > 10) {
      this.preferencesNotice.set('Revisa las repeticiones para guardar las preferencias.'); return;
    }
    const prefs = this.config();
    try { await this.auth.savePreferences(prefs); this.preferencesNotice.set('Preferencias guardadas en tu perfil.'); }
    catch { this.preferencesNotice.set('No se guardaron las preferencias. Vuelve a modificar un campo para reintentar.'); }
  }

  async loadTemplates() {
    try {
      this.templates.set(await this.api.prompts());
      if (this.destroyed) return;
      if (!this.promptA.text) this.setTemplate('A');
      if (!this.promptB.text) this.setTemplate('B');
      this.error.set('');
    } catch { this.error.set('No se pudieron cargar las plantillas. Comprueba la API y pulsa Reintentar plantillas.'); }
  }

  async loadModels() {
    if (this.modelsBusy()) return;
    this.modelsBusy.set(true);
    this.modelNotice.set('Consultando modelos instalados…');
    try {
      const result = await this.api.models();
      if (this.destroyed) return;
      this.models.set(result.models.map(model => model.name));
      if (this.adapter === 'ollama' && result.available) {
        if (!this.modelA) this.modelA = this.models()[0] ?? '';
        if (!this.modelB) this.syncModelB();
      }
      this.modelNotice.set(result.available ? (result.models.length ? `${result.models.length} modelos instalados.` : 'No hay modelos instalados. Instala uno en Ollama y actualiza la lista.') : 'Ollama no está disponible. Inícialo y actualiza la lista.');
    } catch {
      this.models.set([]);
      this.modelNotice.set('No se pudo consultar Ollama. Comprueba la conexión y actualiza la lista.');
    } finally { this.modelsBusy.set(false); }
  }

  availableModels() { return this.adapter === 'simulated' ? ['simulated-a', 'simulated-b'] : this.models(); }
  modelsForB() { return this.availableModels().filter(model => modelIdentity(model) !== modelIdentity(this.modelA)); }
  modelLabel(model: string) { return this.adapter === 'simulated' ? (model === 'simulated-a' ? 'Simulador A' : 'Simulador B') : model; }
  syncModelB() {
    if (!this.modelsForB().includes(this.modelB)) this.modelB = this.modelsForB()[0] ?? '';
  }
  changeAdapter() {
    this.modelA = this.adapter === 'simulated' ? 'simulated-a' : '';
    this.modelB = this.adapter === 'simulated' ? 'simulated-b' : '';
    if (this.adapter === 'ollama') void this.loadModels();
  }
  validModels() {
    return this.availableModels().includes(this.modelA) && (this.mode === 'same_model' || this.modelsForB().includes(this.modelB));
  }

  setTemplate(branch: 'A' | 'B') {
    const prompt = branch === 'A' ? this.promptA : this.promptB;
    if (prompt.template !== 'custom') prompt.text = this.templates().find(t => t.id === prompt.template)?.text ?? '';
  }

  private pack(input: InputData) {
    return {text: input.text, files:input.files.map(({name,data_base64}) => ({name,data_base64})),
      expected_answer:input.expected_answer.trim() ? input.expected_answer : null};
  }

  focusField(id: string) {
    const field = document.getElementById(id);
    for (let parent = field?.parentElement; parent; parent = parent.parentElement) {
      if (parent instanceof HTMLDetailsElement) parent.open = true;
    }
    field?.focus();
  }

  preparationIssues() {
    const issues: {id:string; message:string; group:string}[] = [];
    if (this.pendingDraft()) issues.push({id:'recover-draft',message:'Recupera o descarta el borrador antes de ejecutar.',group:'data'});
    const slots = this.source === 'dataset' ? [] : this.usesIndependentInputs() ? ['inputA','inputB'] : ['shared'];
    for (const file of this.missingAttachments().filter(f => slots.includes(f.slot)))
      issues.push({id:(file.slot === 'inputA' ? 'a' : file.slot === 'inputB' ? 'b' : 'shared')+'-files',message:'Reselecciona u omite '+file.name+'.',group:'data'});
    if (this.datasetBusy() || this.readingA || this.readingB || this.readingShared)
      issues.push({id:'data-source',message:'Espera a que termine la lectura o validación de los datos.',group:'data'});
    if (this.source === 'dataset' && !this.dataset()) issues.push({id:'dataset-file',message:this.datasetError() || 'Importa un dataset válido para continuar.',group:'data'});
    if (this.modelsBusy() || !this.validModels()) issues.push({id:'custom-adapter',message:this.modelsBusy() ? 'Consultando modelos instalados…' : 'Revisa el motor y selecciona modelos disponibles.',group:'variants'});
    if (!this.templates().length) issues.push({id:'retry-templates',message:'Carga las plantillas para continuar.',group:'variants'});
    const fields: [string, string, number, boolean][] = [
      ['comparison-name', this.name, 120, true], ['prompt-a', this.promptA.text, 6000, true], ['prompt-b', this.promptB.text, 6000, true],
      ...(this.source === 'manual' ? (this.usesIndependentInputs() ? [['a', this.inputA], ['b', this.inputB]] as const : [['shared', this.shared]] as const).flatMap(([slot, input]) => [
        [slot + '-input', input.text, 6000, true] as [string,string,number,boolean],
        [slot + '-reference', input.expected_answer, 6000, false] as [string,string,number,boolean],
      ]) : []),
    ];
    const labels: Record<string,string> = {'comparison-name':'Nombre', 'prompt-a':'Instrucciones A', 'prompt-b':'Instrucciones B',
      'a-input':'Entrada A', 'b-input':'Entrada B', 'shared-input':'Entrada compartida',
      'a-reference':'Respuesta esperada A', 'b-reference':'Respuesta esperada B', 'shared-reference':'Respuesta esperada'};
    for (const [id,value,max,required] of fields) {
      const message = textError(value, labels[id], max, required);
      if (message) issues.push({id,message,group:id.includes('prompt') ? 'variants' : id === 'comparison-name' ? 'conditions' : 'data'});
    }
    if (!Number.isInteger(this.repetitions) || this.repetitions < 1 || this.repetitions > 10)
      issues.push({id:'repetitions',message:'Elige entre 1 y 10 repeticiones.',group:'conditions'});
    const parameters: [string, number, number, number, boolean][] = [
      ['temperature',this.settings.temperature,0,2,false], ['seed',this.settings.seed,0,2147483647,true],
      ['context',this.settings.num_ctx,512,131072,true], ['output-limit',this.settings.max_output_tokens,1,16384,true],
      ['timeout',this.settings.timeout_s,1,3600,true],
    ];
    if (this.settings.latency_study) parameters.push(['planned-attempts',this.settings.planned_attempts,2,20,true]);
    const parameterLabels: Record<string,string> = {temperature:'Temperatura',seed:'Semilla',context:'Contexto','output-limit':'Máximo de salida',timeout:'Tiempo límite','planned-attempts':'Intentos previstos'};
    for (const [id,n,min,max,integer] of parameters) {
      if (!Number.isFinite(n) || n < min || n > max || integer && !Number.isInteger(n))
        issues.push({id,message:parameterLabels[id]+': revisa el valor y los límites indicados.',group:'conditions'});
    }
    if (this.evaluation === 'json_match') {
      const references = this.source === 'dataset' ? (this.dataset()?.cases ?? []).map(c => ({id:'dataset-file',value:c.expected_answer})) :
        (this.usesIndependentInputs() ? [{id:'a-reference',value:this.inputA.expected_answer},{id:'b-reference',value:this.inputB.expected_answer}] : [{id:'shared-reference',value:this.shared.expected_answer}]);
      for (const ref of references) {
        try { if (ref.value?.trim()) JSON.parse(ref.value); }
        catch { issues.push({id:ref.id,message:'Para evaluar JSON, las respuestas esperadas deben contener JSON válido.',group:'data'}); }
      }
    }
    if (this.settings.max_output_tokens >= this.settings.num_ctx)
      issues.push({id:'output-limit',message:'El máximo de salida debe ser menor que el contexto para dejar espacio a la entrada.',group:'conditions'});
    if (this.settings.order_policy === 'balanced' && this.repetitions % 2)
      issues.push({id:'repetitions',message:'El orden equilibrado exige repeticiones pares.',group:'conditions'});
    if (this.settings.latency_study && (this.source !== 'dataset' || this.evaluation === 'none' || this.dataset()?.cases.some(c=>c.expected_answer == null)))
      issues.push({id:'data-source',message:'Para estudiar tiempos importa un dataset compartido con referencia en todos los casos y activa su evaluación.',group:'conditions'});
    return issues;
  }
  ready(group:string, issues = this.preparationIssues()) { return !issues.some(issue => issue.group === group); }
  plannedRuns() { return Number.isInteger(this.repetitions) && this.repetitions > 0 && this.repetitions <= 10 ? (this.source === 'dataset' ? this.dataset()?.count ?? 0 : 1) * this.repetitions * 2 : null; }

  async submit() {
    if (this.busy()) return;
    const issue = this.preparationIssues()[0];
    if (issue) { this.invalidField.set(issue.id); this.error.set(issue.message); this.focusField(issue.id); return; }
    this.busy.set(true);
    this.invalidField.set('');
    this.error.set('');
    const body: ComparisonBody = {
      name:this.name, adapter:this.adapter, comparison:this.mode, repetitions:this.repetitions,
      evaluation:this.evaluation, settings:{...this.settings}, split:this.split,
      agents:{
        A:{model:this.modelA.trim(), system_prompt:this.promptA.text, prompt_template:this.promptA.template},
        B:{model:(this.mode === 'same_model' ? this.modelA : this.modelB).trim(), system_prompt:this.promptB.text, prompt_template:this.promptB.template},
      },
      ...(this.source === 'dataset' ? {dataset:this.dataset()!.cases} : this.usesIndependentInputs() ? {branch_inputs:{A:this.pack(this.inputA), B:this.pack(this.inputB)}} : {shared_input:this.pack(this.shared)}),
    };
    this.submissionPending.set(true); this.saveDraft();
    try {
      const result = await this.api.compare(body);
      if (!this.destroyed && this.auth.user()?.id === this.ownerId) {
        this.submissionPending.set(false); this.saveDraft(); this.created.emit(result.id);
      }
    }
    catch (error) {
      const detail = error instanceof HttpErrorResponse ? error.error?.detail : null;
      this.error.set(typeof detail === 'string' ? detail : Array.isArray(detail) ? 'Hay datos no válidos. Revisa los campos, los formatos de archivo y los límites indicados.' :
        'No se pudo confirmar la creación. Revisa la conexión y actualiza el historial antes de repetir.');
    } finally { this.busy.set(false); }
  }
}
