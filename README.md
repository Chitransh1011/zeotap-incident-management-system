# Mission-Critical Incident Management System

This repository implements the Zeotap engineering challenge as a small but complete Incident Management System (IMS).

> Submission note: push this repository to GitHub, then add the final repository URL to the generated submission PDF before sending it.

## Architecture

```mermaid
flowchart LR
    Producer["Failure simulator / clients"] -->|"POST /signals JSON"| API["Ingestion API\nrate limited"]
    API --> Queue["Bounded in-memory queue\nbackpressure"]
    Queue --> Worker["Async processor\nretrying writes"]
    Worker --> Raw["Raw signal lake\nNoSQL-style JSONL"]
    Worker --> Truth["Source of truth\ntransactional work items + RCA"]
    Worker --> Hot["Hot dashboard cache"]
    Worker --> Agg["Timeseries aggregations"]
    UI["React dashboard"] -->|"REST polling"| API
    API --> UI
```

## Tech Stack

- **Backend:** Node.js HTTP server, async worker queue, mutex-based transactional updates, `node:test`.
- **Frontend:** React dashboard served by Vite.
- **Storage model:** File-backed development adapters that mirror the required production separation:
  - `raw-signals.jsonl`: high-volume NoSQL/data-lake audit log.
  - `work-items.json`: source of truth for incidents and RCA records.
  - `aggregations.json`: timeseries aggregation buckets.
  - in-memory cache for live dashboard state.
- **Containerization:** Docker Compose for backend and frontend.

Production equivalents would be Kafka/NATS for ingestion buffering, MongoDB/S3/ClickHouse for raw signal lake, Postgres for source of truth, Redis for hot dashboard state, and TimescaleDB/ClickHouse for aggregations.

## Repository Structure

```text
backend/                  IMS backend engine and tests
frontend/                 React incident dashboard
samples/                  Mock failure events and simulator
docs/API.md               API examples and payloads
docs/BACKEND.md           Backend architecture and internals
docs/FRONTEND.md          Frontend usage and workflow
docs/MCP_HOST_MONITORING.md
docs/TESTING.md           Test and verification guide
docs/REQUIREMENTS_TRACEABILITY.md
docs/ASSIGNMENT_PLAN.md   Prompt/spec/plan record
```

## Backpressure Handling

The ingestion API never writes directly to durable storage. Incoming signals are accepted into a bounded in-memory queue and processed asynchronously by a worker. This prevents slow persistence from crashing the API path.

Backpressure controls:

- Per-IP token-bucket rate limiter on `POST /signals`.
- Bounded queue with a `503` response when the processor is saturated.
- Batch ingestion support so high-throughput clients can send arrays.
- Retry logic with exponential backoff around persistence writes.
- Debouncing window: 100 signals for the same component within 10 seconds create one work item, while all raw signals remain linked to that incident.

## Non-Functional Work and Bonus Points

- Optional API-key security for mutating APIs using `INGEST_API_KEY` and `X-IMS-API-Key`.
- Request body size limit through `MAX_BODY_BYTES`.
- CORS origin configuration through `CORS_ORIGIN`.
- Security headers: `X-Content-Type-Options`, `Referrer-Policy`, and `Cache-Control`.
- Retry logic for persistence writes.
- Mutex-protected source-of-truth updates to avoid race conditions.
- Console throughput metrics every 5 seconds.

## Setup

```bash
docker compose up --build
```

Services:

- Backend: [http://localhost:4000](http://localhost:4000)
- Frontend: [http://localhost:5173](http://localhost:5173)

Local backend without Docker:

```bash
cd backend
npm install
npm start
```

Local frontend without Docker:

```bash
cd frontend
npm install
npm run dev
```

## Useful Commands

Run backend tests:

```bash
cd backend
npm test
```

Simulate an RDBMS outage followed by MCP host failures:

```bash
node samples/simulate-failure.js
```

## Documentation

- [Backend Guide](docs/BACKEND.md)
- [API Guide](docs/API.md)
- [Frontend Guide](docs/FRONTEND.md)
- [MCP Host Monitoring Guide](docs/MCP_HOST_MONITORING.md)
- [Testing Guide](docs/TESTING.md)
- [Requirements Traceability](docs/REQUIREMENTS_TRACEABILITY.md)
- [GitHub Submission Guide](docs/GITHUB_SUBMISSION.md)

## API Summary

- `GET /health` - service health and queue depth.
- `POST /signals` - ingest one signal or an array of signals.
- `GET /incidents` - live dashboard state sorted by severity.
- `GET /incidents/:id` - incident detail with linked raw signals.
- `PATCH /incidents/:id/status` - transition state.
- `POST /incidents/:id/rca` - submit RCA and calculate MTTR.
- `GET /aggregations` - timeseries buckets.

## RCA Rule

Closing an incident is rejected unless the RCA contains:

- `startTime`
- `endTime`
- `rootCauseCategory`
- `fixApplied`
- `preventionSteps`

MTTR is calculated from RCA `startTime` to `endTime` when the RCA is submitted.

## Creative Additions

- Strategy pattern for component-specific alert severity.
- State pattern for lifecycle transitions.
- Console throughput metrics every 5 seconds.
- File-backed sinks make the project runnable without external cloud services while keeping the production data boundaries explicit.
- Optional API key, body-size guard, configurable CORS, and security headers.
