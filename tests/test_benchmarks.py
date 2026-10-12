import asyncio
import copy
import json
import shutil
from pathlib import Path

import pytest
from arena.benchmarks import audit_experiment, bundle_path, load_suite, run_benchmark, validate_bundle
from arena.diagnostics import assess_call
from arena.store import Store

ROOT = Path(__file__).resolve().parents[1]/'benchmarks/v1'


def test_versioned_datasets_are_complete_and_references_match_fixtures():
    manifest = validate_bundle(ROOT)
    assert manifest['version'] == 'arena-benchmarks-v1'
    for split in ('dev','eval'):
        tasks,_ = load_suite(ROOT,'attachments',split)
        catalog = json.loads((ROOT/f'fixtures/catalog-{split}.json').read_text())
        import csv
        with (ROOT/f'fixtures/quantities-{split}.csv').open() as file:
            total = sum(catalog[r['sku']]*int(r['cantidad']) for r in csv.DictReader(file))
        assert json.loads(tasks[0].expected_answer)['total'] == total
    assert sum(len(load_suite(ROOT,s,'dev')[0]) for s in ('text','json','orders','attachments')) == 12
    assert sum(len(load_suite(ROOT,s,'eval')[0]) for s in ('text','json','orders','attachments')) == 18


def test_modified_or_unlisted_dataset_is_rejected(tmp_path):
    root = tmp_path/'bundle'
    shutil.copytree(ROOT,root)
    (root/'datasets/text-dev.csv').write_text('changed')
    with pytest.raises(ValueError,match='SHA-256'):
        validate_bundle(root)
    shutil.copyfile(ROOT/'datasets/text-dev.csv',root/'datasets/text-dev.csv')
    (root/'datasets/extra.csv').write_text('extra')
    with pytest.raises(ValueError,match='exactamente'):
        validate_bundle(root)
    with pytest.raises(ValueError):
        bundle_path(root,'../outside')


def test_isolated_probe_rejects_wrong_arguments_and_extra_calls():
    cases = json.loads((ROOT/'diagnostics/tool-calls.json').read_text())
    environment = json.loads((ROOT/'fixtures/orders.json').read_text())
    case = cases[0]
    response = {'message':{'tool_calls':[{'function':{'name':case['tool'],'arguments':case['arguments']}}]}}
    assert assess_call(response,case,environment)['correct']
    invalid = copy.deepcopy(response)
    invalid['message']['tool_calls'][0]['function']['arguments'] = {'customer_id':'C1','mes':'2026-01'}
    assert assess_call(invalid,case,environment)['arguments_valid'] is False
    invalid = copy.deepcopy(response)
    invalid['message']['tool_calls'] *= 2
    assert not assess_call(invalid,case,environment)['correct']
    assert not assess_call({'message':{'content':'No tool'}},case,environment)['correct']


def test_reproducible_runner_exports_and_audit_detects_corrupt_metrics(tmp_path,monkeypatch):
    class Fixture:
        def __init__(self,*args,**kwargs):
            pass
        async def metadata(self,model):
            return {'version':{'version':'fixture'},'model':{'digest':('a' if model == 'model-a' else 'b')*64},'show':{}}
        async def chat(self,messages,config,remaining):
            content = messages[-1]['content']
            answer = 'París' if 'Francia' in content else '42' if '17 + 25' in content else '11:15'
            return {'message':{'content':answer},'done':True,'prompt_eval_count':10,'eval_count':2,'eval_duration':20_000_000}
    monkeypatch.setattr('arena.adapters.Ollama',Fixture)
    monkeypatch.setattr('arena.worker.Ollama',Fixture)
    output = tmp_path/'results'
    results = asyncio.run(run_benchmark(ROOT,output,'model-a','model-b',suites=['text']))
    assert results[0]['audit_passed']
    assert results[0]['report']['comparison_scope'] == 'models'
    store = Store(output/'arena.sqlite')
    eid = results[0]['experiment_id']
    assert store.snapshot(eid)['benchmark']['version'] == 'arena-benchmarks-v1'
    assert {'snapshot.json','runs.json','events.jsonl','metrics.csv','summary.json','audit.json'} <= {p.name for p in (output/'text').iterdir()}
    with pytest.raises(FileExistsError):
        asyncio.run(run_benchmark(ROOT,output,'model-a','model-b',suites=['text']))
    run = store.list_runs(eid)[0]
    run['result']['output_tokens'] += 1
    with store.connect() as db:
        db.execute('UPDATE runs SET data=? WHERE id=?',(json.dumps(run),run['id']))
    audit = audit_experiment(store,eid)
    assert not audit['passed'] and any('tokens' in error for error in audit['errors'])
