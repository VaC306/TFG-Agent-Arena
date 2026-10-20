import { TermHelpComponent } from './term-help.component';
import { Component, DestroyRef, Input, Output, EventEmitter, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { InputData, Upload } from './arena.service';
import { textError, filenameError, csvError } from './validation';
import { LoadingIndicatorComponent } from './loading-indicator.component';
import { LoadingService } from './loading.service';

@Component({
  selector: 'arena-input-editor', standalone: true, imports: [TermHelpComponent,FormsModule,LoadingIndicatorComponent],
  template: `
    <label [for]="slot + '-input'">{{ title }}</label>
    <textarea [id]="slot + '-input'" [(ngModel)]="value.text" [ngModelOptions]="{standalone: true}"
      [attr.aria-invalid]="invalid ? 'true' : null" [attr.aria-describedby]="invalid ? 'composer-error' : null"
      rows="4" maxlength="6000" placeholder="¿Qué quieres que haga el modelo con esta entrada y sus archivos?" required></textarea>
    @if (attachmentsEnabled) { <details class="upload-zone"><summary>Adjuntos (opcional) · {{ value.files.length }} archivos</summary>
      <label [for]="slot + '-files'">Adjuntar archivos <span>TXT · JSON · CSV · PNG · JPG · WebP</span></label>
      <input [id]="slot + '-files'" type="file" multiple accept=".txt,.json,.csv,.png,.jpg,.jpeg,.webp"
        [attr.aria-describedby]="slot + '-file-help'" [disabled]="reading()" (change)="addFiles($event)">
      <p class="hint" [id]="slot + '-file-help'">Hasta 4 archivos, 1 MiB cada uno. Texto UTF-8; máximo conjunto: 20.000 caracteres.</p>
    </details> }
    @if (reading()) { <arena-loading label="Preparando vista previa…" /> }
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
    <arena-term-help term="reference" /><details class="reference-input"><summary>Respuesta esperada (opcional)</summary>
      <textarea [id]="slot + '-reference'" [attr.aria-invalid]="invalidReference ? 'true' : null" [attr.aria-describedby]="invalidReference ? 'composer-error' : null" [attr.aria-label]="'Respuesta esperada ' + title" [(ngModel)]="value.expected_answer" [ngModelOptions]="{standalone: true}"
        rows="2" maxlength="6000" placeholder="Sin referencia, la calidad aparecerá como no evaluada."></textarea>
      <p class="hint">Se usa con la evaluación de Condiciones de ejecución. La referencia no se envía al modelo. Para JSON equivalente, escribe JSON válido.</p>
    </details>
  `,
})
export class InputEditorComponent {
  private activity = inject(LoadingService);
  private destroyed = false;
  private endReading?: () => void;
  constructor() {
    inject(DestroyRef).onDestroy(() => {
      this.destroyed = true;
      this.endReading?.();
      this.readingChange.emit(false);
    });
  }
  @Input({required:true}) value!: InputData;
  @Input({required:true}) slot!: string;
  @Input() title = 'Entrada';
  @Input() attachmentsEnabled = true;
  @Input() invalid = false;
  @Input() invalidReference = false;
  @Output() readingChange = new EventEmitter<boolean>();
  @Output() changed = new EventEmitter<void>();
  reading = signal(false);
  error = signal('');

  async addFiles(event: Event) {
    const input = event.target as HTMLInputElement;
    const value = this.value;
    const files = Array.from(input.files ?? []);
    this.error.set('');
    this.reading.set(true);
    this.readingChange.emit(true);
    const endLoading = this.activity.begin();
    this.endReading = endLoading;
    try {
      if (files.length + this.value.files.length > 4) throw new Error('Puedes adjuntar un máximo de 4 archivos por entrada.');
      const prepared: Upload[] = [];
      for (const file of files) {
        if (filenameError(file.name)) throw new Error(filenameError(file.name));
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
          const bytes = new Uint8Array(await file.arrayBuffer());
          const signature = extension === 'png' ? bytes.slice(0,8).join(',') === '137,80,78,71,13,10,26,10'
            : extension === 'webp' ? String.fromCharCode(...bytes.slice(0,4)) === 'RIFF' && String.fromCharCode(...bytes.slice(8,12)) === 'WEBP'
            : bytes[0] === 255 && bytes[1] === 216 && bytes[2] === 255;
          if (!signature) throw new Error(file.name + ': el contenido no coincide con el formato de imagen.');
          const mime = extension === 'jpg' || extension === 'jpeg' ? 'jpeg' : extension;
          preview = 'data:image/' + mime + ';base64,' + data_base64;
          await new Promise<void>((resolve, reject) => {
            const decoded = new Image();
            decoded.onload = () => decoded.naturalWidth * decoded.naturalHeight > 10000000
              ? reject(new Error(file.name + ': máximo 10 megapíxeles.')) : resolve();
            decoded.onerror = () => reject(new Error(file.name + ': imagen dañada o no válida.'));
            decoded.src = preview;
          });
        } else {
          preview = new TextDecoder('utf-8', {fatal:true}).decode(await file.arrayBuffer());
          if (textError(preview, file.name, 20000, false)) throw new Error(textError(preview, file.name, 20000, false));
          if (extension === 'json') { try { JSON.parse(preview); } catch { throw new Error(file.name + ': JSON inválido.'); } }
          if (extension === 'csv' && csvError(preview)) throw new Error(file.name + ': ' + csvError(preview));
        }
        prepared.push({name:file.name, data_base64, preview, image, size:file.size});
      }
      if ([...this.value.files, ...prepared].filter(f => !f.image).reduce((n,f) => n + [...f.preview].length,0) > 20000) {
        throw new Error('El texto de todos los adjuntos supera 20.000 caracteres.');
      }
      if (!this.destroyed && this.value === value) { this.value.files = [...this.value.files, ...prepared]; this.changed.emit(); }
    } catch (error) { this.error.set(error instanceof TypeError ? 'No se pudo leer el archivo. Los textos deben usar UTF-8.' : error instanceof Error ? error.message : 'No se pudieron preparar los adjuntos.'); }
    finally { endLoading(); this.endReading = undefined; input.value = ''; this.reading.set(false); if (!this.destroyed) this.readingChange.emit(false); }
  }

  remove(name: string) { this.value.files = this.value.files.filter(file => file.name !== name); this.changed.emit(); }
}
