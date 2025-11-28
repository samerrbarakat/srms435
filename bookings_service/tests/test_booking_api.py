# bookings_service/tests/test_bookings_api.py

from datetime import datetime, timedelta
import pytest
import bookings_service.main as main 


FIXED_NOW = datetime(2025, 1, 1, 12, 0, 0)


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def app(monkeypatch):
    """Create app with stubbed auth and deterministic time for testing."""
    # Stub JWT decoder used by authenticate_request
    def fake_degenerate_jwt(token, secret="your_secret_key"):
        if token == "user-token":
            return {"user_id": 1, "role": "user"}
        if token == "fm-token":
            return {"user_id": 2, "role": "facility_manager"}
        if token == "admin-token":
            return {"user_id": 3, "role": "admin"}
        raise ValueError("invalid token")

    monkeypatch.setattr(main, "degenerate_jwt", fake_degenerate_jwt)
    # Make `now()` deterministic
    monkeypatch.setattr(main, "now", lambda: FIXED_NOW)

    app = main.create_app()
    app.config.update(TESTING=True)
    return app


@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return app.test_client()


# ---------- /api/v1/bookings (POST) ----------

def test_create_booking_requires_auth(client):
    """Test that creating a booking requires authentication."""
    resp = client.post("/api/v1/bookings", json={})
    assert resp.status_code == 401


def test_create_booking_room_not_found(client, monkeypatch):
    """Test that creating a booking fails if the room does not exist."""
    def fake_check_room_exists(room_id):
        return False

    monkeypatch.setattr(main, "db_check_room_exists", fake_check_room_exists)

    payload = {
        "room_id": 10,
        "start_time": "2025-01-01T13:00:00",
        "end_time": "2025-01-01T14:00:00",
    }

    resp = client.post(
        "/api/v1/bookings",
        json=payload,
        headers=_auth_header("user-token"),
    )

    assert resp.status_code == 400
    assert "does not belong" in resp.get_json()["message"]


def test_create_booking_conflict(client, monkeypatch):
    """Test that creating a booking fails if there is a conflict."""
    monkeypatch.setattr(main, "db_check_room_exists", lambda room_id: True)
    monkeypatch.setattr(main, "db_check_room_availability", lambda r, s, e: False)

    payload = {
        "room_id": 10,
        "start_time": "2025-01-01T13:00:00",
        "end_time": "2025-01-01T14:00:00",
    }

    resp = client.post(
        "/api/v1/bookings",
        json=payload,
        headers=_auth_header("user-token"),
    )

    assert resp.status_code == 409
    assert "not available" in resp.get_json()["message"]


def test_create_booking_success(client, monkeypatch):
    """Test that creating a booking succeeds with valid input."""
    
    monkeypatch.setattr(main, "db_check_room_exists", lambda room_id: True)
    monkeypatch.setattr(main, "db_check_room_availability", lambda r, s, e: True)

    def fake_create_booking(user_id, room_id, start, end):
        return {
            "id": 1,
            "user_id": user_id,
            "room_id": room_id,
            "start_time": start,
            "end_time": end,
            "status": "confirmed",
            "created_at": FIXED_NOW,
        }

    monkeypatch.setattr(main, "db_create_booking", fake_create_booking)

    payload = {
        "room_id": 10,
        "start_time": "2025-01-01T13:00:00",
        "end_time": "2025-01-01T14:00:00",
    }

    resp = client.post(
        "/api/v1/bookings",
        json=payload,
        headers=_auth_header("user-token"),
    )

    assert resp.status_code == 201
    assert "Booking creation" in resp.get_json()["message"]


# ---------- /api/v1/bookings/myhistory (GET) ----------

def test_get_booking_history_success(client, monkeypatch):
    """Test that getting booking history for the authenticated user succeeds."""
    expected = [
        {"id": 1, "user_id": 1},
        {"id": 2, "user_id": 1},
    ]

    def fake_get_history(user_id):
        assert user_id == 1
        return expected

    monkeypatch.setattr(main, "db_get_booking_history", fake_get_history)

    resp = client.get(
        "/api/v1/bookings/myhistory",
        headers=_auth_header("user-token"),
    )

    assert resp.status_code == 200
    assert resp.get_json() == expected


# ---------- /api/v1/bookings/user/<user_id> (GET) ----------

def test_get_user_bookings_forbidden_for_other_user(client, monkeypatch):
    """Test that a regular user cannot view another user's bookings."""
    resp = client.get(
        "/api/v1/bookings/user/2",  # different from user_id=1 in token
        headers=_auth_header("user-token"),
    )
    assert resp.status_code == 403


def test_get_user_bookings_admin_can_view_other_user(client, monkeypatch):
    """Test that an admin can view another user's bookings."""
    expected = [{"id": 1, "user_id": 5}]

    def fake_get_bookings(user_id):
        assert user_id == 5
        return expected

    monkeypatch.setattr(main, "db_get_bookings_by_user", fake_get_bookings)

    resp = client.get(
        "/api/v1/bookings/user/5",
        headers=_auth_header("admin-token"),
    )

    assert resp.status_code == 200
    assert resp.get_json() == expected


def test_get_user_bookings_not_found(client, monkeypatch):
    """Test that getting bookings for a user with no bookings returns 404."""
    monkeypatch.setattr(main, "db_get_bookings_by_user", lambda uid: None)

    resp = client.get(
        "/api/v1/bookings/user/5",
        headers=_auth_header("admin-token"),
    )

    assert resp.status_code == 404


# ---------- /api/v1/bookings (GET all) ----------

def test_get_all_bookings_user_forbidden(client):
    """Test that a regular user cannot view all bookings."""
    resp = client.get(
        "/api/v1/bookings",
        headers=_auth_header("user-token"),
    )
    assert resp.status_code == 403


