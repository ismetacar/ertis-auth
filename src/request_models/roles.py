from typing import List


class Role(object):
    name: str
    permissions: List[str]
    membership_owner: bool
