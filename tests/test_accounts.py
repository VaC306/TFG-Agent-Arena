import hashlib
import time
from pathlib import Path
from fastapi.testclient import TestClient
from arena.accounts import Accounts, COOKIE, Preferences
from arena.api import create_app
from arena.store import Store
from arena.scheduler import submit
from conftest import register_client

ROOT = Path(__file__).resolve().parents[1]


def test_isolation_for_history_details_exports_events_and_cancellation(tmp_path):
    app = create_app(tmp_path / 'accounts.sqlite', ROOT)
    alice, bob = TestClient(app), TestClient(app)
    register_client(alice, 'alice')
    eid = alice.post('/experiments', json={'config':'simulated'}).json()['id']
    rid = alice.get('/experiments/' + eid).json()['runs'][0]['id']
    register_client(bob, 'bob')
    assert bob.get('/experiments').json() == []
    for path in [f'/experiments/{eid}', f'/experiments/{eid}/metrics.csv', f'/runs/{rid}/events']:
        assert bob.get(path).status_code == 404
        assert alice.get(path).status_code == 200
    assert bob.post(f'/runs/{rid}/cancel').status_code == 404
    assert alice.post(f'/runs/{rid}/cancel').status_code == 200


def test_preferences_and_profile_persist_across_login(tmp_path):
    app = create_app(tmp_path / 'accounts.sqlite', ROOT)
    client = TestClient(app)
    register_client(client)
    prefs = Preferences(modelA='local-model', repetitions=3).model_dump()
    prefs['promptA']['text'] = 'Mis instrucciones'
    assert client.put('/profile/preferences', json=prefs).status_code == 200
    assert client.patch('/profile', json={'display_name':'Nuevo nombre'}).status_code == 200
    cookie = client.cookies.get(COOKIE)
    assert client.post('/auth/logout').status_code == 200
    assert client.get('/experiments').status_code == 401
    # Revocation also prevents replay of an old cookie.
    stale = TestClient(app)
    stale.cookies.set(COOKIE, cookie)
    assert stale.get('/experiments').status_code == 401
    response = client.post('/auth/login', json={'username':'TESTER','password':'test-password-123'})
    assert response.status_code == 200
    user = response.json()['user']
    assert user['display_name'] == 'Nuevo nombre' and user['preferences'] == prefs
    assert 'password' not in response.text and 'salt' not in response.text
    register_client(TestClient(app), 'other')
    other = TestClient(app)
    other.headers['X-Arena-Request'] = '1'
    user2 = other.post('/auth/login', json={'username':'other','password':'test-password-123'}).json()['user']
    assert user2['preferences'] != prefs


def test_cookie_expiry_hashes_and_no_plaintext_password(tmp_path):
    path = tmp_path / 'accounts.sqlite'
    client = TestClient(create_app(path, ROOT))
    client.headers['X-Arena-Request'] = '1'
    result = client.post('/auth/register', json={'username':'alice','password':'long-secret-password','display_name':'Alice'})
    assert 'HttpOnly' in result.headers['set-cookie'] and 'SameSite=strict' in result.headers['set-cookie']
    token = client.cookies.get(COOKIE)
    with Store(path).connect() as db:
        row = db.execute('SELECT * FROM users').fetchone()
        assert row['password_hash'] != 'long-secret-password'
        session = db.execute('SELECT * FROM sessions').fetchone()
        assert session['token_hash'] == hashlib.sha256(token.encode()).hexdigest()
        db.execute('UPDATE sessions SET expires_at=?', (time.time() - 1,))
    assert client.get('/auth/session').json()['user'] is None
    assert client.get('/presets').status_code == 401


def test_csrf_bad_credentials_validation_and_rate_limit(tmp_path):
    client = TestClient(create_app(tmp_path / 'accounts.sqlite', ROOT))
    assert client.post('/auth/register', json={}).status_code == 403
    register_client(client)
    assert client.post('/auth/logout', headers={'Sec-Fetch-Site':'cross-site'}).status_code == 403
    invalid = client.post('/auth/register', json={'username':'other','password':'SHORTSECRET','display_name':''})
    assert invalid.status_code == 422 and 'SHORTSECRET' not in invalid.text
    response = client.post('/auth/login', json={'username':'tester','password':'wrong'})
    assert response.status_code == 401
    for _ in range(8):
        response = client.post('/auth/login', json={'username':'tester','password':'wrong'})
    assert response.status_code == 429


def test_first_account_claims_legacy_only_once_and_duplicate_users_rejected(tmp_path):
    path = tmp_path / 'accounts.sqlite'
    eid = submit(Store(path), ROOT / 'configs/simulated.json', ROOT / 'data/tasks.jsonl')
    app = create_app(path, ROOT)
    first, second = TestClient(app), TestClient(app)
    register_client(first, 'first')
    assert first.get('/experiments').json()[0]['id'] == eid
    register_client(second, 'second')
    assert second.get('/experiments').json() == []
    result = second.post('/auth/register', json={'username':'FIRST', 'password':'another-password', 'display_name':'X'})
    assert result.status_code == 409


def test_explicit_test_account_without_weak_registration(tmp_path):
    path = tmp_path / 'accounts.sqlite'
    client = TestClient(create_app(path, ROOT))
    client.headers['X-Arena-Request'] = '1'
    assert client.get('/auth/session').json()['has_users'] is False
    assert client.post('/auth/register', json={'username':'test','password':'test','display_name':'Test'}).status_code == 422
    accounts = Accounts(Store(path))
    first = accounts.create_test_user()
    assert accounts.create_test_user() == first
    assert client.post('/auth/login', json={'username':'test','password':'test'}).status_code == 200
