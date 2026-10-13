"""Additional demo-only, synthetic fixtures and a selected historical replay."""
import json


def build_showcase(read, pick, save, details):
    suites = []
    for eid, detail in details.items():
        source = detail['selection']['source']
        if source.startswith('benchmarks/v1/results/'):
            suites.append({'experiment_id': eid, 'suite': source.rsplit('/', 1)[1].removesuffix('.json'),
                           'split': detail['snapshot']['config']['split']})

    def case(suffix, predicate, title, question, explanation):
        eid, detail = next((eid, d) for eid, d in details.items() if d['selection']['source'].endswith(suffix))
        run = next(r for r in detail['runs'] if predicate(r))
        return {'experiment_id': eid, 'run_id': run['id'], 'task_id': run['task_id'], 'branch': run['branch'],
                'title': title, 'question': question, 'explanation': explanation}

    cases = [
        case('/text.json', lambda r: r['branch'] == 'A' and r['result'].get('success') is True,
             'Una respuesta correcta', '¿Qué significa un acierto?', 'La respuesta coincide con la referencia y el criterio registrado. Solo describe este caso.'),
        case('local-flow-2026-10-12/reproducibility.json', lambda r: r['branch'] == 'A' and r['task_id'] == 'capital',
             'Paris frente a París', '¿Qué cambia una tilde?', 'Texto exacto conserva acentos. Paris no coincide con París. Este fallo no demuestra peor razonamiento.'),
        case('/dev/orders.json', lambda r: r['branch'] == 'A' and r['result'].get('format_ok') is False,
             'Una respuesta que rompe el formato', '¿Completar significa acertar?', 'La ejecución devuelve texto, pero no cumple el JSON exigido. Un fallo de formato se distingue de un error de ejecución.'),
        case('/dev/orders.json', lambda r: r['branch'] == 'B' and bool(r['result'].get('error')),
             'Calidad y cobertura', '¿Un 100 % puede ocultar errores?', 'B tiene 1/1 respuestas evaluadas correctas, pero 1/4 ejecuciones programadas correctas y tres errores. Consulta ambos denominadores.'),
        case('simulated-reproducibility.json', lambda r: r['status'] == 'cancelled',
             'Una cancelación guardada', '¿Cómo se conserva lo que no terminó?', 'Esta cancelación pertenece al simulador. Se conserva como cancelada, sin convertirla en una respuesta incorrecta ni una prueba de calidad de un modelo real.'),
    ]
    save('showcase.json', {'suites': suites, 'cases': cases})
    fixtures = []
    for split in ('dev', 'eval'):
        for name in (f'catalog-{split}.json', f'quantities-{split}.csv', f'note-{split}.txt'):
            source = 'benchmarks/v1/fixtures/' + name
            fixtures.append({'name': name, 'split': split, 'content': read(source), 'source': source})
    fixtures.append({'name': 'orders.json', 'split': 'shared', 'content': read('benchmarks/v1/fixtures/orders.json'),
                     'source': 'benchmarks/v1/fixtures/orders.json'})
    save('fixtures.json', {'note': 'Fixtures sintéticos del benchmark; sin datos personales reales. No son datos recibidos de visitantes.', 'files': fixtures})

    source = 'experiments/simulated-dev-final-2026-10-08'
    snapshot = json.loads(read(source + '/snapshot.json'))
    original = json.loads(read(source + '/runs.json'))
    run = next(r for r in original if r['task_id'] == 'dev-partial-return' and r['branch'] == 'B' and r['repetition'] == 0)
    task = next(t for t in snapshot['tasks'] if t['id'] == run['task_id'])
    events = []
    for line in read(source + '/events.jsonl').splitlines():
        event = json.loads(line)
        if event['run_id'] != run['id']: continue
        payload = event['payload']
        if event['kind'] == 'input': selected = pick(payload, 'messages')
        elif event['kind'] == 'inference_request': selected = pick(payload, 'messages max_output_tokens')
        elif event['kind'] == 'inference_response':
            selected = {'response': pick(payload['response'], 'message done done_reason simulated'), **pick(payload, 'duration_s')}
        elif event['kind'] in ('tool_request', 'tool_result'): selected = pick(payload, 'name arguments result error duration_s')
        elif event['kind'] == 'finished': selected = pick(payload, 'status success format_ok answer reason tool_calls tool_errors')
        else: continue  # Host resources and engine metadata are intentionally not published.
        events.append({'seq': event['seq'], 'kind': event['kind'], 'at': event['at'], 'payload': selected})
    save('replay.json', {'source': source, 'run_id': run['id'], 'branch': run['branch'], 'task': pick(task, 'id input criteria'),
                          'system_prompt': snapshot['config']['agents'][run['branch']]['system_prompt'],
                          'events': events, 'note': 'Reproducción de traza guardada del 08/10/2026 · simulador. No se ejecuta un modelo ni se muestra razonamiento interno. Selección de eventos: sin recursos ni metadatos privados. Los tiempos pertenecen al simulador.'})
