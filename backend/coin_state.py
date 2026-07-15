import time
from threading import Lock


class CoinState:
    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.amount = 0
        self.safe = False
        self.last_pulse_time = 0.0
        self._state_lock = Lock()
        self._initialized = True

    def add_coin(self, value: int) -> None:
        with self._state_lock:
            self.amount += value
            self.last_pulse_time = time.time()

    def reset(self) -> None:
        with self._state_lock:
            self.amount = 0
            self.last_pulse_time = 0.0

    def get_seconds_since_last_pulse(self) -> float:
        with self._state_lock:
            if self.last_pulse_time == 0:
                return float("inf")
            return time.time() - self.last_pulse_time

    def to_dict(self, minutes_per_peso: int, auto_grant_timeout: int, minimum_amount: int) -> dict:
        with self._state_lock:
            minutes = self.amount * minutes_per_peso
            if self.last_pulse_time == 0:
                seconds_since = float("inf")
            else:
                seconds_since = time.time() - self.last_pulse_time
            remaining = max(0, auto_grant_timeout - int(seconds_since)) if self.amount > 0 else auto_grant_timeout
            return {
                "amount": self.amount,
                "minutes": minutes,
                "safe": self.safe,
                "button_enabled": self.amount >= minimum_amount,
                "auto_grant_seconds": remaining if self.amount >= minimum_amount else auto_grant_timeout,
                "rate": minutes_per_peso,
            }
