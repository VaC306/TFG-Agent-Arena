import copy
import csv
import hashlib
import io
import json
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from arena.api import create_app
from arena.evaluator import EVALUATOR_VERSION
from arena.model_results import fingerprint
from arena.protocol import inference_identity
from arena.store import Store
from arena.task_analysis import campaign_analysis, task_analysis_csv
from conftest import register_client

ROOT = Path(__file__).resolve().parents[1]


def fixture(count=10,attempts=2,repetitions=1,adapter='ollama',split='eval'):
    tasks = [{'id':f'task-{i}','input':f'Unique input {i}','environment':'empty','expected_answer':'yes','evaluation':'exact_match'} for i in range(count)]
    snapshot = {'config':{'adapter':adapter,'split':split,'repetitions':repetitions,'agents':{
        b:{'model':f'model-{b}','system_prompt':'Same instructions'} for b in ('A','B')}},
        'tasks':tasks,'branch_tasks':None,'environments':{'empty':{'orders':[]}},
        'conditions':{'inputs_shared':True},'protocol':{'evaluator_version':EVALUATOR_VERSION}}
    reports,evidence = [],[]
    for sequence in range(1,attempts+1):
        runs = []
        for i,task in enumerate(tasks):
            for branch in ('A','B'):
                for repetition in range(repetitions):
                    success = i%4 < (1 if branch == 'A' else 2)
                    runs.append({'id':str(uuid.uuid4()),'task_id':task['id'],'branch':branch,'repetition':repetition,
                        'status':'succeeded' if success else 'failed',
                        'result':{'answer':'yes' if success else 'no','success':success,'format_ok':None,
                                  'agent_s':1.,'evaluator_version':EVALUATOR_VERSION}})
        reports.append({'sequence':sequence,'experiment_id':str(sequence),'complete':True,'compatible':True,'warnings':[]})
        evidence.append({'experiment_id':str(sequence),'snapshot':copy.deepcopy(snapshot),'runs':runs})
    return snapshot,reports,evidence


def case(analysis,tid,branch='A'):
    return next(t for t in analysis['tasks'] if t['task_id'] == tid)['branches'][branch]


def test_quality_coverage_errors_format_and_between_attempt_changes_are_distinct():
    snapshot,reports,evidence = fixture(count=3,adapter='simulated')
    def set_run(attempt,tid,branch,status,result):
        run = next(r for r in evidence[attempt]['runs'] if r['task_id'] == tid and r['branch'] == branch)
        run.update(status=status,result=result)
    set_run(0,'task-0','A','succeeded',{'answer':'yes','success':True,'agent_s':2})
    set_run(1,'task-0','A','failed',{'answer':'no','success':False,'agent_s':4})
    set_run(0,'task-1','A','timeout',{'error':'timeout','success':False,'agent_s':100})
    set_run(1,'task-1','A','failed',{'answer':'bad JSON','success':False,'format_ok':False,'agent_s':6})
    snapshot['tasks'][2]['expected_answer'] = None
    for item in evidence:
        for run in item['runs']:
            if run['task_id'] == 'task-2': run.update(status='completed',result={'answer':'open','success':None,'agent_s':8})
    analysis = campaign_analysis(snapshot,reports,evidence)
    variable = case(analysis,'task-0')
    assert variable['quality_stability'] == 'variable'
    assert variable['summary']['correct'] == 1 and variable['summary']['evaluated'] == 2
    assert variable['quality_rate'] == .5 and variable['coverage'] == 1
    assert variable['between_attempt_changes'] == variable['between_attempt_comparisons'] == 1
    broken = case(analysis,'task-1')
    assert broken['summary']['execution_errors'] == broken['summary']['invalid_format'] == 1
    assert broken['quality_rate'] == 0 and broken['coverage'] == .5
    assert broken['summary']['mean_answer_s'] == 6
    assert broken['quality_stability'] == 'insufficient'
    opened = case(analysis,'task-2')
    assert opened['summary']['unscored'] == 2
    assert opened['quality_rate'] is None and opened['coverage'] is None
    paired = analysis['paired']
    assert paired['planned_pairs'] == 4 and paired['missing_pairs'] == 1
    assert paired['mean_B_minus_A'] is None and paired['interval'] is None


