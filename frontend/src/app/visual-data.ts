import type { CampaignDetail, ResultSummary } from './arena.service';

export const outcomes = [
  ['correct','Correctas'], ['incorrect','Incorrectas'], ['invalid_format','Formato inválido'],
  ['execution_errors','Errores de ejecución'], ['cancelled','Canceladas'], ['unscored','Sin evaluar'], ['pending','Pendientes'],
] as const;

export function outcomeSegments(summary: ResultSummary) {
  return outcomes.map(([key,label]) => ({key,label,count:summary[key],width:summary.total > 0 ? 100 * summary[key] / summary.total : 0}));
}
export function outcomeDescription(summary: ResultSummary) {
  return `${summary.total} ejecuciones programadas. ` + outcomeSegments(summary).map(s=>`${s.count} ${s.label.toLowerCase()}`).join(', ') + '.';
}
export function timePoints(rows: {branch:string;mean_answer_s:number|null;timed_answers:number}[]) {
  const valid = (row:typeof rows[number]) => row.timed_answers > 0 && row.mean_answer_s !== null && Number.isFinite(row.mean_answer_s) && row.mean_answer_s >= 0;
  const maximum = Math.max(0,...rows.filter(valid).map(row=>row.mean_answer_s!));
  return rows.map(row=>({...row,maximum,available:valid(row),position:valid(row) && maximum > 0 ? 100 * row.mean_answer_s! / maximum : 0}));
}
export function campaignPoints(campaign: CampaignDetail) {
  const included = new Set(campaign.analysis.included_attempts.map(a=>a.experiment_id));
  return [...campaign.attempts].sort((a,b)=>a.sequence-b.sequence).map(attempt=>({
    id:attempt.experiment_id, sequence:attempt.sequence,
    included:attempt.complete && attempt.compatible && included.has(attempt.experiment_id),
    reason:!attempt.complete ? 'En curso · resultado parcial' : !included.has(attempt.experiment_id) || !attempt.compatible
      ? 'Excluido · ' + (campaign.analysis.excluded_attempts.find(a=>a.experiment_id===attempt.experiment_id)?.reasons.join(' · ') || 'Condiciones no compatibles') : 'Compatible',
    branches:(['A','B'] as const).map(branch=>{
      const s=attempt.overviews[branch];
      return {branch,correct:s.correct,reference:s.planned_evaluable,evaluated:s.evaluated,
        position:s.planned_evaluable > 0 ? 100*s.correct/s.planned_evaluable : null};
    }),
  }));
}

/** Only observed queue/run states; no invented stages, durations or completion ETA. */
export function executionGuidance(runs: {status:string;result?:{error?:string;answer?:string}|null}[]) {
  const queued = runs.filter(r=>r.status === 'queued').length;
  const running = runs.filter(r=>r.status === 'running').length;
  const errors = runs.filter(r=>['timeout','limit','interrupted'].includes(r.status) || r.status === 'failed' && (!!r.result?.error || r.result?.answer === undefined)).length;
  return {queued,running,
    title:!runs.length ? 'Sin ejecuciones registradas' : running ? 'Procesando respuestas' : queued ? 'En espera del worker' : 'Recorrido finalizado',
    next:!runs.length ? 'Selecciona otra comparación del historial o vuelve a Comparar para preparar una prueba.' : queued || running
      ? 'Puedes revisar las respuestas disponibles o cancelar una ejecución pendiente. Si todo sigue en cola, comprueba el worker. La actualización es automática; no hay una duración estimada.'
      : errors ? 'Revisa las respuestas y referencias; si hay un error, abre su traza. Puedes consultar las condiciones antes de repetir el diseño en una campaña.'
      : 'Revisa una respuesta y su referencia. Abre la traza para entender el recorrido o consulta las condiciones antes de repetir el diseño en una campaña.'};
}

export function partialAnswer(run: {status:string;result?:{answer?:string;error?:string}|null}) {
  return !!run.result?.answer && (!!run.result.error || ['cancelled','interrupted','timeout','limit'].includes(run.status));
}
