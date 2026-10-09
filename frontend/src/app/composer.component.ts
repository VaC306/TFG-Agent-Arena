import { Component, DestroyRef, EventEmitter, inject, Output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { ArenaService, ComparisonBody, DatasetPreview, InputData, PresetId, PromptTemplate } from './arena.service';
import { InputEditorComponent } from './input-editor.component';
import { AuthService, Preferences } from './auth.service';

@Component({
  selector: 'arena-composer', standalone: true, imports: [FormsModule, InputEditorComponent],
  templateUrl: './composer.component.html',
})
export class ComposerComponent {
  private api = inject(ArenaService);
  private auth = inject(AuthService);
  private saveTimer?: ReturnType<typeof setTimeout>;
  private ownerId = this.auth.user()?.id;
  preferencesNotice = signal('');
  @Output() created = new EventEmitter<string>();
  mode: 'same_model' | 'different_models' = 'same_model';
  adapter: PresetId = 'simulated';
  name = 'Comparación personalizada';
  repetitions = 1;
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
    try {
      if (file.size > 1024 * 1024) throw new Error('El dataset supera 1 MiB.');
      const content = new TextDecoder('utf-8', {fatal:true}).decode(await file.arrayBuffer());
      const result = await this.api.validateDataset(file.name, content);
      this.dataset.set(result);
      this.datasetName.set(file.name);
    } catch (error) {
      const detail = error instanceof HttpErrorResponse ? error.error?.detail : null;
      this.datasetError.set(typeof detail === 'string' ? detail : error instanceof HttpErrorResponse ? 'No se pudo validar el dataset. Comprueba la API y la estructura del archivo.' : error instanceof Error ? error.message : 'No se pudo leer el archivo UTF-8.');
    } finally { this.datasetBusy.set(false); input.value = ''; }
  }

  constructor() {
    const saved = this.auth.user()?.preferences;
    if (saved) {
      this.name = saved.name; this.adapter = saved.adapter; this.mode = saved.mode;
      this.source = saved.source; this.repetitions = saved.repetitions;
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
    if (this.saveTimer) clearTimeout(this.saveTimer);
    this.preferencesNotice.set('Guardando preferencias…');
    this.saveTimer = setTimeout(() => { this.saveTimer = undefined; void this.savePreferences(); }, 650);
  }

  private async savePreferences() {
    if (this.auth.user()?.id !== this.ownerId || this.modelsBusy()) return;
    if (!Number.isInteger(this.repetitions) || this.repetitions < 1 || this.repetitions > 10) {
      this.preferencesNotice.set('Revisa las repeticiones para guardar las preferencias.'); return;
    }
    const prefs: Preferences = {name:this.name, adapter:this.adapter, mode:this.mode, source:this.source,
      repetitions:this.repetitions, modelA:this.modelA, modelB:this.modelB,
      promptA:{...this.promptA}, promptB:{...this.promptB}};
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
      if (this.adapter === 'ollama') {
        if (!this.models().includes(this.modelA)) this.modelA = this.models()[0] ?? '';
        this.syncModelB();
      }
      this.modelNotice.set(result.available ? (result.models.length ? `${result.models.length} modelos instalados.` : 'No hay modelos instalados. Instala uno en Ollama y actualiza la lista.') : 'Ollama no está disponible. Inícialo y actualiza la lista.');
    } catch {
      this.models.set([]);
      if (this.adapter === 'ollama') { this.modelA = ''; this.modelB = ''; }
      this.modelNotice.set('No se pudo consultar Ollama. Comprueba la conexión y actualiza la lista.');
    } finally { this.modelsBusy.set(false); }
  }

  availableModels() { return this.adapter === 'simulated' ? ['simulated-a', 'simulated-b'] : this.models(); }
  modelsForB() { return this.availableModels().filter(model => model !== this.modelA); }
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
    this.busy.set(true);
    this.error.set('');
    const body: ComparisonBody = {
      name:this.name, adapter:this.adapter, comparison:this.mode, repetitions:this.repetitions,
      agents:{
        A:{model:this.modelA.trim(), system_prompt:this.promptA.text, prompt_template:this.promptA.template},
        B:{model:(this.mode === 'same_model' ? this.modelA : this.modelB).trim(), system_prompt:this.promptB.text, prompt_template:this.promptB.template},
      },
      ...(this.source === 'dataset' ? {dataset:this.dataset()!.cases} : this.mode === 'same_model' ? {branch_inputs:{A:this.pack(this.inputA), B:this.pack(this.inputB)}} : {shared_input:this.pack(this.shared)}),
    };
    try { this.created.emit((await this.api.compare(body)).id); }
    catch (error) {
      const detail = error instanceof HttpErrorResponse ? error.error?.detail : null;
      this.error.set(typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map(d => `${d.loc?.slice(0,4).join(' / ')}: ${d.msg}`).join('\n') :
        'No se pudo confirmar la creación. Revisa la conexión y actualiza el historial antes de repetir.');
    } finally { this.busy.set(false); }
  }
}
