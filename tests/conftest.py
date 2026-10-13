import gc
import os
import random
import tempfile
from pathlib import Path
import httpx
import pytest


def pytest_addoption(parser):
    parser.addoption('--arena-order-seed',type=int,default=None,help='Shuffle collected tests reproducibly to detect order dependencies')


def pytest_configure(config):
    config._arena_temporary = tempfile.TemporaryDirectory(prefix='arena-tests-')
    config._arena_previous_db = os.environ.get('ARENA_DB')
    os.environ['ARENA_DB'] = str(Path(config._arena_temporary.name)/'default.sqlite')


def pytest_unconfigure(config):
    if hasattr(config,'_arena_temporary'):
        previous=config._arena_previous_db
        if previous is None:os.environ.pop('ARENA_DB',None)
        else:os.environ['ARENA_DB']=previous
        gc.collect()
        config._arena_temporary.cleanup()


def pytest_collection_modifyitems(config,items):
    seed=config.getoption('--arena-order-seed')
    if seed is not None:random.Random(seed).shuffle(items)


@pytest.fixture(autouse=True)
def isolated_runtime(monkeypatch):
    monkeypatch.delenv('ARENA_OLLAMA_URL',raising=False)
    def forbidden(*args,**kwargs):
        raise AssertionError('Live HTTP is forbidden in the test suite; use MockTransport or a controlled adapter')
    async def forbidden_async(*args,**kwargs):return forbidden(*args,**kwargs)
    monkeypatch.setattr(httpx.HTTPTransport,'handle_request',forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport,'handle_async_request',forbidden_async)


def register_client(client, username='tester'):
    client.headers['X-Arena-Request'] = '1'
    response = client.post('/auth/register', json={
        'username': username, 'password': 'test-password-123', 'display_name': username})
    assert response.status_code == 201, response.text
    return response.json()['user']
