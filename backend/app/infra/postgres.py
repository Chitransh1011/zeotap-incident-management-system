import json
from datetime import datetime, timezone
from uuid import UUID

import asyncpg

from app.infra.retry import retry


class PostgresStore:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        self.pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=10)
        await self.init_schema()

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()

    async def init_schema(self) -> None:
        assert self.pool
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                create table if not exists work_items (
                    id uuid primary key,
                    component_id text not null,
                    component_type text not null,
                    title text not null,
                    status text not null,
                    severity text not null,
                    alert_channel text not null,
                    responder text not null,
                    signal_count integer not null default 1,
                    first_signal_at timestamptz not null,
                    last_signal_at timestamptz not null,
                    rca jsonb,
                    mttr_ms bigint,
                    created_at timestamptz not null,
                    updated_at timestamptz not null
                );

                create table if not exists raw_signals (
                    id bigserial primary key,
                    work_item_id uuid not null references work_items(id),
                    component_id text not null,
                    component_type text not null,
                    severity text not null,
                    received_at timestamptz not null,
                    payload jsonb not null
                );

                create index if not exists idx_raw_signals_work_item_id
                    on raw_signals(work_item_id);

                create table if not exists aggregations (
                    bucket_minute timestamptz not null,
                    component_id text not null,
                    severity text not null,
                    count integer not null default 0,
                    primary key(bucket_minute, component_id, severity)
                );
                """
            )

    async def create_work_item(self, item: dict) -> dict:
        assert self.pool

        async def op() -> None:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    insert into work_items (
                        id, component_id, component_type, title, status, severity,
                        alert_channel, responder, signal_count, first_signal_at,
                        last_signal_at, rca, mttr_ms, created_at, updated_at
                    )
                    values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
                    """,
                    item["id"],
                    item["componentId"],
                    item["componentType"],
                    item["title"],
                    item["status"],
                    item["severity"],
                    item["alertChannel"],
                    item["responder"],
                    item["signalCount"],
                    item["firstSignalAt"],
                    item["lastSignalAt"],
                    json.dumps(item["rca"]) if item["rca"] else None,
                    item["mttrMs"],
                    item["createdAt"],
                    item["updatedAt"],
                )

        await retry(op)
        return item

    async def increment_work_item_signal(self, work_item_id: UUID, received_at: datetime) -> dict | None:
        assert self.pool

        async def op() -> asyncpg.Record | None:
            async with self.pool.acquire() as conn:
                return await conn.fetchrow(
                    """
                    update work_items
                    set signal_count = signal_count + 1,
                        last_signal_at = $2,
                        updated_at = $2
                    where id = $1
                    returning *
                    """,
                    work_item_id,
                    received_at,
                )

        row = await retry(op)
        return self.row_to_work_item(row) if row else None

    async def append_raw_signal(self, signal: dict) -> None:
        assert self.pool

        async def op() -> None:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    insert into raw_signals (
                        work_item_id, component_id, component_type, severity, received_at, payload
                    )
                    values ($1,$2,$3,$4,$5,$6)
                    """,
                    signal["workItemId"],
                    signal["componentId"],
                    signal["componentType"],
                    signal["severity"],
                    signal["receivedAt"],
                    json.dumps(signal, default=str),
                )

        await retry(op)

    async def update_aggregations(self, signal: dict) -> None:
        assert self.pool
        bucket = signal["receivedAt"].replace(second=0, microsecond=0)

        async def op() -> None:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    insert into aggregations(bucket_minute, component_id, severity, count)
                    values ($1, $2, $3, 1)
                    on conflict(bucket_minute, component_id, severity)
                    do update set count = aggregations.count + 1
                    """,
                    bucket,
                    signal["componentId"],
                    signal["severity"],
                )

        await retry(op)

    async def list_active_incidents(self) -> list[dict]:
        assert self.pool
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                select * from work_items
                where status <> 'CLOSED'
                order by
                    case severity when 'P0' then 0 when 'P1' then 1 when 'P2' then 2 else 3 end,
                    created_at asc
                """
            )
        return [self.row_to_work_item(row) for row in rows]

    async def get_incident(self, work_item_id: UUID) -> dict | None:
        assert self.pool
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("select * from work_items where id = $1", work_item_id)
        return self.row_to_work_item(row) if row else None

    async def list_raw_signals(self, work_item_id: UUID) -> list[dict]:
        assert self.pool
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                select payload
                from raw_signals
                where work_item_id = $1
                order by received_at asc, id asc
                """,
                work_item_id,
            )
        return [json.loads(row["payload"]) if isinstance(row["payload"], str) else row["payload"] for row in rows]

    async def transition_status(self, work_item_id: UUID, next_status: str, validator) -> dict:
        assert self.pool
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow("select * from work_items where id = $1 for update", work_item_id)
                if not row:
                    raise ValueError("Incident not found")
                item = self.row_to_work_item(row)
                validator(item, next_status)
                updated = await conn.fetchrow(
                    """
                    update work_items
                    set status = $2, updated_at = $3
                    where id = $1
                    returning *
                    """,
                    work_item_id,
                    next_status,
                    utcnow(),
                )
        return self.row_to_work_item(updated)

    async def submit_rca(self, work_item_id: UUID, rca: dict, mttr_ms: int) -> dict:
        assert self.pool
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                updated = await conn.fetchrow(
                    """
                    update work_items
                    set rca = $2, mttr_ms = $3, updated_at = $4
                    where id = $1
                    returning *
                    """,
                    work_item_id,
                    json.dumps(rca),
                    mttr_ms,
                    utcnow(),
                )
                if not updated:
                    raise ValueError("Incident not found")
        return self.row_to_work_item(updated)

    async def read_aggregations(self) -> list[dict]:
        assert self.pool
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                select bucket_minute, component_id, severity, count
                from aggregations
                order by bucket_minute desc
                limit 500
                """
            )
        return [
            {
                "bucketMinute": row["bucket_minute"].isoformat(),
                "componentId": row["component_id"],
                "severity": row["severity"],
                "count": row["count"],
            }
            for row in rows
        ]

    @staticmethod
    def row_to_work_item(row: asyncpg.Record | None) -> dict:
        if row is None:
            raise ValueError("Missing work item row")
        rca = row["rca"]
        if isinstance(rca, str):
            rca = json.loads(rca)
        return {
            "id": str(row["id"]),
            "componentId": row["component_id"],
            "componentType": row["component_type"],
            "title": row["title"],
            "status": row["status"],
            "severity": row["severity"],
            "alertChannel": row["alert_channel"],
            "responder": row["responder"],
            "signalCount": row["signal_count"],
            "firstSignalAt": row["first_signal_at"].isoformat(),
            "lastSignalAt": row["last_signal_at"].isoformat(),
            "rca": rca,
            "mttrMs": row["mttr_ms"],
            "createdAt": row["created_at"].isoformat(),
            "updatedAt": row["updated_at"].isoformat(),
        }


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
