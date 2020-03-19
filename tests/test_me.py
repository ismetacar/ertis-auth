import json
#: TODO: hepsi silinecek bastan yazilacak
import pytest
from sanic.websocket import WebSocketProtocol

from run import config_settings
from src import create_sanic_app
from tests import insert_mock_data

# region Init Tests
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

# region Me Tests

async def test_me_valid_token(client):
    membership, role, user = insert_mock_data()
    token = await get_token(client, payload={
        'username': user['username'],
        'password': '123123',
    }, membership_id=user['membership_id'])

    assert token is not None

    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    me_response = await client.get(
        uri='/api/v1/me',
        headers=headers
    )

    assert me_response.status == 200
    me_response_json = await me_response.json()
    username = me_response_json['username']
    assert username == user['username']


async def test_me_with_invalid_token(client):
    membership, role, user = insert_mock_data()
    token = await get_token(client, payload={
        'username': user['username'],
        'password': '123123',
    }, membership_id=user['membership_id'])

    assert token is not None

    invalid_access_token = token[:-4]

    headers = {
        'token': invalid_access_token
    }

    me_response = await client.get(
        uri='/api/v1/me',
        headers=headers
    )

    assert me_response.status == 401
    me_response_json = await me_response.json()
    assert me_response_json['err_code'] == 'errors.authorizationError'

# endregion
