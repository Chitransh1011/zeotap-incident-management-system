# Design Decisions

## Why FastAPI for Backend?

Chosen because:
- Native async/await support via `asyncio`
- High throughput for I/O-bound APIs
- Strong request validation via Pydantic models
- Clean OpenAPI documentation auto-generated at `/docs`

Alternative Considered: Node.js/Express

Why Not Chosen: FastAPI provides stronger structured typing and async ergonomics for this assignment. Pydantic validation catches malformed signal payloads at the boundary, before they reach the queue.

---

## Why React for Frontend?

Chosen because:
- Rapid UI development with component-based architecture
- Easy polling-based live dashboard updates (`setInterval` + `fetch`)
- Familiar ecosystem for responsive incident dashboards

---

## Why PostgreSQL for All Persistence?

Used for:
- Structured Work Items and RCA records (transactional source of truth)
- Raw signal audit log (JSONB column)
- Timeseries aggregation counters

### Why a Single Database?

The assignment specifies separate storage tiers conceptually. In production this maps to:

| Tier | Production Equivalent | This Implementation |
|---|---|---|
| Raw signal audit log | MongoDB / Cassandra / S3 | PostgreSQL `raw_signals` with JSONB |
| Source of truth (Work Items, RCA) | PostgreSQL / CockroachDB | PostgreSQL `work_items` |
| Timeseries aggregations | InfluxDB / TimescaleDB | PostgreSQL `aggregations` |

PostgreSQL was chosen to unify these tiers because:
- **ACID transactions** are required for incident lifecycle transitions — NoSQL stores lack multi-document transactions.
- **JSONB support** handles variable-schema raw signal payloads without a separate document store.
- **`date_trunc` + `GROUP BY`** provides sufficient timeseries aggregation at assignment scale.
- Avoids running three separate database containers in Docker Compose for a single-developer assignment submission.

The README explicitly calls out the production equivalents (Kafka/NATS for ingestion, ClickHouse/S3 for analytics) to demonstrate awareness of where this simplification was made.

Alternative Considered: MongoDB for raw signals

Why Not Chosen: Transactional consistency is required for the workflow engine. Splitting across PostgreSQL + MongoDB adds operational complexity with no functional benefit at this scale.

---

## Why Redis?

Used for three distinct purposes:

### 1. Dashboard Hot-Path Cache
Incident list responses are served from Redis, not from a PostgreSQL `SELECT`. This decouples UI refresh rate from database query latency and supports the "Real-time Dashboard State" requirement.

### 2. Debounce TTL Keys
When a signal arrives for a `componentId`, a Redis key with a 10-second TTL is set. Subsequent signals for the same component within the window are linked to the existing Work Item instead of creating a new one. Redis `SETNX` (set-if-not-exists) makes this atomic.

### 3. Rate Limiting Counters
Per-IP token bucket counters are stored in Redis with TTL-based reset, enabling distributed rate limiting without in-process state.

Reasons:
- Sub-millisecond read/write latency
- Native TTL support — no manual expiry logic
- Atomic operations (`SETNX`, `INCR`) prevent race conditions

---

## Why Async Queue Instead of Direct Persistence?

**Problem:** Direct DB writes during ingestion block request handling under burst traffic. At 10,000 signals/sec, a 5ms PostgreSQL write latency would mean 50,000ms of accumulated blocking — the API would become unresponsive.

**Solution:** Signals are placed in a bounded `asyncio.Queue` immediately upon receipt and processed by a background worker coroutine. The HTTP response (`202 Accepted`) is returned before any persistence occurs.

```
POST /signals
    │
    ├── Enqueue signal (< 0.1ms)
    │
    └── Return 202 Accepted
         │
         Worker (separate coroutine)
              │
              ├── Debounce check (Redis)
              ├── Write raw_signals (PostgreSQL)
              ├── Upsert work_item (PostgreSQL)
              └── Update dashboard cache (Redis)
```

Benefits:
- Decouples ingestion latency from persistence latency
- Absorbs bursts up to queue capacity without dropping signals
- Prevents API thread starvation under database slowness
- Retry logic can live entirely in the worker without affecting HTTP response time