def test_changes_detect_format_and_execution_variation_without_false_quality_variance():
    snapshot,reports,evidence = fixture(count=1,adapter='simulated')
    for index,item in enumerate(evidence):
        run = next(r for r in item['runs'] if r['branch'] == 'A')
        run.update(status='failed',result={'answer':'wrong','success':False,'format_ok':index == 0})
    values = case(campaign_analysis(snapshot,reports,evidence),'task-0')
    assert values['quality_stability'] == 'always_incorrect'
    assert values['between_attempt_changes'] == 1


def test_incompatible_and_pending_attempts_are_explicitly_excluded():
    snapshot,reports,evidence = fixture(attempts=3)
    reports[1].update(compatible=False,warnings=['Code changed'])
    reports[2].update(compatible=False,complete=False,warnings=['Pending'])
    analysis = campaign_analysis(snapshot,reports,evidence)
    assert [a['sequence'] for a in analysis['included_attempts']] == [1]
    assert [a['sequence'] for a in analysis['excluded_attempts']] == [2,3]
    assert case(analysis,'task-0')['summary']['total'] == 1
    assert case(analysis,'task-0')['quality_stability'] == 'insufficient'
    assert analysis['paired']['interval'] is None


@pytest.mark.parametrize('defect',['missing','duplicate'])
def test_incomplete_run_plan_is_not_treated_as_a_complete_sample(defect):
    snapshot,reports,evidence = fixture()
    if defect == 'missing': evidence[1]['runs'].pop()
    else: evidence[1]['runs'][-1] = copy.deepcopy(evidence[1]['runs'][0])
    analysis = campaign_analysis(snapshot,reports,evidence)
    assert len(analysis['included_attempts']) == 1
    assert 'plan de ejecuciones' in analysis['excluded_attempts'][0]['reasons'][0]


def test_independent_branch_inputs_are_not_paired_even_when_ids_match():
    snapshot,reports,evidence = fixture(count=1)
    snapshot['branch_tasks'] = {'A':snapshot['tasks'][0],'B':snapshot['tasks'][0] | {'input':'Different input'}}
    snapshot['conditions']['inputs_shared'] = False
    analysis = campaign_analysis(snapshot,reports,evidence)
    assert len(analysis['tasks']) == 1
    assert case(analysis,'task-0')['summary']['total'] == 2
    assert analysis['paired']['planned_pairs'] == 0
    assert analysis['paired']['mean_B_minus_A'] is None
    assert analysis['paired']['scope'] == 'configurations'


@pytest.mark.parametrize('policy',['few_tasks','one_attempt','simulation','development','duplicate_inputs','constant_difference','missing_scores'])
def test_uncertainty_is_suppressed_when_its_conditions_are_not_met(policy):
    snapshot,reports,evidence = fixture()
    if policy == 'few_tasks': snapshot,reports,evidence = fixture(count=3)
    if policy == 'one_attempt': snapshot,reports,evidence = fixture(attempts=1)
    if policy == 'simulation': snapshot['config']['adapter'] = 'simulated'
    if policy == 'development': snapshot['config']['split'] = 'dev'
    if policy == 'duplicate_inputs': snapshot['tasks'][1]['input'] = snapshot['tasks'][0]['input']
    if policy == 'constant_difference':
        for item in evidence:
            for run in item['runs']: run.update(status='succeeded',result={'answer':'yes','success':True})
    if policy == 'missing_scores': evidence[0]['runs'][0].update(status='timeout',result={'error':'timeout','success':False})
    paired = campaign_analysis(snapshot,reports,evidence)['paired']
    assert paired['interval'] is None and paired['interval_unavailable_reasons']


def test_bootstrap_is_deterministic_and_repetitions_do_not_inflate_task_sample_size():
    snapshot,reports,evidence = fixture()
    first = campaign_analysis(snapshot,reports,evidence)['paired']
    second = campaign_analysis(snapshot,reports,evidence)['paired']
    assert first == second
    assert first['interval'] is not None and first['mean_B_minus_A'] == pytest.approx(.3)
    snapshot,reports,evidence = fixture(repetitions=10)
    repeated = campaign_analysis(snapshot,reports,evidence)['paired']
    assert repeated['planned_pairs'] == 200 and first['planned_pairs'] == 20
    assert repeated['task_count'] == first['task_count'] == 10
    assert repeated['interval'] == first['interval']
    assert repeated['method']['input_sha256'] == first['method']['input_sha256']
    assert repeated['method']['unit'] == 'task'


