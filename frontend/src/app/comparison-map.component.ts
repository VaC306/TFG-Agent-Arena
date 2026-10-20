import { Component, EventEmitter, Input, Output } from '@angular/core';

/** A map of the current draft only; never substitutes for an executed snapshot. */
@Component({selector:'arena-comparison-map',standalone:true,template:`
  <nav class="comparison-map" aria-label="Mapa de la comparación preparada">
    <p class="eyebrow">TU RECORRIDO · selecciona un bloque para editarlo</p>
    <ol class="map-flow">
      <li><button type="button" (click)="edit.emit(inputTarget)"><span aria-hidden="true">▤</span><strong>Entrada</strong><small>{{ dataset ? 'Casos compartidos A/B' : independent ? 'Datos independientes A/B' : 'Datos compartidos A/B' }}</small></button></li>
      <li><div class="map-branches" aria-label="Variantes A y B">
        <button type="button" (click)="edit.emit('model-a')"><strong><span class="branch">A</span> Variante A</strong><small>{{ modelA || 'Modelo por elegir' }}</small></button>
        <button type="button" (click)="edit.emit(twoModels ? 'model-b' : 'template-b')"><strong><span class="branch branch-b">B</span> Variante B</strong><small>{{ (twoModels ? modelB : modelA) || 'Modelo por elegir' }}</small></button>
      </div></li>
      <li><button type="button" (click)="edit.emit('repetitions')"><span aria-hidden="true">☷</span><strong>Respuestas</strong><small>{{ planned === null ? 'Revisa las repeticiones' : planned + ' ejecuciones previstas' }}</small></button></li>
      <li><button type="button" (click)="edit.emit('evaluation-mode')"><span aria-hidden="true">◎</span><strong>Evaluación</strong><small>{{ evaluation === 'none' ? 'Revisión manual' : evaluation === 'json_match' ? 'JSON equivalente' : 'Texto exacto' }}</small></button></li>
    </ol>
    <ul class="map-invariants">
      <li>{{ independent && !dataset ? '↔ Entradas independientes' : '= Mismos datos y referencias' }}</li>
      <li>{{ modelsEqual ? '= Mismo modelo' : '↔ Modelos distintos' }}</li>
      <li><button class="text-button" type="button" (click)="edit.emit('prompt-b')">{{ promptsEqual ? '= Mismo prompt' : '↔ Prompts diferentes' }}</button></li>
      <li>= Mismos parámetros</li>
    </ul>
    <p class="hint">{{ simulated ? 'Simulación: los nombres representan configuraciones; no se ejecutan modelos reales.' : 'Ollama: se ejecutan los modelos locales seleccionados.' }} El mapa describe lo preparado; los resultados conservarán su propia copia.</p>
  </nav>
`})
export class ComparisonMapComponent {
  @Input() dataset = false;
  @Input() independent = false;
  @Input() inputTarget = 'shared-input';
  @Input() twoModels = false;
  @Input() modelA = '';
  @Input() modelB = '';
  @Input() modelsEqual = true;
  @Input() promptsEqual = true;
  @Input() planned: number | null = 0;
  @Input() evaluation = 'none';
  @Input() simulated = true;
  @Output() edit = new EventEmitter<string>();
}
