import { Component, computed, DestroyRef, inject, input, output, signal } from '@angular/core';
import { DatePipe, DecimalPipe, JsonPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ArenaService, CampaignDetail, CampaignSummary } from './arena.service';
import { accountError } from './auth.service';
import { LoadingIndicatorComponent } from './loading-indicator.component';

@Component({selector:'arena-campaigns',standalone:true,imports:[DatePipe,DecimalPipe,JsonPipe,FormsModule,LoadingIndicatorComponent],
  templateUrl:'./campaigns.component.html'})
export class CampaignsComponent {
  private api = inject(ArenaService);
  private destroyed = false;
  private version = 0;
  private listVersion = 0;
  private refreshing = false;
  // Preserve the key after an uncertain response so retrying cannot enqueue a duplicate.
  private requests = new Map<string,string>();
  initialId = input('');
  opened = output<string>();
  changed = output<void>();
  campaigns = signal<CampaignSummary[]>([]);
  selectedId = signal('');
  detail = signal<CampaignDetail|null>(null);
  loading = signal(false);
  loadingList = signal(false);
  busy = signal(false);
  error = signal('');
  listError = signal('');
  notice = signal('');
  taskFilter = signal('all');
  visibleTasks = computed(() => (this.detail()?.analysis?.tasks ?? []).filter(task => {
    const branches = [task.branches.A,task.branches.B];
    return this.taskFilter() === 'variable' ? branches.some(b => b.quality_stability === 'variable')
      : this.taskFilter() === 'changed' ? branches.some(b => b.between_attempt_changes > 0)
      : this.taskFilter() === 'errors' ? branches.some(b => b.summary.execution_errors > 0)
      : this.taskFilter() === 'coverage' ? branches.some(b => b.reference_evaluable && b.coverage !== 1) : true;
  }));
  stabilityLabel(value:string) {
    return ({insufficient:'Evidencia insuficiente',variable:'Calidad variable',always_correct:'Evaluadas siempre correctas',always_incorrect:'Evaluadas siempre incorrectas'} as Record<string,string>)[value] ?? value;
  }
  outcomeLabel(value:string) {
    return ({correct:'Correcta',incorrect:'Incorrecta',invalid_format:'Formato inválido',execution_error:'Error de ejecución',unscored:'Sin evaluar',pending:'Pendiente'} as Record<string,string>)[value] ?? value;
  }
  constructor() {
    const timer = setInterval(() => {
      if (this.detail()?.pending && !this.loading() && !this.busy()) void this.refresh();
    },2500);
    inject(DestroyRef).onDestroy(() => {this.destroyed = true; ++this.version; ++this.listVersion; clearInterval(timer);});
  }
  ngOnInit() { void this.initialize(); }
  savedTasks(branch:'A'|'B') {
    const design = this.detail()?.design;
    return design?.branch_tasks ? [design.branch_tasks[branch]] : design?.tasks ?? [];
  }
  private acceptDetail(detail:CampaignDetail) {
    this.detail.set(detail);
    const key = this.requests.get(detail.id);
    if (key && detail.attempts.some(a => a.request_id === key)) {
      this.requests.delete(detail.id);
      this.changed.emit();
      this.notice.set('La solicitud anterior ya estaba guardada. Su intento aparece en el historial de la campaña.');
    }
  }
  async initialize() {
    await this.loadList();
    if (this.destroyed || this.selectedId()) return;
    const id = this.initialId() || this.campaigns()[0]?.id;
    if (id) await this.select(id);
  }
  async loadList() {
    const version = ++this.listVersion;
    this.loadingList.set(true); this.listError.set('');
    try {
      const campaigns = await this.api.campaigns();
      if (!this.destroyed && version === this.listVersion) this.campaigns.set(campaigns);
    } catch { if (!this.destroyed && version === this.listVersion) this.listError.set('No se pudieron cargar las campañas. Reintenta la conexión.'); }
    finally { if (!this.destroyed && version === this.listVersion) this.loadingList.set(false); }
  }
  async select(id:string) {
    const version = ++this.version;
    this.taskFilter.set('all');
    this.selectedId.set(id); this.detail.set(null); this.notice.set(''); this.error.set(''); this.loading.set(true);
    try {
      const detail = await this.api.campaign(id);
      if (!this.destroyed && version === this.version) this.acceptDetail(detail);
    } catch { if (!this.destroyed && version === this.version) this.error.set('No se pudo cargar esta campaña. Puedes reintentar.'); }
    finally { if (!this.destroyed && version === this.version) this.loading.set(false); }
  }
  async refresh() {
    if (this.refreshing || this.loading()) return;
    this.refreshing = true;
    const id = this.selectedId(), version = this.version;
    try {
      const [campaigns,detail] = await Promise.all([this.api.campaigns(),id ? this.api.campaign(id) : Promise.resolve(null)]);
      if (!this.destroyed && version === this.version) {
        this.campaigns.set(campaigns); if (detail) this.acceptDetail(detail); else this.detail.set(null); this.error.set(''); this.listError.set('');
        if (!id && campaigns.length) await this.select(campaigns[0].id);
      }
    } catch { if (!this.destroyed && version === this.version) this.error.set('No se pudo actualizar. Los datos visibles pueden estar desactualizados; reintenta antes de repetir.'); }
    finally { this.refreshing = false; }
  }
  async repeat() {
    const id = this.selectedId(), version = this.version;
    if (!id || !this.detail() || this.detail()?.pending || this.error() || this.listError() || this.busy() || this.loading()) return;
    this.busy.set(true); this.notice.set('');
    const key = this.requests.get(id) ?? crypto.randomUUID();
    this.requests.set(id,key);
    try {
      await this.api.repeatCampaign(id,key);
      this.requests.delete(id);
      this.changed.emit();
      if (this.destroyed || version !== this.version) return;
      this.notice.set('Nuevo intento guardado. El worker procesará las ejecuciones con el diseño fijado.');
      await this.refresh();
    } catch(error) { if (!this.destroyed && version === this.version) this.error.set(accountError(error) + ' Actualiza antes de reintentar; se conserva la clave de esta solicitud.'); }
    finally { if (!this.destroyed) this.busy.set(false); }
  }
}
