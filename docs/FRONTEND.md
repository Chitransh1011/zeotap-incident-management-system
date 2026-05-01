# Frontend Guide

## Purpose

The frontend is a responsive incident dashboard for responders. It focuses on the operational workflow requested in the assignment: active incident feed, incident detail, raw signals, status transitions, and RCA submission.

## Runtime

- React 18
- Vite development server
- Backend API URL from `VITE_API_BASE`

## Run Locally

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Build

```bash
cd frontend
npm install
npm run build
```

## Screens

### Live Feed

- Polls `GET /incidents` every 2.5 seconds.
- Shows only active incidents.
- Backend sorts by severity, so P0 incidents appear first.

### Incident Detail

- Loads `GET /incidents/:id`.
- Shows component, responder, alert channel, current status, MTTR, and raw signal payloads.

### Workflow Actions

- Uses `PATCH /incidents/:id/status`.
- The backend rejects invalid transitions and blocks `CLOSED` when RCA is missing.

### RCA Form

Fields:

- Incident start date-time.
- Incident end date-time.
- Root cause category dropdown.
- Fix applied text area.
- Prevention steps text area.

## Optional Security

If the backend is started with `INGEST_API_KEY`, set the same value as `VITE_API_KEY` in `frontend/.env`. The UI then sends `X-IMS-API-Key` on mutating requests.
