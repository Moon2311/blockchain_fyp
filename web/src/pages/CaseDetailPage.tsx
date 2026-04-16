import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { apiGet, apiPostJson } from "../services/api";

export function CaseDetailPage() {
  const { case_id } = useParams();
  const cid = Number(case_id);
  const [data, setData] = useState<{
    case: Record<string, unknown>;
    ev_rows: Array<Record<string, unknown>>;
  } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [eid, setEid] = useState("");

  const load = () =>
    apiGet<{ case: Record<string, unknown>; ev_rows: unknown[] }>(
      `/cases/${cid}`
    ).then((r) => setData(r as { case: Record<string, unknown>; ev_rows: Array<Record<string, unknown>> }));

  useEffect(() => {
    load().catch((e) => setErr(String(e)));
  }, [cid]);

  async function linkEv(e: React.FormEvent) {
    e.preventDefault();
    try {
      await apiPostJson(`/cases/${cid}/link`, {
        evidence_id: Number(eid),
      });
      setEid("");
      await load();
    } catch (ex) {
      alert(ex instanceof Error ? ex.message : "Failed");
    }
  }

  if (err) return <p style={{ color: "var(--color-danger)" }}>{err}</p>;
  if (!data) return <p className="muted">Loading…</p>;

  const c = data.case;

  return (
    <div className="stack" style={{ paddingTop: "1rem" }}>
      <p>
        <Link to="/cases">← Cases</Link>
      </p>
      <h1>
        {String(c.case_number)} — {String(c.title)}
      </h1>
      <p className="muted">{String(c.description || "")}</p>
      <Card title="Linked evidence">
        <ul>
          {data.ev_rows.map((row) => (
            <li key={String(row.evidence_id)}>
              <Link to={`/evidence/${row.evidence_id}`}>
                #{String(row.evidence_id)}
              </Link>{" "}
              {String(row.fileName)}
            </li>
          ))}
          {!data.ev_rows.length && (
            <li className="muted">None linked</li>
          )}
        </ul>
      </Card>
      <Card title="Link evidence ID">
        <form onSubmit={linkEv} className="row">
          <input
            type="number"
            min={1}
            placeholder="Evidence ID"
            value={eid}
            onChange={(e) => setEid(e.target.value)}
            style={{ padding: "0.45rem", width: 140 }}
          />
          <Button type="submit" variant="secondary">
            Link
          </Button>
        </form>
      </Card>
      <p>
        <Link to={`/cases/${cid}/report`}>Case report →</Link>
      </p>
    </div>
  );
}