def test_all_excluded_and_no_reference_yield_no_false_zero_percentages():
    snapshot,reports,evidence = fixture(count=1)
    for r in reports: r.update(compatible=False,warnings=['Unknown model'])
    analysis = campaign_analysis(snapshot,reports,evidence)
    assert analysis['included_attempts'] == []
    assert case(analysis,'task-0')['quality_rate'] is None
    assert analysis['paired']['mean_B_minus_A'] is None
    snapshot,reports,evidence = fixture(count=1)
    snapshot['tasks'][0]['expected_answer'] = None
    for item in evidence:
        for run in item['runs']: run.update(status='completed',result={'answer':'open','success':None})
    paired = campaign_analysis(snapshot,reports,evidence)['paired']
    assert paired['task_count'] == paired['planned_pairs'] == 0
    assert paired['coverage'] is None


def test_task_csv_preserves_counts_and_protects_formula_like_strings():
    snapshot,reports,evidence = fixture(count=1,adapter='simulated')
    snapshot['tasks'][0].update(id='=task',input='=SUM(1,2)')
    for item in evidence:
        for run in item['runs']: run['task_id'] = '=task'
    analysis = campaign_analysis(snapshot,reports,evidence)
    report = {'id':'campaign','design_sha256':fingerprint(snapshot),'analysis':analysis}
    rows = list(csv.DictReader(io.StringIO(task_analysis_csv(report))))
    assert len(rows) == 2
    assert rows[0]['task_id'] == "'=task" and rows[0]['input_preview'].startswith("'=")
    assert int(rows[0]['evaluated']) == 2
    assert len(json.loads(rows[0]['series'])) == 2


def test_analysis_api_exports_are_consistent_account_scoped_and_reproducible(tmp_path):
    path = tmp_path/'analysis.sqlite'
    client,other = TestClient(create_app(path,ROOT)),TestClient(create_app(path,ROOT))
    register_client(client)
    register_client(other,'other')
    body = {'name':'Controlled analysis','adapter':'ollama','comparison':'different_models','split':'eval',
            'agents':{b:{'model':'model-'+b,'system_prompt':'Same instructions'} for b in ('A','B')},
            'dataset':[{'id':f'case-{i}','input':f'Input {i}','expected_answer':'yes'} for i in range(10)]}
    eid = client.post('/comparisons',json=body).json()['id']
    store = Store(path)
    def finish():
        while run := store.claim():
            i = int(run['task_id'].split('-')[1]); b = run['branch']
            success = i%4 < (1 if b == 'A' else 2)
            identity = inference_identity('model-'+b,{'version':{'version':'controlled'},'model':{'digest':b.lower()*64},'show':{}})
            store.finish(run,{'answer':'yes' if success else 'no','success':success,'agent_s':1,
                              'evaluator_version':EVALUATOR_VERSION,'inference_identity':identity},'succeeded' if success else 'failed')
    finish()
    cid = client.post('/campaigns',json={'name':'Controlled analysis','experiment_id':eid}).json()['id']
    assert client.post('/campaigns/'+cid+'/attempts',json={'request_id':str(uuid.uuid4())}).status_code == 201
    finish()
    report = client.get('/campaigns/'+cid).json()
    analysis = report['analysis']
    assert analysis['paired']['interval'] is not None
    exported = client.get('/campaigns/'+cid+'/export.json').json()
    assert exported['analysis'] == analysis
    for name,source in exported['analysis_sources'].items():
        assert hashlib.sha256(source.encode()).hexdigest() == analysis['source_sha256'][name]
    response = client.get('/campaigns/'+cid+'/analysis.csv')
    assert 'attachment;' in response.headers['content-disposition']
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert len(rows) == 20
    for row in rows:
        values = case(analysis,row['task_id'],row['branch'])
        assert int(row['correct']) == values['summary']['correct']
        assert float(row['coverage']) == values['coverage']
    for branch in ('A','B'):
        assert sum(t['branches'][branch]['summary']['correct'] for t in analysis['tasks']) == sum(a['overviews'][branch]['correct'] for a in report['attempts'])
    markdown = client.get('/campaigns/'+cid+'/export.md').text
    assert 'Análisis por tarea' in markdown and 'task_cluster_bootstrap_BCa' in markdown
    assert other.get('/campaigns/'+cid+'/analysis.csv').status_code == 404
    partial = client.post('/campaigns/'+cid+'/attempts',json={'request_id':str(uuid.uuid4())})
    assert partial.status_code == 201
    report = client.get('/campaigns/'+cid).json()
    assert len(report['analysis']['excluded_attempts']) == 1
    assert report['analysis']['paired']['interval'] is None
