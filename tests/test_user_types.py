import json

from run import app
from tests import insert_mock_data
from tests.helpers import get_token

membership_doc, role_doc, user_doc = insert_mock_data()
user_type_id = None
user_type = None


def test_create_user_type():
    token = get_token(app, membership_doc, user_doc)
    token = token.json["access_token"]

    request, response = app.test_client.post(
        '/api/v1/memberships/{}/user-types'.format(str(membership_doc['_id'])),
        data=json.dumps({
            "name": "TestUserModel",
            "description": "Test model",
            "schema": {
                "properties": {
                    "photo_url": {
                        "type": "string",
                        "description": "Photo Url",
                        "maxLength": 250,
                        "minLength": 0,
                    },
                    "profile_link": {
                        "type": "string",
                        "description": "Profile Link",
                        "maxLength": 250,
                        "minLength": 0
                    },
                    "facebook_login_name": {
                        "type": "string",
                        "description": "Facebook Login Name",
                        "maxLength": 250,
                        "minLength": 0
                    }
                },
                "required": ["photo_url", "profile_link"],
                "additionalProperties": True
            }
        }),
        headers={
            'Authorization': 'Bearer {}'.format(token)
        }
    )

    assert response.status == 201
    assert response.json['_id'] is not None

    global user_type_id
    user_type_id = response.json['_id']


def test_get_user_type():
    token = get_token(app, membership_doc, user_doc)
    token = token.json["access_token"]

    request, response = app.test_client.get(
        '/api/v1/memberships/{}/user-types/{}'.format(str(membership_doc['_id']), user_type_id),
        headers={
            'Authorization': 'Bearer {}'.format(token)
        }
    )

    assert response.status == 200
    assert response.json['_id'] == user_type_id


def test_update_user_type():
    token = get_token(app, membership_doc, user_doc)
    token = token.json["access_token"]

    request, response = app.test_client.put(
        '/api/v1/memberships/{}/user-types/{}'.format(str(membership_doc['_id']), user_type_id),
        data=json.dumps({
            'name': 'UpdatedTestUserModel',
            "schema": {
                "properties": {
                    "display_name": {
                        "type": "string",
                        "description": "Display Name"
                    },
                    "photo_url": {
                        "type": "string",
                        "description": "Photo Url",
                        "maxLength": 250,
                        "minLength": 0,
                    },
                    "profile_link": {
                        "type": "string",
                        "description": "Profile Link",
                        "maxLength": 250,
                        "minLength": 0
                    },
                    "facebook_login_name": {
                        "type": "string",
                        "description": "Facebook Login Name",
                        "maxLength": 250,
                        "minLength": 0
                    }
                },
                "required": ["photo_url", "profile_link", "facebook_login_name"],
                "additionalProperties": True
            }
        }),
        headers={
            'Authorization': 'Bearer {}'.format(token)
        }
    )

    assert response.status == 200
    assert response.json['_id'] is not None
