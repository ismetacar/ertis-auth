import json
import pytest
from sanic.websocket import WebSocketProtocol

from run import config_settings
from src import create_sanic_app
from tests import insert_mock_data
#: TODO: hepsi silinecek bastan yazilacak
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


membership, role, user = insert_mock_data()


# endregion


# region Generate Token Tests
async def test_generate_token_with_valid_payload(client):
    payload = {
        'username': user['username'],
        'password': '123123'
    }

    headers = {
        'x-ertis-alias': str(membership['_id'])
    }

    response = await client.post(
        uri='/api/v1/generate-token',
        data=json.dumps(payload),
        headers=headers
    )

    assert response.status == 201
    resp_json = await response.json()
    assert 'access_token' in resp_json.keys()
    assert 'refresh_token' in resp_json.keys()
    assert 'expires_in' in resp_json.keys()
    assert resp_json['token_type'] == 'bearer'


async def test_generate_token_with_invalid_membership_id(client):
    payload = {
        'username': user['username'],
        'password': '123123'
    }

    headers = {
        'x-ertis-alias': 'invalid_membership_id'
    }

    response = await client.post(
        uri='/api/v1/generate-token',
        data=json.dumps(payload),
        headers=headers
    )

    assert response.status == 404


async def test_generate_token_with_invalid_payload(client):
    payload = {
        'password': '123123'
    }

    headers = {
        'x-ertis-alias': str(membership['_id'])
    }

    response = await client.post(
        uri='/api/v1/generate-token',
        data=json.dumps(payload),
        headers=headers
    )

    assert response.status == 400


async def test_generate_token_with_invalid_password(client):
    payload = {
        'username': user['username'],
        'password': 'invalid_password'
    }

    headers = {
        'x-ertis-alias': str(membership['_id'])
    }

    response = await client.post(
        uri='/api/v1/generate-token',
        data=json.dumps(payload),
        headers=headers
    )

    resp_json = await response.json()

    assert response.status == 403
    assert resp_json['err_code'] == 'errors.wrongUsernameOrPassword'


async def test_generate_token_with_not_allowed_method(client):
    payload = {
        'username': user['username'],
        'password': '123123'
    }

    headers = {
        'x-ertis-alias': str(membership['_id'])
    }

    response = await client.put(
        uri='/api/v1/generate-token',
        data=json.dumps(payload),
        headers=headers
    )

    assert response.status == 405


async def test_generate_token_should_user_updated_with_token(client):
    payload = {
        'username': user['username'],
        'password': '123123'
    }

    headers = {
        'x-ertis-alias': str(membership['_id'])
    }

    token_response = await client.post(
        uri='/api/v1/generate-token',
        data=json.dumps(payload),
        headers=headers
    )

    assert token_response.status == 201
    token_response_json = await token_response.json()
    access_token = token_response_json.get('access_token')

    headers = {
        'Authorization': 'Bearer {}'.format(access_token)
    }

    me_response = await client.get(
        uri='/api/v1/me',
        headers=headers
    )

    me_response_json = await me_response.json()
    assert me_response.status == 200
    assert 'token' in me_response_json
    assert me_response_json['token']['access_token'] == access_token


# endregion

# region Refresh Token Tests

async def test_refresh_token_with_valid_refreshable_token(client):
    payload = {
        'username': user['username'],
        'password': '123123'
    }

    headers = {
        'x-ertis-alias': str(membership['_id'])
    }

    token_response = await client.post(
        uri='/api/v1/generate-token',
        data=json.dumps(payload),
        headers=headers
    )

    assert token_response.status == 201

    token_response_json = await token_response.json()
    access_token = token_response_json['access_token']
    refreshable_token = token_response_json['refresh_token']

    payload = {
        'token': refreshable_token
    }

    refresh_token_response = await client.post(
        uri='/api/v1/refresh-token',
        data=json.dumps(payload)
    )

    assert refresh_token_response.status == 200
    refresh_token_response_json = await refresh_token_response.json()
    assert access_token != refresh_token_response_json['access_token']
    assert refreshable_token != refresh_token_response_json['refresh_token']


