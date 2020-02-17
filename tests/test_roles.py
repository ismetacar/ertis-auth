# region Init Tests
import json

import pytest
from sanic.websocket import WebSocketProtocol

from run import config_settings
from src import create_sanic_app
from tests import insert_mock_data
from tests.test_users import get_token


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

# region Create Role Test
async def test_create_role_with_valid_body(client):
    membership, role, user = insert_mock_data()
    token = await get_token(client, payload={
        'username': user['username'],
        'password': '123123',
    }, membership_id=user['membership_id'])

    role_model = {
        'name': 'role 1',
        'permissions': ['*']
    }

    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    role_response = await client.post(
        uri='/api/v1/memberships/{}/roles'.format(str(user['membership_id'])),
        data=json.dumps(role_model),
        headers=headers
    )

    assert role_response.status == 201
    role_response_json = await role_response.json()
    assert role_model['name'] == role_response_json['name']


# endregion

# region Query Roles Tests
async def test_query_roles_test(client):
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
            'name': 1,
            'secret': 1
        }
    }

    roles_response = await client.post(
        uri='/api/v1/memberships/{}/roles/_query'.format(str(user['membership_id'])),
        data=json.dumps(payload),
        headers=headers
    )

    assert roles_response.status == 200


# endregion

# region Get Role Test
async def test_get_valid_role(client):
    membership, role, user = insert_mock_data()
    token = await get_token(client, payload={
        'username': user['username'],
        'password': '123123',
    }, membership_id=user['membership_id'])

    role_model = {
        'name': 'role 2',
        'permissions': ['*']
    }

    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    role_response = await client.post(
        uri='/api/v1/memberships/{}/roles'.format(str(membership['_id'])),
        data=json.dumps(role_model),
        headers=headers
    )

    assert role_response.status == 201
    role_response_json = await role_response.json()

    inserted_role = await client.get(
        uri='/api/v1/memberships/{}/roles/{}'.format(str(membership['_id']), str(role_response_json['_id'])),
        headers=headers
    )

    assert inserted_role.status == 200


# endregion

# region Update Role Test
async def test_update_name_of_role(client):
    membership, role, user = insert_mock_data()
    token = await get_token(client, payload={
        'username': user['username'],
        'password': '123123',
    }, membership_id=user['membership_id'])

    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    role_model = {
        'name': 'role 3',
        'permissions': ['*']
    }

    role_response = await client.post(
        uri='/api/v1/memberships/{}/roles'.format(str(user['membership_id'])),
        data=json.dumps(role_model),
        headers=headers
    )

    role_response_json = await role_response.json()
    payload = {
        'name': 'role 3.1',
        'permissions': ['*']
    }

    update_role_response = await client.put(
        uri='/api/v1/memberships/{}/roles/{}'.format(str(user['membership_id']), str(role_response_json['_id'])),
        data=json.dumps(payload),
        headers=headers
    )

    assert update_role_response.status == 200


async def test_update_role_with_not_permitted_user(client):
    membership, role, user = insert_mock_data()
    #: get token
    token = await get_token(client, payload={
        'username': user['username'],
        'password': '123123',
    }, membership_id=user['membership_id'])

    # create role
    role_model = {
        'name': 'role 4',
        'permissions': ['*']
    }

    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    role_response = await client.post(
        uri='/api/v1/memberships/{}/roles'.format(str(user['membership_id'])),
        data=json.dumps(role_model),
        headers=headers
    )

    assert role_response.status == 201
    role_response_json = await role_response.json()

    user_model = {
        'username': 'not_permitted3',
        'password': '123123',
        'email': 'hubele2@blutv.com'
    }

    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    # create new user without permissions
    user_response = await client.post(
        uri='/api/v1/memberships/{}/users'.format(str(user['membership_id'])),
        data=json.dumps(user_model),
        headers=headers
    )

    user_response_json = await user_response.json()
    assert user_response.status == 201
    assert user_model['username'] == user_response_json['username']

    payload = {
        'username': user_model['username'],
        'password': '123123'
    }

    token = await get_token(client, payload=payload, membership_id=user_response_json['membership_id'])

    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }
    update_role_response = await client.put(
        uri='/api/v1/memberships/{}/roles/{}'.format(
            str(user_response_json['membership_id']),
            str(role_response_json['_id'])
        ),
        data=json.dumps(payload),
        headers=headers
    )

    assert update_role_response.status == 403


async def test_update_role_with_no_changes_body(client):
    membership, role, user = insert_mock_data()
    token = await get_token(client, payload={
        'username': user['username'],
        'password': '123123',
    }, membership_id=user['membership_id'])

    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    role_model = {
        'name': 'role 5',
        'permissions': ['*']
    }

    role_response = await client.post(
        uri='/api/v1/memberships/{}/roles'.format(str(user['membership_id'])),
        data=json.dumps(role_model),
        headers=headers
    )

    role_response_json = await role_response.json()
    payload = {
    }

    update_role_response = await client.put(
        uri='/api/v1/memberships/{}/roles/{}'.format(str(user['membership_id']), str(role_response_json['_id'])),
        data=json.dumps(payload),
        headers=headers
    )

    assert update_role_response.status == 409
# endregion


# region Delete Role Test
async def test_delete_role(client):
    membership, role, user = insert_mock_data()
    token = await get_token(client, payload={
        'username': user['username'],
        'password': '123123',
    }, membership_id=user['membership_id'])

    role_model = {
        'name': 'role 6',
        'permissions': ['*']
    }

    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    role_response = await client.post(
        uri='/api/v1/memberships/{}/roles'.format(str(user['membership_id'])),
        data=json.dumps(role_model),
        headers=headers
    )

    assert role_response.status == 201
    role_response_json = await role_response.json()

    role_response = await client.delete(
        uri='/api/v1/memberships/{}/roles/{}'.format(str(user['membership_id']), role_response_json['_id']),
        headers=headers
    )
    assert role_response.status == 204
# endregion
