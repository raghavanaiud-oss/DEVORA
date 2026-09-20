import time
from collections import defaultdict
from typing import Dict, List
from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    """Sliding-window rate limiter for sensitive endpoints (Auth, AI, Executions)."""

    def __init__(self, requests_limit: int = 60, window_seconds: int = 60):
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        self.history: Dict[str, List[float]] = defaultdict(list)

    async def check(self, request: Request, key: str = "") -> None:
        client_ip = request.client.host if request.client else "unknown"
        identifier = f"{client_ip}:{key}"
        now = time.time()

        # Filter out timestamps outside the window
        timestamps = [t for t in self.history[identifier] if now - t < self.window_seconds]
        if len(timestamps) >= self.requests_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please wait before trying again."
                    }
                }
            )

        timestamps.append(now)
        self.history[identifier] = timestamps


auth_rate_limiter = InMemoryRateLimiter(requests_limit=20, window_seconds=60)
ai_rate_limiter = InMemoryRateLimiter(requests_limit=30, window_seconds=60)
exec_rate_limiter = InMemoryRateLimiter(requests_limit=15, window_seconds=60)