async def test_refresh_token_with_access_token(client):
    payload = {
        'username': user['username'],
        'password': '123123'
    }

    headers = {
        'x-ertis-alias': str(membership['_id'])
    }

    token_response = await client.post(
        uri='/api/v1/generate-token',
        data=json.dumps(payload),
        headers=headers
    )

    assert token_response.status == 201

    token_response_json = await token_response.json()
    access_token = token_response_json['access_token']

    payload = {
        'token': access_token
    }

    refresh_token_response = await client.post(
        uri='/api/v1/refresh-token',
        data=json.dumps(payload)
    )

    assert refresh_token_response.status == 400
    refresh_token_response_json = await refresh_token_response.json()
    assert refresh_token_response_json['err_code'] == 'errors.refreshableTokenError'


async def test_refresh_token_with_invalid_refreshable_token(client):
    payload = {
        'username': user['username'],
        'password': '123123'
    }

    headers = {
        'x-ertis-alias': str(membership['_id'])
    }

    token_response = await client.post(
        uri='/api/v1/generate-token',
        data=json.dumps(payload),
        headers=headers
    )

    assert token_response.status == 201
    token_response_json = await token_response.json()
    invalid_refresh_token = token_response_json['refresh_token'][:-1]

    payload = {
        'token': invalid_refresh_token
    }

    refresh_token_response = await client.post(
        uri='/api/v1/refresh-token',
        data=json.dumps(payload)
    )

    assert refresh_token_response.status == 401


# endregion

# region Verify Token Tests

async def test_verify_valid_token(client):
    payload = {
        'username': user['username'],
        'password': '123123'
    }

    headers = {
        'x-ertis-alias': str(membership['_id'])
    }

    token_response = await client.post(
        uri='/api/v1/generate-token',
        data=json.dumps(payload),
        headers=headers
    )

    assert token_response.status == 201
    token_response_json = await token_response.json()
    access_token = token_response_json['access_token']
    refresh_token = token_response_json['refresh_token']
    payload = {
        'token': access_token
    }

    verify_token_response = await client.post(
        uri='/api/v1/verify-token',
        data=json.dumps(payload)
    )

    assert verify_token_response.status == 200
    verify_token_response_json = await verify_token_response.json()
    assert verify_token_response_json['verified'] == True
    assert verify_token_response_json['refreshable'] == False

    payload = {
        'token': refresh_token
    }

    verify_token_response = await client.post(
        uri='/api/v1/verify-token',
        data=json.dumps(payload)
    )

    assert verify_token_response.status == 200
    verify_token_response_json = await verify_token_response.json()
    assert verify_token_response_json['verified'] == True
    assert verify_token_response_json['refreshable'] == True


async def test_verify_invalid_token(client):
    payload = {
        'username': user['username'],
        'password': '123123'
    }

    headers = {
        'x-ertis-alias': str(membership['_id'])
    }

    token_response = await client.post(
        uri='/api/v1/generate-token',
        data=json.dumps(payload),
        headers=headers
    )

    assert token_response.status == 201

    token_response_json = await token_response.json()
    invalid_access_token = token_response_json['access_token'][:-3]

    payload = {
        'token': invalid_access_token
    }

    verify_token_response = await client.post(
        uri='/api/v1/verify-token',
        data=json.dumps(payload)
    )

    verify_token_response_json = await verify_token_response.json()

    assert verify_token_response.status == 401
    assert verify_token_response_json['err_code'] == 'errors.tokenIsInvalid'


# endregion Test

# region Revoke Token Tests
async def test_revoke_token(client):
    payload = {
        'username': user['username'],
        'password': '123123'
    }

    headers = {
        'x-ertis-alias': str(membership['_id'])
    }

    token_response = await client.post(
        uri='/api/v1/generate-token',
        data=json.dumps(payload),
        headers=headers
    )

    assert token_response.status == 201

    token_response_json = await token_response.json()
    access_token = token_response_json['access_token']

    payload = {
        'token': access_token
    }

    revoke_response = await client.post(
        uri='/api/v1/revoke-token',
        data=json.dumps(payload)
    )

    assert revoke_response.status == 204


