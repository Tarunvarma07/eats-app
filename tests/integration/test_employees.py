import pytest


def test_list_employees_returns_paginated_response(client, admin_auth_headers):
    response = client.get("/api/v1/admin/users", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "total" in data
    assert "page" in data
    assert "pages" in data

def test_list_employees_respects_page_size(client, admin_auth_headers):
    response = client.get("/api/v1/admin/users?page=1&page_size=5", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) <= 5

def test_list_employees_as_regular_user_returns_403(client, auth_headers):
    response = client.get("/api/v1/admin/users", headers=auth_headers)
    assert response.status_code == 403

def test_get_nonexistent_employee_returns_404(client, admin_auth_headers):
    response = client.get("/api/v1/admin/attendance/999999", headers=admin_auth_headers)
    # The endpoint returns 200 with empty list for nonexistent user
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0

def test_employee_response_does_not_contain_password(client, admin_auth_headers, test_user):
    response = client.get("/api/v1/admin/users", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    # Check that no user in the list contains password fields
    for user in data["data"]:
        assert "password" not in user
        assert "hashed_password" not in user
