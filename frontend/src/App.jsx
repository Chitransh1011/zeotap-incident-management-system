import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API = import.meta.env.VITE_API_BASE ?? "http://localhost:4000";
const API_KEY = import.meta.env.VITE_API_KEY;
const statuses = ["OPEN", "INVESTIGATING", "RESOLVED", "CLOSED"];

function apiHeaders() {
  return {
    "Content-Type": "application/json",
    ...(API_KEY ? { "X-IMS-API-Key": API_KEY } : {})
  };
}

function App() {
  const [incidents, setIncidents] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState("");

  async function loadIncidents() {
    const response = await fetch(`${API}/incidents`);
    setIncidents(await response.json());
  }

  async function loadDetail(id) {
    const response = await fetch(`${API}/incidents/${id}`);
    setDetail(await response.json());
    setSelectedId(id);
  }

  useEffect(() => {
    loadIncidents();
    const timer = setInterval(loadIncidents, 2500);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (selectedId) {
      loadDetail(selectedId);
    }
  }, [incidents, selectedId]);

  async function transition(status) {
    setError("");
    const response = await fetch(`${API}/incidents/${selectedId}/status`, {
      method: "PATCH",
      headers: apiHeaders(),
      body: JSON.stringify({ status })
    });
    const body = await response.json();
    if (!response.ok) {
      setError(body.error || body.detail || "Status update failed");
      return;
    }
    setDetail(body);
    loadIncidents();
  }

  async function submitRca(event) {
    event.preventDefault();
    setError("");
    const form = new FormData(event.currentTarget);
    const payload = Object.fromEntries(form.entries());
    const response = await fetch(`${API}/incidents/${selectedId}/rca`, {
      method: "POST",
      headers: apiHeaders(),
      body: JSON.stringify(payload)
    });
    const body = await response.json();
    if (!response.ok) {
      setError(body.error || body.detail || "RCA submission failed");
      return;
    }
    setDetail(body);
  }

  return (
    <main className="shell">
      <section className="feed">
        <div className="topbar">
          <h1>Incident Management</h1>
          <span>{incidents.length} active</span>
        </div>
        <div className="incident-list">
          {incidents.map((incident) => (
            <button
              className={`incident ${selectedId === incident.id ? "selected" : ""}`}
              key={incident.id}
              onClick={() => loadDetail(incident.id)}
            >
              <span className={`severity ${incident.severity}`}>{incident.severity}</span>
              <strong>{incident.title}</strong>
              <small>{incident.componentType} · {incident.status}</small>
            </button>
          ))}
          {incidents.length === 0 && <p className="empty">No active incidents.</p>}
        </div>
      </section>

      <section className="detail">
        {!detail && <p className="empty">Select an incident to review signals and RCA.</p>}
        {detail && (
          <>
            <div className="detail-head">
              <div>
                <h2>{detail.componentId}</h2>
                <p>{detail.responder} via {detail.alertChannel}</p>
              </div>
              <span className={`severity ${detail.severity}`}>{detail.severity}</span>
            </div>

            <div className="status-row">
              {statuses.map((status) => (
                <button key={status} onClick={() => transition(status)} disabled={status === detail.status}>
                  {status}
                </button>
              ))}
            </div>
            {error && <p className="error">{error}</p>}

            <form className="rca" onSubmit={submitRca}>
              <h3>Root Cause Analysis</h3>
              <label>Incident Start<input name="startTime" type="datetime-local" required /></label>
              <label>Incident End<input name="endTime" type="datetime-local" required /></label>
              <label>Category
                <select name="rootCauseCategory" required>
                  <option value="">Select</option>
                  <option>DATABASE</option>
                  <option>CACHE</option>
                  <option>QUEUE</option>
                  <option>DEPLOYMENT</option>
                  <option>CONFIGURATION</option>
                </select>
              </label>
              <label>Fix Applied<textarea name="fixApplied" required /></label>
              <label>Prevention Steps<textarea name="preventionSteps" required /></label>
              <button className="primary">Save RCA</button>
              {detail.mttrMs !== null && <p className="mttr">MTTR: {Math.round(detail.mttrMs / 60000)} minutes</p>}
            </form>

            <div className="signals">
              <h3>Raw Signals</h3>
              {(detail.rawSignals ?? []).map((signal, index) => (
                <pre key={index}>{JSON.stringify(signal, null, 2)}</pre>
              ))}
            </div>
          </>
        )}
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