async def test_revoked_token_should_be_invalid(client):
    payload = {
        'username': user['username'],
        'password': '123123'
    }

    headers = {
        'x-ertis-alias': str(membership['_id'])
    }

    token_response = await client.post(
        uri='/api/v1/generate-token',
        data=json.dumps(payload),
        headers=headers
    )

    assert token_response.status == 201

    token_response_json = await token_response.json()
    access_token = token_response_json['access_token']

    payload = {
        'token': access_token
    }

    revoke_response = await client.post(
        uri='/api/v1/revoke-token',
        data=json.dumps(payload)
    )

    assert revoke_response.status == 204

    verify_response = await client.post(
        uri='/api/v1/verify-token',
        data=json.dumps(payload)
    )

    assert verify_response.status == 401


# endregion

# region Reset Password Test
async def test_reset_password(client):
    payload = {
        'email': 'john@domain.com'
    }

    headers = {
        'x-ertis-alias': str(membership['_id'])
    }

    reset_password_response = await client.post(
        uri='/api/v1/reset-password',
        data=json.dumps(payload),
        headers=headers
    )

    assert reset_password_response.status == 404

    payload = {
        'email': 'doe@domain.com'
    }

    reset_password_response = await client.post(
        uri='/api/v1/reset-password',
        data=json.dumps(payload),
        headers=headers
    )

    assert reset_password_response.status == 200
    reset_password_response_json = await reset_password_response.json()
    assert 'reset_token' in reset_password_response_json.keys()


# endregion

# region Set New Password
async def test_set_new_password(client):
    payload = {
        'email': user['email']
    }

    headers = {
        'x-ertis-alias': str(membership['_id'])
    }

    reset_password_response = await client.post(
        uri='/api/v1/reset-password',
        data=json.dumps(payload),
        headers=headers
    )

    reset_password_response_json = await reset_password_response.json()

    assert reset_password_response.status == 200

    payload = {
        'email': user['email'],
        'reset_token': reset_password_response_json['reset_token'],
        'password': 'qweqwe'
    }

    set_new_password_response = await client.post(
        uri='/api/v1/set-password',
        data=json.dumps(payload),
        headers=headers
    )

    assert set_new_password_response.status == 204

    payload = {
        'username': user['username'],
        'password': 'qweqwe'
    }

    token_response = await client.post(
        uri='/api/v1/generate-token',
        data=json.dumps(payload),
        headers=headers
    )

    assert token_response.status == 201


# endregion


# region Change Password Test
async def test_change_password_of_user(client):
    token = await get_token(client, payload={
        'username': user['username'],
        'password': '123123',
    }, membership_id=user['membership_id'])

    assert token is not None

    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    payload = {
        'password': '12341234',
        'password_confirm': '12341234',
        'user_id': str(user['_id'])
    }

    change_password_response = await client.post(
        uri='/api/v1/change-password',
        data=json.dumps(payload),
        headers=headers
    )
    assert change_password_response.status == 200


async def test_change_other_user_password(client):
    membership, role, user = insert_mock_data()
    token = await get_token(client, payload={
        'username': user['username'],
        'password': '123123',
    }, membership_id=user['membership_id'])

    assert token is not None

    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    payload = {
        'password': '12341234',
        'password_confirm': '12341234',
        'user_id': 'invalid_user_id'
    }

    change_password_response = await client.post(
        uri='/api/v1/change-password',
        data=json.dumps(payload),
        headers=headers
    )

    assert change_password_response.status == 403


async def test_change_password_with_not_confirmed_password(client):
    membership, role, user = insert_mock_data()
    token = await get_token(client, payload={
        'username': user['username'],
        'password': '123123',
    }, membership_id=user['membership_id'])

    assert token is not None

    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    payload = {
        'password': '12341234',
        'password_confirm': '1234123',
        'user_id': str(user['_id'])
    }

    change_password_response = await client.post(
        uri='/api/v1/change-password',
        data=json.dumps(payload),
        headers=headers
    )

    assert change_password_response.status == 400
# endregion
