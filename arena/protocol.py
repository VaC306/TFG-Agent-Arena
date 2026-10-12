"""Explicit evaluation and reproducibility evidence; never infer semantic quality."""
import hashlib
import json
import re


def inference_identity(identifier, metadata):
    model = metadata.get('model')
    model = model if isinstance(model, dict) else {}
    identity = {'identifier': identifier if ':' in identifier else identifier + ':latest',
                'adapter': metadata.get('adapter', 'ollama'), 'digest': model.get('digest'),
                'server_version': metadata.get('version', {}).get('version'),
                'quantization': model.get('details', {}).get('quantization_level')}
    identity['verified'] = bool(isinstance(identity['digest'], str) and re.fullmatch(r'[a-fA-F0-9]{64}', identity['digest'])
                                and isinstance(identity['server_version'], str) and identity['server_version'])
    # Includes server-side template/defaults/capabilities, independent of modified_at.
    identity['fingerprint'] = hashlib.sha256(json.dumps(
        identity | {'show':metadata.get('show')}, sort_keys=True).encode()).hexdigest()
    return identity


def quality_value(run):
    result = run.get('result') or {}
    if result.get('error') or run['status'] not in ('completed', 'succeeded', 'failed'):
        return None
    return result.get('success') if isinstance(result.get('success'), bool) else None


def protocol_report(snapshot, runs):
    config = snapshot['config']
    agents = config['agents']
    shared = snapshot.get('conditions', {}).get('inputs_shared', not snapshot.get('branch_tasks'))
    prompts_equal = agents['A']['system_prompt'] == agents['B']['system_prompt']
    parameters_equal = all(agents['A'].get(k) == agents['B'].get(k)
                           for k in ('temperature', 'seed', 'num_ctx', 'limits', 'tools_enabled'))
    identifiers = [a.get('model', '') for a in agents.values()]
    models_equal = len({m if ':' in m else m + ':latest' for m in identifiers}) == 1
    tasks = list((snapshot.get('branch_tasks') or {}).values()) or snapshot['tasks']
    identities = {r['branch']: (r.get('result') or {}).get('inference_identity') for r in runs
                  if (r.get('result') or {}).get('inference_identity')}
    warnings = []
    same_digest = (set(identities) == {'A', 'B'} and all(i['verified'] for i in identities.values())
                   and identities['A']['digest'] == identities['B']['digest'])
    if same_digest and not models_equal:
        warnings.append('Los identificadores distintos apuntan al mismo digest de modelo. No representan dos modelos diferentes.')
        models_equal = True
    if config['adapter'] == 'simulated':
        warnings.append('Simulación: tokens y tiempo de generación sintéticos. El tiempo del agente mide el simulador, no un modelo real; no aporta evidencia sobre calidad de modelos reales.')
    if not shared:
        warnings.append('Entradas independientes: las diferencias no se pueden atribuir solo al prompt o al modelo.')
    if not prompts_equal:
        warnings.append('Los prompts son distintos: se comparan configuraciones, no solo modelos.')
    if not parameters_equal:
        warnings.append('Los parámetros de A y B son distintos.')
    if snapshot.get('git_worktree_dirty'):
        warnings.append('Había cambios sin commit al guardar. Para identificar el código, usa también las fuentes y hashes del informe.')
    if any('identidad del modelo' in (r.get('result') or {}).get('error', '') for r in runs):
        warnings.append('Se detectó un cambio de modelo o servidor. Las ejecuciones afectadas se detuvieron antes de enviar la entrada.')
    if any(t.get('evaluation', 'exact_match') == 'none' or not t.get('expected_answer') and not t.get('criteria') for t in tasks):
        warnings.append('Hay casos sin evaluación automática de calidad. Las respuestas abiertas requieren revisión humana.')
    if config['adapter'] != 'simulated' and (set(identities) != {'A', 'B'} or not all(i['verified'] for i in identities.values())):
        warnings.append('La identidad de ambos modelos aún no está verificada. Se registra al ejecutar, no al guardar.')
    warnings.append('Sin calentamiento previo. El tiempo del agente incluye consulta de metadatos y puede incluir carga del modelo.')
    warnings.append('Política de memoria del modelo (keep_alive): ' + snapshot.get('conditions', {}).get('keep_alive', 'no registrada') + '. No se garantiza un inicio en frío si otro programa lo tiene cargado.')
    warnings.append('Semilla fija no garantiza respuestas idénticas. La carga de otros programas no está aislada.')
    if config['repetitions'] > 1:
        warnings.append('Las repeticiones de un mismo caso no son observaciones independientes.')
    branches = {}
    for branch in ('A', 'B'):
        selected = [r for r in runs if r['branch'] == branch]
        scored = [quality_value(r) for r in selected if quality_value(r) is not None]
        answers = [r for r in selected if 'answer' in (r.get('result') or {}) and not (r.get('result') or {}).get('error')]
        times = [(r['result'])['agent_s'] for r in answers if isinstance(r['result'].get('agent_s'), (int, float))]
        branches[branch] = {'total':len(selected), 'answers':len(answers), 'evaluated':len(scored),
                            'correct':sum(scored), 'execution_errors':sum(bool((r.get('result') or {}).get('error')) for r in selected),
                            'mean_answer_s':sum(times) / len(times) if times else None}
    return {'version':snapshot.get('protocol', {}).get('version', 'legacy'),
            'evaluator_version':snapshot.get('protocol', {}).get('evaluator_version', 'legacy'),
            'comparison_scope':('repeatability' if models_equal else 'models') if shared and prompts_equal and parameters_equal else 'configurations',
            'inputs_shared':shared, 'prompts_equal':prompts_equal, 'parameters_equal':parameters_equal,
            'evaluations':sorted({t.get('evaluation', 'exact_match') if not t.get('criteria') else 'order_benchmark' for t in tasks}),
            'models':identities, 'branches':branches, 'warnings':warnings}
