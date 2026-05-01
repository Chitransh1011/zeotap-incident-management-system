from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config import settings
from app.infra.postgres import PostgresStore
from app.infra.redis_store import RedisStore
from app.services.incidents import IncidentService
from app.services.processor import SignalProcessor


class Signal(BaseModel):
    componentId: str
    componentType: str
    message: str
    severity: str = "ERROR"
    payload: dict[str, Any] = Field(default_factory=dict)


class StatusUpdate(BaseModel):
    status: str


class RcaPayload(BaseModel):
    startTime: str
    endTime: str
    rootCauseCategory: str
    fixApplied: str
    preventionSteps: str


store = PostgresStore(settings.postgres_dsn)
redis_store = RedisStore(settings.redis_url)
processor = SignalProcessor(
    store,
    redis_store,
    queue_max_size=settings.queue_max_size,
    debounce_window_seconds=settings.debounce_window_seconds,
)
incident_service = IncidentService(store, redis_store)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await store.connect()
    await redis_store.connect()
    processor.start()
    try:
        yield
    finally:
        await processor.stop()
        await redis_store.close()
        await store.close()


app = FastAPI(title="Incident Management System", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin, "http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "X-IMS-API-Key"],
)


@app.middleware("http")
async def security_and_body_guard(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.max_body_bytes:
        return Response('{"error":"Request body too large"}', status_code=413, media_type="application/json")
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


def require_api_key(request: Request, x_ims_api_key: str | None = Header(default=None)) -> None:
    if (
        settings.ingest_api_key
        and request.method in {"POST", "PATCH"}
        and (request.url.path == "/signals" or request.url.path.startswith("/incidents/"))
        and x_ims_api_key != settings.ingest_api_key
    ):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.get("/health")
async def health():
    return {"ok": True, "queueDepth": processor.queue.qsize()}


@app.post("/signals", status_code=202, dependencies=[Depends(require_api_key)])
async def ingest_signals(request: Request, body: Signal | list[Signal]):
    signals = body if isinstance(body, list) else [body]
    client_ip = request.client.host if request.client else "unknown"
    allowed = await redis_store.allow_rate(client_ip, settings.rate_limit_per_second, len(signals))
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    accepted = 0
    for signal in signals:
        if not processor.enqueue(signal.model_dump()):
            raise HTTPException(
                status_code=503,
                detail={"error": "Ingestion queue saturated", "accepted": accepted},
            )
        accepted += 1
    return {"accepted": accepted}


@app.get("/incidents")
async def list_incidents():
    return await incident_service.list_active()


@app.get("/incidents/{incident_id}")
async def incident_detail(incident_id: UUID):
    incident = await incident_service.get_detail(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@app.patch("/incidents/{incident_id}/status", dependencies=[Depends(require_api_key)])
async def transition_incident(incident_id: UUID, body: StatusUpdate):
    try:
        return await incident_service.transition(incident_id, body.status)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/incidents/{incident_id}/rca", dependencies=[Depends(require_api_key)])
async def submit_rca(incident_id: UUID, body: RcaPayload):
    try:
        return await incident_service.submit_rca(incident_id, body.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/aggregations")
async def aggregations():
    return await store.read_aggregations()
