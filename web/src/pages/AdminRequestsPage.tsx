import { useEffect, useState } from "react";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { apiGet, apiPostJson } from "../services/api";

type ReqRow = {
  id: number;
  evidence_id: number;
  requester_username: string;
  status: string;
};

export function AdminRequestsPage() {
  const [rows, setRows] = useState<ReqRow[]>([]);

  const load = () =>
    apiGet<{ requests: ReqRow[] }>("/admin/requests").then((r) =>
      setRows(r.requests)
    );

  useEffect(() => {
    load().catch(() => {});
  }, []);

  async function decide(id: number, action: "approve" | "reject") {
    try {
      await apiPostJson(`/admin/requests/${id}/decide`, { action });
      await load();
    } catch (ex) {
      alert(ex instanceof Error ? ex.message : "Failed");
    }
  }

  return (
    <div className="stack" style={{ paddingTop: "1rem" }}>
      <h1>Access requests</h1>
      <Card>
        <table style={{ width: "100%", fontSize: "0.9rem" }}>
          <thead>
            <tr>
              <th>ID</th>
              <th>Evidence</th>
              <th>Requester</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{r.id}</td>
                <td>#{r.evidence_id}</td>
                <td>{r.requester_username}</td>
                <td>{r.status}</td>
                <td>
                  {r.status === "pending" && (
                    <span className="row">
                      <Button variant="primary" onClick={() => decide(r.id, "approve")}>
                        Approve
                      </Button>
                      <Button variant="danger" onClick={() => decide(r.id, "reject")}>
                        Reject
                      </Button>
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!rows.length && <p className="muted">No requests</p>}
      </Card>
    </div>
  );
}
