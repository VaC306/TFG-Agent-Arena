"""Readable reports alongside the complete reproducibility JSON."""
import json
import re
from .model_results import outcome, summarize
from .protocol import protocol_report


def code_block(text):
    text = str(text)
    fence = '`' * max(3,max((len(m) for m in re.findall(r'`+',text)),default=0)+1)
    return fence+'\n'+text+'\n'+fence+'\n'


def markdown_report(snapshot,runs):
    config = snapshot['config']
    protocol = protocol_report(snapshot,runs)
    lines = ['# Agent Arena — informe de resultados\n',code_block(config['name']),
             f"Adaptador: {config['adapter']} · Fase: {config['split']} · Repeticiones: {config['repetitions']}\n",
             'Aciertos sobre casos con referencia incluye los fallos y errores de esos casos en el denominador. La calidad entre respuestas evaluadas excluye errores de ejecución.\n']
    labels = {'correct':'Correcta','incorrect':'Respuesta incorrecta','invalid_format':'Formato inválido',
              'execution_error':'Error de ejecución','unscored':'Sin evaluar','pending':'Pendiente'}
    lines += ['## Tiempos por ejecución y recursos observados',
              'El tiempo total incluye preparación, calentamiento si se solicitó y muestreo. El tiempo de tarea incluye inferencia, herramientas y evaluación. Worker RSS/CPU no mide el servidor Ollama; RAM/GPU del host incluye otros procesos. Máximos observados no son picos garantizados.']
    for run in runs:
        result = run.get('result') or {}
        lines += [code_block(json.dumps({'run_id':run['id'],'branch':run['branch'],'task_id':run['task_id'],
                   **{k:result.get(k) for k in ('agent_s','preparation_s','task_s','warmup','resources','failure_phase')}},ensure_ascii=False,indent=2))]
    for branch in ('A','B'):
        tasks = [snapshot['branch_tasks'][branch]] if snapshot.get('branch_tasks') else snapshot['tasks']
        selected = [r for r in runs if r['branch'] == branch]
        summary = summarize(selected,tasks)
        accuracy = f"{summary['correct']}/{summary['planned_evaluable']} casos con referencia" if summary['planned_evaluable'] else 'Sin casos con referencia'
        timing = f"{summary['mean_answer_s']:.3f} s" if summary['mean_answer_s'] is not None else 'Sin mediciones'
        lines += [f'## Variante {branch}\n',code_block(config['agents'][branch]['model']),
                  f"Aciertos: {accuracy}. "
                  f"Respuestas evaluadas: {summary['evaluated']}. Ejecuciones programadas: {summary['total']}.\n",
                  f"Incorrectas: {summary['incorrect']}. Formatos inválidos: {summary['invalid_format']}. "
                  f"Errores de ejecución: {summary['execution_errors']}. Sin evaluar: {summary['unscored']}. Pendientes: {summary['pending']}.\n",
                  f"Tiempo medio de respuestas sin error: {timing} ({summary['timed_answers']} mediciones).\n",
                  '### Configuración guardada\n',code_block(json.dumps(config['agents'][branch],ensure_ascii=False,indent=2))]
        by_id = {t['id']:t for t in tasks}
        for run in selected:
            task = by_id[run['task_id']]
            result = run.get('result') or {}
            reference = task.get('expected_answer')
            if task.get('criteria'):
                reference = json.dumps({k:task['criteria'][k] for k in ('total_cents','order_ids')},ensure_ascii=False,indent=2)
            lines += ['### Caso\n',code_block(run['task_id']),f"Repetición {run['repetition']+1} · {labels[outcome(run)]}\n",
                      'Respuesta recibida:\n',code_block(result.get('answer','No hay respuesta final.')),
                      'Referencia:\n',code_block(reference if reference is not None else 'Sin referencia')]
            if result.get('error') or result.get('reason'):
                lines.append(code_block(result.get('error') or result['reason']))
    evidence = {k:snapshot.get(k) for k in ('conditions','data_sha256','source_sha256','git_commit','git_worktree_dirty','host','protocol')}
    evidence['order_seed'] = config.get('order_seed')
    lines += ['## Condiciones y limitaciones\n',code_block(json.dumps(protocol,ensure_ascii=False,indent=2)),
              '### Evidencia de reproducibilidad\n',code_block(json.dumps(evidence,ensure_ascii=False,indent=2)),
              'El tiempo incluye preparación y puede incluir carga del modelo. No es latencia pura. Las simulaciones no miden modelos reales. '
              'El informe es parcial mientras haya ejecuciones pendientes. El JSON reproducible conserva entradas, archivos, fuentes y hashes completos.\n']
    return '\n'.join(lines)
