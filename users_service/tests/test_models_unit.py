# tests/test_models_unit.py

import pytest
from contextlib import contextmanager

# import models  # adjust if you package as users_service.models
from users_service import models

class DummyCursor:
    def __init__(self):
        self.queries = []
        self.params = []
        self.fetchone_result = None
        self.fetchall_result = []
        self.rowcount = 0
        self.closed = False
        self.execute_side_effect = None  # optional: raise on execute

    def execute(self, query, params=None):
        self.queries.append(query)
        self.params.append(params)
        if self.execute_side_effect is not None:
            raise self.execute_side_effect

    def fetchone(self):
        return self.fetchone_result

    def fetchall(self):
        return self.fetchall_result

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


class DummyConnection:
    def __init__(self, cursor: DummyCursor):
        self._cursor = cursor
        self.commits = 0
        self.closed = False

    def cursor(self, cursor_factory=None):
        # We ignore cursor_factory; our DummyCursor already returns dict-like rows
        return self._cursor

    def commit(self):
        self.commits += 1

    def close(self):
        self.closed = True


def patch_get_db_connection(monkeypatch, cursor: DummyCursor) -> DummyConnection:
    """
    Replace models.get_db_connection() with a context manager that yields
    a DummyConnection using the provided DummyCursor.
    """
    conn = DummyConnection(cursor)

    @contextmanager
    def fake_get_db_connection():
        yield conn

    monkeypatch.setattr(models, "get_db_connection", fake_get_db_connection)
    return conn


# ---------------------------------------------------------------------------
# get_db_connection tests (resource mgmt)
# ---------------------------------------------------------------------------

def test_get_db_connection_closes_connection_on_success(monkeypatch):
    class FakeConn:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    fake_conn = FakeConn()

    def fake_connect(_url):
        return fake_conn

    monkeypatch.setattr(models.psycopg2, "connect", fake_connect)

    with models.get_db_connection() as conn:
        assert conn is fake_conn

    assert fake_conn.closed is True


def test_get_db_connection_closes_connection_on_error(monkeypatch):
    class FakeConn:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    fake_conn = FakeConn()
    monkeypatch.setattr(models.psycopg2, "connect", lambda _url: fake_conn)

    with pytest.raises(RuntimeError):
        with models.get_db_connection() as conn:
            assert conn is fake_conn
            raise RuntimeError("boom")

    assert fake_conn.closed is True


# ---------------------------------------------------------------------------
# get_user_by_username_or_email
# ---------------------------------------------------------------------------

def test_get_user_by_username_or_email_returns_user_dict(monkeypatch):
    cursor = DummyCursor()
    expected_user = {
        "id": 1,
        "name": "Alice",
        "username": "alice",
        "email": "alice@example.com",
        "role": "user",
    }
    cursor.fetchone_result = expected_user
    patch_get_db_connection(monkeypatch, cursor)

    result = models.get_user_by_username_or_email("alice", "alice@example.com")

    assert result == expected_user
    assert len(cursor.queries) == 1
    assert "FROM users" in cursor.queries[0]
    assert cursor.params[0] == ("alice", "alice@example.com")


def test_get_user_by_username_or_email_returns_none_when_not_found(monkeypatch):
    cursor = DummyCursor()
    cursor.fetchone_result = None
    patch_get_db_connection(monkeypatch, cursor)

    result = models.get_user_by_username_or_email("ghost", "ghost@example.com")
    assert result is None


def test_get_user_by_username_or_email_returns_error_tuple_on_exception(monkeypatch):
    def fake_get_db_connection():
        raise Exception("db down")

    monkeypatch.setattr(models, "get_db_connection", fake_get_db_connection)

    user, err = models.get_user_by_username_or_email("alice", "alice@example.com")
    assert user is None
    assert isinstance(err, dict)
    assert err["type"] == "database_error"
    assert "db down" in err["msg"]


# ---------------------------------------------------------------------------
# insert_user
# ---------------------------------------------------------------------------

def test_insert_user_returns_new_user_id_and_commits(monkeypatch):
    cursor = DummyCursor()
    cursor.fetchone_result = (5,)  # cursor.fetchone()[0] -> 5
    conn = patch_get_db_connection(monkeypatch, cursor)

    new_id = models.insert_user(
        name="Bob",
        username="bob",
        email="bob@example.com",
        password_hash="hashedpw",
        role="user",
    )

    assert new_id == 5
    assert conn.commits == 1
    assert cursor.params[0] == (
        "Bob",
        "bob",
        "bob@example.com",
        "hashedpw",
        "user",
    )


