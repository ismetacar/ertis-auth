import json

from run import app
from tests import insert_mock_data, remove_mock_data
from tests.helpers import get_token


membership_doc, role_doc, user_doc = insert_mock_data()
role_id = None
role = None


def test_create_role():
    token = get_token(app, membership_doc, user_doc)
    token = token.json["access_token"]

    role_model = {
        'name': 'test_role',
        'permissions': [
            'users.*',
            'applications.*',
            'roles.*',
            'user_types.*'
        ]
    }

    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    request, response = app.test_client.post(
        '/api/v1/memberships/{}/roles'.format(str(membership_doc['_id'])),
        data=json.dumps(role_model),
        headers=headers
    )

    assert response.status == 201
    assert response.json['name'] == 'test_role'

    global role_id
    role_id = response.json['_id']


def test_get_role():
    token = get_token(app, membership_doc, user_doc)
    token = token.json["access_token"]

    request, response = app.test_client.get(
        '/api/v1/memberships/{}/roles/{}'.format(str(membership_doc['_id']), role_id),
        headers={
            'Authorization': 'Bearer {}'.format(token)
        }
    )
    assert response.status == 200
    assert response.json['name'] == 'test_role'

    global role
    role = response.json


def test_update_role():
    token = get_token(app, membership_doc, user_doc)
    token = token.json["access_token"]

    role['name'] = 'updated_test_role'
    request, response = app.test_client.put(
        '/api/v1/memberships/{}/roles/{}'.format(str(membership_doc['_id']), role['_id'], token),
        data=json.dumps(role),
        headers={
            'Authorization': 'Bearer {}'.format(token)
        }
    )
    assert response.status == 200
    assert response.json['_id'] == role['_id']
    assert response.json['name'] == "updated_test_role"


def test_query_roles():
    token = get_token(app, membership_doc, user_doc)
    token = token.json["access_token"]

    request, response = app.test_client.post(
        '/api/v1/memberships/{}/roles/_query'.format(str(membership_doc['_id'])),
        data=json.dumps({
            'where': {},
            'select': {}
        }),
        headers={
            'Authorization': 'Bearer {}'.format(token)
        }
    )

    assert response.status == 200
    assert response.json is not None
    roles_query_result = response.json
    assert 'data' in roles_query_result
    data = roles_query_result['data']
    assert 'items' in data
    assert 'count' in data

    assert data['count'] != 0


def test_delete_role():
    token = get_token(app, membership_doc, user_doc)
    token = token.json["access_token"]

    request, response = app.test_client.delete(
        '/api/v1/memberships/{}/roles/{}'.format(str(membership_doc['_id']), role_id),
        headers={
            'Authorization': 'Bearer {}'.format(token)
        }
    )

    assert response.status == 204

    request, response = app.test_client.get(
        '/api/v1/memberships/{}/roles/{}'.format(str(membership_doc['_id']), role_id),
        headers={
            'Authorization': 'Bearer {}'.format(token)
        }
    )

    assert response.status == 404
