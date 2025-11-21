# tests/test_auth_unit.py
import jwt
import pytest

from users_service.auth import (
    hasher,
    verify_password,
    generate_jwt,
    degenerate_jwt,  
)
TEST_SECRET = "your_secret_key" # must match for encode/decode


def test_hasher_is_deterministic_for_same_password():
    password = "my-secret-password"
    h1 = hasher(password)
    h2 = hasher(password)

    assert isinstance(h1, str)
    assert h1 == h2


def test_hasher_produces_different_hash_for_different_passwords():
    password_1 = "pw-1"
    password_2 = "pw-2"

    hash_1 = hasher(password_1)
    hash_2 = hasher(password_2)

    assert hash_1 != hash_2


def test_verify_password_accepts_correct_password():
    password = "some-password"
    hashed = hasher(password)

    assert verify_password(hashed, password) is True


def test_verify_password_rejects_wrong_password():
    password = "some-password"
    hashed = hasher(password)

    assert verify_password(hashed, "wrong-password") is False


def test_generate_and_degenerate_jwt_roundtrip():
    """
    Happy path: encoding + decoding preserves payload fields.
    """
    payload = {"user_id": 123, "username": "alice", "role": "user"}

    token = generate_jwt(payload, TEST_SECRET)
    assert isinstance(token, str)
    assert len(token) > 0

    decoded = degenerate_jwt(token, TEST_SECRET)
    # We only assert on keys we know you put into the payload.
    for key, value in payload.items():
        assert decoded[key] == value


def test_degenerate_jwt_invalid_token_behavior():
    payload = {"user_id": 1}
    token = generate_jwt(payload, TEST_SECRET)

    tampered = token + "a"

    with pytest.raises(jwt.exceptions.InvalidTokenError):
        degenerate_jwt(tampered, TEST_SECRET)
