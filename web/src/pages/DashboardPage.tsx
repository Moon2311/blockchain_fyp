import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Card } from "../components/ui/Card";
import { apiGet } from "../services/api";

type RecentEv = {
  id: number;
  fileName: string;
  uploadedBy: string;
};

type Dash = {
  blockchain: { connected: boolean; deployed: boolean };
  stats: {
    total: number;
    recent: RecentEv[];
    error?: string;
  };
  recent_alerts: Array<{
    id: number;
    level: string;
    message: string;
    created_at: string | null;
  }>;
};

export function DashboardPage() {
  const [data, setData] = useState<Dash | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    apiGet<Dash>("/dashboard")
      .then(setData)
      .catch((e) => setErr(String(e)));
  }, []);

  if (err) return <p style={{ color: "var(--color-danger)" }}>{err}</p>;
  if (!data) return <p className="muted">Loading dashboard…</p>;

  const { blockchain, stats, recent_alerts } = data;

  return (
    <div className="stack" style={{ paddingTop: "1rem" }}>
      <h1>Dashboard</h1>
      <p className="muted">
        Blockchain connection and recent activity at a glance.
      </p>
      <div className="grid-2">
        <Card title="Network">
          <p style={{ margin: 0 }}>
            Ganache:{" "}
            <strong>{blockchain.connected ? "Connected" : "Offline"}</strong>
          </p>
          <p style={{ margin: "0.5rem 0 0" }}>
            Contract:{" "}
            <strong>{blockchain.deployed ? "Deployed" : "Not deployed"}</strong>
          </p>
        </Card>
        <Card title="Evidence on chain">
          <p style={{ fontSize: "2rem", fontWeight: 700, margin: 0 }}>
            {stats.total}
          </p>
          <p className="muted" style={{ margin: "0.25rem 0 0" }}>
            Total records
          </p>
          {stats.error && (
            <p style={{ color: "var(--color-warning)", fontSize: "0.9rem" }}>
              {stats.error}
            </p>
          )}
        </Card>
      </div>
      <Card title="Recent evidence">
        <ul style={{ margin: 0, paddingLeft: "1.2rem" }}>
          {(stats.recent || []).map((r) => (
            <li key={r.id} style={{ marginBottom: "0.35rem" }}>
              <Link to={`/evidence/${r.id}`}>#{r.id}</Link> — {r.fileName}{" "}
              <span className="muted">({r.uploadedBy})</span>
            </li>
          ))}
          {!stats.recent?.length && (
            <li className="muted">No items (deploy contract & upload)</li>
          )}
        </ul>
      </Card>
      <Card title="Security alerts">
        <ul style={{ margin: 0, paddingLeft: "1.2rem" }}>
          {recent_alerts.map((a) => (
            <li key={a.id} style={{ marginBottom: "0.35rem" }}>
              <span
                style={{
                  fontSize: "0.75rem",
                  padding: "0.1rem 0.35rem",
                  borderRadius: 4,
                  background: "var(--color-surface)",
                  marginRight: "0.35rem",
                }}
              >
                {a.level}
              </span>
              {a.message}
            </li>
          ))}
          {!recent_alerts.length && (
            <li className="muted">No recent alerts</li>
          )}
        </ul>
      </Card>
    </div>
  );
}
