class GenerateToken(object):
    username: str
    password: str


class RefreshToken(object):
    token: str


class RevokeToken(object):
    token: str


class VerifyToken(object):
    token: str


class ResetPassword(object):
    email: str


class SetPassword(object):
    email: str
    password: str
    reset_token: str


class ChangePassword(object):
    user_id: str
    password: str
    password_confirm: str
