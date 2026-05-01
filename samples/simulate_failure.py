import json
import os
import urllib.request
from pathlib import Path

API_BASE = os.getenv("API_BASE", "http://localhost:4000")
API_KEY = os.getenv("INGEST_API_KEY")
EVENTS_PATH = Path(__file__).with_name("failure-events.json")


def post_signal(payload):
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["X-IMS-API-Key"] = API_KEY

    request = urllib.request.Request(
        f"{API_BASE}/signals",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=10) as response:
        body = json.loads(response.read().decode())
        print("Backend Response:", body)


def main():
    events = json.loads(EVENTS_PATH.read_text(encoding="utf-8"))

    batch = []
    for index in range(120):
        batch.append({**events[index % len(events)], "sequence": index})

    post_signal(batch)
    print(f"Sent batch of {len(batch)} failure signals to {API_BASE}")


if __name__ == "__main__":
    main()