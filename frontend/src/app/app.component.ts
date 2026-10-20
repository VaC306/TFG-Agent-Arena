import { partialAnswer } from './visual-data';
import { ExecutionGuideComponent } from './execution-guide.component';
import { TermHelpComponent } from './term-help.component';
import { TimeChartComponent } from './time-chart.component';
import { OutcomeChartComponent } from './outcome-chart.component';
import { ThemePickerComponent } from './theme-picker.component';
import { DEMO_MODE } from './runtime-mode';
import { WorkerStatusComponent } from './worker-status.component';
import { DemoOverviewComponent } from './demo-overview.component';
import { DemoGuideComponent } from './demo-guide.component';
import { ContactComponent } from './contact.component';
import { Component, computed, DestroyRef, HostListener, inject, signal } from '@angular/core';
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
  imports: [ExecutionGuideComponent, TermHelpComponent, TimeChartComponent, OutcomeChartComponent, ThemePickerComponent, WorkerStatusComponent, DemoOverviewComponent, DemoGuideComponent, ContactComponent, DatePipe, DecimalPipe, JsonPipe, FormsModule, ComposerComponent, ProfileComponent, InfoDialogComponent, GuideComponent, BrandMarkComponent, ModelLibraryComponent, CampaignsComponent, LoadingIndicatorComponent],
  templateUrl: './app.component.html',
})
export class AppComponent {
  demo = DEMO_MODE;
  download(file:string) { return this.demo ? `demo/exports/${encodeURIComponent(this.selectedId())}/${file}` : `/api/experiments/${encodeURIComponent(this.selectedId())}/${file}`; }
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
  focusMain(event:Event) { event.preventDefault(); document.getElementById('main')?.focus(); }
  private writeRoute(replace = false) {
    const query = new URLSearchParams();
    if (this.selectedId()) query.set('comparison', this.selectedId());
    if (this.view() === 'campaigns' && this.campaignId()) query.set('campaign', this.campaignId());
    const url = `#/${this.view()}${query.size ? '?' + query : ''}`;
    if (window.location.hash !== url) window.history[replace ? 'replaceState' : 'pushState'](null, '', url);
  }
  private readRoute() {
    const [path,query = ''] = window.location.hash.replace(/^#\/?/, '').split('?');
    const views = ['compose','results','profile','guide','contact','models','campaigns'] as const;
    const view = views.find(v => v === path && !(this.demo && v === 'profile')) ?? 'compose';
    const params = new URLSearchParams(query);
    return {view, id:params.get('comparison') ?? '', campaign:params.get('campaign') ?? ''};
  }
  @HostListener('window:hashchange')
  async routeChanged() {
    const route = this.readRoute();
    this.campaignId.set(route.campaign);
    this.navigate(route.view, false);
    if (route.id !== this.selectedId()) {
      if (route.id) await this.select(route.id, false);
      else { ++this.selectionVersion; this.selectedId.set(''); this.detail.set(null); this.loading.set(false); this.error.set(''); }
    }
  }
  @HostListener('document:keydown.escape', ['$event'])
  escapeTrace(event: KeyboardEvent) {
    if (this.selectedRun() && this.view() === 'results' && !document.querySelector('dialog[open]')) { event.preventDefault(); this.closeTrace(true); }
  }
  navigate(view: 'compose' | 'results' | 'profile' | 'guide' | 'contact' | 'models' | 'campaigns', write = true) {
    if (view !== 'results') this.closeTrace();
    this.view.set(view);
    if (write) this.writeRoute();
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
  partialAnswer = partialAnswer;
  labels: Record<Status, string> = {
    queued: 'En cola', running: 'En curso', succeeded: 'Correcta', failed: 'Fallida',
    completed: 'Completada · sin evaluar',
    timeout: 'Tiempo agotado', limit: 'Límite alcanzado', cancelled: 'Cancelada', interrupted: 'Interrumpida',
  };
  executionCounts = computed(() => {
    const summaries = this.summaries();
    const count = (key:'total'|'execution_errors'|'cancelled'|'pending') => summaries.reduce((n,s)=>n+s[key],0);
    return {finishedWithoutError:Math.max(0,summaries.reduce((n,s)=>n+s.finished,0)-count('execution_errors')-count('cancelled')),total:count('total'),errors:count('execution_errors'),cancelled:count('cancelled'),pending:count('pending')};
  });
  completed = computed(() => this.detail()?.runs.filter(terminal).length ?? 0);
  pending = computed(() => this.detail()?.runs.some(r => !terminal(r)) ?? false);
  visibleRuns = computed(() => this.detail()?.runs.filter(r => this.branchFilter() === 'all' || r.branch === this.branchFilter()) ?? []);
  allCases = signal(false);
  resultCases = computed(() => {
    const cases = new Map<string,{key:string;task:string;repetition:number;runs:Partial<Record<'A'|'B',Run>>}>();
    for (const run of this.detail()?.runs ?? []) {
      const key = JSON.stringify([run.task_id,run.repetition]);
      const item = cases.get(key) ?? {key,task:run.task_id,repetition:run.repetition,runs:{}};
      item.runs[run.branch] = run; cases.set(key,item);
    }
    return [...cases.values()];
  });
  summaries = computed(() => (['A', 'B'] as const).map(branch => {
    return {branch,...(this.detail()?.overviews?.[branch] ?? {total:0,finished:0,evaluated:0,planned_evaluable:0,correct:0,incorrect:0,invalid_format:0,execution_errors:0,cancelled:0,unscored:0,pending:0,mean_answer_s:null,timed_answers:0})};
  }));

  toggleCases() {
    this.allCases.set(!this.allCases());
    requestAnimationFrame(() => document.getElementById('response-case-' + (this.allCases() ? 3 : 0))?.focus());
  }

  runLabel(run: Run) {
    if (run.status === 'failed') return run.result?.error || run.result?.answer === undefined ? 'Error de ejecución' : run.result?.format_ok === false ? 'Formato inválido' : 'Respuesta incorrecta';
    return this.labels[run.status];
  }
  evaluationLabel(value: string) {
    return ({exact_match:'Texto exacto', json_match:'JSON equivalente', none:'Sin evaluación automática', order_benchmark:'Criterios del benchmark de pedidos'} as Record<string,string>)[value] ?? value;
  }

  constructor() {
    const route = this.readRoute();
    this.selectedId.set(route.id); this.campaignId.set(route.campaign);
    this.navigate(route.view, false);
    this.writeRoute(true);
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
      if (selection === this.selectionVersion) {
        if (this.selectedId()) await this.select(this.selectedId(), false);
        else if (experiments.length) { await this.select(experiments[0].id, false); if (!this.destroyed) this.writeRoute(true); }
      }
    } catch { if (version === this.initializationVersion) this.error.set(this.demo ? 'No se pudieron cargar los resultados guardados. Pulsa Actualizar para reintentar.' : 'No se puede conectar con la API. Comprueba que esté en marcha y pulsa Actualizar.'); }
    finally { if (version === this.initializationVersion && selection === this.selectionVersion) this.loading.set(false); }
  }

  async select(id: string, write = true) {
    const version = ++this.selectionVersion;
    this.selectedId.set(id);
    if (write) this.writeRoute();
    this.detail.set(null);
    this.closeTrace();
    this.branchFilter.set('all'); this.allCases.set(false);
    this.loading.set(true);
    this.error.set('');
    this.campaignError.set('');
    try {
      const detail = await this.api.detail(id);
      if (version === this.selectionVersion && !this.destroyed) { this.detail.set(detail); this.campaignName.set(detail.snapshot.config.name); }
    } catch { if (version === this.selectionVersion && !this.destroyed) this.error.set('No se ha podido cargar la comparación. Puede no existir o no pertenecer a tu cuenta. Abre otra desde el historial o vuelve a Comparar.'); }
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
    const selection = this.selectionVersion;
    try {
      const { id } = await this.api.create(this.preset);
      if (this.destroyed) return;
      if (this.view() !== 'compose' || selection !== this.selectionVersion) { this.notice.set('Comparación guardada. Puedes abrirla desde el historial.'); await this.refresh(); return; }
      this.selectedId.set(id); this.navigate('results');
      this.notice.set('Comparación creada. El worker procesará las ejecuciones en cola.');
      await this.select(id);
      await this.refresh();
    } catch { this.error.set('No se pudo confirmar la creación. Actualiza el historial antes de repetir para evitar duplicados.'); }
    finally { this.creating.set(false); }
  }
  async simulatedExample() { this.preset = 'simulated'; await this.create(); }

  async customCreated(id: string) {
    if (this.destroyed) return;
    if (this.view() !== 'compose') { this.notice.set('Comparación personalizada guardada. Puedes abrirla desde el historial.'); await this.refresh(); return; }
    this.selectedId.set(id); this.navigate('results');
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

  async openModelResult(id:string) { this.selectedId.set(id); this.navigate('results'); await this.select(id, false); }

  clearSelection() {
    ++this.selectionVersion; this.selectedId.set(''); this.detail.set(null); this.loading.set(false); this.error.set(''); this.navigate('compose');
  }

  eventLabel(kind:string) {
    return ({resources:'Recursos observados',inference_metadata:'Identidad del motor registrada',input:'Entrada preparada',inference_request:'Solicitud al modelo',inference_response:'Respuesta del modelo',tool_request:'Herramienta solicitada',tool_result:'Resultado de herramienta',warmup_request:'Calentamiento solicitado',warmup_response:'Calentamiento completado',cancel_requested:'Cancelación solicitada',interruption:'Worker interrumpido',cancelled:'Ejecución cancelada',queued:'En cola',running:'Ejecución iniciada',finished:'Ejecución finalizada',result:'Resultado registrado'} as Record<string,string>)[kind] ?? 'Evento de ejecución';
  }
  eventSummary(event:ArenaEvent) {
    const payload = event.payload as Record<string,unknown> | null;
    if (event.kind === 'finished' && payload && typeof payload['status'] === 'string') return this.labels[payload['status'] as Status] ?? 'Resultado registrado';
    if (event.kind === 'tool_request') return 'El agente solicitó una herramienta; consulta los argumentos en el JSON técnico.';
    if (event.kind === 'tool_result') return payload?.['error'] ? 'La herramienta devolvió un error; consulta el detalle técnico.' : 'La herramienta devolvió un resultado al agente.';
    if (event.kind === 'input') return 'Se prepararon los mensajes y datos de esta ejecución.';
    if (event.kind === 'inference_request') return 'Se envió una petición al motor de ejecución configurado.';
    if (event.kind === 'inference_response') return 'Se recibió una respuesta del motor de ejecución.';
    if (event.kind === 'resources') return 'Muestra de recursos del worker y del equipo; consulta valores y límites en el JSON técnico.';
    if (event.kind === 'inference_metadata') return 'Se registraron el adaptador y la identidad del modelo cuando están disponibles.';
    return this.eventLabel(event.kind) + '.';
  }
  traceFailure(error:string) {
    return ({'Cancelled before execution':'Cancelada antes de ejecutar','Cancelled':'Ejecución cancelada','Worker interrupted; partial metrics in events':'Worker interrumpido; métricas parciales en los eventos'} as Record<string,string>)[error] ?? error;
  }

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
