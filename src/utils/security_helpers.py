_PART_DIVIDER = "."
_SUBPART_DIVIDER = ","
_WILDCARD_TOKEN = "*"


def partify(permission_string):
    if not permission_string:
        raise ValueError("Wildcard string cannot be none or empty")
    permission_string = permission_string.strip()

    _parts = []

    splitted_parts = permission_string.split(_PART_DIVIDER)
    for splitted_part in splitted_parts:
        subparts = splitted_part.lower().split(_SUBPART_DIVIDER)
        if not subparts:
            raise ValueError(
                "Wildcard string cannot contains"
                "parts with only dividers.")
        _parts.append(set(subparts))

    if not _parts:
        raise ValueError("Wildcard string cannot contain only dividers")

    return _parts


def implies(permission_1, permission_2):
    permission_parts = partify(permission_1)
    other_permission_parts = partify(permission_2)

    i = 0
    for other_permission_part in other_permission_parts:
        if len(permission_parts) - 1 < i:
            return True
        elif _WILDCARD_TOKEN not in permission_parts[i] and \
                not permission_parts[i].issuperset(other_permission_part):
            return False
        i += 1

    for i in range(i, len(permission_parts) - 1):
        if _WILDCARD_TOKEN not in permission_parts[i]:
            return False

    return True


def implies_any(permission_collection, permission):
    for _permission in permission_collection:
        if implies(_permission, permission):
            return True

    return False
