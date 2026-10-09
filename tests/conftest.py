def register_client(client, username='tester'):
    client.headers['X-Arena-Request'] = '1'
    response = client.post('/auth/register', json={
        'username': username, 'password': 'test-password-123', 'display_name': username})
    assert response.status_code == 201, response.text
    return response.json()['user']
