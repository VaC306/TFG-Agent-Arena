import { Component, Input } from '@angular/core';
import type { ResultSummary } from './arena.service';
import { outcomeDescription, outcomeSegments } from './visual-data';

@Component({selector:'arena-outcome-chart',standalone:true,template:`
  <figure class="outcome-chart" [attr.aria-label]="label">
    <figcaption>{{ label }} <span class="hint">{{ summary.total }} programadas</span></figcaption>
    <p class="chart-denominator"><strong>{{ summary.planned_evaluable ? summary.correct + '/' + summary.planned_evaluable : '—' }}</strong><span>{{ summary.planned_evaluable ? 'aciertos / casos con referencia' : 'Sin referencia para evaluar calidad' }}</span><small>{{ summary.evaluated }} respuestas evaluadas</small></p>
    @if (summary.total) {
      <div class="outcome-track" role="img" [attr.aria-label]="description(summary)">
        @for (part of segments(summary); track part.key) { @if (part.count) {
          <span [class]="'outcome-segment outcome-' + part.key" [style.width.%]="part.width" aria-hidden="true"></span>
        } }
      </div>
      <ul class="outcome-legend" aria-label="Recuento de estados">
        @for (part of segments(summary); track part.key) { @if (part.count) {
          <li><i [class]="'outcome-' + part.key" aria-hidden="true"></i><span class="outcome-symbol" aria-hidden="true">{{ symbols[part.key] }}</span><strong>{{ part.count }}</strong> {{ part.label }}</li>
        } }
      </ul>
      <p class="hint">{{ summary.finished }}/{{ summary.total }} finalizadas; {{ summary.evaluated }} evaluadas{{ summary.unscored ? '; ' + summary.unscored + ' sin puntuar' : '' }}. {{ !summary.planned_evaluable ? 'Sin casos con referencia evaluable: revisa las respuestas; la barra no indica calidad.' : summary.pending ? 'Hay respuestas pendientes: la evidencia es parcial.' : 'Los aciertos usan los casos con referencia, no el total de la barra.' }}</p>
    } @else { <p class="hint">Sin ejecuciones registradas. Abre la comparación de origen para consultar su evidencia.</p> }
  </figure>
`})
export class OutcomeChartComponent {
  @Input({required:true}) summary!: ResultSummary;
  @Input() label = 'Distribución de respuestas';
  symbols = {correct:'✓',incorrect:'×',invalid_format:'◇',execution_errors:'!',cancelled:'⊘',unscored:'—',pending:'◷'};
  segments = outcomeSegments;
  description = outcomeDescription;
}
