import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { apiGet, apiPostForm } from "../services/api";

type CaseRow = { id: number; case_number: string; title: string };

export function UploadPage() {
  const nav = useNavigate();
  const [opts, setOpts] = useState<{
    next_id: number;
    cases: CaseRow[];
  } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [encrypt, setEncrypt] = useState(false);
  const [notes, setNotes] = useState(
    "Evidence collected and recorded on blockchain"
  );
  const [caseId, setCaseId] = useState<number | "">("");

  useEffect(() => {
    apiGet<{ next_id: number; cases: CaseRow[] }>("/upload/options")
      .then(setOpts)
      .catch((e) => setErr(String(e)));
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    if (encrypt) fd.append("encrypt", "on");
    fd.append("notes", notes);
    if (caseId !== "") fd.append("case_id", String(caseId));
    try {
      const res = await apiPostForm<{ evidence_id: number }>("/upload", fd);
      nav(`/evidence/${res.evidence_id}`);
    } catch (ex) {
      alert(ex instanceof Error ? ex.message : "Upload failed");
    }
  }

  if (err) return <p style={{ color: "var(--color-danger)" }}>{err}</p>;
  if (!opts) return <p className="muted">Loading…</p>;

  return (
    <div className="stack" style={{ paddingTop: "1rem" }}>
      <h1>Upload evidence</h1>
      <p className="muted">Next on-chain ID (estimate): #{opts.next_id}</p>
      <Card title="File">
        <form onSubmit={onSubmit} className="stack">
          <input
            type="file"
            required
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
          <label className="row">
            <input
              type="checkbox"
              checked={encrypt}
              onChange={(e) => setEncrypt(e.target.checked)}
            />
            Encrypt at rest (Fernet)
          </label>
          <label>
            Notes
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              style={{ width: "100%", marginTop: "0.35rem", padding: "0.5rem" }}
            />
          </label>
          <label>
            Link to case (optional)
            <select
              value={caseId === "" ? "" : caseId}
              onChange={(e) =>
                setCaseId(e.target.value === "" ? "" : Number(e.target.value))
              }
              style={{ display: "block", marginTop: "0.35rem", padding: "0.45rem" }}
            >
              <option value="">—</option>
              {opts.cases.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.case_number} — {c.title}
                </option>
              ))}
            </select>
          </label>
          <Button type="submit" variant="primary">
            Upload & register
          </Button>
        </form>
      </Card>
    </div>
  );
}