---

## Why Bounded Queue?

An unbounded queue risks:
- Memory exhaustion under sustained overload
- Gradual process crash with no signal to the caller

A bounded queue (`maxsize=10_000` configurable) allows:
- Predictable memory usage
- Controlled degradation — once full, `POST /signals` returns `503 Queue Saturated`
- Operators can monitor `queueDepth` via `GET /health` and scale accordingly

---

## Why Debounce by Component ID?

**Without debounce:**
```
100 RDBMS_PRIMARY_01 errors in 10 seconds → 100 Work Items created
→ 100 separate Slack/PagerDuty alerts
→ On-call engineer overwhelmed
```

**With debounce:**
```
100 RDBMS_PRIMARY_01 errors in 10 seconds → 1 Work Item created
→ All 100 raw signals linked to that Work Item in raw_signals table
→ 1 alert, full signal history preserved for RCA
```

Implementation:
1. On signal arrival, check Redis for key `debounce:{componentId}`.
2. If key **absent**: create Work Item, set Redis key with 10-second TTL, fire alert.
3. If key **present**: look up existing Work Item ID from Redis, insert raw signal linked to it — no new Work Item, no new alert.

This satisfies both the "one Work Item" requirement and the "all signals linked" audit requirement.

---

## Why State Pattern for Work Item Lifecycle?

The incident lifecycle is a strict finite state machine:

```
OPEN → INVESTIGATING → RESOLVED → CLOSED
```

Rules:
- Transitions must be validated (cannot jump from OPEN directly to CLOSED).
- `CLOSED` transition requires a complete RCA object — the state itself enforces this.
- Each state may have different allowed actions (e.g. only `RESOLVED` state accepts an RCA submission that then auto-transitions to `CLOSED`).

The State Pattern encapsulates transition logic inside state objects rather than a long `if/elif` chain. Adding a new state (e.g. `ESCALATED`) requires only a new state class, not changes to a monolithic switch statement.

---

## Why Strategy Pattern for Alert Severity?

Different component types warrant different alert priorities and notification channels:

| Component Type | Priority | Rationale |
|---|---|---|
| RDBMS | P0 | Database failure cascades to all dependent services |
| MCP_HOST | P1 | Affects orchestration but partial fallback possible |
| CACHE | P2 | Latency impact, usually self-healing |
| API | P1 | User-facing degradation |
| QUEUE | P1 | Message processing delays |

The Strategy Pattern allows swapping the alerting logic per component type at runtime. Each strategy implements a common `AlertStrategy` interface with a single `alert(work_item)` method. The processor selects the correct strategy based on `componentType` from the incoming signal.

Benefits:
- Open/Closed Principle: new component types get new strategy classes, not modified existing ones.
- Testable in isolation: each strategy can be unit-tested without instantiating the full processor.

---

## Concurrency and Race Condition Prevention

Two sources of concurrency risk exist:

### 1. Debounce Race Condition
If two signals for the same `componentId` arrive simultaneously, both could pass the "no existing Work Item" check before either creates one, resulting in duplicate Work Items.

**Mitigation:** Redis `SETNX` (atomic set-if-not-exists) is used for the debounce key. Only the first writer succeeds; the second finds the key already set and links to the existing Work Item.

### 2. Status Transition Race Condition
If two clients attempt to transition the same Work Item simultaneously, one transition could overwrite the other.

**Mitigation:** PostgreSQL transactional row-level locking (`SELECT ... FOR UPDATE`) is used during status transitions to serialize concurrent updates on the same incident.

---

## Security Additions (Bonus)

| Feature | Implementation |
|---|---|
| API key authentication | `INGEST_API_KEY` env var; `X-IMS-API-Key` header required on mutating endpoints |
| Request body size limit | `MAX_BODY_BYTES` env var; requests exceeding limit return `413` |
| CORS origin control | `CORS_ORIGIN` env var; defaults to `http://localhost:5173` |
| Security headers | `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store` |