def test_get_all_bookings_admin_ok(client, monkeypatch):
    """Test that an admin can view all bookings."""
    expected = [{"id": 1}, {"id": 2}]
    monkeypatch.setattr(main, "db_get_all_bookings", lambda: expected)

    resp = client.get(
        "/api/v1/bookings",
        headers=_auth_header("admin-token"),
    )

    assert resp.status_code == 200
    assert resp.get_json() == expected


# ---------- /api/v1/bookings/<id> (GET) ----------

def test_get_booking_not_found(client, monkeypatch):
    """Test that getting a booking that does not exist returns 404."""
    monkeypatch.setattr(main, "db_get_booking_by_id", lambda bid: None)

    resp = client.get(
        "/api/v1/bookings/1",
        headers=_auth_header("admin-token"),
    )

    assert resp.status_code == 404


def test_get_booking_user_only_own(client, monkeypatch):
    """Test that a regular user can only view their own booking."""
    booking = {"id": 1, "user_id": 2}  # different from user_id=1 token

    monkeypatch.setattr(main, "db_get_booking_by_id", lambda bid: booking)

    resp = client.get(
        "/api/v1/bookings/1",
        headers=_auth_header("user-token"),
    )

    assert resp.status_code == 403


def test_get_booking_success(client, monkeypatch):
    """Test that a regular user can view their own booking."""
    booking = {"id": 1, "user_id": 1}

    monkeypatch.setattr(main, "db_get_booking_by_id", lambda bid: booking)

    resp = client.get(
        "/api/v1/bookings/1",
        headers=_auth_header("user-token"),
    )

    assert resp.status_code == 200
    assert resp.get_json() == booking


# ---------- /api/v1/bookings/<id> (PATCH) ----------

def test_update_booking_success(client, monkeypatch):
    """Test that updating a booking succeeds with valid input."""
    future_start = FIXED_NOW + timedelta(hours=1)

    booking_row = {
        "id": 1,
        "user_id": 1,
        "room_id": 10,
        "start_time": future_start,
        "end_time": future_start + timedelta(hours=1),
        "status": "confirmed",
    }

    monkeypatch.setattr(main, "db_get_booking_by_id", lambda bid: booking_row)
    monkeypatch.setattr(main, "db_check_room_exists", lambda rid: True)
    monkeypatch.setattr(
        main, "db_check_room_availability",
        lambda rid, s, e: True,
    )

    def fake_update(bid, room_id, start, end):
        """Fake update booking function for testing."""
        assert bid == 1
        return {
            **booking_row,
            "room_id": room_id,
            "start_time": start,
            "end_time": end,
        }

    monkeypatch.setattr(main, "db_update_booking", fake_update)

    payload = {
        "room_id": 99,
        "start_time": future_start,
        "end_time": future_start + timedelta(hours=2),
    }

    resp = client.patch(
        "/api/v1/bookings/1",
        json=payload,
        headers=_auth_header("user-token"),
    )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["room_id"] == 99


# ---------- /api/v1/bookings/<id>/cancel (POST) ----------

def test_soft_cancel_booking_success(client, monkeypatch):
    """Test that soft cancelling a booking succeeds."""
    future_start = FIXED_NOW + timedelta(hours=1)

    booking = {
        "id": 1,
        "user_id": 1,
        "room_id": 10,
        "start_time": future_start,
        "end_time": future_start + timedelta(hours=1),
        "status": "confirmed",
    }

    monkeypatch.setattr(main, "db_get_booking_by_id", lambda bid: booking)

    def fake_soft_cancel(bid):
        assert bid == 1
        return {**booking, "status": "cancelled"}

    monkeypatch.setattr(main, "db_soft_cancel_booking", fake_soft_cancel)

    resp = client.post(
        "/api/v1/bookings/1/cancel",
        headers=_auth_header("user-token"),
    )

    assert resp.status_code == 200
    assert "cancelled" in resp.get_json()["message"]


# ---------- /api/v1/bookings/<id>/hard (DELETE) ----------

def test_hard_cancel_booking_admin_only(client, monkeypatch):
    """Test that only an admin can hard delete a booking."""
    booking = {"id": 1}
    monkeypatch.setattr(main, "db_get_booking_by_id", lambda bid: booking)
    monkeypatch.setattr(main, "db_hard_delete_booking", lambda bid: None)

    resp = client.delete(
        "/api/v1/bookings/1/hard",
        headers=_auth_header("admin-token"),
    )

    assert resp.status_code == 200
    assert "permanently deleted" in resp.get_json()["message"]


# ---------- /api/v1/bookings/availability (GET) ----------

def test_check_availability_success(client, monkeypatch):
    """Test that checking room availability succeeds."""
    monkeypatch.setattr(main, "db_check_room_exists", lambda rid: True)
    monkeypatch.setattr(
        main, "db_check_room_availability",
        lambda rid, s, e: True,
    )

    resp = client.get(
        "/api/v1/bookings/availability"
        "?room_id=10&start_time=s&end_time=e",
        headers=_auth_header("user-token"),
    )

    assert resp.status_code == 200
    assert resp.get_json() == {"room_available": True}


# ---------- /api/v1/bookings/room/<room_id> (GET) ----------

def test_get_bookings_for_room_facility_manager(client, monkeypatch):
    """Test that a facility manager can view bookings for a specific room."""
    expected = [
        {"id": 1, "room_id": 10},
        {"id": 2, "room_id": 10},
    ]

    monkeypatch.setattr(main, "db_get_bookings_by_room", lambda room_id: expected)

    resp = client.get(
        "/api/v1/bookings/room/10",
        headers=_auth_header("fm-token"),
    )

    assert resp.status_code == 200
    assert resp.get_json()["bookings"] == expected
