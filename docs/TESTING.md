# Testing and Verification Guide

## Backend Unit Tests

```bash
cd backend
python -m pytest tests -v
```

### RCA Validation Tests

Covered in `tests/test_rca.py`:

- RCA validation rejects an object missing `startTime`.
- RCA validation rejects an object missing `rootCauseCategory`.
- RCA validation rejects an object missing `fixApplied`.
- RCA validation rejects an object missing `preventionSteps`.
- RCA validation accepts a fully complete object.
- `CLOSED` transition is blocked when RCA is `null`.
- `CLOSED` transition is blocked when RCA is incomplete (partial fields).
- `CLOSED` transition succeeds when RCA is complete.
- MTTR is calculated correctly from `startTime` to `endTime`.
- MTTR returns 0 for identical `startTime` and `endTime`.

### State Machine Tests

Covered in `tests/test_state_machine.py`:

- `OPEN` → `INVESTIGATING` is a valid transition.
- `OPEN` → `RESOLVED` raises `InvalidTransitionError`.
- `OPEN` → `CLOSED` raises `InvalidTransitionError`.
- `INVESTIGATING` → `RESOLVED` is a valid transition.
- `INVESTIGATING` → `OPEN` raises `InvalidTransitionError` (no backward transitions).
- `RESOLVED` → `CLOSED` succeeds when RCA is complete.
- `RESOLVED` → `CLOSED` raises `RcaRequiredError` when RCA is missing.
- `CLOSED` → any status raises `InvalidTransitionError` (terminal state).

### Concurrency and Race Condition Tests

Covered in `tests/test_concurrency.py`:

- Concurrent signals for the same `componentId` within the debounce window produce exactly one Work Item (not two).
- Concurrent status transitions on the same Work Item serialise correctly — the second transition sees the state written by the first.
- Simultaneous `POST /incidents/:id/rca` calls do not corrupt the RCA object (last-write-wins with mutex protection).

Example test (debounce race):

```python
import asyncio
import pytest

async def test_debounce_concurrent_signals(processor, redis_client):
    """Two signals for the same component arriving concurrently
    must result in exactly one Work Item."""
    signal = {"componentId": "CACHE_01", "componentType": "CACHE", "message": "down"}
    await asyncio.gather(
        processor.handle(signal),
        processor.handle(signal),
    )
    work_items = await db.fetch("SELECT id FROM work_items WHERE component_id = 'CACHE_01'")
    assert len(work_items) == 1
```

### Retry Logic Tests

Covered in `tests/test_resilience.py`:

- Worker retries a failed PostgreSQL write up to 3 times with exponential backoff before dropping and logging the error.
- Worker continues processing subsequent signals after a single signal causes a write failure.
- A simulated Redis unavailability falls back gracefully (debounce disabled, raw writes continue).

---

## Frontend Build Test

```bash
cd frontend
npm install
npm run build
```

A clean build with no TypeScript or lint errors is required before submission.

---

## End-to-End Manual Test

Start the full stack:

```bash
docker compose up --build
```

Check health:

```bash
curl http://localhost:4000/health
```

Expected response:

```json
{ "ok": true, "queueDepth": 0, "time": "..." }
```

Generate sample incidents:

```bash
python samples/simulate_failure.py
```

Open the dashboard:

```
http://localhost:5173
```

### Manual Assertions Checklist

#### Severity and Priority
- [ ] RDBMS incident appears with priority `P0`.
- [ ] MCP host incident appears with priority `P1`.
- [ ] Cache incident appears with priority `P2`.
- [ ] Incidents are sorted P0 → P1 → P2 in the live feed.

#### Incident Workflow
- [ ] Clicking an incident opens the detail view.
- [ ] Raw signals linked to the incident are visible in detail view.
- [ ] Status can be transitioned: `OPEN` → `INVESTIGATING` → `RESOLVED`.
- [ ] `CLOSED` transition is rejected (HTTP 422) when RCA has not been submitted.
- [ ] After submitting a complete RCA, status transitions to `CLOSED`.
- [ ] MTTR appears in minutes on the closed incident detail.

#### Backpressure
- [ ] `GET /health` shows `queueDepth` increasing during burst ingestion.
- [ ] Sustained burst eventually returns `503 Queue Saturated`.
- [ ] Console prints throughput metrics (Signals/sec) every 5 seconds.

#### Debounce
- [ ] Running `simulate_failure.py` produces one Work Item per component, not one per signal.
- [ ] Incident detail shows multiple raw signals linked to the single Work Item.

---

## API Smoke Test (PowerShell)

```powershell
$body = Get-Content samples/failure-events.json -Raw
Invoke-RestMethod -Uri http://localhost:4000/signals -Method Post -ContentType application/json -Body $body
Invoke-RestMethod -Uri http://localhost:4000/incidents
```

---

## API Smoke Test (curl)

```bash
# Ingest a single signal
curl -X POST http://localhost:4000/signals \
  -H "Content-Type: application/json" \
  -d '{"componentId":"RDBMS_PRIMARY_01","componentType":"RDBMS","message":"Connection pool exhausted","severity":"ERROR"}'

# List incidents
curl http://localhost:4000/incidents

# Transition status
INCIDENT_ID=$(curl -s http://localhost:4000/incidents | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")
curl -X PATCH http://localhost:4000/incidents/$INCIDENT_ID/status \
  -H "Content-Type: application/json" \
  -d '{"status":"INVESTIGATING"}'

# Submit RCA
curl -X POST http://localhost:4000/incidents/$INCIDENT_ID/rca \
  -H "Content-Type: application/json" \
  -d '{
    "startTime": "2026-05-01T10:00:00.000Z",
    "endTime": "2026-05-01T10:30:00.000Z",
    "rootCauseCategory": "DATABASE",
    "fixApplied": "Promoted standby database",
    "preventionSteps": "Add failover drill and connection pool alerts"
  }'

# Verify CLOSED and MTTR
curl http://localhost:4000/incidents/$INCIDENT_ID
```

---

## Optional Security Test

Start backend with API key enabled:

```bash
INGEST_API_KEY=change-me uvicorn app.main:app --host 0.0.0.0 --port 4000
```

Verify unauthenticated ingestion is rejected:

```bash
curl -X POST http://localhost:4000/signals \
  -H "Content-Type: application/json" \
  -d '{"componentId":"RDBMS_PRIMARY_01","componentType":"RDBMS","message":"test"}'
# Expected: 401 Unauthorized
```

Retry with the correct API key header:

```bash
curl -X POST http://localhost:4000/signals \
  -H "Content-Type: application/json" \
  -H "X-IMS-API-Key: change-me" \
  -d '{"componentId":"RDBMS_PRIMARY_01","componentType":"RDBMS","message":"test"}'
# Expected: 202 Accepted
```

---

## Throughput Smoke Test

The worker prints a throughput metric to console every 5 seconds. To verify:

```bash
# In one terminal — watch the backend logs
docker compose logs -f backend

# In another terminal — send a burst
python samples/simulate_failure.py --count 500
```

Expected output in backend logs:
```
[IMS] Throughput: 87 signals/sec | Queue depth: 12
[IMS] Throughput: 61 signals/sec | Queue depth: 0
```