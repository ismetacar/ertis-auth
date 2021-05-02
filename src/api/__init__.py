from sanic_openapi import swagger_blueprint


def init_swagger(app, settings):
    app.blueprint(swagger_blueprint)

    app.config["API_VERSION"] = "2.0.0"
    app.config["API_TITLE"] = "Ertis Auth"
    app.config["API_DESCRIPTION"] = "Generic token generator and validator"
    app.config["API_LICENSE_URL"] = "https://github.com/ismetacar/ertis-auth/blob/master/LICENSE"
    app.config["API_CONTACT_EMAIL"] = "dismetacar@gmail.com"
    app.config["API_LICENSE_NAME"] = "MIT"
    app.config["API_SECURITY"] = [{"Authorization": []}]
    app.config["API_SECURITY_DEFINITIONS"] = {
        "Authorization": {"type": "apiKey", "in": "header", "name": "Authorization"}
    }
    app.config.SWAGGER_UI_CONFIGURATION = {
        'displayRequestDuration': True
    }

    app.config["API_BASEPATH"] = "/api"
    app.config["API_HOST"] = settings["host"]
