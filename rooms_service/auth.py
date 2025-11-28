
import os
import jwt
from typing import List, Optional


DEFAULT_ALGORITHMS = ["HS256"]


def get_jwt_secret() -> str:
    """Return the JWT secret, preferring the environment variable if set."""
    return os.getenv("your_secret_key")


def degenerate_jwt(token, secret = "your_secret_key", algorithms: list = ['HS256']) -> dict:
    """Decodes a JWT token.

    Args:
        token (str): The JWT token to decode.
        secret (str): The secret key to verify the JWT.
        algorithms (list, optional): List of allowed algorithms. Defaults to ['HS256'].

    Returns:
        dict: The decoded payload.

    Raises jwt.ExpiredSignatureError, jwt.InvalidTokenError on failure.
    """
    return jwt.decode(token, secret , algorithms=algorithms)     