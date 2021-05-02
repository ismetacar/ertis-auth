import enum


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    PASSIVE = "passive"
    WARNING = "warning"
    BLOCKED = "blocked"


class User(object):
    username: str
    password: str
    email: str
    firstname: str
    lastname: str
    role: str
    status: UserStatus
