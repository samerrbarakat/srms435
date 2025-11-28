"""
This is a small inm memory reate limiter for the api endpoiints 
so we dont allow a lot short interval calls and the potential overloading of our server

It will be used like a decorator to all our routes, specifying directly what is the max number of calls in the short period of time"""


import time 
from functools import wraps

class InMemoryRateLimiter: 
    def __init__(self, calls,period): 
        """
        :param calls: max number of calls allowed
        :param period: time period in seconds
        This class stores the number of calls by id, so a user wont be alowed to call the endpoint if he exceeded the timed limit 
        
        self._store stores per-client/ip, maps key to [window_start_time, call_count]
        """
        self.calls = calls 
        self.period = period 
        
        self._store = {}    
        
    def is_allowed(self, key) -> tuple[bool, float | None]:
        now = time.time()
        window, count = self._store.get(key,[now,0])
        
        # if request count exceeds the rate limit period , reset the window and count
        if now - window >= self.period:
            window, count = now, 0
        
        if count >= self.calls:
            retry = self.period - (now - window)
            self._store[key] = [window, count]
            return False, max(0.0, retry)

        self._store[key] = [window, count + 1]
        return True, None

def rate_limit(calls, period):
    """
    this is a decorator to limit requests per client/IP 
    It takes as input the max num of requests and the period of the window in seconds
    """

    limiter = InMemoryRateLimiter(calls, period)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from flask import request, jsonify
            
            # Use client IP as key
            client_ip = request.remote_addr or "unknown"
            
            allowed, retry_after = limiter.is_allowed(client_ip)
            if not allowed:
                response = jsonify({
                    "message": f"Rate limit exceeded. Try again in {int(retry_after)} seconds."
                })
                response.status_code = 429  # Too Many Requests
                response.headers['Retry-After'] = str(int(retry_after))
                return response
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator