# Requirements Traceability

| Requirement | Implementation |
| --- | --- |
| High-throughput signal ingestion | `POST /signals` supports single and batch JSON payloads. |
| Bursts up to 10,000 signals/sec | Async bounded queue keeps persistence off the request path; `503` protects memory when saturated. |
| Debounce same component | `SignalProcessor` reuses one incident per component within 10 seconds and links all raw signals. |
| Raw data lake | PostgreSQL `raw_signals` table stores every signal as JSONB audit data. |
| Source of truth | PostgreSQL `work_items` table stores incidents and RCA records transactionally. |
| Transactional transitions | PostgreSQL transactions and row locks guard work item updates. |
| Hot dashboard cache | Redis stores active incident dashboard JSON. |
| Timeseries aggregations | PostgreSQL `aggregations` table stores minute-level counters. |
| Alerting Strategy pattern | `alert_strategies.py` maps component type to severity/channel/responder. |
| Work Item State pattern | `state_machine.py` validates lifecycle transitions. |
| Async processing | Queue worker drains signals asynchronously using `asyncio.Queue`. |
| Mandatory RCA | `CLOSED` transition rejects incomplete or missing RCA. |
| MTTR calculation | `calculateMttrMs` computes from RCA start/end timestamps. |
| Live feed UI | React dashboard polls `GET /incidents`. |
| Incident detail UI | React dashboard loads `GET /incidents/:id` and displays raw signals. |
| RCA form | React form includes date-time pickers, category dropdown, and text areas. |
| Concurrency | Mutex prevents race conditions during status and RCA updates. |
| Rate limiting | Redis-backed per-second limiter protects `POST /signals`. |
| Observability | `/health` endpoint and 5-second console throughput metrics. |
| Retry logic | `retry.js` wraps persistence writes. |
| Unit tests | `backend/tests/test_rca.py`. |
| Docker Compose | Root `docker-compose.yml`. |
| Sample data | `samples/failure-events.json` and `samples/simulate_failure.py`. |
| Prompts/spec/plans | `docs/ASSIGNMENT_PLAN.md`. |
| Non-functional bonus | Optional API key, body-size limit, security headers, CORS config. |
