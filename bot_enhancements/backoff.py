import random
import time

def expo_jitter_backoff(base: float = 0.5, factor: float = 2.0, max_sleep: float = 30.0):
    delay = base
    while True:
        sleep = min(max_sleep, delay * (0.5 + random.random()))
        yield sleep
        delay *= factor

def with_backoff(fn, *args, retries: int = 5, **kwargs):
    backoff = expo_jitter_backoff()
    for attempt in range(retries):
        try:
            return fn(*args, **kwargs)
        except Exception:
            time.sleep(next(backoff))
    # Last try raises
    return fn(*args, **kwargs)