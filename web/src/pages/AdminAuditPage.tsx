import { useEffect, useState } from "react";
import { Card } from "../components/ui/Card";
import { apiGet } from "../services/api";

type AuditRow = {
  id: number;
  username: string;
  action: string;
  detail: string | null;
  evidence_id: number | null;
  case_id: number | null;
  created_at: string | null;
};

type VerRow = {
  id: number;
  evidence_id: number;
  success: boolean;
  username: string;
  created_at: string | null;
};

export function AdminAuditPage() {
  const [audit, setAudit] = useState<AuditRow[]>([]);
  const [verifications, setVerifications] = useState<VerRow[]>([]);

  useEffect(() => {
    apiGet<{ audit: AuditRow[]; verifications: VerRow[] }>("/admin/audit")
      .then((r) => {
        setAudit(r.audit);
        setVerifications(r.verifications);
      })
      .catch(() => {});
  }, []);

  return (
    <div className="stack" style={{ paddingTop: "1rem" }}>
      <h1>Audit trail</h1>
      <p className="muted">
        Off-chain activity log (uploads, logins, custody actions, verification attempts).
      </p>
      <Card title="Activity log">
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", fontSize: "0.88rem" }}>
            <thead>
              <tr style={{ textAlign: "left" }}>
                <th>When</th>
                <th>User</th>
                <th>Action</th>
                <th>Evidence</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {audit.map((a) => (
                <tr key={a.id}>
                  <td>{a.created_at || "—"}</td>
                  <td>{a.username}</td>
                  <td>{a.action}</td>
                  <td>{a.evidence_id != null ? `#${a.evidence_id}` : "—"}</td>
                  <td style={{ maxWidth: 280, wordBreak: "break-word" }}>
                    {a.detail || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!audit.length && <p className="muted">No entries yet.</p>}
        </div>
      </Card>
      <Card title="Verification history">
        <table style={{ width: "100%", fontSize: "0.88rem" }}>
          <thead>
            <tr style={{ textAlign: "left" }}>
              <th>When</th>
              <th>User</th>
              <th>Evidence</th>
              <th>Result</th>
            </tr>
          </thead>
          <tbody>
            {verifications.map((v) => (
              <tr key={v.id}>
                <td>{v.created_at || "—"}</td>
                <td>{v.username}</td>
                <td>#{v.evidence_id}</td>
                <td>{v.success ? "Match" : "Mismatch"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!verifications.length && <p className="muted">No verifications yet.</p>}
      </Card>
    </div>
  );
}
