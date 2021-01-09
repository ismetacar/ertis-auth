import json

from run import app
from tests import insert_mock_data
from tests.helpers import get_token

membership_doc, role_doc, user_doc = insert_mock_data()

application_id = None
application = None


def test_create_application():
    token = get_token(app, membership_doc, user_doc)
    token = token.json["access_token"]
    application_model = {
        'name': 'test_application',
        'role': 'admin-2'
    }

    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    request, response = app.test_client.post(
        '/api/v1/memberships/{}/applications'.format(str(membership_doc['_id'])),
        data=json.dumps(application_model),
        headers=headers
    )

    global application_id
    application_id = response.json['_id']

    assert response.status == 201
    assert response.json['name'] == 'test_application'


def test_get_application_test():
    token = get_token(app, membership_doc, user_doc)
    token = token.json["access_token"]
    request, response = app.test_client.get(
        '/api/v1/memberships/{}/applications/{}'.format(str(membership_doc['_id']), application_id),
        headers={
            'Authorization': 'Bearer {}'.format(token)
        }
    )

    assert response.status == 200
    assert response.json['name'] == 'test_application'

    global application
    application = response.json


def test_update_application():
    token = get_token(app, membership_doc, user_doc)
    token = token.json["access_token"]
    application['name'] = 'updated_test_application'
    request, response = app.test_client.put(
        '/api/v1/memberships/{}/applications/{}'.format(str(membership_doc['_id']), application['_id']),
        data=json.dumps(application),
        headers={
            'Authorization': 'Bearer {}'.format(token)
        }
    )

    assert response.status == 200
    assert response.json['_id'] == application['_id']
    assert response.json['name'] == "updated_test_application"


def test_query_applications():
    token = get_token(app, membership_doc, user_doc)
    token = token.json["access_token"]
    request, response = app.test_client.post(
        '/api/v1/memberships/{}/applications/_query'.format(str(membership_doc['_id'])),
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
    applications_query_result = response.json
    assert 'data' in applications_query_result
    data = applications_query_result['data']
    assert 'items' in data
    assert 'count' in data

    assert data['count'] == 1


def test_delete_application():
    token = get_token(app, membership_doc, user_doc)
    token = token.json["access_token"]
    request, response = app.test_client.delete(
        '/api/v1/memberships/{}/applications/{}'.format(str(membership_doc['_id']), application_id),
        headers={
            'Authorization': 'Bearer {}'.format(token)
        }
    )
    assert response.status == 204

    request, response = app.test_client.get(
        '/api/v1/memberships/{}/applications/{}'.format(str(membership_doc['_id']), application_id),
        headers={
            'Authorization': 'Bearer {}'.format(token)
        }
    )

    assert response.status == 404
