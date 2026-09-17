import pytest
from fastapi.testclient import TestClient

from backend.core.config import get_settings
from backend.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/auth/login",
        data={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def get_scope(
    client: TestClient,
    token: str,
    organization_unit_id: int | None = None,
):
    params = (
        {"organization_unit_id": organization_unit_id}
        if organization_unit_id is not None
        else None
    )
    return client.get(
        "/auth/scope",
        params=params,
        headers={"Authorization": f"Bearer {token}"},
    )


@pytest.fixture(scope="module")
def tokens(client: TestClient) -> dict[str, str]:
    return {
        "ho": login(client, "houser001", "houser001"),
        "co1": login(client, "couser001", "couser001"),
        "ro1": login(client, "rouser001", "rouser001"),
        "branch1": login(client, "bankuser001", "bankuser001"),
    }


@pytest.fixture(scope="module")
def organizations(client: TestClient, tokens: dict[str, str]) -> dict[str, dict]:
    response = get_scope(client, tokens["ho"])
    assert response.status_code == 200
    return {item["code"]: item for item in response.json()["organizations"]}


@pytest.mark.security
def test_co_can_access_own_ro_descendants(
    client: TestClient,
    tokens: dict[str, str],
    organizations: dict[str, dict],
) -> None:
    response = get_scope(client, tokens["co1"], organizations["RO001"]["id"])

    assert response.status_code == 200
    assert response.json()["effective_root_id"] == organizations["RO001"]["id"]
    assert response.json()["organization_count"] == 9


@pytest.mark.security
def test_co_cannot_access_sibling_co(
    client: TestClient,
    tokens: dict[str, str],
    organizations: dict[str, dict],
) -> None:
    response = get_scope(client, tokens["co1"], organizations["CO002"]["id"])

    assert response.status_code == 403


@pytest.mark.security
def test_co_cannot_access_ro_in_another_circle(
    client: TestClient,
    tokens: dict[str, str],
    organizations: dict[str, dict],
) -> None:
    response = get_scope(client, tokens["co1"], organizations["RO005"]["id"])

    assert response.status_code == 403


@pytest.mark.security
def test_ro_cannot_access_sibling_ro(
    client: TestClient,
    tokens: dict[str, str],
    organizations: dict[str, dict],
) -> None:
    response = get_scope(client, tokens["ro1"], organizations["RO002"]["id"])

    assert response.status_code == 403


@pytest.mark.security
def test_ro_cannot_expand_scope_to_parent_co(
    client: TestClient,
    tokens: dict[str, str],
    organizations: dict[str, dict],
) -> None:
    response = get_scope(client, tokens["ro1"], organizations["CO001"]["id"])

    assert response.status_code == 403


@pytest.mark.security
def test_ro_cannot_access_branch_under_sibling_ro(
    client: TestClient,
    tokens: dict[str, str],
    organizations: dict[str, dict],
) -> None:
    response = get_scope(client, tokens["ro1"], organizations["BR0009"]["id"])

    assert response.status_code == 403


@pytest.mark.security
def test_branch_cannot_access_sibling_branch(
    client: TestClient,
    tokens: dict[str, str],
    organizations: dict[str, dict],
) -> None:
    response = get_scope(client, tokens["branch1"], organizations["BR0002"]["id"])

    assert response.status_code == 403


@pytest.mark.security
def test_branch_cannot_expand_scope_to_parent_ro(
    client: TestClient,
    tokens: dict[str, str],
    organizations: dict[str, dict],
) -> None:
    response = get_scope(client, tokens["branch1"], organizations["RO001"]["id"])

    assert response.status_code == 403


@pytest.mark.security
def test_branch_cannot_access_unrelated_circle(
    client: TestClient,
    tokens: dict[str, str],
    organizations: dict[str, dict],
) -> None:
    response = get_scope(client, tokens["branch1"], organizations["CO008"]["id"])

    assert response.status_code == 403


@pytest.mark.security
def test_ho_can_select_any_circle(
    client: TestClient,
    tokens: dict[str, str],
    organizations: dict[str, dict],
) -> None:
    response = get_scope(client, tokens["ho"], organizations["CO008"]["id"])

    assert response.status_code == 200
    assert response.json()["organization_count"] == 37
