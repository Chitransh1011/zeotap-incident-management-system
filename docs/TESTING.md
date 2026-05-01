# Testing and Verification Guide

## Backend Unit Tests

```bash
cd backend
npm test
```

Covered:

- RCA validation rejects incomplete objects.
- RCA validation accepts complete objects.
- `CLOSED` transition is blocked without RCA.
- MTTR calculation from RCA timestamps.

## Frontend Build Test

```bash
cd frontend
npm install
npm run build
```

## End-to-End Manual Test

Start the stack:

```bash
docker compose up --build
```

Check health:

```bash
curl http://localhost:4000/health
```

Generate sample incidents:

```bash
node samples/simulate-failure.js
```

Open the dashboard:

```text
http://localhost:5173
```

Manual assertions:

- RDBMS incident appears as `P0`.
- MCP host incident appears as `P1`.
- Cache incident appears as `P2`.
- Raw signals are visible in incident detail.
- `CLOSED` fails until RCA is submitted.
- After RCA submission, MTTR appears in minutes.

## API Smoke Test with PowerShell

```powershell
$body = Get-Content samples/failure-events.json -Raw
Invoke-RestMethod -Uri http://localhost:4000/signals -Method Post -ContentType application/json -Body $body
Invoke-RestMethod -Uri http://localhost:4000/incidents
```

## Optional Security Test

Start backend with:

```bash
INGEST_API_KEY=change-me npm start
```

Then verify unauthenticated ingestion is rejected:

```bash
curl -X POST http://localhost:4000/signals \
  -H "Content-Type: application/json" \
  -d '{"componentId":"RDBMS_PRIMARY_01","componentType":"RDBMS","message":"test"}'
```

Expected: `401`.

Retry with header:

```bash
curl -X POST http://localhost:4000/signals \
  -H "Content-Type: application/json" \
  -H "X-IMS-API-Key: change-me" \
  -d '{"componentId":"RDBMS_PRIMARY_01","componentType":"RDBMS","message":"test"}'
```

Expected: `202`.