def test_insert_user_returns_error_tuple_on_exception(monkeypatch):
    def fake_get_db_connection():
        raise Exception("insert failed")

    monkeypatch.setattr(models, "get_db_connection", fake_get_db_connection)

    new_id, err = models.insert_user(
        name="Bob",
        username="bob",
        email="bob@example.com",
        password_hash="hashedpw",
        role="user",
    )

    assert new_id is None
    assert err["type"] == "database_error"
    assert "insert failed" in err["msg"]


# ---------------------------------------------------------------------------
# get_all_users
# ---------------------------------------------------------------------------

def test_get_all_users_returns_list_of_dicts(monkeypatch):
    cursor = DummyCursor()
    cursor.fetchall_result = [
        {"id": 1, "name": "Alice", "username": "alice", "email": "a@example.com", "role": "user"},
        {"id": 2, "name": "Bob", "username": "bob", "email": "b@example.com", "role": "admin"},
    ]
    patch_get_db_connection(monkeypatch, cursor)

    users = models.get_all_users()

    assert isinstance(users, list)
    assert users[0]["username"] == "alice"
    assert users[1]["role"] == "admin"


def test_get_all_users_returns_error_tuple_on_exception(monkeypatch):
    def fake_get_db_connection():
        raise Exception("boom")

    monkeypatch.setattr(models, "get_db_connection", fake_get_db_connection)

    users, err = models.get_all_users()
    assert users is None
    assert err["type"] == "database_error"
    assert "boom" in err["msg"]


# ---------------------------------------------------------------------------
# get_user_by_id
# ---------------------------------------------------------------------------

def test_get_user_by_id_returns_dict_when_found(monkeypatch):
    cursor = DummyCursor()
    cursor.fetchone_result = {
        "id": 42,
        "name": "Carol",
        "username": "carol",
        "email": "carol@example.com",
        "role": "user",
    }
    patch_get_db_connection(monkeypatch, cursor)

    user = models.get_user_by_id(42)
    assert user["id"] == 42
    assert user["username"] == "carol"


def test_get_user_by_id_returns_none_when_not_found(monkeypatch):
    cursor = DummyCursor()
    cursor.fetchone_result = None
    patch_get_db_connection(monkeypatch, cursor)

    user = models.get_user_by_id(999)
    assert user is None


def test_get_user_by_id_returns_error_tuple_on_exception(monkeypatch):
    def fake_get_db_connection():
        raise Exception("terrible failure")

    monkeypatch.setattr(models, "get_db_connection", fake_get_db_connection)

    user, err = models.get_user_by_id(1)
    assert user is None
    assert err["type"] == "database_error"
    assert "terrible failure" in err["msg"]


# ---------------------------------------------------------------------------
# delete_user
# ---------------------------------------------------------------------------

def test_delete_user_returns_true_when_row_deleted(monkeypatch):
    cursor = DummyCursor()
    cursor.rowcount = 1
    conn = patch_get_db_connection(monkeypatch, cursor)

    result = models.delete_user(1)
    assert result is True
    assert conn.commits == 1
    assert cursor.params[0] == (1,)


def test_delete_user_returns_false_when_no_row_deleted(monkeypatch):
    cursor = DummyCursor()
    cursor.rowcount = 0
    conn = patch_get_db_connection(monkeypatch, cursor)

    result = models.delete_user(999)
    assert result is False
    assert conn.commits == 1


def test_delete_user_returns_error_tuple_on_exception(monkeypatch):
    def fake_get_db_connection():
        raise Exception("delete failed")

    monkeypatch.setattr(models, "get_db_connection", fake_get_db_connection)

    result, err = models.delete_user(1)
    assert result is False
    assert err["type"] == "database_error"
    assert "delete failed" in err["msg"]


# ---------------------------------------------------------------------------
# get_bookings_by_user_id
# ---------------------------------------------------------------------------

def test_get_bookings_by_user_id_returns_list_of_dicts(monkeypatch):
    cursor = DummyCursor()
    cursor.fetchall_result = [
        {"id": 1, "user_id": 10, "slot_id": 100},
        {"id": 2, "user_id": 10, "slot_id": 200},
    ]
    patch_get_db_connection(monkeypatch, cursor)

    bookings = models.get_bookings_by_user_id(10)
    assert isinstance(bookings, list)
    assert len(bookings) == 2
    assert bookings[0]["user_id"] == 10


def test_get_bookings_by_user_id_returns_error_tuple_on_exception(monkeypatch):
    def fake_get_db_connection():
        raise Exception("bookings error")

    monkeypatch.setattr(models, "get_db_connection", fake_get_db_connection)

    bookings, err = models.get_bookings_by_user_id(10)
    assert bookings is None
    assert err["type"] == "database_error"
    assert "bookings error" in err["msg"]


