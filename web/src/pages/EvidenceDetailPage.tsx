import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { useAuth } from "../hooks/useAuth";
import { apiGet, apiPostJson } from "../services/api";
import { truncateHash } from "../utils/format";

export function EvidenceDetailPage() {
  const { evidence_id } = useParams();
  const id = Number(evidence_id);
  const { user } = useAuth();
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [action, setAction] = useState("Transferred");
  const [notes, setNotes] = useState("");
  const [toUser, setToUser] = useState("");
  const [unlockAt, setUnlockAt] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () =>
    apiGet<Record<string, unknown>>(`/evidence/${id}`).then(setData);

  useEffect(() => {
    if (!Number.isFinite(id)) return;
    load().catch((e) => setErr(String(e)));
  }, [id]);

  async function submitAction(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await apiPostJson(`/evidence/${id}/action`, { action, notes });
      await load();
    } catch (ex) {
      alert(ex instanceof Error ? ex.message : "Failed");
    } finally {
      setBusy(false);
    }
  }

  async function submitTransfer(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await apiPostJson(`/evidence/${id}/transfer-request`, {
        to_username: toUser,
        notes: "",
      });
      await load();
    } catch (ex) {
      alert(ex instanceof Error ? ex.message : "Failed");
    } finally {
      setBusy(false);
    }
  }

  async function submitTimeLock(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await apiPostJson(`/evidence/${id}/time-lock`, { unlock_at: unlockAt });
      await load();
    } catch (ex) {
      alert(ex instanceof Error ? ex.message : "Failed");
    } finally {
      setBusy(false);
    }
  }

  if (err) return <p style={{ color: "var(--color-danger)" }}>{err}</p>;
  if (!data) return <p className="muted">Loading…</p>;
  if (data.error) return <p style={{ color: "var(--color-danger)" }}>{String(data.error)}</p>;

  const ev = data.evidence as Record<string, unknown> | null;
  const chain = (data.chain as Array<Record<string, unknown>>) || [];
  const locked = Boolean(data.locked_view);
  const canManage = Boolean(data.can_manage_custody);

  return (
    <div className="stack" style={{ paddingTop: "1rem" }}>
      <p>
        <Link to="/evidence">← Evidence</Link>
      </p>
      <h1>Evidence #{id}</h1>
      {locked && (
        <p style={{ color: "var(--color-warning)" }}>
          Time-locked view for your role until {String(data.unlock_at || "unlock")}.
        </p>
      )}
      {ev && (
        <Card title="Metadata">
          <dl style={{ display: "grid", gap: "0.35rem", margin: 0 }}>
            <dt className="muted" style={{ margin: 0 }}>
              File
            </dt>
            <dd style={{ margin: 0 }}>{String(ev.fileName)}</dd>
            <dt className="muted" style={{ margin: 0 }}>
              Hash
            </dt>
            <dd style={{ margin: 0, wordBreak: "break-all" }}>
              {truncateHash(String(ev.fileHash), 16, 16)}
            </dd>
            <dt className="muted" style={{ margin: 0 }}>
              Uploaded by
            </dt>
            <dd style={{ margin: 0 }}>
              {String(ev.uploadedByLabel || ev.uploadedBy || "")}
            </dd>
          </dl>
        </Card>
      )}
      <Card title="Custody chain">
        <ol style={{ margin: 0, paddingLeft: "1.2rem" }}>
          {chain.map((c, i) => (
            <li key={i} style={{ marginBottom: "0.35rem" }}>
              <strong>{String(c.action)}</strong> by{" "}
              {String(c.actor_label || c.actor)} —{" "}
              {String(c.datetime)}
            </li>
          ))}
          {!chain.length && <li className="muted">No events</li>}
        </ol>
      </Card>
      {ev && !locked && canManage && (
        <>
          <Card title="Log custody action">
            <form onSubmit={submitAction} className="stack">
              <select
                value={action}
                onChange={(e) => setAction(e.target.value)}
                style={{ maxWidth: 220, padding: "0.45rem" }}
              >
                {Object.values(
                  (data.action_names as Record<string, string>) || {}
                ).map((v) => (
                  <option key={v} value={v}>
                    {v}
                  </option>
                ))}
              </select>
              <textarea
                placeholder="Notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
                style={{ width: "100%", padding: "0.5rem", borderRadius: "var(--radius-md)" }}
              />
              <Button type="submit" disabled={busy}>
                Submit
              </Button>
            </form>
          </Card>
          <Card title="Request transfer">
            <form onSubmit={submitTransfer} className="stack">
              <select
                value={toUser}
                onChange={(e) => setToUser(e.target.value)}
                required
                style={{ maxWidth: 320, padding: "0.45rem" }}
              >
                <option value="">Select user…</option>
                {(data.users_for_transfer as string[] | undefined)?.map((u) => (
                  <option key={u} value={u}>
                    {u}
                  </option>
                ))}
              </select>
              <Button type="submit" variant="secondary" disabled={busy}>
                Send request
              </Button>
            </form>
          </Card>
          {user?.role === "Admin" && (
            <Card title="Time lock (admin)">
              <form onSubmit={submitTimeLock} className="stack">
                <input
                  type="datetime-local"
                  value={unlockAt}
                  onChange={(e) => setUnlockAt(e.target.value)}
                  required
                  style={{ maxWidth: 280, padding: "0.45rem" }}
                />
                <Button type="submit" variant="secondary" disabled={busy}>
                  Set lock
                </Button>
              </form>
            </Card>
          )}
        </>
      )}
      <p>
        <Link to={`/evidence/${id}/timeline`}>Open timeline view →</Link>
      </p>
    </div>
  );
}
