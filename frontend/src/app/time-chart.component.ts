import { Component, Input } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { timePoints } from './visual-data';

@Component({selector:'arena-time-chart',standalone:true,imports:[DecimalPipe],template:`
  <figure class="time-chart" aria-label="Tiempo total medio por rama">
    <figcaption>Tiempo total medio <span class="hint">Escala común desde 0 s</span></figcaption>
    @for (point of points(rows); track point.branch) {
      <div class="time-row"><span class="branch" [class.branch-b]="point.branch === 'B'">{{ point.branch }}</span>
        <div class="time-track" aria-hidden="true">@if (point.available) { <i [style.left.%]="point.position"></i> }</div>
        <span>{{ point.available ? (point.mean_answer_s | number:'1.2-2') + ' s' : 'Sin mediciones' }}<small class="hint">{{ point.timed_answers }} respuestas sin error</small></span>
      </div>
    }
    <div class="time-axis" aria-hidden="true"><span>0 s</span><span>{{ (points(rows)[0]?.maximum ?? 0) | number:'1.2-2' }} s</span></div>
  </figure>
`})
export class TimeChartComponent {
  @Input({required:true}) rows!: {branch:string;mean_answer_s:number|null;timed_answers:number}[];
  points = timePoints;
}
