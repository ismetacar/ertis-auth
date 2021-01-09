import json

from run import app
from tests import insert_mock_data, remove_mock_data
from tests.helpers import get_token

membership_doc, role_doc, user_doc = insert_mock_data()


def test_generate_token():
    response = get_token(app, membership_doc, user_doc)
    assert response.status == 201
    assert 'access_token' in response.json
    assert 'refresh_token' in response.json


def test_get_me():
    token = get_token(app, membership_doc, user_doc)
    token = token.json["access_token"]
    request, response = app.test_client.get(
        '/api/v1/me',
        headers={
            'Authorization': 'Bearer {}'.format(token)
        }
    )
    assert response.status == 200


def test_refresh_token():
    token = get_token(app, membership_doc, user_doc)
    a_token = token.json["access_token"]
    r_token = token.json["refresh_token"]
    request, response = app.test_client.post(
        '/api/v1/refresh-token',
        data=json.dumps({'token': r_token}),
        headers={
            'Authorization': 'Bearer {}'.format(a_token)
        }
    )

    assert response.status == 200
    assert 'access_token' in response.json
    assert 'refresh_token' in response.json


def test_revoke_token():
    token = get_token(app, membership_doc, user_doc)
    a_token = token.json["access_token"]
    r_token = token.json["refresh_token"]

    request, response = app.test_client.post(
        '/api/v1/revoke-token',
        data=json.dumps({'token': r_token}),
        headers={
            'Authorization': 'Bearer {}'.format(a_token)
        }
    )

    assert response.status is 204
