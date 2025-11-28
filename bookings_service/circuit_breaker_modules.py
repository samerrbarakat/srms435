import requests
from bookings_service.circuit_breaker import CircuitBreaker, ServiceUnavailable


user_service_cb = CircuitBreaker(
    name="users_service",
    failure_threshold=3,
    recovery_timeout=20,
    expected_exception=requests.RequestException,
)


@user_service_cb
def fetch_user(user_id: int, token: str) -> dict:
    """
    Call Users service to verify the user exists and get its info.
    Protected by circuit breaker, forwards the Authorization token.
    """
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(
        f"http://users_service:8000/api/v1/users/{user_id}",
        headers=headers,
        timeout=3
    )
    resp.raise_for_status()
    return resp.json()

