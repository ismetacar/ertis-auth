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


def get_user_type_of_membership(app, membership, token):
    request, response = app.test_client.get(
        '/api/v1/memberships/{}/get-user-type'.format(str(membership['_id'])),
        headers={
            'Authorization': 'Bearer {}'.format(token)
        }
    )

    return response
