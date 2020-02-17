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

# region Create Application Test
async def test_create_application_with_valid_body(client):
    membership, role, user = insert_mock_data()
    token = await get_token(client, payload={
        'username': user['username'],
        'password': '123123',
    }, membership_id=user['membership_id'])

    application_model = {
        'name': 'blutv application'
    }

    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    application_response = await client.post(
        uri='/api/v1/memberships/{}/applications'.format(str(user['membership_id'])),
        data=json.dumps(application_model),
        headers=headers
    )

    assert application_response.status == 201
    application_response_json = await application_response.json()
    assert application_model['name'] == application_response_json['name']


# endregion

# region Query Applications Tests
async def test_query_applications_test(client):
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

    application_response = await client.post(
        uri='/api/v1/memberships/{}/users/_query'.format(str(user['membership_id'])),
        data=json.dumps(payload),
        headers=headers
    )

    assert application_response.status == 200


# endregion

# region Application Get Test
async def test_get_valid_application(client):
    membership, role, user = insert_mock_data()
    token = await get_token(client, payload={
        'username': user['username'],
        'password': '123123',
    }, membership_id=user['membership_id'])

    application_model = {
        'name': 'blutv smarttv'
    }

    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    application_response = await client.post(
        uri='/api/v1/memberships/{}/applications'.format(str(membership['_id'])),
        data=json.dumps(application_model),
        headers=headers
    )

    assert application_response.status == 201
    application_response_json = await application_response.json()

    inserted_application = await client.get(
        uri='/api/v1/memberships/{}/applications/{}'.format(str(membership['_id']),
                                                            str(application_response_json['_id'])),
        headers=headers
    )

    assert inserted_application.status == 200


# endregion

# region Update Application Test
async def test_update_name_of_application(client):
    membership, role, user = insert_mock_data()
    token = await get_token(client, payload={
        'username': user['username'],
        'password': '123123',
    }, membership_id=user['membership_id'])

    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    application_model = {
        'name': 'blutv smarttv 2'
    }

    application_response = await client.post(
        uri='/api/v1/memberships/{}/applications'.format(str(user['membership_id'])),
        data=json.dumps(application_model),
        headers=headers
    )

    application_response_json = await application_response.json()
    payload = {
        'name': 'blutv smarttv 1'
    }

    update_application_response = await client.put(
        uri='/api/v1/memberships/{}/applications/{}'.format(str(user['membership_id']),
                                                            str(application_response_json['_id'])),
        data=json.dumps(payload),
        headers=headers
    )

    assert update_application_response.status == 200


async def test_update_application_with_not_permitted_user(client):
    membership, role, user = insert_mock_data()
    #: get token
    token = await get_token(client, payload={
        'username': user['username'],
        'password': '123123',
    }, membership_id=user['membership_id'])

    # create application
    application_model = {
        'name': 'blutv smarttv 4'
    }

    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    application_response = await client.post(
        uri='/api/v1/memberships/{}/applications'.format(str(user['membership_id'])),
        data=json.dumps(application_model),
        headers=headers
    )

    assert application_response.status == 201
    application_response_json = await application_response.json()

    user_model = {
        'username': 'not_permitted2',
        'password': '123123',
        'email': 'hubele1@blutv.com'
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
    update_application_response = await client.put(
        uri='/api/v1/memberships/{}/applications/{}'.format(
            str(user_response_json['membership_id']),
            str(application_response_json['_id'])
        ),
        data=json.dumps(payload),
        headers=headers
    )

    assert update_application_response.status == 403


async def test_update_application_with_no_changes_body(client):
    membership, role, user = insert_mock_data()
    token = await get_token(client, payload={
        'username': user['username'],
        'password': '123123',
    }, membership_id=user['membership_id'])

    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    application_model = {
        'name': 'blutv smarttv for no changes test'
    }

    application_response = await client.post(
        uri='/api/v1/memberships/{}/applications'.format(str(user['membership_id'])),
        data=json.dumps(application_model),
        headers=headers
    )

    application_response_json = await application_response.json()
    payload = {
    }

    update_application_response = await client.put(
        uri='/api/v1/memberships/{}/applications/{}'.format(str(user['membership_id']),
                                                            str(application_response_json['_id'])),
        data=json.dumps(payload),
        headers=headers
    )

    assert update_application_response.status == 409
# endregion

# region Delete Application Test
async def test_delete_application(client):
    membership, role, user = insert_mock_data()
    token = await get_token(client, payload={
        'username': user['username'],
        'password': '123123',
    }, membership_id=user['membership_id'])

    application_model = {
        'name': 'blutv application for deleting'
    }

    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    application_response = await client.post(
        uri='/api/v1/memberships/{}/applications'.format(str(user['membership_id'])),
        data=json.dumps(application_model),
        headers=headers
    )

    assert application_response.status == 201
    application_response_json = await application_response.json()

    application_response = await client.delete(
        uri='/api/v1/memberships/{}/applications/{}'.format(str(user['membership_id']),
                                                            application_response_json['_id']),
        headers=headers
    )
    assert application_response.status == 204
# endregion
