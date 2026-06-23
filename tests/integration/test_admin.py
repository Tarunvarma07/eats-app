import pytest


def test_get_dashboard_stats(client, admin_auth_headers):
    response = client.get("/api/v1/admin/stats", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_employees" in data
    assert "currently_logged_in" in data


def test_get_dashboard_stats_as_employee_forbidden(client, auth_headers):
    response = client.get("/api/v1/admin/stats", headers=auth_headers)
    assert response.status_code == 403


def test_get_today_attendance(client, admin_auth_headers):
    response = client.get("/api/v1/admin/attendance/today", headers=admin_auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_weekly_report(client, admin_auth_headers):
    response = client.get("/api/v1/admin/report/weekly", headers=admin_auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_monthly_report(client, admin_auth_headers):
    response = client.get("/api/v1/admin/report/monthly", headers=admin_auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
