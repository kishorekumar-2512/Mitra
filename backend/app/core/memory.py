"""Redis session persistence with a safe in-memory fallback for local development."""
import json
from typing import Any
from redis.asyncio import Redis


class SessionMemory:
    """Stores compact Claude history, last result, pinned views and history for two hours."""
    def __init__(self, redis: Redis | None = None) -> None:
        self.redis = redis
        self._fallback: dict[str, dict[str, Any]] = {}
        self.ttl = 7200

    async def get(self, session_id: str) -> dict[str, Any]:
        key = f"insightforge:{session_id}"
        if self.redis:
            raw = await self.redis.get(key)
            return json.loads(raw) if raw else self._default()
        return self._fallback.get(session_id, self._default())

    async def save(self, session_id: str, data: dict[str, Any]) -> None:
        key = f"insightforge:{session_id}"
        if self.redis:
            await self.redis.set(key, json.dumps(data, default=str), ex=self.ttl)
        else:
            self._fallback[session_id] = data

    @staticmethod
    def _default() -> dict[str, Any]:
        return {"history": [], "last_result": None, "pinned": [], "query_history": []}
