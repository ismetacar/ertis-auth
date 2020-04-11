from run import app
from tests import insert_mock_data, remove_mock_data
from tests.helpers import (
    get_token,
    please_refresh_token,
    get_me,
    revoke_token
)

membership_doc, role_doc, user_doc = insert_mock_data()


def test_auth_all_operations():
    # region Generate Token
    response = get_token(app, membership_doc, user_doc)

    assert response.status == 201
    assert 'access_token' in response.json
    token = response.json['access_token']
    _refresh_token = response.json['refresh_token']
    # endregion

    # region Get Me

    response = get_me(app, token)

    assert response.status == 200
    user = response.json

    # endregion

    # region Refresh Token
    response = please_refresh_token(app, _refresh_token, token)
    assert response.status == 201
    assert 'access_token' in response.json
    token = response.json['access_token']
    _refresh_token = response.json['refresh_token']

    # endregion

    # region Revoke Token
    response = revoke_token(app, _refresh_token, token)
    assert response.status is 204

    # endregion
    remove_mock_data(membership_doc, user_doc, role_doc)

