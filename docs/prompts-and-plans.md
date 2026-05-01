# Prompts, Specifications, and Build Plan

## Original Assignment Requirements Considered

Key Functional Goals:
- Async signal ingestion with backpressure
- Debounce repeated failures per component within a 10-second window
- RCA-enforced incident workflow (CLOSED state blocked without complete RCA)
- MTTR calculation from RCA start/end timestamps
- Live React dashboard with incident detail and RCA form
- Rate limiting on ingestion API
- Hot cache + source of truth separation

---

## Development Plan

### Phase 1 — Architecture Design

Designed system components and data flow:
- FastAPI ingestion layer with Pydantic validation
- Bounded `asyncio.Queue` as backpressure buffer
- Background worker coroutine consuming the queue
- PostgreSQL for persistence (work_items, raw_signals, aggregations)
- Redis for debounce TTL keys, rate limit counters, and hot dashboard cache
- React dashboard with polling

Key decisions made upfront:
- Single PostgreSQL instance covers all three storage tiers (NoSQL audit, relational source of truth, timeseries aggregations) to keep Docker Compose simple while meeting all functional requirements
- Redis `SETNX` chosen for atomic debounce to prevent race conditions

---

### Phase 2 — Backend Core

Implemented:
- `POST /signals` ingestion endpoint (single + batch)
- `asyncio.Queue` worker with exception resilience
- Debounce logic using Redis `SETNX` with 10-second TTL
- Alert strategy pattern (`RdbmsAlertStrategy` P0, `McpAlertStrategy` P1, `CacheAlertStrategy` P2)
- Work Item state machine (`OpenState`, `InvestigatingState`, `ResolvedState`, `ClosedState`)
- RCA completeness validation
- MTTR calculation

---

### Phase 3 — Persistence Layer

Implemented:
- `raw_signals` table (JSONB payload, FK to `work_items`)
- `work_items` table (status, priority, rca JSONB, mttr_minutes)
- `aggregations` table (minute bucket, component, severity, count)
- Redis dashboard cache invalidation on every write
- Retry logic with exponential backoff for persistence writes

---

### Phase 4 — Frontend Dashboard

Implemented:
- Active incident feed — polling `GET /incidents` every 5 seconds
- Incident detail view — raw signals from `GET /incidents/:id`
- Status transition buttons (OPEN → INVESTIGATING → RESOLVED)
- RCA form (startTime, endTime pickers, rootCauseCategory dropdown, fixApplied, preventionSteps text areas)
- MTTR display on closed incidents

---

### Phase 5 — Resilience and Testing

Implemented:
- Per-IP token bucket rate limiting via Redis
- `503` on queue saturation
- `GET /health` with `queueDepth`
- Console throughput metrics every 5 seconds
- Worker loop exception handling (bad signal cannot halt the worker)
- PostgreSQL row-level transactional locking (`SELECT ... FOR UPDATE`) for serialising concurrent status transitions
- Dockerised deployment via Docker Compose

---

## AI / Prompt Assistance Disclosure

AI tooling was used during development for:
- Architecture brainstorming and tradeoff discussion
- Documentation drafting and structure
- Design review and debugging assistance
- README refinement

All architectural decisions, debugging, and final implementation validation were manually reviewed and integrated. The design choices (single PostgreSQL vs. multi-DB, Redis debounce strategy, asyncio queue sizing) reflect deliberate engineering judgment, not generated defaults.

---

## Key Iterations During Development

### Iteration 1
Initial prototype with file-based persistence (JSON files). Established the ingestion → queue → worker pipeline shape.

### Iteration 2
Migrated to PostgreSQL + Redis. Defined the three-table schema. Moved debounce logic from in-process dict to Redis for correctness under async concurrency.

### Iteration 3
Added batch signal ingestion (`POST /signals` accepts both `{}` and `[{}, {}]`). Improved Pydantic models to handle both shapes transparently.

### Iteration 4
Improved worker resilience. Added exponential backoff retry around all DB writes. Added per-signal exception handling so one bad payload doesn't halt the worker loop.

### Iteration 5
Refined dashboard polling and RCA workflow UX. Added MTTR display. Added status transition buttons inline with incident detail.

### Iteration 6
Security hardening. Added optional `INGEST_API_KEY`, request body size limit, CORS configuration, and security response headers.

---

## Final Deliverables Checklist

- [x] Async backend ingestion pipeline
- [x] Debounce logic (Redis SETNX, 10-second TTL)
- [x] PostgreSQL persistence (work_items, raw_signals, aggregations)
- [x] Redis hot cache + rate limiting
- [x] Aggregation endpoint
- [x] RCA-enforced CLOSED transition
- [x] MTTR calculation
- [x] React dashboard (live feed, detail, RCA form, status transitions)
- [x] Docker Compose setup
- [x] Sample failure simulation script
- [x] Architecture documentation with Mermaid diagram
- [x] Design decisions documentation
- [x] LLD section (State Pattern, Strategy Pattern class designs)
- [x] Unit tests (RCA validation, state machine, concurrency, retry)
- [x] API documentation
- [x] Prompts and build plan (this file)
- [x] Requirements traceability matrix

---

## Notes

This repository reflects an iterative engineering process:

```
Requirements → Design → Implementation → Debugging → Hardening → Documentation
```

The final system balances assignment scope with realistic production-inspired design choices. Where simplifications were made (e.g. PostgreSQL instead of MongoDB for raw signals), they are explicitly documented with the production equivalent called out.