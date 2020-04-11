import json


def get_token(app, membership, user):
    request, response = app.test_client.post(
        '/api/v1/generate-token',
        data=json.dumps({
            'username': user['username'],
            'password': '123123'
        }),
        headers={
            'x-ertis-alias': str(membership['_id'])
        }
    )

    return response


def create_user_type(app, membership, token):
    request, response = app.test_client.post(
        '/api/v1/memberships/{}/user-types'.format(str(membership['_id'])),
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

    return response


def create_user(app, membership, role, token):
    request, response = app.test_client.post(
        '/api/v1/memberships/{}/users'.format(str(membership['_id'])),
        data=json.dumps({
            "username": "testuser",
            "password": "123123",
            "firstname": "test",
            "lastname": "user",
            "role": role['slug'],
            "email": "test@user.com",
            "photo_url": "http://test.com/user-profile/photos/photo.jpg",
            "profile_link": "http://test.com/user-profile"
        }),
        headers={
            'Authorization': 'Bearer {}'.format(token)
        }
    )

    return response


def get_user_type_by_id(app, membership, user_type_id, token):
    request, response = app.test_client.get(
        '/api/v1/memberships/{}/user-types/{}'.format(str(membership['_id']), user_type_id),
        headers={
            'Authorization': 'Bearer {}'.format(token)
        }
    )

    return response


def get_user_type_of_membership(app, membership, token):
    request, response = app.test_client.get(
        '/api/v1/memberships/{}/get-user-type'.format(str(membership['_id'])),
        headers={
            'Authorization': 'Bearer {}'.format(token)
        }
    )

    return response


def update_username_of_created_user(app, membership, user, token):
    user['username'] = 'updated_testuser'
    user['_id'] = str(user['_id'])

    request, response = app.test_client.put(
        '/api/v1/memberships/{}/users/{}'.format(str(membership['_id']), str(user['_id'])),
        data=json.dumps(user),
        headers={
            'Authorization': 'Bearer {}'.format(token)
        }
    )

    return response


def delete_user(app, membership, user, token):
    request, response = app.test_client.delete(
        '/api/v1/memberships/{}/users/{}'.format(str(membership['_id']), str(user['_id'])),
        headers={
            'Authorization': 'Bearer {}'.format(token)
        }
    )

    return response


def create_application(app, membership, token):
    application_model = {
        'name': 'test_application'
    }

    headers = {
        'Authorization': 'Bearer {}'.format(token)
    }

    request, response = app.test_client.post(
        '/api/v1/memberships/{}/applications'.format(str(membership['_id'])),
        data=json.dumps(application_model),
        headers=headers
    )

    return response


def get_application(app, membership, application_id, token):
    request, response = app.test_client.get(
        '/api/v1/memberships/{}/applications/{}'.format(str(membership['_id']), application_id),
        headers={
            'Authorization': 'Bearer {}'.format(token)
        }
    )

    return response


def update_application_name(app, membership, application, token):
    application['name'] = 'updated_test_application'
    request, response = app.test_client.put(
        '/api/v1/memberships/{}/applications/{}'.format(str(membership['_id']), application['_id'], token),
        data=json.dumps(application),
        headers={
            'Authorization': 'Bearer {}'.format(token)
        }
    )

    return response


def query_applications(app, membership, token):
    request, response = app.test_client.post(
        '/api/v1/memberships/{}/applications/_query'.format(str(membership['_id'])),
        data=json.dumps({
            'where': {},
            'select': {}
        }),
        headers={
            'Authorization': 'Bearer {}'.format(token)
        }
    )

    return response


def delete_application(app, membership, application_id, token):
    request, response = app.test_client.delete(
        '/api/v1/memberships/{}/applications/{}'.format(str(membership['_id']), application_id),
        headers={
            'Authorization': 'Bearer {}'.format(token)
        }
    )

    return response


def create_role(app, membership, token):
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
        '/api/v1/memberships/{}/roles'.format(str(membership['_id'])),
        data=json.dumps(role_model),
        headers=headers
    )

    return response


def get_role(app, membership, role_id, token):
    request, response = app.test_client.get(
        '/api/v1/memberships/{}/roles/{}'.format(str(membership['_id']), role_id),
        headers={
            'Authorization': 'Bearer {}'.format(token)
        }
    )

    return response


def update_role_name(app, membership, role, token):
    role['name'] = 'updated_test_role'
    request, response = app.test_client.put(
        '/api/v1/memberships/{}/roles/{}'.format(str(membership['_id']), role['_id'], token),
        data=json.dumps(role),
        headers={
            'Authorization': 'Bearer {}'.format(token)
        }
    )

    return response


def query_roles(app, membership, token):
    request, response = app.test_client.post(
        '/api/v1/memberships/{}/roles/_query'.format(str(membership['_id'])),
        data=json.dumps({
            'where': {},
            'select': {}
        }),
        headers={
            'Authorization': 'Bearer {}'.format(token)
        }
    )

    return response


def delete_role(app, membership, role_id, token):
    request, response = app.test_client.delete(
        '/api/v1/memberships/{}/roles/{}'.format(str(membership['_id']), role_id),
        headers={
            'Authorization': 'Bearer {}'.format(token)
        }
    )

    return response


def get_me(app, token):
    request, response = app.test_client.delete(
        '/api/v1/me',
        headers={
            'Authorization': 'Bearer {}'.format(token)
        }
    )

    return response


def please_refresh_token(app, r_token, a_token):
    request, response = app.test_client.post(
        '/api/v1/refres-token',
        data=json.dumps({'token': r_token}),
        headers={
            'Authorization': 'Bearer {}'.format(a_token)
        }
    )

    return response


def revoke_token(app, r_token, a_token):
    request, response = app.test_client.post(
        '/api/v1/revoke-token',
        data=json.dumps({'token': r_token}),
        headers={
            'Authorization': 'Bearer {}'.format(a_token)
        }
    )