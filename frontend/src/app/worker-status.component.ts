import { Component, DestroyRef, inject, Input, signal } from '@angular/core';
import { ArenaService, WorkerStatus } from './arena.service';
import { FormsModule } from '@angular/forms';

@Component({selector:'arena-worker-status',standalone:true,imports:[FormsModule],template:`
  <div class="worker-status-compact">
    <p class="hint" role="status">{{ error() || (state() ? state()!.state === 'active' ? 'Worker disponible · Cola de tu cuenta: ' + state()!.queued + ' en cola · ' + state()!.running + ' en ejecución' : 'Sin señal reciente del worker. Las ejecuciones pueden quedar en cola.' : 'Comprobando worker…') }}</p>
    <button type="button" class="text-button" (click)="refresh()" [disabled]="busy">Comprobar worker</button>
    @if (state()?.running && state()?.state !== 'active') {
      <details><summary>Recuperar ejecuciones abandonadas</summary><p class="hint">Detén todos los workers antes de recuperar y espera 60 segundos desde la última señal. Se marcarán como interrumpidas las ejecuciones activas de tu cuenta; las trazas se conservan. Después puedes reiniciar el worker.</p>
      <label><input type="checkbox" [(ngModel)]="workersStopped" [ngModelOptions]="{standalone:true}"> He detenido todos los workers de esta base.</label>
      <button type="button" class="secondary" (click)="recover()" [disabled]="busy || !workersStopped">Recuperar ejecuciones de mi cuenta</button></details>
    }
    @if (notice()) { <p class="hint" role="status">{{ notice() }}</p> }
    <details><summary>Qué indica esta señal</summary><p class="hint">Corresponde a esta base de datos y a la cola de tu cuenta. No garantiza que Ollama responda. Si no hay señal reciente, revisa la terminal del worker; no se recuperan ejecuciones automáticamente.</p></details>
  </div>
`})
export class WorkerStatusComponent {
  @Input() active = true;
  private api = inject(ArenaService);
  private destroyed = false;
  state = signal<WorkerStatus|null>(null);
  error = signal('');
  busy = false;
  workersStopped = false;
  notice = signal('');
  async recover() {
    if (this.busy || !this.workersStopped) return;
    this.busy = true; this.notice.set('');
    try { const result = await this.api.recoverWorker(); if (!this.destroyed) this.notice.set(result.recovered+' ejecuciones marcadas como interrumpidas.'); }
    catch (error) { if (!this.destroyed) this.notice.set((error as {error?:{detail?:string}}).error?.detail || 'No se pudo recuperar. Comprueba que todos los workers estén detenidos.'); }
    finally { this.busy = false; this.workersStopped = false; if (!this.destroyed) void this.refresh(); }
  }
  constructor() {
    const timer = setInterval(() => { if (this.active) void this.refresh(); },2500);
    inject(DestroyRef).onDestroy(() => { this.destroyed = true; clearInterval(timer); });
  }
  ngOnInit() { if (this.active) void this.refresh(); }
  async refresh() {
    if (this.busy || this.destroyed || !this.active) return;
    this.busy = true;
    try {
      const state = await this.api.workerStatus();
      if (!this.destroyed) { this.state.set(state); this.error.set(''); }
    } catch { if (!this.destroyed) { this.state.set(null); this.error.set('No se pudo comprobar el worker. Reintenta la conexión.'); } }
    finally { this.busy = false; }
  }
}
