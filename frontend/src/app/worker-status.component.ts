import { Component, DestroyRef, inject, Input, signal } from '@angular/core';
import { ArenaService, WorkerStatus } from './arena.service';

@Component({selector:'arena-worker-status',standalone:true,template:`
  <div class="worker-status-compact">
    <p class="hint" role="status">{{ error() || (state() ? state()!.state === 'active' ? 'Worker disponible · ' + state()!.queued + ' en cola · ' + state()!.running + ' en ejecución' : 'Sin señal reciente del worker. Las ejecuciones pueden quedar en cola.' : 'Comprobando worker…') }}</p>
    <button type="button" class="text-button" (click)="refresh()" [disabled]="busy">Comprobar worker</button>
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
