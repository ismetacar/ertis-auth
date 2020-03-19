import json

from run import app
from tests import insert_mock_data, remove_mock_data, remove_user_type
from tests.helpers import get_token, create_user_type, get_user_type_by_id

membership_doc, role_doc, user_doc = insert_mock_data()


def test_user_type_crud_operations():
    # region Get Token
    response = get_token(app, membership_doc, user_doc)

    assert response.status == 201
    assert response.json['token_type'] == 'bearer'

    token = response.json['access_token']

    # endregion

    # region Create User Type
    response = create_user_type(app, membership_doc, token)

    assert response.status == 201
    assert response.json['_id'] is not None

    user_type_id = response.json['_id']
    # endregion

    # region Get User Type
    response = get_user_type_by_id(app, membership_doc, user_type_id, token)

    assert response.status == 200
    assert response.json['_id'] == user_type_id
    # endregion

    # region Update User Type

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

    # endregion

    # region Delete User Type From Db
    remove_user_type(user_type_id)
    # endregion

    remove_mock_data(membership_doc, user_doc, role_doc)
