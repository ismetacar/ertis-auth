from run import app
from tests import insert_mock_data, remove_mock_data
from tests.helpers import (
    get_token,
    create_application,
    get_application,
    update_application_name,
    query_applications,
    delete_application
)

membership_doc, role_doc, user_doc = insert_mock_data()


def test_application_crud_operations():
    # region Create Application
    response = get_token(app, membership_doc, user_doc)
    token = response.json['access_token']

    response = create_application(app, membership_doc, token)

    assert response.status == 201
    assert response.json['name'] == 'test_application'

    application_id = response.json['_id']

    # endregion

    # region Get Application

    response = get_application(app, membership_doc, application_id, token)

    assert response.status == 200
    assert response.json['name'] == 'test_application'
    application = response.json

    # endregion

    # region Update Application

    response = update_application_name(app, membership_doc, application, token)
    assert response.status == 200
    assert response.json['_id'] == application['_id']

    # endregion

    # region Query Applications

    response = query_applications(app, membership_doc, token)
    assert response.status == 200
    assert response.json is not None
    applications_query_result = response.json
    assert 'data' in applications_query_result
    data = applications_query_result['data']
    assert 'items' in data
    assert 'count' in data

    assert data['count'] == 1

    # endregion

    # region Delete Application

    response = delete_application(app, membership_doc, application_id, token)
    assert response.status == 204

    # endregion

    remove_mock_data(membership_doc, user_doc, role_doc)
