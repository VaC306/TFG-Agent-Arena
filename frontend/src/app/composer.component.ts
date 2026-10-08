import { Component, EventEmitter, inject, Output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { ArenaService, ComparisonBody, InputData, PresetId, PromptTemplate } from './arena.service';
import { InputEditorComponent } from './input-editor.component';

@Component({
  selector: 'arena-composer', standalone: true, imports: [FormsModule, InputEditorComponent],
  templateUrl: './composer.component.html',
})
export class ComposerComponent {
  private api = inject(ArenaService);
  @Output() created = new EventEmitter<string>();
  mode: 'same_model' | 'different_models' = 'same_model';
  adapter: PresetId = 'simulated';
  name = 'Comparación personalizada';
  repetitions = 1;
  modelA = 'qwen2.5:3b';
  modelB = 'llama3.2:3b';
  promptA = {template:'general',text:''};
  promptB = {template:'analyst',text:''};
  inputA: InputData = {text:'',files:[],expected_answer:''};
  inputB: InputData = {text:'',files:[],expected_answer:''};
  shared: InputData = {text:'',files:[],expected_answer:''};
  templates = signal<PromptTemplate[]>([]);
  models = signal<string[]>([]);
  modelNotice = signal('');
  error = signal('');
  busy = signal(false);
  readingA = false;
  readingB = false;
  readingShared = false;

  constructor() { void this.loadTemplates(); }

  async loadTemplates() {
    try {
      this.templates.set(await this.api.prompts());
      if (!this.promptA.text) this.setTemplate('A');
      if (!this.promptB.text) this.setTemplate('B');
      this.error.set('');
    } catch { this.error.set('No se pudieron cargar las plantillas. Comprueba la API y pulsa Reintentar plantillas.'); }
  }

  async loadModels() {
    this.modelNotice.set('Consultando modelos instalados…');
    try {
      const result = await this.api.models();
      this.models.set(result.models.map(model => model.name));
      this.modelNotice.set(result.error ?? (result.models.length ? 'Modelos instalados disponibles en las sugerencias.' : 'Ollama no tiene modelos instalados.'));
    } catch { this.modelNotice.set('No se pudo consultar Ollama. Puedes escribir el nombre manualmente.'); }
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
    if (this.busy() || this.readingA || this.readingB || this.readingShared) return;
    this.busy.set(true);
    this.error.set('');
    const body: ComparisonBody = {
      name:this.name, adapter:this.adapter, comparison:this.mode, repetitions:this.repetitions,
      agents:{
        A:{model:this.modelA.trim(), system_prompt:this.promptA.text, prompt_template:this.promptA.template},
        B:{model:(this.mode === 'same_model' ? this.modelA : this.modelB).trim(), system_prompt:this.promptB.text, prompt_template:this.promptB.template},
      },
      ...(this.mode === 'same_model' ? {branch_inputs:{A:this.pack(this.inputA), B:this.pack(this.inputB)}} : {shared_input:this.pack(this.shared)}),
    };
    try { this.created.emit((await this.api.compare(body)).id); }
    catch (error) {
      const detail = error instanceof HttpErrorResponse ? error.error?.detail : null;
      this.error.set(typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map(d => `${d.loc?.slice(0,4).join(' / ')}: ${d.msg}`).join('\n') :
        'No se pudo confirmar la creación. Revisa la conexión y actualiza el historial antes de repetir.');
    } finally { this.busy.set(false); }
  }
}
