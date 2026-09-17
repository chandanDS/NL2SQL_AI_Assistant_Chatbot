from backend.auth.demo_identity import (
    demo_username_for_employee_id,
    legacy_username_for_demo,
)


def test_demo_usernames_reset_for_each_office_type():
    assert demo_username_for_employee_id("BNK000001") == "houser001"
    assert demo_username_for_employee_id("BNK000008") == "houser008"
    assert demo_username_for_employee_id("BNK000009") == "couser001"
    assert demo_username_for_employee_id("BNK000041") == "rouser001"
    assert demo_username_for_employee_id("BNK000137") == "bankuser001"
    assert demo_username_for_employee_id("BNK000138") == "bankuser002"
    assert demo_username_for_employee_id("BNK000400") == "bankuser264"


def test_new_usernames_resolve_to_existing_records():
    assert legacy_username_for_demo("houser001") == "bankuser0001"
    assert legacy_username_for_demo("couser001") == "bankuser0009"
    assert legacy_username_for_demo("rouser001") == "bankuser0041"
    assert legacy_username_for_demo("bankuser001") == "bankuser0137"
    assert legacy_username_for_demo("bankuser002") == "bankuser0138"
    assert legacy_username_for_demo("bankuser265") is None
