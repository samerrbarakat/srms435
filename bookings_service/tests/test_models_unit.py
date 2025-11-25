
from contextlib import contextmanager
from datetime import datetime, timedelta

import pytest

from bookings_service import models


class DummyCursor:
    """ A dummy cursor to simulate database operations."""
    def __init__(self, one=None, many=None):
        """ Initialize with optional single row or multiple rows to return."""
        self._one = one
        self._many = many or []
        self.executed = []
        self.closed = False

    def execute(self, sql, params=None):
        """Simulate executing a SQL command."""
        # strip to reduce whitespace differences
        self.executed.append((sql.strip(), params))

    def fetchone(self):
        """Return a single row."""
        return self._one

    def fetchall(self):
        """Return all rows."""
        return self._many

    def __enter__(self):
        """Enter the runtime context related to this object."""
        return self

    def __exit__(self, exc_type, exc, tb):
        """Exit the runtime context related to this object."""
        self.closed = True


class DummyConn:
    """ A dummy connection to simulate database connection."""
    def __init__(self, cursor: DummyCursor):
        """ Initialize with a dummy cursor."""
        self.cursor_obj = cursor
        self.committed = False
        self.closed = False

    def cursor(self, *args, **kwargs):
        """Return the dummy cursor."""
        return self.cursor_obj

    def commit(self):
        """Simulate committing a transaction."""
        self.committed = True

    def close(self):
        """Simulate closing the connection."""
        self.closed = True


@contextmanager
def conn_ctx(conn: DummyConn):
    """Context manager for dummy connection."""
    yield conn


# ---------- db_check_room_availability ----------

def test_db_check_room_availability_missing_args_returns_false():
    """Test that db_check_room_availability returns False when any argument is missing."""
    assert models.db_check_room_availability(None, "s", "e") is False
    assert models.db_check_room_availability(1, None, "e") is False
    assert models.db_check_room_availability(1, "s", None) is False


def test_db_check_room_availability_no_conflict(monkeypatch):
    """Test that db_check_room_availability returns True when there is no conflicting booking."""
    cur = DummyCursor(one=None)  # no conflicting row
    conn = DummyConn(cur)

    monkeypatch.setattr(models, "get_db_connection", lambda: conn_ctx(conn))

    ok = models.db_check_room_availability(10, "start", "end")

    assert ok is True
    assert len(cur.executed) == 1
    sql, params = cur.executed[0]
    assert "FROM bookings" in sql
    assert params == (10, "start", "end")


def test_db_check_room_availability_with_conflict(monkeypatch):
    """Test that db_check_room_availability returns False when there is a conflicting booking."""
    cur = DummyCursor(one={"dummy": 1})  # conflict row
    conn = DummyConn(cur)

    monkeypatch.setattr(models, "get_db_connection", lambda: conn_ctx(conn))

    ok = models.db_check_room_availability(10, "start", "end")

    assert ok is False


# ---------- db_create_booking ----------

def test_db_create_booking_success(monkeypatch):
    """Test that db_create_booking successfully creates a booking and returns the booking row."""
    booking_row = {
        "id": 1,
        "user_id": 5,
        "room_id": 10,
        "start_time": "s",
        "end_time": "e",
        "status": "confirmed",
        "created_at": "2025-01-01T12:00:00",
    }
    cur = DummyCursor(one=booking_row)
    conn = DummyConn(cur)

    monkeypatch.setattr(models, "get_db_connection", lambda: conn_ctx(conn))

    result = models.db_create_booking(5, 10, "s", "e")

    assert result == booking_row
    assert conn.committed is True
    assert len(cur.executed) == 1
    sql, params = cur.executed[0]
    assert "INSERT INTO bookings" in sql
    assert params == (5, 10, "s", "e")


def test_db_create_booking_returns_none_when_no_row(monkeypatch):
    """Test that db_create_booking returns None when no row is returned."""
    cur = DummyCursor(one=None)
    conn = DummyConn(cur)
    monkeypatch.setattr(models, "get_db_connection", lambda: conn_ctx(conn))

    result = models.db_create_booking(5, 10, "s", "e")

    assert result is None
    assert conn.committed is True


# ---------- db_get_all_bookings ----------

def test_db_get_all_bookings(monkeypatch):
    """Test that db_get_all_bookings returns all bookings."""
    rows = [
        {"id": 1, "user_id": 1},
        {"id": 2, "user_id": 2},
    ]
    cur = DummyCursor(many=rows)
    conn = DummyConn(cur)
    monkeypatch.setattr(models, "get_db_connection", lambda: conn_ctx(conn))

    result = models.db_get_all_bookings()

    assert result == rows
    assert len(cur.executed) == 1
    sql, _ = cur.executed[0]
    assert "FROM bookings" in sql


