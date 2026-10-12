import { Component, DestroyRef, EventEmitter, inject, Output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { ArenaService, ComparisonBody, DatasetPreview, InputData, PresetId, PromptTemplate, EvaluationMode, defaultSettings } from './arena.service';
import { InputEditorComponent } from './input-editor.component';
import { InfoDialogComponent } from './info-dialog.component';
import { AuthService, Preferences } from './auth.service';
import { textError, filenameError, modelIdentity } from './validation';
import { LoadingIndicatorComponent } from './loading-indicator.component';
import { LoadingService } from './loading.service';

@Component({
  selector: 'arena-composer', standalone: true, imports: [FormsModule, InputEditorComponent, InfoDialogComponent,LoadingIndicatorComponent],
  templateUrl: './composer.component.html',
})
export class ComposerComponent {
  private api = inject(ArenaService);
  private auth = inject(AuthService);
  private activity = inject(LoadingService);
  private saveTimer?: ReturnType<typeof setTimeout>;
  private ownerId = this.auth.user()?.id;
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
  dataset = signal<DatasetPreview | null>(null);
  datasetName = signal('');
  datasetBusy = signal(false);
  datasetError = signal('');

  async importDataset(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
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
      this.dataset.set(result);
      this.datasetName.set(file.name);
    } catch (error) {
      const detail = error instanceof HttpErrorResponse ? error.error?.detail : null;
      this.datasetError.set(typeof detail === 'string' ? detail : error instanceof HttpErrorResponse ? 'No se pudo validar el dataset. Comprueba la API y la estructura del archivo.' : error instanceof Error ? error.message : 'No se pudo leer el archivo UTF-8.');
    } finally { endLoading(); this.datasetBusy.set(false); input.value = ''; }
  }

  constructor() {
    const saved = this.auth.user()?.preferences;
    if (saved) {
      this.name = saved.name; this.adapter = saved.adapter; this.mode = saved.mode;
      this.source = saved.source; this.repetitions = saved.repetitions;
      this.evaluation = saved.evaluation ?? 'exact_match'; this.settings = {...defaultSettings(), ...saved.settings};
      this.split = saved.split ?? 'dev';
      this.modelA = saved.modelA; this.modelB = saved.modelB;
      this.promptA = {...saved.promptA}; this.promptB = {...saved.promptB};
    }
    void this.loadTemplates();
    if (this.adapter === 'ollama') void this.loadModels();
    inject(DestroyRef).onDestroy(() => {
      if (this.saveTimer) { clearTimeout(this.saveTimer); void this.savePreferences(); }
    });
  }

  queueSave() {
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
    const prefs: Preferences = {name:this.name, adapter:this.adapter, mode:this.mode, source:this.source,
      repetitions:this.repetitions, modelA:this.modelA, modelB:this.modelB,
      promptA:{...this.promptA}, promptB:{...this.promptB}, evaluation:this.evaluation, settings:{...this.settings}, split:this.split};
    try { await this.auth.savePreferences(prefs); this.preferencesNotice.set('Preferencias guardadas en tu perfil.'); }
    catch { this.preferencesNotice.set('No se guardaron las preferencias. Vuelve a modificar un campo para reintentar.'); }
  }

  async loadTemplates() {
    try {
      this.templates.set(await this.api.prompts());
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
      this.models.set(result.models.map(model => model.name));
      if (this.adapter === 'ollama' && result.available) {
        if (!this.models().includes(this.modelA)) this.modelA = this.models()[0] ?? '';
        this.syncModelB();
      }
      this.modelNotice.set(result.available ? (result.models.length ? `${result.models.length} modelos instalados.` : 'No hay modelos instalados. Instala uno en Ollama y actualiza la lista.') : 'Ollama no está disponible. Inícialo y actualiza la lista.');
    } catch {
      this.models.set([]);
      this.modelNotice.set('No se pudo consultar Ollama. Comprueba la conexión y actualiza la lista.');
    } finally { this.modelsBusy.set(false); this.queueSave(); }
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

  async submit() {
    if (this.busy() || this.modelsBusy() || !this.validModels() || this.datasetBusy() || this.readingA || this.readingB || this.readingShared || (this.source === 'dataset' && !this.dataset())) return;
    const fields: [string, string, number, boolean][] = [
      ['comparison-name', this.name, 120, true], ['prompt-a', this.promptA.text, 6000, true], ['prompt-b', this.promptB.text, 6000, true],
      ...(this.source === 'manual' ? (this.mode === 'same_model' ? [['a', this.inputA], ['b', this.inputB]] as const : [['shared', this.shared]] as const).flatMap(([slot, input]) => [
        [slot + '-input', input.text, 6000, true] as [string,string,number,boolean],
        [slot + '-reference', input.expected_answer, 6000, false] as [string,string,number,boolean],
      ]) : []),
    ];
    const badText = fields.find(([, value, max, required]) => textError(value, 'Campo', max, required));
    const labels: Record<string,string> = {'comparison-name':'Nombre', 'prompt-a':'Instrucciones A', 'prompt-b':'Instrucciones B',
      'a-input':'Entrada A', 'b-input':'Entrada B', 'shared-input':'Entrada compartida',
      'a-reference':'Respuesta esperada A', 'b-reference':'Respuesta esperada B', 'shared-reference':'Respuesta esperada'};
    const invalid = badText ? [badText[0], textError(badText[1], labels[badText[0]], badText[2], badText[3])]
      : !Number.isInteger(this.repetitions) || this.repetitions < 1 || this.repetitions > 10 ? ['repetitions', 'Elige entre 1 y 10 repeticiones.']
      : null;
    if (invalid) {
      this.invalidField.set(invalid[0]);
      this.error.set(invalid[1]);
      const field = document.getElementById(invalid[0]);
      const details = field?.closest('details');
      if (details) details.open = true;
      field?.focus();
      return;
    }
    const parameters: [string, number, number, number, boolean][] = [
      ['temperature',this.settings.temperature,0,2,false], ['seed',this.settings.seed,0,2147483647,true],
      ['context',this.settings.num_ctx,512,131072,true], ['output-limit',this.settings.max_output_tokens,1,16384,true],
      ['timeout',this.settings.timeout_s,1,3600,true],
    ];
    if (this.settings.latency_study) parameters.push(['planned-attempts',this.settings.planned_attempts,2,20,true]);
    const badParameter = parameters.find(([,n,min,max,integer]) => !Number.isFinite(n) || n < min || n > max || integer && !Number.isInteger(n));
    if (badParameter) {
      this.invalidField.set(badParameter[0]); this.error.set('Revisa este parámetro y los límites indicados.');
      const field = document.getElementById(badParameter[0]); const details = field?.closest('details'); if (details) details.open = true; field?.focus(); return;
    }
    if (this.evaluation === 'json_match') {
      const references = this.source === 'dataset' ? this.dataset()!.cases.map(c => c.expected_answer) :
        (this.mode === 'same_model' ? [this.inputA, this.inputB] : [this.shared]).map(i => i.expected_answer);
      try { references.filter(r => r?.trim()).forEach(r => JSON.parse(r!)); }
      catch { this.error.set('Para evaluar JSON, las respuestas esperadas deben contener JSON válido.'); return; }
    }
    if (this.settings.max_output_tokens >= this.settings.num_ctx) {
      this.invalidField.set('output-limit'); this.error.set('El máximo de salida debe ser menor que el contexto para dejar espacio a la entrada.');
      const field = document.getElementById('output-limit'); const details = field?.closest('details'); if (details) details.open = true; field?.focus(); return;
    }
    if (this.settings.order_policy === 'balanced' && this.repetitions % 2 || this.settings.latency_study &&
        (this.source !== 'dataset' || this.evaluation === 'none' || this.dataset()!.cases.some(c=>c.expected_answer == null))) {
      this.error.set('El orden equilibrado exige repeticiones pares. Para estudiar tiempos importa un dataset compartido con referencia en todos los casos.');
      const id = this.settings.order_policy === 'balanced' && this.repetitions % 2 ? 'repetitions' : 'data-source';
      this.invalidField.set(id);
      const field = document.getElementById(id); const details = field?.closest('details');if (details) details.open = true;field?.focus();return;
    }
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
      ...(this.source === 'dataset' ? {dataset:this.dataset()!.cases} : this.mode === 'same_model' ? {branch_inputs:{A:this.pack(this.inputA), B:this.pack(this.inputB)}} : {shared_input:this.pack(this.shared)}),
    };
    try { this.created.emit((await this.api.compare(body)).id); }
    catch (error) {
      const detail = error instanceof HttpErrorResponse ? error.error?.detail : null;
      this.error.set(typeof detail === 'string' ? detail : Array.isArray(detail) ? 'Hay datos no válidos. Revisa los campos, los formatos de archivo y los límites indicados.' :
        'No se pudo confirmar la creación. Revisa la conexión y actualiza el historial antes de repetir.');
    } finally { this.busy.set(false); }
  }
}
