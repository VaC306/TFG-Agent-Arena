"""Small, explicit tool-call probes; separate from model-quality benchmarks."""
import copy
import hashlib
import json
import time
from pathlib import Path

import httpx
from .adapters import Ollama
from .contracts import AgentConfig
from .protocol import inference_identity
from .resources import provenance
from .tools import SCHEMAS, Tools


def assess_call(response, case, environment):
    calls = response.get('message', {}).get('tool_calls') or []
    if len(calls) != 1:
        return {'correct':False,'reason':'Se esperaba exactamente una llamada a herramienta'}
    function = calls[0].get('function', {})
    try:
        result = Tools(environment).call(function.get('name'), function.get('arguments'))
    except Exception as exc:
        return {'correct':False,'reason':str(exc),'arguments_valid':False}
    correct = function.get('name') == case['tool'] and function.get('arguments') == case['arguments']
    return {'correct':correct,'arguments_valid':True,'tool_result':result,
            'reason':'Llamada y argumentos correctos' if correct else 'Herramienta o argumentos distintos de la referencia'}


async def diagnose_tools(models, output, cases_path, environment_path, url='http://127.0.0.1:11434'):
    cases_path, environment_path = Path(cases_path), Path(environment_path)
    cases = json.loads(cases_path.read_text(encoding='utf-8'))
    environment = json.loads(environment_path.read_text(encoding='utf-8'))
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    adapter = Ollama(url, keep_alive='0')
    report = {'version':'tool-diagnostics-v1','models':{},'host':provenance(),
              'cases':cases,'environment':environment,
              'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')},
              'inputs_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (cases_path,environment_path)},
              'conditions':{'temperature':0,'seed':42,'num_ctx':4096,'max_output_tokens':256,
                            'keep_alive':'0','warmup':'none','timeout_s':120},'probes':[],
              'note':'Synthetic development probes, one observation per condition. Not a quality ranking or statistical benchmark.'}

    def save():
        (output/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')

    async with httpx.AsyncClient(timeout=120,trust_env=False) as client:
        for model in models:
            metadata = await adapter.metadata(model)
            report['models'][model] = {'identity':inference_identity(model,metadata),'metadata':metadata}
            config = AgentConfig(model=model, system_prompt='Usa la herramienta solicitada con sus argumentos exactos. No respondas de memoria.',num_ctx=4096)
            for case in cases:
                for condition in ('single_tool','all_tools'):
                    messages = [{'role':'system','content':config.system_prompt},{'role':'user','content':case['input']}]
                    payload = adapter.payload(messages,config,256)
                    if condition == 'single_tool':
                        payload['tools'] = [copy.deepcopy(t) for t in SCHEMAS if t['function']['name'] == case['tool']]
                    probe = {'model':model,'case':case['id'],'condition':condition,'request':payload}
                    start = time.perf_counter()
                    try:
                        response = await client.post(url+'/api/chat',json=payload)
                        response.raise_for_status()
                        data = response.json()
                        data.get('message',{}).pop('thinking',None)
                        probe['response'] = data
                        probe['assessment'] = assess_call(data,case,environment)
                        if data.get('done') is not True or data.get('done_reason') == 'length':
                            probe['assessment'] = {'correct':False,'reason':'Respuesta incompleta o truncada'}
                        if probe['assessment']['correct']:
                            continuation = adapter.payload(messages + [data['message'],{
                                'role':'tool','tool_name':case['tool'],
                                'content':json.dumps(probe['assessment']['tool_result'],ensure_ascii=False)},
                                {'role':'user','content':'Devuelve únicamente el resultado de la herramienta como JSON válido, sin cambiar los datos ni llamar más herramientas.'}],config,256)
                            continuation.pop('tools',None)
                            probe['continuation_request'] = continuation
                            final = await client.post(url+'/api/chat',json=continuation)
                            final.raise_for_status()
                            final_data = final.json()
                            final_data.get('message',{}).pop('thinking',None)
                            probe['continuation_response'] = final_data
                            from .evaluator import json_equal
                            from .json_input import load_json
                            try:
                                probe['continuation_correct'] = (final_data.get('done') is True
                                    and final_data.get('done_reason') != 'length'
                                    and json_equal(load_json(final_data['message']['content']),probe['assessment']['tool_result']))
                            except (ValueError,KeyError,TypeError):
                                probe['continuation_correct'] = False
                    except Exception as exc:
                        probe['error'] = f'{type(exc).__name__}: {exc}'
                    probe['elapsed_s'] = time.perf_counter()-start
                    report['probes'].append(probe)
                    save()
                    print(f"{model} {case['id']} {condition}: {probe.get('assessment',{}).get('correct')} error={probe.get('error')}",flush=True)
    save()
    return report
