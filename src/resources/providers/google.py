import json
import requests
from src.utils.errors import ErtisError
from src.utils.json_helpers import _parse_boolean


def validate_with_google(token, settings, membership_id):
    """
    Google return response like below.
    {
          "iss": "accounts.google.com",
          "azp": "45981970221125-h2mof6rplm390rfip01m5fc79pafvmvjj.apps.googleusercontent.com",
          "aud": "45981970221125-h2mof6rplm390rfip01m5fc79pafvmvjj.apps.googleusercontent.com",
          "sub": "106162576476054171439729",
          "email": "user@gmail.com",
          "email_verified": "true",
          "at_hash": "11fzms1WUSbHI6tdIaMYIhmw",
          "name": "user name",
          "picture": "https://lh3.googleusercontent.com/a-/AOh14GgdJJKR5aLLa8iE2PHu2RhlOjmxS0QpxndqtMWlasd3=s96-c",
          "given_name": "user",
          "family_name": "name",
          "locale": "tr",
          "iat": "15872614081",
          "exp": "15872650081",
          "jti": "196c875cc5e3b425d59b56080a66d551ca6d24780",
          "alg": "RS256",
          "kid": "f9d97b4cae904bcd76aeb20026f6b770cac221783",
          "typ": "JWT"
        }
    :param token: valid token for google
    :param settings: app settings
    :param membership_id: app membership_id
    :return: user model
    """
    response = requests.get(
        "{}?id_token={}".format(settings['google_token_validator_url'], token)
    )

    if response.status_code != 200:
        raise ErtisError(
            err_msg="Invalid token provided. ",
            err_code="errors.invalidToken",
            status_code=400
        )

    response_json = json.loads(response.text)

    return {
        'user_id': response_json['sub'],
        'email': response_json['email'],
        'email_verified': _parse_boolean(response_json['email_verified']),
        'firstname': response_json['given_name'],
        'lastname': response_json['family_name'],
        'name': response_json['name'],
        'picture': response_json['picture'],
        'locale': response_json['locale'],
        'membership_id': membership_id
    }
