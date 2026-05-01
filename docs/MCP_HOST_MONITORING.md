# MCP Host Monitoring Guide

## Why MCP Hosts Matter

The assignment explicitly includes MCP Hosts as part of the distributed stack. In this IMS, MCP host failures are treated as platform incidents because they often sit between tool/client traffic and downstream services.

## Signal Shape

Example MCP signal:

```json
{
  "componentId": "MCP_HOST_07",
  "componentType": "MCP_HOST",
  "message": "MCP host cannot reach primary RDBMS",
  "severity": "ERROR",
  "payload": {
    "region": "ap-south-1",
    "dependency": "RDBMS_PRIMARY_01"
  }
}
```

## Alerting Strategy

`MCP_HOST` uses `McpAlertStrategy`:

- Severity: `P1`
- Channel: `pager`
- Responder: `platform-oncall`

This is intentionally lower than direct RDBMS failure (`P0`) but higher than cache degradation (`P2`).

## Failure Mediation Workflow

1. MCP host emits repeated signals.
2. Ingestion API accepts the signals into the bounded queue.
3. Debouncing creates one incident per affected MCP host inside the 10 second window.
4. Every raw signal is linked to that incident in PostgreSQL `raw_signals`.
5. Platform on-call moves the incident through `OPEN -> INVESTIGATING -> RESOLVED`.
6. A complete RCA is required before `CLOSED`.

## Sample Scenario

`samples/failure-events.json` models an RDBMS outage followed by an MCP host failure. This demonstrates dependency-aware incident review: responders can see the MCP error payload and its dependency on `RDBMS_PRIMARY_01`.
