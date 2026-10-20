import type { ExperimentDetail, Run } from './arena.service';

/** Read the executed snapshot, never the current composer or another case. */
export function caseInputs(snapshot: ExperimentDetail['snapshot'] | undefined, taskId: string) {
  if (snapshot?.branch_tasks || snapshot?.conditions?.inputs_shared === false) {
    return (['A', 'B'] as const).map(branch => {
      const task = snapshot.branch_tasks?.[branch];
      return {label: 'Entrada ' + branch, text: task?.id === taskId ? task.input ?? null : null};
    });
  }
  return [{label: 'Entrada compartida por A y B', text: snapshot?.tasks?.find(task => task.id === taskId)?.input ?? null}];
}

export function evaluationStatus(run: Run) {
  if (run.status === 'queued' || run.status === 'running') return 'Evaluación pendiente.';
  if (run.status === 'cancelled') return 'Sin evaluación: ejecución cancelada.';
  if (run.result?.reason) return run.result.reason;
  if (run.status === 'completed') return 'Calidad sin evaluar automáticamente.';
  if (run.status === 'succeeded') return 'Respuesta correcta según el criterio registrado.';
  if (run.status === 'failed' && run.result?.answer !== undefined && !run.result.error)
    return run.result.format_ok === false ? 'La respuesta no cumple el formato requerido.' : 'La respuesta no cumple el criterio de evaluación.';
  return 'Sin evaluación disponible: la ejecución no se completó normalmente.';
}
