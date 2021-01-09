import json

from run import app
from tests import insert_mock_data
from tests.helpers import (
    get_token,
    get_user_type_of_membership
)

membership_doc, role_doc, user_doc = insert_mock_data()
user_id = None
user = None
user_type_id = None
user_token = None


def test_create_user():
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

    global user_type_id
    user_type_id = response.json['_id']

    request, response = app.test_client.post(
        '/api/v1/memberships/{}/users'.format(str(membership_doc['_id'])),
        data=json.dumps({
            "username": "testuser",
            "password": "123123",
            "firstname": "test",
            "lastname": "user",
            "role": role_doc['slug'],
            "status": "active",
            "email": "test@user.com",
            "photo_url": "http://test.com/user-profile/photos/photo.jpg",
            "profile_link": "http://test.com/user-profile"
        }),
        headers={
            'Authorization': 'Bearer {}'.format(token)
        }
    )

    global user
    user = response.json

    assert response.status == 201
    assert user['username'] == 'testuser'
    assert user['_id'] is not None

    response = get_user_type_of_membership(app, membership_doc, token)
    assert response.status == 200
    assert response.json['_id'] is not None

    required_custom_fields = response.json['schema']['required']

    for prop in required_custom_fields:
        assert prop in user.keys()


def test_get_token_with_created_user():
    response = get_token(app, membership_doc, user)
    assert response.status == 201
    assert response.json['access_token'] is not None
    assert response.json['token_type'] == 'bearer'

    global user_token
    user_token = response.json['access_token']


def test_update_user():
    user['username'] = 'updated_testuser'
    user['_id'] = str(user['_id'])

    request, response = app.test_client.put(
        '/api/v1/memberships/{}/users/{}'.format(str(membership_doc['_id']), str(user['_id'])),
        data=json.dumps(user),
        headers={
            'Authorization': 'Bearer {}'.format(user_token)
        }
    )

    assert response.status == 200
    assert response.json['_id'] == user['_id']


def test_delete_user():

    token = get_token(app, membership_doc, user_doc)
    token = token.json["access_token"]


    request, response = app.test_client.delete(
        '/api/v1/memberships/{}/users/{}'.format(str(membership_doc['_id']), str(user['_id'])),
        headers={
            'Authorization': 'Bearer {}'.format(token)
        }
    )

    assert response.status == 204
    assert response.json is None
