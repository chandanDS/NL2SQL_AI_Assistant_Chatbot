"""Stable office-type usernames for the 400 synthetic POC identities."""

import re


DEMO_USER_PATTERN = re.compile(r"(houser|couser|rouser|bankuser)(\d{3})\Z")
OFFICE_GROUPS = (
    ("houser", 1, 8),
    ("couser", 9, 40),
    ("rouser", 41, 136),
    ("bankuser", 137, 400),
)


def demo_username_for_employee_id(employee_id: str) -> str | None:
    if not re.fullmatch(r"BNK\d{6}", employee_id):
        return None
    global_number = int(employee_id[3:])
    for prefix, first, last in OFFICE_GROUPS:
        if first <= global_number <= last:
            return f"{prefix}{global_number - first + 1:03d}"
    return None


def legacy_username_for_demo(username: str) -> str | None:
    match = DEMO_USER_PATTERN.fullmatch(username)
    if match is None:
        return None
    prefix, suffix = match.groups()
    number = int(suffix)
    for group_prefix, first, last in OFFICE_GROUPS:
        if prefix == group_prefix and 1 <= number <= last - first + 1:
            return f"bankuser{first + number - 1:04d}"
    return None
