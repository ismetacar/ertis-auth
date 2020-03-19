from run import app
from tests import insert_mock_data, remove_mock_data, remove_user_type
from tests.helpers import (
    get_token,
    delete_user,
    create_user,
    create_user_type,
    get_user_type_of_membership,
    update_username_of_created_user
)

membership_doc, role_doc, user_doc = insert_mock_data()


def test_user_crud_operations():
    # region Create User
    response = get_token(app, membership_doc, user_doc)
    token = response.json['access_token']

    response = create_user_type(app, membership_doc, token)
    user_type_id = response.json['_id']
    response = create_user(app, membership_doc, role_doc, token)

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

    # endregion

    # region Get Token With Created User

    response = get_token(app, membership_doc, user)
    assert response.status == 201
    assert response.json['access_token'] is not None
    assert response.json['token_type'] == 'bearer'

    # endregion

    # region Update User

    response = update_username_of_created_user(app, membership_doc, user, token)
    assert response.status == 200
    assert response.json['_id'] == user['_id']

    # endregion

    # region Delete User

    response = delete_user(app, membership_doc, user, token)
    assert response.status == 204
    assert response.json is None

    # endregion

    remove_user_type(user_type_id)
    remove_mock_data(membership_doc, user_doc, role_doc)
