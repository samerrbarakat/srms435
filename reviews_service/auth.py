import hashlib
import jwt 

def hasher(password) :
    """Hashes a password using SHA-256.

    Args:
        password (str): The plain text password.

    Returns:
        str: The hashed password in hexadecimal format using SHA-256.
    """
    # How do we now that the same password next time will hash to the same value? 
    # Answer : Because the SHA-256 algorithm is deterministic, meaning it will always produce the same output for the same input.
    return hashlib.sha256(password.encode('utf-8')).hexdigest()
print(hasher("mypassword"))  # Example usage
def verify_password(stored_hash, provided_password) -> bool:
    """Verifies a provided password against the stored hash.

    Args:
        stored_hash (str): The stored hashed password.
        provided_password (str): The plain text password to verify.

    Returns:
        bool: True if the password matches, False otherwise.
    """
    return stored_hash == hasher(provided_password)


def generate_jwt(payload, secret, algorithm = 'HS256') :
    """Generates a JWT token.

    Args:
        payload (dict): The payload to encode in the JWT.
        secret (str): The secret key to sign the JWT.
        algorithm (str, optional): The signing algorithm. Defaults to 'HS256'.

    Returns:
        str: The generated JWT token.
    """
    return jwt.encode(payload, secret, algorithm=algorithm)

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