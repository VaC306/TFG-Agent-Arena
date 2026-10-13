"""Evidence correspondence, privacy boundary and reproducible generation."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'frontend/demo-assets/demo'


def test_selected_runs_are_original_and_sources_unchanged():
    catalog = json.loads((OUT / 'catalog.json').read_text(encoding='utf-8'))
    manifest = json.loads((OUT / 'manifest.json').read_text(encoding='utf-8'))
    assert len(catalog['experiments']) == 10
    assert sum(len(d['runs']) for d in catalog['details'].values()) == 72
    for relative, digest in manifest['sources'].items():
        raw = (ROOT / relative).read_bytes()
        if relative in manifest.get('lf_normalized_sources', []):
            raw = raw.replace(b'\r\n', b'\n')
        assert hashlib.sha256(raw).hexdigest() == digest
    for detail in catalog['details'].values():
        original = json.loads((ROOT / detail['selection']['source']).read_text(encoding='utf-8'))
        by_id = {r['id']: r for r in original['runs']}
        for run in detail['runs']:
            assert all(by_id[run['id']][k] == v for k, v in run.items() if k != 'result')
            assert all(by_id[run['id']]['result'][k] == v for k, v in run['result'].items())
        assert set(detail['snapshot']) == {'config','tasks','conditions','data_sha256'}
        assert set(detail['snapshot']['config']) <= {'name','adapter','split','repetitions','comparison','agents'}
        assert 'source' not in detail['snapshot'] and 'host' not in detail['snapshot']
        for b in ('A','B'):
            summary = detail['overviews'][b]
            assert summary['total'] == sum(r['branch'] == b for r in detail['runs'])
            assert summary['cancelled'] == sum(r['branch'] == b and r['status'] == 'cancelled' for r in detail['runs'])
    assert catalog['campaigns'] == []
    simulated = next(d for d in catalog['details'].values() if d['snapshot']['config']['adapter'] == 'simulated')
    assert simulated['overviews']['B']['cancelled'] == 1
    assert simulated['overviews']['B']['execution_errors'] == 0


def test_generation_is_deterministic():
    before = {str(p.relative_to(OUT)): p.read_bytes() for p in OUT.rglob('*') if p.is_file()}
    subprocess.run([sys.executable, str(ROOT / 'scripts/build_demo_data.py')], check=True, cwd=ROOT)
    after = {str(p.relative_to(OUT)): p.read_bytes() for p in OUT.rglob('*') if p.is_file()}
    assert before == after


def test_showcase_fixtures_and_replay_are_grounded_and_sanitized():
    catalog = json.loads((OUT / 'catalog.json').read_text(encoding='utf-8'))
    showcase = json.loads((OUT / 'showcase.json').read_text(encoding='utf-8'))
    assert len(showcase['suites']) == 8 and len(showcase['cases']) == 5
    for case in showcase['cases']:
        detail = catalog['details'][case['experiment_id']]
        assert any(r['id'] == case['run_id'] and r['branch'] == case['branch'] and r['task_id'] == case['task_id'] for r in detail['runs'])
    fixtures = json.loads((OUT / 'fixtures.json').read_text(encoding='utf-8'))
    assert len(fixtures['files']) == 7
    for fixture in fixtures['files']:
        assert fixture['content'] == (ROOT / fixture['source']).read_bytes().decode('utf-8')
    replay = json.loads((OUT / 'replay.json').read_text(encoding='utf-8'))
    original = [json.loads(line) for line in (ROOT / replay['source'] / 'events.jsonl').read_text(encoding='utf-8').splitlines()]
    by_seq = {e['seq']:e for e in original if e['run_id'] == replay['run_id']}
    assert len(replay['events']) == 20
    for event in replay['events']:
        source = by_seq[event['seq']]
        assert event['at'] == source['at'] and event['kind'] == source['kind']
        assert event['kind'] not in ('resources','inference_metadata')
        assert 'environment' not in event['payload']
        if event['kind'] != 'inference_response':
            assert all(source['payload'][key] == value for key,value in event['payload'].items())
        else:
            assert event['payload']['response']['message'] == source['payload']['response']['message']
    assert replay['events'][-1]['payload']['answer'] == '{"total_cents": 3500, "order_ids": ["O2", "O1"]}'
