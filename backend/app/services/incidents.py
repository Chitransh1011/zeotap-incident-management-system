from uuid import UUID

from app.domain.state_machine import assert_transition, calculate_mttr_ms, is_complete_rca
from app.infra.postgres import PostgresStore
from app.infra.redis_store import RedisStore


class IncidentService:
    def __init__(self, store: PostgresStore, redis: RedisStore):
        self.store = store
        self.redis = redis

    async def list_active(self) -> list[dict]:
        cached = await self.redis.list_dashboard_items()
        if cached:
            return cached
        active = await self.store.list_active_incidents()
        for item in active:
            await self.redis.upsert_dashboard_item(item)
        return active

    async def get_detail(self, incident_id: UUID) -> dict | None:
        item = await self.store.get_incident(incident_id)
        if not item:
            return None
        raw_signals = await self.store.list_raw_signals(incident_id)
        return {**item, "rawSignals": raw_signals}

    async def transition(self, incident_id: UUID, next_status: str) -> dict:
        def validator(item: dict, status: str) -> None:
            assert_transition(item["status"], status, item)

        updated = await self.store.transition_status(incident_id, next_status, validator)
        await self.redis.upsert_dashboard_item(updated)
        return updated

    async def submit_rca(self, incident_id: UUID, rca: dict) -> dict:
        if not is_complete_rca(rca):
            raise ValueError("RCA is incomplete")
        mttr_ms = calculate_mttr_ms(rca)
        updated = await self.store.submit_rca(incident_id, rca, mttr_ms or 0)
        await self.redis.upsert_dashboard_item(updated)
        return updated
