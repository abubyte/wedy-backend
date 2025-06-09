from functools import wraps
from fastapi import HTTPException, status
from datetime import datetime, timedelta
from typing import Dict, Tuple
import time

# TODO: In production, use Redis
rate_limit_store: Dict[str, Tuple[int, float]] = {}

def rate_limit(times: int, minutes: int):
    """
    Rate limiting decorator.
    Args:
        times: Number of allowed requests
        minutes: Time window in minutes
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get client IP from request
            request = kwargs.get('request')
            if not request:
                for arg in args:
                    if hasattr(arg, 'client'):
                        request = arg
                        break
            
            if not request:
                return await func(*args, **kwargs)
            
            client_ip = request.client.host
            key = f"{func.__name__}:{client_ip}"
            
            # Check rate limit
            now = time.time()
            if key in rate_limit_store:
                count, timestamp = rate_limit_store[key]
                if now - timestamp < minutes * 60:
                    if count >= times:
                        raise HTTPException(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail=f"Rate limit exceeded. Try again in {int((timestamp + minutes * 60 - now) / 60)} minutes"
                        )
                    rate_limit_store[key] = (count + 1, timestamp)
                else:
                    rate_limit_store[key] = (1, now)
            else:
                rate_limit_store[key] = (1, now)
            
            # Clean up old entries
            for k in list(rate_limit_store.keys()):
                if now - rate_limit_store[k][1] > minutes * 60:
                    del rate_limit_store[k]
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator 