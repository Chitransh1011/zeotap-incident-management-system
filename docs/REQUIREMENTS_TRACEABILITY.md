# Requirements Traceability

| Requirement | Implementation |
| --- | --- |
| High-throughput signal ingestion | `POST /signals` supports single and batch JSON payloads. |
| Bursts up to 10,000 signals/sec | Async bounded queue keeps persistence off the request path; `503` protects memory when saturated. |
| Debounce same component | `SignalProcessor` reuses one incident per component within 10 seconds and links all raw signals. |
| Raw data lake | `backend/data/raw-signals.jsonl` stores every signal as append-only audit data. |
| Source of truth | `backend/data/work-items.json` stores work items and RCA records. |
| Transactional transitions | `Mutex.runExclusive` guards work item updates. |
| Hot dashboard cache | `DashboardCache` serves active incidents without reading source of truth on every refresh. |
| Timeseries aggregations | `backend/data/aggregations.json` stores minute-level counters. |
| Alerting Strategy pattern | `alertStrategies.js` maps component type to severity/channel/responder. |
| Work Item State pattern | `stateMachine.js` validates lifecycle transitions. |
| Async processing | Queue worker drains signals asynchronously using `setImmediate`. |
| Mandatory RCA | `CLOSED` transition rejects incomplete or missing RCA. |
| MTTR calculation | `calculateMttrMs` computes from RCA start/end timestamps. |
| Live feed UI | React dashboard polls `GET /incidents`. |
| Incident detail UI | React dashboard loads `GET /incidents/:id` and displays raw signals. |
| RCA form | React form includes date-time pickers, category dropdown, and text areas. |
| Concurrency | Mutex prevents race conditions during status and RCA updates. |
| Rate limiting | Token bucket protects `POST /signals`. |
| Observability | `/health` endpoint and 5-second console throughput metrics. |
| Retry logic | `retry.js` wraps persistence writes. |
| Unit tests | `backend/test/rca.test.js`. |
| Docker Compose | Root `docker-compose.yml`. |
| Sample data | `samples/failure-events.json` and `samples/simulate-failure.js`. |
| Prompts/spec/plans | `docs/ASSIGNMENT_PLAN.md`. |
| Non-functional bonus | Optional API key, body-size limit, security headers, CORS config. |
