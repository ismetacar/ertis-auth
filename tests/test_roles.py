from run import app
from tests import insert_mock_data, remove_mock_data
from tests.helpers import (
    get_token,
    update_role_name,
    query_roles,
    delete_role,
    create_role,
    get_role
)

membership_doc, role_doc, user_doc = insert_mock_data()


def test_role_crud_operations():
    # region Create Role
    response = get_token(app, membership_doc, user_doc)
    token = response.json['access_token']

    response = create_role(app, membership_doc, token)

    assert response.status == 201
    assert response.json['name'] == 'test_role'

    role_id = response.json['_id']

    # endregion

    # region Get Role

    response = get_role(app, membership_doc, role_id, token)

    assert response.status == 200
    assert response.json['name'] == 'test_role'
    role = response.json

    # endregion

    # region Update Role

    response = update_role_name(app, membership_doc, role, token)
    assert response.status == 200
    assert response.json['_id'] == role['_id']

    # endregion

    # region Query Roles

    response = query_roles(app, membership_doc, token)
    assert response.status == 200
    assert response.json is not None
    roles_query_result = response.json
    assert 'data' in roles_query_result
    data = roles_query_result['data']
    assert 'items' in data
    assert 'count' in data

    assert data['count'] != 0

    # endregion

    # region Delete Role

    response = delete_role(app, membership_doc, role_id, token)
    assert response.status == 204

    # endregion

    remove_mock_data(membership_doc, user_doc, role_doc)
