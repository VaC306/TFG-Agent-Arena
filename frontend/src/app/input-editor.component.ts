import { Component, Input, Output, EventEmitter, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { InputData, Upload } from './arena.service';

@Component({
  selector: 'arena-input-editor', standalone: true, imports: [FormsModule],
  template: `
    <label [for]="slot + '-input'">{{ title }}</label>
    <textarea [id]="slot + '-input'" [(ngModel)]="value.text" [ngModelOptions]="{standalone: true}"
      rows="4" maxlength="6000" placeholder="¿Qué quieres que haga el modelo con esta entrada y sus archivos?" required></textarea>
    <div class="upload-zone">
      <label [for]="slot + '-files'">Adjuntar archivos <span>TXT · JSON · CSV · PNG · JPG · WebP</span></label>
      <input [id]="slot + '-files'" type="file" multiple accept=".txt,.json,.csv,.png,.jpg,.jpeg,.webp"
        [disabled]="reading()" (change)="addFiles($event)">
      <p class="hint">Hasta 4 archivos, 1 MiB cada uno. Texto UTF-8; máximo conjunto: 20.000 caracteres.</p>
    </div>
    @if (reading()) { <p role="status" class="hint">Preparando vista previa…</p> }
    @if (error()) { <p class="alert error" role="alert">{{ error() }}</p> }
    <div class="file-list">
      @for (file of value.files; track file.name) {
        <details class="file-preview">
          <summary>{{ file.name }} <span>{{ (file.size / 1024).toFixed(1) }} KiB</span></summary>
          @if (file.image) { <img [src]="file.preview" [alt]="'Vista previa de ' + file.name"> }
          @else { <pre>{{ file.preview }}</pre> }
          <button type="button" class="text-button danger" (click)="remove(file.name)">Quitar {{ file.name }}</button>
        </details>
      }
    </div>
    <details class="reference-input"><summary>Respuesta esperada (opcional)</summary>
      <textarea [attr.aria-label]="'Respuesta esperada ' + title" [(ngModel)]="value.expected_answer" [ngModelOptions]="{standalone: true}"
        rows="2" maxlength="6000" placeholder="Sin referencia, la calidad aparecerá como no evaluada."></textarea>
      <p class="hint">Evalúa coincidencia exacta del texto, ignorando espacios al principio y al final. No es un juez de calidad semántica.</p>
    </details>
  `,
})
export class InputEditorComponent {
  @Input({required:true}) value!: InputData;
  @Input({required:true}) slot!: string;
  @Input() title = 'Entrada';
  @Output() readingChange = new EventEmitter<boolean>();
  reading = signal(false);
  error = signal('');

  async addFiles(event: Event) {
    const input = event.target as HTMLInputElement;
    const files = Array.from(input.files ?? []);
    this.error.set('');
    this.reading.set(true);
    this.readingChange.emit(true);
    try {
      if (files.length + this.value.files.length > 4) throw new Error('Puedes adjuntar un máximo de 4 archivos por entrada.');
      const prepared: Upload[] = [];
      for (const file of files) {
        const extension = file.name.split('.').pop()?.toLowerCase() ?? '';
        if (!['txt','json','csv','png','jpg','jpeg','webp'].includes(extension)) throw new Error('Formato no admitido: ' + file.name);
        if (!file.size || file.size > 1024 * 1024) throw new Error(file.name + ': el tamaño debe estar entre 1 byte y 1 MiB.');
        if ([...this.value.files, ...prepared].some(f => f.name === file.name)) throw new Error('Nombre duplicado: ' + file.name);
        const image = ['png','jpg','jpeg','webp'].includes(extension);
        const dataUrl = await new Promise<string>((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(String(reader.result));
          reader.onerror = () => reject(new Error('No se pudo leer ' + file.name));
          reader.readAsDataURL(file);
        });
        const data_base64 = dataUrl.slice(dataUrl.indexOf(',') + 1);
        let preview: string;
        if (image) {
          const mime = extension === 'jpg' || extension === 'jpeg' ? 'jpeg' : extension;
          preview = 'data:image/' + mime + ';base64,' + data_base64;
        } else {
          preview = new TextDecoder('utf-8', {fatal:true}).decode(await file.arrayBuffer());
          if (preview.length > 20000) throw new Error(file.name + ': supera los 20.000 caracteres.');
          if (extension === 'json') JSON.parse(preview);
        }
        prepared.push({name:file.name, data_base64, preview, image, size:file.size});
      }
      if ([...this.value.files, ...prepared].filter(f => !f.image).reduce((n,f) => n + f.preview.length,0) > 20000) {
        throw new Error('El texto de todos los adjuntos supera 20.000 caracteres.');
      }
      this.value.files = [...this.value.files, ...prepared];
    } catch (error) { this.error.set(error instanceof Error ? error.message : 'No se pudieron preparar los adjuntos.'); }
    finally { input.value = ''; this.reading.set(false); this.readingChange.emit(false); }
  }

  remove(name: string) { this.value.files = this.value.files.filter(file => file.name !== name); }
}
