import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { useAuth } from "../hooks/useAuth";
import { apiGet, apiPostForm } from "../services/api";

export function VerifyPage() {
  const { user } = useAuth();
  const [count, setCount] = useState(0);
  const [evidenceId, setEvidenceId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    apiGet<{ evidence_count: number }>("/verify")
      .then((r) => setCount(r.evidence_count))
      .catch(() => {});
  }, []);

  if (
    user &&
    user.role !== "Admin" &&
    user.role !== "Investigator"
  ) {
    return <Navigate to="/dashboard" replace />;
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file || !evidenceId) return;
    const fd = new FormData();
    fd.append("evidence_id", evidenceId);
    fd.append("file", file);
    try {
      const r = await apiPostForm<Record<string, unknown>>("/verify", fd);
      setResult(r);
    } catch (ex) {
      alert(ex instanceof Error ? ex.message : "Verify failed");
    }
  }

  return (
    <div className="stack" style={{ paddingTop: "1rem" }}>
      <h1>Verify integrity</h1>
      <p className="muted">On-chain records: {count}</p>
      <Card title="Compare file hash">
        <form onSubmit={onSubmit} className="stack">
          <label>
            Evidence ID
            <input
              type="number"
              min={1}
              required
              value={evidenceId}
              onChange={(e) => setEvidenceId(e.target.value)}
              style={{ display: "block", marginTop: "0.35rem", padding: "0.45rem" }}
            />
          </label>
          <input
            type="file"
            required
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
          <Button type="submit">Verify</Button>
        </form>
      </Card>
      {result && (
        <Card title="Result">
          <p style={{ margin: 0 }}>
            Authentic:{" "}
            <strong>
              {result.authentic ? "Yes ✓" : "No — mismatch"}
            </strong>
          </p>
          <p className="muted" style={{ fontSize: "0.88rem" }}>
            {String(result.new_hash || "").slice(0, 32)}…
          </p>
        </Card>
      )}
    </div>
  );
}
