"""
Error recovery utilities: retry logic and circuit breakers.
"""
from functools import wraps
from typing import Callable, Optional
import time
from app.logger import get_logger

logger = get_logger(__name__)


class CircuitBreaker:
    """Simple circuit breaker implementation"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half_open
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker"""
        if self.state == "open":
            # Check if timeout has passed
            if self.last_failure_time and (time.time() - self.last_failure_time) > self.timeout:
                self.state = "half_open"
                logger.info("Circuit breaker: transitioning to half-open")
            else:
                raise Exception("Circuit breaker is OPEN - service unavailable")
        
        try:
            result = func(*args, **kwargs)
            # Success - reset failure count
            if self.state == "half_open":
                self.state = "closed"
                logger.info("Circuit breaker: transitioning to closed")
            self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.warning(f"Circuit breaker: OPEN after {self.failure_count} failures")
            
            raise e
    
    def reset(self):
        """Reset circuit breaker"""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"


def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Retry decorator with exponential backoff"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay
            
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        logger.error(f"Function {func.__name__} failed after {max_attempts} attempts: {str(e)}")
                        raise
                    
                    logger.warning(f"Function {func.__name__} failed (attempt {attempt}/{max_attempts}): {str(e)}. Retrying in {current_delay}s...")
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            raise Exception(f"Function {func.__name__} failed after {max_attempts} attempts")
        return wrapper
    return decorator


# Global circuit breakers for IBM services
cloudant_circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)
nlu_circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)
watsonx_circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)
speech_circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)


