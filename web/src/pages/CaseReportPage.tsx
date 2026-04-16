import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Card } from "../components/ui/Card";
import { apiGet } from "../services/api";

export function CaseReportPage() {
  const { case_id } = useParams();
  const cid = Number(case_id);
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    apiGet<Record<string, unknown>>(`/cases/${cid}/report`)
      .then(setData)
      .catch((e) => setErr(String(e)));
  }, [cid]);

  if (err) return <p style={{ color: "var(--color-danger)" }}>{err}</p>;
  if (!data) return <p className="muted">Loading…</p>;

  const c = data.case as Record<string, unknown>;
  const items = (data.items as Array<Record<string, unknown>>) || [];

  return (
    <div className="stack" style={{ paddingTop: "1rem" }}>
      <p>
        <Link to={`/cases/${cid}`}>← Case</Link>
      </p>
      <h1>Report — {String(c.case_number)}</h1>
      <p className="muted">Generated {String(data.generated_at)}</p>
      <Card>
        <table style={{ width: "100%", fontSize: "0.92rem" }}>
          <thead>
            <tr style={{ textAlign: "left" }}>
              <th>Evidence</th>
              <th>Chain length</th>
            </tr>
          </thead>
          <tbody>
            {items.map((row) => (
              <tr key={String(row.evidence_id)}>
                <td>
                  <Link to={`/evidence/${row.evidence_id}`}>
                    #{String(row.evidence_id)}
                  </Link>
                </td>
                <td>{String(row.chain_len)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
