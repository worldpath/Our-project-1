import time
from collections import defaultdict, deque

class RateGovernor:
    """Adaptive token-bucket based governor keyed by endpoint group.
    Use record_weight(key, weight) after each request.
    Call sleep_if_needed(key) before requests; it returns seconds slept.
    """
    def __init__(self, refill_per_sec: float = 20.0, bucket_cap: float = 1200.0):
        self.refill_per_sec = refill_per_sec
        self.bucket_cap = bucket_cap
        self.tokens = defaultdict(lambda: bucket_cap)
        self.last = defaultdict(lambda: time.time())
        self.events = defaultdict(lambda: deque(maxlen=100))

    def _refill(self, key: str):
        now = time.time()
        dt = now - self.last[key]
        self.tokens[key] = min(self.bucket_cap, self.tokens[key] + dt * self.refill_per_sec)
        self.last[key] = now

    def sleep_if_needed(self, key: str, weight: float = 1.0):
        self._refill(key)
        if self.tokens[key] < weight:
            deficit = weight - self.tokens[key]
            sleep_s = deficit / self.refill_per_sec
            time.sleep(max(0.0, sleep_s))
            self._refill(key)
            return sleep_s
        return 0.0

    def record_weight(self, key: str, weight: float = 1.0):
        self._refill(key)
        self.tokens[key] = max(0.0, self.tokens[key] - weight)
        self.events[key].append((time.time(), weight))