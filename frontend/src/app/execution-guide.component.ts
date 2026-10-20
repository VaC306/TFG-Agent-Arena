import { Component, Input } from '@angular/core';
import type { Run } from './arena.service';
import { executionGuidance } from './visual-data';
@Component({selector:'arena-execution-guide',standalone:true,template:`
  <aside class="execution-guide" aria-label="Orientación de la ejecución">
    <p role="status"><strong>{{ guidance.title }}</strong> · {{ guidance.queued }} en cola · {{ guidance.running }} en curso</p>
    <p class="hint">{{ readOnly ? 'Evidencia guardada: no se actualiza ni permite cancelar o crear intentos en la demo. Revisa respuestas, referencias y trazas disponibles; abre Comparar para explorar otros ejemplos.' : guidance.next }}</p>
    <details><summary>Cómo leer los estados</summary><dl class="state-guide">
      <dt>✓ Respuesta completada</dt><dd>Hay una respuesta final. Completar no significa acertar.</dd>
      <dt>◎ Correcta / incorrecta / formato inválido</dt><dd>Resultado del criterio de evaluación aplicado a una referencia; revisa también la respuesta.</dd>
      <dt>— Sin evaluar</dt><dd>No hay puntuación de calidad: falta referencia o no se solicitó evaluación.</dd>
      <dt>⊘ Cancelación</dt><dd>Se detuvo por solicitud. Conserva la evidencia registrada; no cuenta como error de ejecución.</dd>
      <dt>! Error de ejecución</dt><dd>No se completó normalmente: puede conservar una respuesta parcial. Abre su traza para investigar.</dd>
    </dl></details>
  </aside>
`})
export class ExecutionGuideComponent {
  @Input({required:true}) runs: Run[] = [];
  @Input() readOnly = false;
  get guidance() { return executionGuidance(this.runs); }
}
