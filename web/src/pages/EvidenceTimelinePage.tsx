import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Card } from "../components/ui/Card";
import { apiGet } from "../services/api";

export function EvidenceTimelinePage() {
  const { evidence_id } = useParams();
  const id = Number(evidence_id);
  const [data, setData] = useState<{
    evidence: Record<string, unknown> | null;
    chain: Array<Record<string, unknown>>;
  } | null>(null);

  useEffect(() => {
    apiGet<{ evidence: Record<string, unknown> | null; chain: unknown[] }>(
      `/evidence/${id}/timeline`
    ).then((r) => setData(r as { evidence: Record<string, unknown> | null; chain: Array<Record<string, unknown>> }));
  }, [id]);

  if (!data) return <p className="muted">Loading…</p>;

  return (
    <div className="stack" style={{ paddingTop: "1rem" }}>
      <p>
        <Link to={`/evidence/${id}`}>← Evidence #{id}</Link>
      </p>
      <h1>Timeline</h1>
      {data.evidence && (
        <p className="muted">{String(data.evidence.fileName)}</p>
      )}
      <Card>
        <ol>
          {data.chain.map((c, i) => (
            <li key={i}>
              {String(c.datetime)} — <strong>{String(c.action)}</strong> —{" "}
              {String(c.actor)}
            </li>
          ))}
        </ol>
      </Card>
    </div>
  );
}
