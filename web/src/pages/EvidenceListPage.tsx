import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Card } from "../components/ui/Card";
import { apiGet } from "../services/api";
import { formatBytes } from "../utils/format";

type Item = {
  id: number;
  fileName: string;
  fileType: string;
  fileSize: number;
  uploadedBy: string;
  createdAt: string;
  encrypted: boolean;
};

export function EvidenceListPage() {
  const [data, setData] = useState<{
    blockchain: { connected: boolean; deployed: boolean };
    items: Item[];
    warning?: string;
  } | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    apiGet<{
      blockchain: { connected: boolean; deployed: boolean };
      items: Item[];
      warning?: string;
    }>("/evidence")
      .then(setData)
      .catch((e) => setErr(String(e)));
  }, []);

  if (err) return <p style={{ color: "var(--color-danger)" }}>{err}</p>;
  if (!data) return <p className="muted">Loading…</p>;

  return (
    <div className="stack" style={{ paddingTop: "1rem" }}>
      <h1>Evidence</h1>
      {data.warning && (
        <p style={{ color: "var(--color-warning)" }}>{data.warning}</p>
      )}
      <p className="muted">
        Status:{" "}
        {data.blockchain.deployed && data.blockchain.connected
          ? "Blockchain ready"
          : "Check Ganache / contract"}
      </p>
      <Card>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.92rem" }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "1px solid var(--color-border)" }}>
                <th style={{ padding: "0.5rem" }}>ID</th>
                <th>File</th>
                <th>Type</th>
                <th>Size</th>
                <th>Uploader</th>
                <th>Recorded</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((row) => (
                <tr key={row.id} style={{ borderBottom: "1px solid var(--color-border)" }}>
                  <td style={{ padding: "0.5rem" }}>
                    <Link to={`/evidence/${row.id}`}>#{row.id}</Link>
                  </td>
                  <td>{row.fileName}</td>
                  <td>{row.fileType}</td>
                  <td>{formatBytes(row.fileSize)}</td>
                  <td>{row.uploadedBy}</td>
                  <td className="muted">{row.createdAt}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!data.items.length && (
          <p className="muted" style={{ margin: 0 }}>
            No evidence visible (assignments apply for Investigator/Viewer/Member).
          </p>
        )}
      </Card>
    </div>
  );
}
