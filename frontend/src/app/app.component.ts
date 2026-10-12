import { Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { DatePipe, DecimalPipe, JsonPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ComposerComponent } from './composer.component';
import { ProfileComponent } from './profile.component';
import { InfoDialogComponent } from './info-dialog.component';
import { GuideComponent } from './guide.component';
import { BrandMarkComponent } from './brand-mark.component';
import { ModelLibraryComponent } from './model-library.component';
import { CampaignsComponent } from './campaigns.component';
import { accountError } from './auth.service';
import { textError } from './validation';
import { LoadingIndicatorComponent } from './loading-indicator.component';
import { AuthService } from './auth.service';
import { ArenaService, ArenaEvent, ExperimentDetail, ExperimentSummary, Preset, PresetId, Run, Status, terminal } from './arena.service';

@Component({
  selector: 'arena-workspace', standalone: true,
  imports: [DatePipe, DecimalPipe, JsonPipe, FormsModule, ComposerComponent, ProfileComponent, InfoDialogComponent, GuideComponent, BrandMarkComponent, ModelLibraryComponent, CampaignsComponent, LoadingIndicatorComponent],
  templateUrl: './app.component.html',
})
export class AppComponent {
  auth = inject(AuthService);
  view = signal<'compose' | 'results' | 'profile' | 'guide' | 'contact' | 'models' | 'campaigns'>('compose');
  campaignId = signal('');
  campaignName = signal('');
  campaignError = signal('');
  campaignBusy = signal(false);
  private api = inject(ArenaService);
  private destroyed = false;
  private selectionVersion = 0;
  private initializationVersion = 0;
  private traceVersion = 0;
  private refreshing = false;
  private traceTrigger: HTMLElement | null = null;
  navigate(view: 'compose' | 'results' | 'profile' | 'guide' | 'contact' | 'models' | 'campaigns') {
    this.view.set(view);
    document.title = `${view === 'compose' ? 'Comparar' : view === 'results' ? 'Resultados' : view === 'guide' ? 'Guía' : view === 'contact' ? 'Contacto' : view === 'models' ? 'Modelos' : view === 'campaigns' ? 'Campañas' : 'Perfil'} · Agent Arena`;
    requestAnimationFrame(() => {
      const heading = document.getElementById(view === 'compose' ? 'page-title' : view === 'results' ? 'collection-title' : view === 'guide' ? 'guide-title' : view === 'contact' ? 'contact-title' : view === 'models' ? 'models-title' : view === 'campaigns' ? 'campaigns-title' : 'profile-title');
      heading?.setAttribute('tabindex', '-1');
      heading?.focus();
    });
  }
  experiments = signal<ExperimentSummary[]>([]);
  presets = signal<Preset[]>([]);
  selectedId = signal('');
  detail = signal<ExperimentDetail | null>(null);
  selectedRun = signal<Run | null>(null);
  events = signal<ArenaEvent[]>([]);
  error = signal('');
  traceError = signal('');
  notice = signal('');
  loading = signal(true);
  creating = signal(false);
  traceLoading = signal(false);
  cancelling = signal('');
  preset: PresetId = 'simulated';
  branchFilter = signal('all');
  isTerminal = terminal;
  labels: Record<Status, string> = {
    queued: 'En cola', running: 'En curso', succeeded: 'Correcta', failed: 'Fallida',
    completed: 'Completada · sin evaluar',
    timeout: 'Tiempo agotado', limit: 'Límite alcanzado', cancelled: 'Cancelada', interrupted: 'Interrumpida',
  };
  completed = computed(() => this.detail()?.runs.filter(terminal).length ?? 0);
  pending = computed(() => this.detail()?.runs.some(r => !terminal(r)) ?? false);
  visibleRuns = computed(() => this.detail()?.runs.filter(r => this.branchFilter() === 'all' || r.branch === this.branchFilter()) ?? []);
  summaries = computed(() => (['A', 'B'] as const).map(branch => {
    return {branch,...(this.detail()?.overviews?.[branch] ?? {total:0,finished:0,evaluated:0,planned_evaluable:0,correct:0,incorrect:0,invalid_format:0,execution_errors:0,unscored:0,pending:0,mean_answer_s:null,timed_answers:0})};
  }));

  runLabel(run: Run) {
    if (run.status === 'failed') return run.result?.error || run.result?.answer === undefined ? 'Error de ejecución' : run.result?.format_ok === false ? 'Formato inválido' : 'Respuesta incorrecta';
    return this.labels[run.status];
  }
  evaluationLabel(value: string) {
    return ({exact_match:'Texto exacto', json_match:'JSON equivalente', none:'Sin evaluación automática', order_benchmark:'Criterios del benchmark de pedidos'} as Record<string,string>)[value] ?? value;
  }

  constructor() {
    document.title = 'Comparar · Agent Arena';
    const interval = setInterval(() => {
      if (this.pending() && !this.loading()) void this.refresh();
    }, 2500);
    inject(DestroyRef).onDestroy(() => { this.destroyed = true; clearInterval(interval); });
    void this.initialize();
  }

  async initialize() {
    const version = ++this.initializationVersion;
    const selection = this.selectionVersion;
    this.error.set('');
    this.loading.set(true);
    try {
      const [presets, experiments] = await Promise.all([this.api.presets(), this.api.experiments()]);
      if (this.destroyed || version !== this.initializationVersion) return;
      this.presets.set(presets);
      this.experiments.set(experiments);
      if (experiments.length && selection === this.selectionVersion) await this.select(experiments[0].id);
    } catch { if (version === this.initializationVersion) this.error.set('No se puede conectar con la API. Comprueba que esté en marcha y pulsa Actualizar.'); }
    finally { if (version === this.initializationVersion && selection === this.selectionVersion) this.loading.set(false); }
  }

  async select(id: string) {
    const version = ++this.selectionVersion;
    this.selectedId.set(id);
    this.detail.set(null);
    this.closeTrace();
    this.branchFilter.set('all');
    this.loading.set(true);
    this.error.set('');
    this.campaignError.set('');
    try {
      const detail = await this.api.detail(id);
      if (version === this.selectionVersion && !this.destroyed) { this.detail.set(detail); this.campaignName.set(detail.snapshot.config.name); }
    } catch { if (version === this.selectionVersion) this.error.set('No se ha podido cargar la comparación. Puedes volver a intentarlo.'); }
    finally { if (version === this.selectionVersion) this.loading.set(false); }
  }

  async refresh() {
    if (this.refreshing) return;
    if (!this.presets().length) { await this.initialize(); return; }
    this.refreshing = true;
    const id = this.selectedId();
    const version = this.selectionVersion;
    try {
      const [experiments, detail] = await Promise.all([this.api.experiments(), id ? this.api.detail(id) : Promise.resolve(null)]);
      if (this.destroyed) return;
      if (version === this.selectionVersion) {
        this.experiments.set(experiments);
        this.detail.set(detail);
        this.error.set('');
        const selected = this.selectedRun();
        if (selected && detail) {
          const run = detail.runs.find(r => r.id === selected.id);
          if (run) { this.selectedRun.set(run); await this.loadEvents(run); }
        }
      }
      if (version === this.selectionVersion && !id && experiments.length) await this.select(experiments[0].id);
    } catch { if (version === this.selectionVersion) this.error.set('No se han podido actualizar los datos. Los resultados visibles pueden estar desactualizados.'); }
    finally { this.refreshing = false; }
  }

  async create() {
    if (this.creating()) return;
    this.creating.set(true);
    this.error.set('');
    this.notice.set('');
    try {
      const { id } = await this.api.create(this.preset);
      this.navigate('results');
      this.notice.set('Comparación creada. El worker procesará las ejecuciones en cola.');
      await this.select(id);
      await this.refresh();
    } catch { this.error.set('No se pudo confirmar la creación. Actualiza el historial antes de repetir para evitar duplicados.'); }
    finally { this.creating.set(false); }
  }

  async customCreated(id: string) {
    this.navigate('results');
    this.notice.set('Comparación personalizada guardada. El worker ejecutará A y B secuencialmente.');
    await this.select(id);
    await this.refresh();
  }

  async historyCleared() {
    ++this.selectionVersion;
    this.closeTrace(); this.detail.set(null); this.selectedId.set(''); this.experiments.set([]);
    this.branchFilter.set('all'); this.notice.set('Historial eliminado.');
    await this.initialize();
  }

  savedTasks(branch: 'A' | 'B') {
    const snapshot = this.detail()?.snapshot;
    const task = snapshot?.branch_tasks?.[branch];
    return task ? [task] : snapshot?.tasks ?? [];
  }

  answers(branch: 'A' | 'B') {
    return this.detail()?.runs.filter(run => run.branch === branch && terminal(run)) ?? [];
  }

  referenceFor(run: Run) {
    const task = this.savedTasks(run.branch).find(task => task.id === run.task_id);
    return task?.expected_answer ?? (task?.criteria ? JSON.stringify(task.criteria,null,2) : null);
  }

  async openModelResult(id:string) { this.navigate('results'); await this.select(id); }

  openCampaign(id:string) { this.campaignId.set(id); this.navigate('campaigns'); }

  async createCampaign() {
    if (this.campaignBusy() || this.pending() || !this.detail()) return;
    const invalid = textError(this.campaignName(),'Nombre de campaña',120);
    if (invalid) { this.campaignError.set(invalid); document.getElementById('campaign-name')?.focus(); return; }
    const id = this.selectedId(), version = this.selectionVersion;
    this.campaignBusy.set(true); this.campaignError.set('');
    try {
      const created = await this.api.createCampaign(id,this.campaignName());
      if (!this.destroyed && version === this.selectionVersion) {
        if (this.view() === 'results') this.openCampaign(created.id);
        await this.refresh();
      }
    } catch(error) { if (!this.destroyed && version === this.selectionVersion) this.campaignError.set(accountError(error)); }
    finally { if (!this.destroyed) this.campaignBusy.set(false); }
  }

  async showTrace(run: Run) {
    this.traceTrigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    this.selectedRun.set(run);
    this.events.set([]);
    await this.loadEvents(run);
    if (this.selectedRun()?.id === run.id) {
      requestAnimationFrame(() => document.getElementById('trace-title')?.focus());
    }
  }

  private async loadEvents(run: Run) {
    const version = ++this.traceVersion;
    this.traceLoading.set(true);
    this.traceError.set('');
    try {
      const events = await this.api.events(run.id);
      if (version === this.traceVersion && this.selectedRun()?.id === run.id) this.events.set(events);
    } catch { if (version === this.traceVersion) this.traceError.set('No se han podido cargar los eventos.'); }
    finally { if (version === this.traceVersion) this.traceLoading.set(false); }
  }

  closeTrace(restore = false) {
    ++this.traceVersion; this.selectedRun.set(null); this.events.set([]); this.traceLoading.set(false);
    if (restore && this.traceTrigger?.isConnected) this.traceTrigger.focus();
  }

  async cancel(run: Run) {
    this.cancelling.set(run.id);
    try {
      await this.api.cancel(run.id);
      this.notice.set('Cancelación solicitada. Se conservarán las trazas y el resultado.');
      await this.refresh();
    } catch { this.error.set('No se pudo confirmar la cancelación. Actualiza el estado antes de volver a intentarlo.'); }
    finally { this.cancelling.set(''); }
  }
}
