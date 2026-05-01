# Backend Guide

## Purpose

The backend is the IMS control plane. It ingests high-volume failure signals, performs asynchronous processing, debounces noisy component failures, persists raw and structured data separately, and enforces the incident lifecycle.

## Runtime

- Node.js HTTP server in `backend/src/server.js`.
- No framework dependency, which keeps the intern assignment easy to run and inspect.
- File-backed stores under `backend/data` for local/Docker execution.

## Main Modules

- `src/server.js`: routes, CORS, health checks, API key guard, body-size guard.
- `src/services/processor.js`: async queue, backpressure, signal processing, debouncing.
- `src/services/incidents.js`: status transitions and RCA submission.
- `src/services/dashboardCache.js`: hot-path dashboard state.
- `src/domain/alertStrategies.js`: Strategy pattern for alert severity/routing.
- `src/domain/stateMachine.js`: State pattern style transition validation and RCA rules.
- `src/infra/store.js`: separated raw signal, work item, and aggregation persistence.
- `src/infra/rateLimiter.js`: token-bucket rate limiter.
- `src/infra/retry.js`: retry helper with exponential backoff for persistence writes.
- `src/infra/mutex.js`: concurrency primitive for transactional work-item updates.

## Environment Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `PORT` | `4000` | Backend HTTP port. |
| `DATA_DIR` | `backend/data` | Persistence directory. |
| `CORS_ORIGIN` | request origin or `*` | Allowed UI origin. |
| `MAX_BODY_BYTES` | `1048576` | Request body limit. |
| `INGEST_API_KEY` | unset | Optional security layer for mutating APIs. |

## Backpressure Design

Signals are accepted into a bounded in-memory queue. The ingestion API returns quickly and a worker drains the queue asynchronously. If the queue is full, the API returns `503` instead of letting memory grow unbounded.

Additional controls:

- Token-bucket rate limiting on `POST /signals`.
- Batch ingestion support.
- Retry logic for persistence.
- Debouncing by `componentId` for a 10 second window.

## Debouncing Rule

If many signals arrive for the same component inside the debounce window, the backend reuses the existing incident and links every raw signal to it in `raw-signals.jsonl`. The incident `signalCount` and `lastSignalAt` are updated transactionally.

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
