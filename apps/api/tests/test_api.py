from __future__ import annotations

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["data"] == {"status": "ok", "database": "ok"}


def test_protected_endpoint_requires_bearer(client: TestClient) -> None:
    response = client.get("/api/projects")

    assert response.status_code == 401
    assert response.json()["success"] is False


def test_login_and_user_info(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/admin/user/info", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["data"]["username"] == "admin"


def test_login_rejects_bad_password(client: TestClient) -> None:
    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "wrong"},
    )

    assert response.status_code == 401
    assert response.json()["success"] is False


def test_validation_error_uses_envelope(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/projects",
        headers=auth_headers,
        json={"name": "", "path": "relative", "vcs_type": "git"},
    )

    assert response.status_code == 422
    assert response.json()["success"] is False
    assert response.json()["code"] == 422


def test_menu_is_available(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/admin/menu/userMenu/admin", headers=auth_headers)

    assert response.status_code == 200
    menus = response.json()["data"]
    names = {child["name"] for item in menus for child in item.get("children", [])}
    assert "projects" in names


def _create_project(
    client: TestClient, headers: dict[str, str], name: str, path: str
) -> dict[str, object]:
    response = client.post(
        "/api/projects",
        headers=headers,
        json={"name": name, "path": path, "vcs_type": "git", "enabled": True},
    )
    assert response.status_code == 200
    return response.json()["data"]


def test_project_create_writes_audit(client: TestClient, auth_headers: dict[str, str]) -> None:
    project = _create_project(client, auth_headers, "项目 A", "/workspace/a")

    assert project["name"] == "项目 A"

    audit = client.get("/admin/audit-logs", headers=auth_headers)
    assert audit.status_code == 200
    assert audit.json()["data"]["total"] == 1
    assert audit.json()["data"]["records"][0]["action"] == "project.create"
    assert audit.json()["data"]["records"][0]["actor"] == "admin"


def test_project_pagination_envelope(client: TestClient, auth_headers: dict[str, str]) -> None:
    for index in range(3):
        _create_project(client, auth_headers, f"项目 {index}", f"/workspace/p{index}")

    response = client.get("/api/projects?limit=2&offset=1", headers=auth_headers)
    body = response.json()

    assert response.status_code == 200
    assert body["code"] == 0
    assert body["success"] is True
    assert body["data"]["total"] == 3
    assert len(body["data"]["records"]) == 2


def test_business_modules_are_reachable(client: TestClient, auth_headers: dict[str, str]) -> None:
    project = _create_project(client, auth_headers, "项目 B", "/workspace/b")
    project_id = project["id"]

    paths = [
        f"/api/documents?project_id={project_id}",
        f"/api/reports?project_id={project_id}",
        f"/api/capabilities?project_id={project_id}",
        "/api/jobs",
        f"/api/chat/conversations?project_id={project_id}",
    ]
    for path in paths:
        response = client.get(path, headers=auth_headers)
        assert response.status_code == 200, path
        assert response.json()["success"] is True, path
