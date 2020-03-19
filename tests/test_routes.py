from run import app


# region Route Test

def test_get_routes():
    request, response = app.test_client.get(
        '/api/v1/api-map'
    )

    assert response.status == 200

# endregion
