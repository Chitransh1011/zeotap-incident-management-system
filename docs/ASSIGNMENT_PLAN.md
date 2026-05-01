# Assignment Build Plan

## Checklist Coverage

- High-throughput ingestion: `POST /signals` supports single and batch JSON payloads.
- Memory management: bounded async queue with saturated `503` response.
- Debouncing: component-based 10 second window links many raw signals to one work item.
- Data lake: raw signals stored in PostgreSQL JSONB audit table.
- Source of truth: structured work items and RCA records stored in PostgreSQL with transactional row locks.
- Hot path cache: active incident dashboard state maintained in Redis.
- Aggregations: per-minute component/severity counters stored in PostgreSQL.
- Workflow engine: Strategy pattern for alerting severity and State pattern for transitions.
- Mandatory RCA: close transition is blocked unless RCA is complete.
- MTTR: calculated on RCA submission.
- UI: React live feed, incident detail, raw signals, status transition, RCA form.
- Resilience: Redis-backed rate limiter, retrying writes, `/health`, throughput logs.
- Tests: RCA validation and close rejection covered by unit tests.

## Prompts Used

The repository was created from the assignment PDF/text supplied by the candidate in this workspace. The implementation goal was to cover every explicit requirement in a concise, runnable codebase suitable for an internship submission.