# ---------------------------------------------------------------------------
# update_user
# ---------------------------------------------------------------------------

def test_update_user_returns_validation_error_when_no_fields():
    ok, err = models.update_user(user_id=1)
    assert ok is False
    assert err["type"] == "validation_error"
    # Keep message loose in case you tweak wording
    assert "meaninful udates" in err["msg"]  # matches your exact string


def test_update_user_rejects_role_elevation_to_admin():
    ok, err = models.update_user(user_id=1, role="admin")
    assert ok is False
    assert err["type"] == "validation_error"
    assert "Cannot elevate role to admin" in err["msg"]


def test_update_user_success_updates_fields_and_hashes_password(monkeypatch):
    cursor = DummyCursor()
    cursor.fetchone_result = {
        "id": 1,
        "name": "New Name",
        "username": "newuser",
        "email": "new@example.com",
        "role": "user",
    }
    conn = patch_get_db_connection(monkeypatch, cursor)

    hashed_inputs = []

    def fake_hasher(pw: str) -> str:
        hashed_inputs.append(pw)
        return f"hashed-{pw}"

    monkeypatch.setattr(models, "hasher", fake_hasher)

    result = models.update_user(
        user_id=1,
        name="New Name",
        username="newuser",
        email="new@example.com",
        password="rawpw",
        role="user",
    )

    # Returned user dict
    assert result["id"] == 1
    assert result["name"] == "New Name"
    assert result["role"] == "user"

    # hasher called correctly
    assert hashed_inputs == ["rawpw"]

    # Params order: name, username, email, password(hashed), role, user_id
    params = cursor.params[0]
    assert params[0] == "New Name"
    assert params[1] == "newuser"
    assert params[2] == "new@example.com"
    assert params[3] == "hashed-rawpw"
    assert params[4] == "user"
    assert params[5] == 1

    assert conn.commits == 1


def test_update_user_returns_none_when_no_row_updated(monkeypatch):
    cursor = DummyCursor()
    cursor.fetchone_result = None
    patch_get_db_connection(monkeypatch, cursor)

    result = models.update_user(user_id=1, name="Does Not Matter")
    assert result is None


def test_update_user_unique_violation_username_returns_conflict(monkeypatch):
    # Make sure the exception type used in the except clause is our FakeUniqueViolation
    class FakeUniqueViolation(Exception):
        pass

    monkeypatch.setattr(
        models.psycopg2.errors,
        "UniqueViolation",
        FakeUniqueViolation,
        raising=False,
    )

    @contextmanager
    def fake_get_db_connection():
        # Raised inside the try: block of update_user
        raise FakeUniqueViolation("username already exists")
        yield  # unreachable

    monkeypatch.setattr(models, "get_db_connection", fake_get_db_connection)

    user, err = models.update_user(user_id=1, username="taken")
    assert user is None
    assert err["type"] == "conflict"
    assert err["msg"] == "Username already exists."


def test_update_user_unique_violation_email_returns_conflict(monkeypatch):
    class FakeUniqueViolation(Exception):
        pass

    monkeypatch.setattr(
        models.psycopg2.errors,
        "UniqueViolation",
        FakeUniqueViolation,
        raising=False,
    )

    @contextmanager
    def fake_get_db_connection():
        raise FakeUniqueViolation("email already exists")
        yield

    monkeypatch.setattr(models, "get_db_connection", fake_get_db_connection)

    user, err = models.update_user(user_id=1, email="taken@example.com")
    assert user is None
    assert err["type"] == "conflict"
    assert err["msg"] == "Email already exists."


def test_update_user_unique_violation_other_constraint_returns_generic_conflict(monkeypatch):
    class FakeUniqueViolation(Exception):
        pass

    monkeypatch.setattr(
        models.psycopg2.errors,
        "UniqueViolation",
        FakeUniqueViolation,
        raising=False,
    )

    @contextmanager
    def fake_get_db_connection():
        raise FakeUniqueViolation("some other unique constraint")
        yield

    monkeypatch.setattr(models, "get_db_connection", fake_get_db_connection)

    user, err = models.update_user(user_id=1, name="X")
    assert user is None
    assert err["type"] == "conflict"
    assert err["msg"] == "Unique constraint violated."


def test_update_user_returns_database_error_on_generic_exception(monkeypatch):
    def fake_get_db_connection():
        raise Exception("update failed")

    monkeypatch.setattr(models, "get_db_connection", fake_get_db_connection)

    user, err = models.update_user(user_id=1, name="Y")
    assert user is None
    assert err["type"] == "database_error"
    assert "update failed" in err["msg"]
