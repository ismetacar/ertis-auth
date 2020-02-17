# region Init Tests
import json

import pytest
from sanic.websocket import WebSocketProtocol

from run import config_settings
from src import create_sanic_app
from tests import insert_mock_data, remove_mock_data


@pytest.fixture
def app():
    settings = config_settings('test')
    app = create_sanic_app(settings)

    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.yield_fixture
def loop(event_loop):
    return event_loop


@pytest.fixture
def client(loop, app, sanic_client):
    return loop.run_until_complete(sanic_client(app, protocol=WebSocketProtocol))


# endregion

# region Helpers
async def get_token(client, payload=None, membership_id=None):
    membership, role, user = insert_mock_data()
    if not payload:
        payload = {
            'username': user['username'],
            'password': '123123'
        }

    if not membership_id:
        membership_id = str(membership['_id'])

    headers = {
        'x-blupoint-alias': membership_id
    }

    token_response = await client.post(
        uri='/api/v1/generate-token',
        data=json.dumps(payload),
        headers=headers
    )

    token_response_json = await token_response.json()
    return token_response_json['access_token']


# endregion

# region User Create Test
async def test_create_user_with_valid_body(client):
    membership, role, user = insert_mock_data()
    token = await get_token(client, payload={
        'username': user['username'],
        'password': '123123',
    }, membership_id=user['membership_id'])

    user_model = {
        'username': 'ismetacar',
        'password': '123123',
        'email': 'idogan@blut.com'
    }

    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    user_response = await client.post(
        uri='/api/v1/memberships/{}/users'.format(str(membership['_id'])),
        data=json.dumps(user_model),
        headers=headers
    )

    assert user_response.status == 201
    user_response_json = await user_response.json()
    assert user_model['username'] == user_response_json['username']

    user_delete_response = await client.delete(
        uri='/api/v1/memberships/{}/users/{}'.format(str(membership['_id']), str(user_response_json['_id'])),
        headers=headers
    )
    assert user_delete_response.status == 204
    remove_mock_data(membership, user, role)


async def test_create_user_with_uppercase_email_and_username(client):
    membership, role, user = insert_mock_data()
    token = await get_token(client, payload={
        'username': user['username'],
        'password': '123123',
    }, membership_id=user['membership_id'])

    user_model = {
        'username': 'ISMETACAR',
        'password': '123123',
        'email': 'IDOGAN@BLUTV.COM'
    }

    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    user_response = await client.post(
        uri='/api/v1/memberships/{}/users'.format(str(membership['_id'])),
        data=json.dumps(user_model),
        headers=headers
    )

    assert user_response.status == 201
    user_response_json = await user_response.json()
    assert user_model['username'].lower() == user_response_json['username']

    token_payload = {
        'username': user_model['username'],
        'password': user_model['password']
    }

    token_response = await client.post(
        uri='/api/v1/generate-token',
        data=json.dumps(token_payload),
        headers={
            'x-blupoint-alias': user['membership_id']
        }
    )

    token_response_json = await token_response.json()
    assert 'access_token' in token_response_json.keys()
    assert 'refresh_token' in token_response_json.keys()
    assert 'expires_in' in token_response_json.keys()
    assert token_response_json['token_type'] == 'bearer'

    user_delete_response = await client.delete(
        uri='/api/v1/memberships/{}/users/{}'.format(str(membership['_id']), str(user_response_json['_id'])),
        headers=headers
    )
    assert user_delete_response.status == 204
    remove_mock_data(membership, user, role)


# endregion

# region Query Users Tests
async def test_query_users_test(client):
    membership, role, user = insert_mock_data()
    token = await get_token(client, payload={
        'username': user['username'],
        'password': '123123',
    }, membership_id=user['membership_id'])
    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    payload = {
        'where': {},
        'select': {
            'username': 1,
            'email': 1
        }
    }

    user_response = await client.post(
        uri='/api/v1/memberships/{}/users/_query'.format(str(membership['_id'])),
        data=json.dumps(payload),
        headers=headers
    )

    assert user_response.status == 200
    remove_mock_data(membership, user, role)


# endregion

# region User Get Test
async def test_get_valid_user(client):
    membership, role, user = insert_mock_data()
    token = await get_token(client, payload={
        'username': user['username'],
        'password': '123123',
    }, membership_id=user['membership_id'])

    user_model = {
        'username': 'ismetacar',
        'password': '123123',
        'email': 'idogan@blut.com'
    }

    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    user_response = await client.post(
        uri='/api/v1/memberships/{}/users'.format(str(membership['_id'])),
        data=json.dumps(user_model),
        headers=headers
    )

    assert user_response.status == 201
    user_response_json = await user_response.json()

    inserted_user = await client.get(
        uri='/api/v1/memberships/{}/users/{}'.format(str(membership['_id']), str(user_response_json['_id'])),
        headers=headers
    )

    assert inserted_user.status == 200
    user_delete_response = await client.delete(
        uri='/api/v1/memberships/{}/users/{}'.format(str(membership['_id']), str(user_response_json['_id'])),
        headers=headers
    )
    assert user_delete_response.status == 204
    remove_mock_data(membership, user, role)


# endregion

# region Update User Test
async def test_update_username_of_user(client):
    membership, role, user = insert_mock_data()
    token = await get_token(client, payload={
        'username': user['username'],
        'password': '123123',
    }, membership_id=user['membership_id'])

    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    payload = {
        'username': 'hyurtseven'
    }

    update_user_response = await client.put(
        uri='/api/v1/memberships/{}/users/{}'.format(str(membership['_id']), str(user['_id'])),
        data=json.dumps(payload),
        headers=headers
    )

    assert update_user_response.status == 200
    remove_mock_data(membership, user, role)


async def test_update_no_changes_body(client):
    membership, role, user = insert_mock_data()
    token = await get_token(client, payload={
        'username': user['username'],
        'password': '123123',
    }, membership_id=user['membership_id'])

    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    payload = {
    }

    update_user_response = await client.put(
        uri='/api/v1/memberships/{}/users/{}'.format(str(membership['_id']), str(user['_id'])),
        data=json.dumps(payload),
        headers=headers
    )

    assert update_user_response.status == 409
    remove_mock_data(membership, user, role)


async def test_update_user_with_not_permitted_user(client):
    membership, role, user = insert_mock_data()
    token = await get_token(client, payload={
        'username': user['username'],
        'password': '123123',
    }, membership_id=user['membership_id'])

    user_model = {
        'username': 'not_permitted 1',
        'password': '123123',
        'email': 'hebele1@blutv.com'
    }

    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    user_response = await client.post(
        uri='/api/v1/memberships/{}/users'.format(str(membership['_id'])),
        data=json.dumps(user_model),
        headers=headers
    )

    assert user_response.status == 201
    user_response_json = await user_response.json()
    assert user_model['username'] == user_response_json['username']

    payload = {
        'username': user_model['username'],
        'password': '123123'
    }

    token = await get_token(client, payload=payload, membership_id=user['membership_id'])

    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    payload = {
        'username': 'permitted'
    }
    update_user_response = await client.put(
        uri='/api/v1/memberships/{}/users/{}'.format(str(membership['_id']), str(user['_id'])),
        data=json.dumps(payload),
        headers=headers
    )

    assert update_user_response.status == 403
    remove_mock_data(membership, user, role)

# endregion
