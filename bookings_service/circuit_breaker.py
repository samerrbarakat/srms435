"""
Docstring for infra.circuit_breaker
In here I buuild a tiny in memory circuit breaker for inter-service HTTP calls. 

The probolem with inter-service HTTP calls is that if one service goes down, it can cause a cascading failure across the system.
The solution is to use a circuit breaker pattern, which will stop making requests to a service if it is deemed unhealthy.

States: 
- CLOSED: All requests are allowed. If the failure rate exceeds a threshold, transition to OPEN.
- OPEN: Requests are not allowed. After a timeout, transition to HALF-OPEN.
- HALF-OPEN: Allow a limited number of requests to test if the service has recovered. If successful, transition to CLOSED. If not, transition back to OPEN.

"""
import time 
from functools import wraps 


class ServiceUnavailable(RuntimeError): 
    """ This exception is rased when the circuit breaker is open and the calls are thus blocked"""
    
    pass 

class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: int = 30,
        expected_exception: type = Exception,
    ) -> None:
        """
        :param name: logical name of the downstream (e.g. 'users_service').
        :param failure_threshold: #consecutive failures before OPEN.
        :param recovery_timeout: seconds to wait before HALF_OPEN trial.
        :param expected_exception: exception type that counts as a failure.
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.state = "CLOSED"  # CLOSED | OPEN | HALF_OPEN
        self.failure_count = 0
        self.last_failure_time: float | None = None

    def current_state(self) -> str:
        """Helper so you can expose this in a health endpoint if you want."""
        return self.state

    def __call__(self, func):
        """Decorator around the function that talks to the remote service."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()

            # Fast-fail if OPEN and timeout has not expired.
            if self.state == "OPEN":
                assert self.last_failure_time is not None
                if (now - self.last_failure_time) < self.recovery_timeout:
                    # Still in cool-down period → fail fast.
                    raise ServiceUnavailable(
                        f"Circuit '{self.name}' is OPEN; "
                        f"retry after {int(self.recovery_timeout - (now - self.last_failure_time))}s."
                    )
                # Cool-down passed → give it a try in HALF_OPEN
                self.state = "HALF_OPEN"

            try:
                result = func(*args, **kwargs)
            except self.expected_exception as exc:
                # Count failure
                self.failure_count += 1
                self.last_failure_time = now

                # Transition to OPEN if threshold reached
                if self.failure_count >= self.failure_threshold:
                    self.state = "OPEN"

                # Re-raise original error so caller can decide what to do
                raise exc
            else:
                # Success → reset breaker
                self.state = "CLOSED"
                self.failure_count = 0
                self.last_failure_time = None
                return result

        return wrapper