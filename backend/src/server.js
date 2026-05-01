import http from "node:http";
import { fileURLToPath } from "node:url";
import { FileStore } from "./infra/store.js";
import { TokenBucketRateLimiter } from "./infra/rateLimiter.js";
import { DashboardCache } from "./services/dashboardCache.js";
import { SignalProcessor } from "./services/processor.js";
import { IncidentService } from "./services/incidents.js";

const port = Number(process.env.PORT ?? 4000);
const dataDir = process.env.DATA_DIR ?? fileURLToPath(new URL("../data", import.meta.url));
const ingestApiKey = process.env.INGEST_API_KEY;
const maxBodyBytes = Number(process.env.MAX_BODY_BYTES ?? 1_048_576);

const store = new FileStore(dataDir);
await store.init();

const cache = new DashboardCache();
cache.hydrate(await store.readWorkItems());

const processor = new SignalProcessor(store, cache);
const incidents = new IncidentService(store, cache);
const limiter = new TokenBucketRateLimiter({ capacity: 1_000, refillPerSecond: 1_000 });

setInterval(() => {
  const accepted = processor.metrics.accepted;
  const processed = processor.metrics.processed;
  processor.metrics.accepted = 0;
  processor.metrics.processed = 0;
  console.log(
    `[metrics] accepted=${accepted / 5}/sec processed=${processed / 5}/sec queue=${processor.queue.length}`
  );
}, 5_000);

const server = http.createServer(async (req, res) => {
  try {
    applyCors(req, res);
    if (req.method === "OPTIONS") {
      return send(res, 204);
    }

    const url = new URL(req.url, `http://${req.headers.host}`);
    if (requiresApiKey(req, url) && !hasValidApiKey(req)) {
      return json(res, 401, { error: "Invalid or missing API key" });
    }

    if (req.method === "GET" && url.pathname === "/health") {
      return json(res, 200, { ok: true, queueDepth: processor.queue.length, time: new Date().toISOString() });
    }

    if (req.method === "POST" && url.pathname === "/signals") {
      const ip = req.socket.remoteAddress ?? "unknown";
      const body = await readJson(req);
      const signals = Array.isArray(body) ? body : [body];
      if (!limiter.allow(ip, signals.length)) {
        return json(res, 429, { error: "Rate limit exceeded" });
      }
      const accepted = [];
      for (const signal of signals) {
        validateSignal(signal);
        if (!processor.enqueue(signal)) {
          return json(res, 503, { error: "Ingestion queue saturated", accepted: accepted.length });
        }
        accepted.push(signal);
      }
      return json(res, 202, { accepted: accepted.length });
    }

    if (req.method === "GET" && url.pathname === "/incidents") {
      return json(res, 200, cache.listActive());
    }

    const incidentMatch = url.pathname.match(/^\/incidents\/([^/]+)$/);
    if (req.method === "GET" && incidentMatch) {
      const incident = await incidents.getIncident(incidentMatch[1]);
      return incident ? json(res, 200, incident) : json(res, 404, { error: "Incident not found" });
    }

    const statusMatch = url.pathname.match(/^\/incidents\/([^/]+)\/status$/);
    if (req.method === "PATCH" && statusMatch) {
      const body = await readJson(req);
      const updated = await incidents.transition(statusMatch[1], body.status);
      return json(res, 200, updated);
    }

    const rcaMatch = url.pathname.match(/^\/incidents\/([^/]+)\/rca$/);
    if (req.method === "POST" && rcaMatch) {
      const updated = await incidents.submitRca(rcaMatch[1], await readJson(req));
      return json(res, 200, updated);
    }

    if (req.method === "GET" && url.pathname === "/aggregations") {
      return json(res, 200, await store.readAggregations());
    }

    return json(res, 404, { error: "Not found" });
  } catch (error) {
    return json(res, error.statusCode ?? 400, { error: error.message });
  }
});

server.listen(port, () => {
  console.log(`IMS backend listening on http://localhost:${port}`);
});

function validateSignal(signal) {
  for (const field of ["componentId", "componentType", "message"]) {
    if (!signal?.[field]) {
      throw new Error(`Missing signal field: ${field}`);
    }
  }
  signal.severity ??= "ERROR";
}

function applyCors(req, res) {
  res.setHeader("Access-Control-Allow-Origin", process.env.CORS_ORIGIN ?? req.headers.origin ?? "*");
  res.setHeader("Access-Control-Allow-Methods", "GET,POST,PATCH,OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type,X-IMS-API-Key");
  res.setHeader("X-Content-Type-Options", "nosniff");
  res.setHeader("Referrer-Policy", "no-referrer");
  res.setHeader("Cache-Control", "no-store");
}

function requiresApiKey(req, url) {
  return Boolean(
    ingestApiKey &&
      (req.method === "POST" || req.method === "PATCH") &&
      (url.pathname === "/signals" || url.pathname.startsWith("/incidents/"))
  );
}

function hasValidApiKey(req) {
  return req.headers["x-ims-api-key"] === ingestApiKey;
}

function send(res, status, body = "") {
  res.writeHead(status);
  res.end(body);
}

function json(res, status, body) {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(body));
}

async function readJson(req) {
  const chunks = [];
  let totalBytes = 0;
  for await (const chunk of req) {
    totalBytes += chunk.length;
    if (totalBytes > maxBodyBytes) {
      const error = new Error("Request body too large");
      error.statusCode = 413;
      throw error;
    }
    chunks.push(chunk);
  }
  return JSON.parse(Buffer.concat(chunks).toString("utf8") || "{}");
}
