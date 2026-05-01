import asyncio
import traceback
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.alert_strategies import get_alert_strategy
from app.infra.postgres import PostgresStore
from app.infra.redis_store import RedisStore


class SignalProcessor:
    def __init__(
        self,
        store: PostgresStore,
        redis: RedisStore,
        queue_max_size: int,
        debounce_window_seconds: int,
    ):
        self.store = store
        self.redis = redis
        self.queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=queue_max_size)
        self.debounce_window_seconds = debounce_window_seconds
        self.metrics = {"accepted": 0, "processed": 0, "rejected": 0}
        self.worker_task: asyncio.Task | None = None
        self.metrics_task: asyncio.Task | None = None

    def start(self) -> None:
        self.worker_task = asyncio.create_task(self.worker())
        self.metrics_task = asyncio.create_task(self.print_metrics())

    async def stop(self) -> None:
        for task in (self.worker_task, self.metrics_task):
            if task:
                task.cancel()

        await asyncio.gather(
            *(task for task in (self.worker_task, self.metrics_task) if task),
            return_exceptions=True,
        )

    def enqueue(self, signal: dict) -> bool:
        try:
            self.queue.put_nowait(
                {
                    **signal,
                    "receivedAt": datetime.now(timezone.utc),
                }
            )
            self.metrics["accepted"] += 1
            return True

        except asyncio.QueueFull:
            self.metrics["rejected"] += 1
            return False

    async def worker(self) -> None:
        while True:
            signal = await self.queue.get()

            try:
                await self.process_signal(signal)
                self.metrics["processed"] += 1

            except Exception as e:
                print(f"[worker-error] Failed processing signal: {e}", flush=True)
                traceback.print_exc()

            finally:
                self.queue.task_done()

    async def print_metrics(self) -> None:
        while True:
            await asyncio.sleep(5)

            accepted = self.metrics["accepted"]
            processed = self.metrics["processed"]

            self.metrics["accepted"] = 0
            self.metrics["processed"] = 0

            print(
                f"[metrics] accepted={accepted / 5}/sec "
                f"processed={processed / 5}/sec "
                f"queue={self.queue.qsize()}",
                flush=True,
            )

    async def process_signal(self, signal: dict) -> None:
        work_item = await self.find_or_create_work_item(signal)

        linked_signal = {
            **signal,
            "workItemId": UUID(work_item["id"]),
            "receivedAt": signal["receivedAt"],
        }

        await self.store.append_raw_signal(linked_signal)
        await self.store.update_aggregations(linked_signal)
        await self.redis.upsert_dashboard_item(work_item)

    async def find_or_create_work_item(self, signal: dict) -> dict:
        existing_id = await self.redis.get_debounce_work_item(signal["componentId"])

        if existing_id:
            updated = await self.store.increment_work_item_signal(
                existing_id,
                signal["receivedAt"],
            )
            if updated:
                return updated

        work_item_id = uuid4()

        acquired = await self.redis.try_set_debounce_work_item(
            signal["componentId"],
            work_item_id,
            self.debounce_window_seconds,
        )

        if not acquired:
            existing_id = await self.redis.get_debounce_work_item(
                signal["componentId"]
            )

            if existing_id:
                updated = await self.store.increment_work_item_signal(
                    existing_id,
                    signal["receivedAt"],
                )
                if updated:
                    return updated

        alert = get_alert_strategy(signal["componentType"]).evaluate(signal)
        now = signal["receivedAt"]

        item = {
            "id": work_item_id,
            "componentId": signal["componentId"],
            "componentType": signal["componentType"],
            "title": f"{signal['componentId']} failure detected",
            "status": "OPEN",
            "severity": alert.severity,
            "alertChannel": alert.channel,
            "responder": alert.responder,
            "signalCount": 1,
            "firstSignalAt": now,
            "lastSignalAt": now,
            "rca": None,
            "mttrMs": None,
            "createdAt": now,
            "updatedAt": now,
        }

        saved = await self.store.create_work_item(item)

        return {**saved, "id": str(saved["id"])}