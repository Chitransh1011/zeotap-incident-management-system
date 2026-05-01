# Backend Guide

## Purpose

The backend is the IMS control plane. It ingests high-volume failure signals, performs asynchronous processing, debounces noisy component failures, persists raw and structured data separately, and enforces the incident lifecycle.

## Runtime

- Python FastAPI app in `backend/app/main.py`.
- `asyncio.Queue` for ingestion backpressure.
- PostgreSQL for source-of-truth, raw signal audit data, and aggregations.
- Redis for hot dashboard cache, rate limiting, and debounce state.

## Main Modules

- `app/main.py`: routes, CORS, health checks, API key guard, body-size guard.
- `app/services/processor.py`: async queue, backpressure, signal processing, debouncing.
- `app/services/incidents.py`: status transitions and RCA submission.
- `app/domain/alert_strategies.py`: Strategy pattern for alert severity/routing.
- `app/domain/state_machine.py`: State pattern style transition validation and RCA rules.
- `app/infra/postgres.py`: PostgreSQL schema and persistence.
- `app/infra/redis_store.py`: Redis cache, rate limiter, and debounce state.
- `app/infra/retry.py`: retry helper with exponential backoff for persistence writes.

## Environment Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `PORT` | `4000` | Backend HTTP port. |
| `POSTGRES_DSN` | `postgresql://ims:ims_password@localhost:5432/ims` | PostgreSQL connection string. |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL. |
| `CORS_ORIGIN` | request origin or `*` | Allowed UI origin. |
| `MAX_BODY_BYTES` | `1048576` | Request body limit. |
| `INGEST_API_KEY` | unset | Optional security layer for mutating APIs. |

## Backpressure Design

Signals are accepted into a bounded `asyncio.Queue`. The ingestion API returns quickly and a worker drains the queue asynchronously. If the queue is full, the API returns `503` instead of letting memory grow unbounded.

Additional controls:

- Redis-backed per-second rate limiting on `POST /signals`.
- Batch ingestion support.
- Retry logic for persistence.
- Debouncing by `componentId` for a 10 second window.

## Debouncing Rule

If many signals arrive for the same component inside the debounce window, Redis stores the active debounce key and the backend reuses the existing incident. Every raw signal is linked in PostgreSQL `raw_signals`. The incident `signalCount` and `lastSignalAt` are updated transactionally.

## Incident Lifecycle

Allowed transitions:

- `OPEN -> INVESTIGATING`
- `INVESTIGATING -> RESOLVED`
- `RESOLVED -> CLOSED`
- `RESOLVED -> INVESTIGATING`

Closing is rejected unless RCA is complete.

## RCA and MTTR

Required RCA fields:

- `startTime`
- `endTime`
- `rootCauseCategory`
- `fixApplied`
- `preventionSteps`

`mttrMs` is calculated as `endTime - startTime` when RCA is saved.