# ---------- db_get_booking_history ----------

def test_db_get_booking_history(monkeypatch):
    """Test that db_get_booking_history returns the booking history for a user."""
    rows = [
        {"id": 1, "user_id": 10},
        {"id": 2, "user_id": 10},
    ]
    cur = DummyCursor(many=rows)
    conn = DummyConn(cur)
    monkeypatch.setattr(models, "get_db_connection", lambda: conn_ctx(conn))

    result = models.db_get_booking_history(10)

    assert result == rows
    sql, params = cur.executed[0]
    assert "WHERE user_id = %s" in sql
    assert params == (10,)


# ---------- db_get_bookings_by_user ----------

def test_db_get_bookings_by_user(monkeypatch):
    """Test that db_get_bookings_by_user returns bookings for a user excluding cancelled ones."""
    rows = [
        {"id": 1, "user_id": 7, "status": "confirmed"},
        {"id": 2, "user_id": 7, "status": "pending"},
    ]
    cur = DummyCursor(many=rows)
    conn = DummyConn(cur)
    monkeypatch.setattr(models, "get_db_connection", lambda: conn_ctx(conn))

    result = models.db_get_bookings_by_user(7)

    assert result == rows
    sql, params = cur.executed[0]
    assert "FROM bookings" in sql
    assert "status != 'cancelled'" in sql
    assert params == (7,)


# ---------- db_get_booking_by_id ----------

def test_db_get_booking_by_id_found(monkeypatch):
    """Test that db_get_booking_by_id returns the booking when found."""
    row = {"id": 42, "user_id": 1}
    cur = DummyCursor(one=row)
    conn = DummyConn(cur)
    monkeypatch.setattr(models, "get_db_connection", lambda: conn_ctx(conn))

    result = models.db_get_booking_by_id(42)

    assert result == row
    sql, params = cur.executed[0]
    assert "WHERE id = %s" in sql
    assert params == (42,)


def test_db_get_booking_by_id_not_found(monkeypatch):
    """Test that db_get_booking_by_id returns None when booking is not found."""
    cur = DummyCursor(one=None)
    conn = DummyConn(cur)
    monkeypatch.setattr(models, "get_db_connection", lambda: conn_ctx(conn))

    result = models.db_get_booking_by_id(999)

    assert result is None


# ---------- db_update_booking ----------

def test_db_update_booking_success(monkeypatch):
    """Test that db_update_booking successfully updates a booking and returns the updated row."""
    row = {"id": 1, "room_id": 2}
    cur = DummyCursor(one=row)
    conn = DummyConn(cur)
    monkeypatch.setattr(models, "get_db_connection", lambda: conn_ctx(conn))

    result = models.db_update_booking(1, 2, "s", "e")

    assert result == row
    assert conn.committed is True
    sql, params = cur.executed[0]
    assert "UPDATE bookings" in sql
    assert params == (2, "s", "e", 1)


# ---------- db_soft_cancel_booking ----------

def test_db_soft_cancel_booking_success(monkeypatch):
    """Test that db_soft_cancel_booking successfully cancels a booking and returns the updated row."""
    row = {"id": 1, "status": "cancelled"}
    cur = DummyCursor(one=row)
    conn = DummyConn(cur)
    monkeypatch.setattr(models, "get_db_connection", lambda: conn_ctx(conn))

    result = models.db_soft_cancel_booking(1)

    assert result == row
    assert conn.committed is True
    sql, params = cur.executed[0]
    assert "SET status = 'cancelled'" in sql
    assert params == (1,)


# ---------- db_hard_delete_booking ----------

def test_db_hard_delete_booking_commits(monkeypatch):
    """Test that db_hard_delete_booking deletes a booking and commits the transaction."""
    cur = DummyCursor()
    conn = DummyConn(cur)
    monkeypatch.setattr(models, "get_db_connection", lambda: conn_ctx(conn))

    models.db_hard_delete_booking(1)

    assert conn.committed is True
    sql, params = cur.executed[0]
    assert "DELETE FROM bookings" in sql
    assert params == (1,)


# ---------- db_get_bookings_by_room ----------

def test_db_get_bookings_by_room(monkeypatch):
    """Test that db_get_bookings_by_room returns all bookings for a specific room."""
    rows = [{"id": 1, "room_id": 99}]
    cur = DummyCursor(many=rows)
    conn = DummyConn(cur)
    monkeypatch.setattr(models, "get_db_connection", lambda: conn_ctx(conn))

    result = models.db_get_bookings_by_room(99)

    assert result == rows
    sql, params = cur.executed[0]
    assert "WHERE room_id = %s" in sql
    assert params == (99,)
