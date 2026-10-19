import { OutcomeChartComponent } from './outcome-chart.component';
import { Component, computed, DestroyRef, inject, output, signal } from '@angular/core';
import { DEMO_MODE } from './runtime-mode';
import { DatePipe, DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ArenaService, ModelResult } from './arena.service';
import { LoadingIndicatorComponent } from './loading-indicator.component';

@Component({selector:'arena-model-library',standalone:true,imports:[OutcomeChartComponent, DatePipe,DecimalPipe,FormsModule,LoadingIndicatorComponent],
  templateUrl:'./model-library.component.html'})
export class ModelLibraryComponent {
  demo = DEMO_MODE;
  private api = inject(ArenaService);
  private destroyed = false;
  private initialized = false;
  private refreshing = false;
  opened = output<string>();
  entries = signal<ModelResult[]>([]);
  loading = signal(true);
  error = signal('');
  filter = signal('all');
  provider = signal('all');
  model = signal('all');
  selected = signal<string[]>([]);
  kinds = computed(() => [...new Set(this.entries().map(e => e.kind))].sort());
  models = computed(() => [...new Set(this.entries().filter(e => this.provider() === 'all' || e.adapter === this.provider()).map(e => e.model))].sort());
  visible = computed(() => this.entries().filter(e => (this.filter() === 'all' || e.kind === this.filter()) && (this.provider() === 'all' || e.adapter === this.provider()) && (this.model() === 'all' || e.model === this.model())));
  compared = computed(() => this.selected().flatMap(id => this.entries().filter(e => e.id === id)));
  hiddenSelected = computed(() => this.compared().filter(e => !this.visible().some(v => v.id === e.id)).length);
  differences = computed(() => {
    const [a,b] = this.compared();
    if (!a || !b) return [];
    const labels: Record<string,string> = {data:'Dataset, referencias o archivos',prompt:'Prompt',parameters:'Parámetros y límites',repetitions:'Repeticiones',split:'Fase',adapter:'Adaptador',conditions:'Condiciones de ejecución',source_sha256:'Versión del código',evaluator_versions:'Versión del evaluador',server_version:'Versión de Ollama',order_seed:'Orden de ejecución',host:'Equipo o dependencias'};
    return Object.entries(labels).filter(([key]) => JSON.stringify(a.comparison_conditions?.[key]) !== JSON.stringify(b.comparison_conditions?.[key])).map(([,label]) => label);
  });
  compatible = computed(() => {
    const [a,b] = this.compared();
    return !this.error() && !!a && !!b && !a.external_deviation && !b.external_deviation && a.adapter === 'ollama' && b.adapter === 'ollama' && a.verified && b.verified
      && a.digest !== b.digest && a.cohort_key === b.cohort_key;
  });
  constructor() {
    inject(DestroyRef).onDestroy(() => this.destroyed = true);
    void this.refresh();
  }
  async refresh() {
    if (this.refreshing) return;
    this.refreshing = true;
    this.loading.set(true); this.error.set('');
    try {
      const result = await this.api.modelResults();
      if (this.destroyed) return;
      this.entries.set(result.entries);
      if (!this.initialized) { this.provider.set(result.entries.some(e => e.adapter === 'ollama') ? 'ollama' : 'all'); this.initialized = true; }
      this.selected.update(ids => ids.filter(id => result.entries.some(e => e.id === id)));
      if (!this.kinds().includes(this.filter())) this.filter.set('all');
      if (!this.models().includes(this.model())) this.model.set('all');
    } catch { if (!this.destroyed) this.error.set('No se pudieron actualizar los resultados guardados. Reintenta antes de comparar.'); }
    finally { this.refreshing = false; if (!this.destroyed) this.loading.set(false); }
  }
  toggle(id:string) {
    this.selected.update(ids => ids.includes(id) ? ids.filter(i => i !== id) : ids.length < 2 ? [...ids,id] : ids);
  }
  changeFilter(value:string) { this.filter.set(value); }
  changeProvider(value:string) { this.provider.set(value); if (!this.models().includes(this.model())) this.model.set('all'); }
  changeModel(value:string) { this.model.set(value); }
  kindLabel(kind:string) {
    const [evaluation,modality] = kind.split(':');
    const label = ({exact_match:'Texto exacto',json_match:'JSON',none:'Respuesta abierta',order_benchmark:'Pedidos con herramientas'} as Record<string,string>)[evaluation] ?? evaluation;
    return label + (modality === 'files' ? ' · archivos' : modality === 'images' ? ' · imágenes' : '');
  }
}
