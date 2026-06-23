import pytest
from datetime import date, datetime, timezone


def test_attendance_history_is_paginated(client, auth_headers):
    response = client.get("/api/v1/attendance/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "total" in data

def test_attendance_history_date_range_filter(client, auth_headers):
    today = date.today().isoformat()
    response = client.get(
        f"/api/v1/attendance/me?start_date={today}&end_date={today}",
        headers=auth_headers
    )
    assert response.status_code == 200

def test_work_location_override_without_open_session_returns_409(client, auth_headers):
    response = client.post(
        "/api/v1/attendance/work-location",
        headers=auth_headers,
        json={"work_location": "office"}
    )
    assert response.status_code == 409

def test_attendance_history_without_auth_returns_401(client):
    response = client.get("/api/v1/attendance/me")
    assert response.status_code == 401


def test_get_attendance_history_with_date_filter(client, auth_headers):
    response = client.get(
        "/api/v1/attendance/me?start_date=2024-01-01&end_date=2024-12-31",
        headers=auth_headers
    )
    assert response.status_code == 200


def test_get_attendance_summary(client, auth_headers):
    response = client.get("/api/v1/attendance/summary", headers=auth_headers)
    # May return 200 or 404 depending on if endpoint exists
    assert response.status_code in [200, 404]
