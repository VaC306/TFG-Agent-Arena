import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from arena.api import create_app
from arena.store import Store
from conftest import register_client
from test_comparisons import request_data, upload

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def client(tmp_path):
    result = TestClient(create_app(tmp_path / 'validation.sqlite', ROOT))
    register_client(result)
    return result


@pytest.mark.parametrize('repetitions', [True, 1.5, '2', None, 0, 11])
def test_invalid_repetitions_leave_no_history(client, repetitions):
    data = request_data()
    data['repetitions'] = repetitions
    assert client.post('/comparisons', json=data).status_code == 422
    assert client.get('/experiments').json() == []


@pytest.mark.parametrize('field,value', [('name', '   '), ('name', 'x' * 121),
                                       ('text', '  '), ('text', 'x' * 6001),
                                       ('text', '\x00'), ('text', '\ud800')])
def test_invalid_text_leave_no_history(client, field, value):
    data = request_data()
    if field == 'name':
        data['name'] = value
    else:
        data['branch_inputs']['A']['text'] = value
    # Raw JSON allows testing invalid Unicode without the HTTP client's encoder rejecting it first.
    import json
    result = client.post('/comparisons', content=json.dumps(data), headers={'Content-Type':'application/json'})
    assert result.status_code == 422
    assert client.get('/experiments').json() == []


def test_optional_reference_and_exact_text_limits(client):
    data = request_data()
    data['name'] = 'x' * 120
    data['branch_inputs']['A']['text'] = '😀' * 6000
    data['branch_inputs']['A']['expected_answer'] = '   '
    assert client.post('/comparisons', json=data).status_code == 201
    data['branch_inputs']['A']['expected_answer'] = 'x' * 6001
    assert client.post('/comparisons', json=data).status_code == 422


@pytest.mark.parametrize('body', ['{"display_name":"ok","display_name":"other"}',
                                '{"display_name":NaN}', '{"display_name":' + '[' * 1500 + '0' + ']' * 1500 + '}'])
def test_bad_json_is_safe_client_error(client, body):
    assert client.patch('/profile', content=body).status_code == 422


def test_blank_password_and_strict_preferences(client):
    response = client.post('/auth/register', json={'username':'other','display_name':'Other','password':' ' * 12})
    assert response.status_code == 422 and 'input' not in response.json()['detail'][0]
    prefs = client.get('/auth/session').json()['user']['preferences']
    prefs['repetitions'] = True
    assert client.put('/profile/preferences', json=prefs).status_code == 422


@pytest.mark.parametrize('content', ['"' + 'a' * 140000, '{"id":"a","input":"x","input":"y"}', '{"id":"a","input":NaN}'], ids=['large-header','duplicate-key','nonfinite'])
def test_malformed_dataset_returns_422(client, content):
    extension = 'csv' if content.startswith('"') else 'jsonl'
    assert client.post('/datasets/validate', json={'filename':'cases.' + extension,'content':content}).status_code == 422


def test_duplicate_json_attachment_returns_422(client):
    data = request_data()
    data['branch_inputs']['A']['files'] = [upload('data.json', b'{"x":1,"x":2}')]
    assert client.post('/comparisons', json=data).status_code == 422
    assert client.get('/experiments').json() == []


def clear(client, state):
    return client.request('DELETE', '/profile/history', json={'confirmation':'clear-history','revision':state['revision']})


def test_history_clear_is_atomic_scoped_and_preserves_account(tmp_path):
    path = tmp_path / 'history.sqlite'
    app = create_app(path, ROOT)
    alice, bob = TestClient(app), TestClient(app)
    register_client(alice, 'alice')
    register_client(bob, 'bob')
    own = alice.post('/comparisons', json=request_data()).json()['id']
    other = bob.post('/comparisons', json=request_data()).json()['id']
    before = alice.get('/auth/session').json()
    state = alice.get('/profile/history').json()
    assert state['count'] == 1 and state['pending'] == 2
    assert clear(alice, state).status_code == 409
    with Store(path).connect() as db:
        db.execute("UPDATE runs SET status='cancelled' WHERE experiment_id=?", (own,))
    assert alice.request('DELETE', '/profile/history', json={'revision':state['revision']}).status_code == 422
    assert clear(alice, state).json() == {'deleted':1}
    assert alice.get('/experiments').json() == []
    assert alice.get('/experiments/' + own).status_code == 404
    assert bob.get('/experiments/' + other).status_code == 200
    assert alice.get('/auth/session').json() == before
    with Store(path).connect() as db:
        assert not db.execute('SELECT 1 FROM runs WHERE experiment_id=?', (own,)).fetchone()
        assert not db.execute('SELECT 1 FROM events e LEFT JOIN runs r ON r.id=e.run_id WHERE r.id IS NULL').fetchone()
    assert clear(alice, alice.get('/profile/history').json()).json() == {'deleted':0}


def test_stale_revision_does_not_delete_new_history(client):
    old = client.get('/profile/history').json()
    client.post('/comparisons', json=request_data())
    assert clear(client, old).status_code == 409
    assert len(client.get('/experiments').json()) == 1


def test_clear_requires_session_and_csrf(tmp_path):
    client = TestClient(create_app(tmp_path / 'csrf.sqlite', ROOT))
    assert client.get('/profile/history').status_code == 401
    assert clear(client, {'revision':'a' * 64}).status_code == 403
    client.headers['X-Arena-Request'] = '1'
    assert clear(client, {'revision':'a' * 64}).status_code == 401


def test_preview_counts_and_clear_deletes_more_than_list_limit(tmp_path):
    from arena.comparisons import ComparisonRequest, submit_comparison
    path = tmp_path / 'full-history.sqlite'
    client = TestClient(create_app(path, ROOT))
    register_client(client)
    owner = client.get('/auth/session').json()['user']['id']
    store = Store(path, owner_id=owner)
    for _ in range(52):
        submit_comparison(store, ComparisonRequest.model_validate(request_data()))
    with store.connect() as db:
        db.execute("UPDATE runs SET status='cancelled'")
    assert len(client.get('/experiments').json()) == 50
    state = client.get('/profile/history').json()
    assert state['count'] == 52
    assert clear(client, state).json() == {'deleted':52}
    assert client.get('/experiments').json() == []


def test_preset_duplicate_keys_and_invalid_dataset_name(client):
    assert client.post('/experiments', content='{"config":"simulated","config":"ollama"}').status_code == 422
    assert client.post('/datasets/validate', json={'filename':'../cases.csv', 'content':'id,input\na,x'}).status_code == 422
    assert client.get('/experiments?limit=0').status_code == 422
