import hashlib
import jwt 

def degenerate_jwt(token, secret, algorithms: list = ['HS256']) -> dict:
    """Decodes a JWT token.

    Args:
        token (str): The JWT token to decode.
        secret (str): The secret key to verify the JWT.
        algorithms (list, optional): List of allowed algorithms. Defaults to ['HS256'].

    Returns:
        dict: The decoded payload.

    Raises jwt.ExpiredSignatureError, jwt.InvalidTokenError on failure.
    """
    return jwt.decode(token, secret, algorithms=algorithms)     