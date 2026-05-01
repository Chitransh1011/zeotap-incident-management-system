import json
import time
from uuid import UUID
from redis.asyncio import Redis


class RedisStore:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.client: Redis | None = None

    async def connect(self) -> None:
        self.client = Redis.from_url(self.redis_url, decode_responses=True)
        await self.client.ping()

    async def close(self) -> None:
        if self.client:
            await self.client.aclose()

    async def allow_rate(self, key: str, limit_per_second: int, cost: int = 1) -> bool:
        assert self.client
        bucket = f"rate:{key}:{int(time.time())}"
        count = await self.client.incrby(bucket, cost)
        if count == cost:
            await self.client.expire(bucket, 2)
        return count <= limit_per_second

    async def get_debounce_work_item(self, component_id: str) -> UUID | None:
        assert self.client
        value = await self.client.get(f"debounce:{component_id}")
        return UUID(value) if value else None

    async def try_set_debounce_work_item(
        self,
        component_id: str,
        work_item_id: UUID,
        ttl_seconds: int,
    ) -> bool:
        """
        Atomically set debounce key only if absent.
        Prevents duplicate incident creation under concurrency.
        """
        assert self.client
        return bool(
            await self.client.set(
                f"debounce:{component_id}",
                str(work_item_id),
                ex=ttl_seconds,
                nx=True,
            )
        )

    async def upsert_dashboard_item(self, item: dict) -> None:
        assert self.client
        key = f"incident:{item['id']}"

        if item["status"] == "CLOSED":
            await self.client.srem("active_incidents", item["id"])
            await self.client.delete(key)
            return

        await self.client.set(
            key,
            json.dumps(item, default=str),
        )
        await self.client.sadd("active_incidents", item["id"])

    async def list_dashboard_items(self) -> list[dict]:
        assert self.client
        ids = await self.client.smembers("active_incidents")

        if not ids:
            return []

        values = await self.client.mget(
            [f"incident:{incident_id}" for incident_id in ids]
        )

        items = [json.loads(value) for value in values if value]

        severity_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}

        return sorted(
            items,
            key=lambda item: (
                severity_order.get(item["severity"], 4),
                item["createdAt"],
            ),
        )