import fs from "node:fs/promises";

const api = process.env.API_BASE ?? "http://localhost:4000";
const apiKey = process.env.INGEST_API_KEY;
const events = JSON.parse(await fs.readFile(new URL("./failure-events.json", import.meta.url), "utf8"));

for (let i = 0; i < 120; i += 1) {
  const event = events[i % events.length];
  await fetch(`${api}/signals`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(apiKey ? { "X-IMS-API-Key": apiKey } : {})
    },
    body: JSON.stringify({ ...event, sequence: i })
  });
}

console.log(`Sent ${120} failure signals to ${api}`);
