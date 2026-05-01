# API Guide

Base URL: `http://localhost:4000`

If `INGEST_API_KEY` is enabled, include this header on `POST` and `PATCH` requests:

```http
X-IMS-API-Key: change-me
```

## Health

```bash
curl http://localhost:4000/health
```

Response:

```json
{
  "ok": true,
  "queueDepth": 0,
  "time": "2026-05-01T10:00:00.000Z"
}
```

## Ingest Signal

```bash
curl -X POST http://localhost:4000/signals \
  -H "Content-Type: application/json" \
  -d '{
    "componentId": "RDBMS_PRIMARY_01",
    "componentType": "RDBMS",
    "message": "Connection pool exhausted",
    "severity": "ERROR",
    "payload": { "latencyMs": 5120 }
  }'
```

Batch ingestion is also supported:

```bash
curl -X POST http://localhost:4000/signals \
  -H "Content-Type: application/json" \
  --data-binary @samples/failure-events.json
```

Success response:

```json
{ "accepted": 3 }
```

## List Active Incidents

```bash
curl http://localhost:4000/incidents
```

Incidents are returned from the hot dashboard cache and sorted by severity.

## Incident Detail

```bash
curl http://localhost:4000/incidents/<incident-id>
```

The response includes the structured work item plus linked raw signals.

## Transition Status

```bash
curl -X PATCH http://localhost:4000/incidents/<incident-id>/status \
  -H "Content-Type: application/json" \
  -d '{ "status": "INVESTIGATING" }'
```

Valid statuses are `OPEN`, `INVESTIGATING`, `RESOLVED`, and `CLOSED`.

## Submit RCA

```bash
curl -X POST http://localhost:4000/incidents/<incident-id>/rca \
  -H "Content-Type: application/json" \
  -d '{
    "startTime": "2026-05-01T10:00:00.000Z",
    "endTime": "2026-05-01T10:30:00.000Z",
    "rootCauseCategory": "DATABASE",
    "fixApplied": "Promoted standby database",
    "preventionSteps": "Add failover drill and connection pool alerts"
  }'
```

## Aggregations

```bash
curl http://localhost:4000/aggregations
```

Returns minute-level PostgreSQL counters by component and severity.
