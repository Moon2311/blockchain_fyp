import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { useAuth } from "../hooks/useAuth";
import { apiGet, apiPostJson } from "../services/api";

type Tr = {
  id: number;
  evidence_id: number;
  from_username: string;
  to_username: string;
  status: string;
};

export function TransfersPage() {
  const { user } = useAuth();
  const [rows, setRows] = useState<Tr[]>([]);

  const load = () =>
    apiGet<{ transfers: Tr[] }>("/transfers").then((r) => setRows(r.transfers));

  useEffect(() => {
    load().catch(() => {});
  }, []);

  async function approve(id: number) {
    try {
      await apiPostJson(`/transfers/${id}/approve`, {});
      await load();
    } catch (ex) {
      alert(ex instanceof Error ? ex.message : "Failed");
    }
  }

  async function reject(id: number) {
    try {
      await apiPostJson(`/transfers/${id}/reject`, {});
      await load();
    } catch (ex) {
      alert(ex instanceof Error ? ex.message : "Failed");
    }
  }

  return (
    <div className="stack" style={{ paddingTop: "1rem" }}>
      <h1>Transfers</h1>
      <Card>
        <table style={{ width: "100%", fontSize: "0.9rem" }}>
          <thead>
            <tr style={{ textAlign: "left" }}>
              <th>ID</th>
              <th>Evidence</th>
              <th>From</th>
              <th>To</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((t) => (
              <tr key={t.id}>
                <td>#{t.id}</td>
                <td>
                  <Link to={`/evidence/${t.evidence_id}`}>#{t.evidence_id}</Link>
                </td>
                <td>{t.from_username}</td>
                <td>{t.to_username}</td>
                <td>{t.status}</td>
                <td>
                  {t.status === "pending" &&
                    (user?.email === t.to_username || user?.role === "Admin") && (
                      <span className="row">
                        <Button variant="primary" onClick={() => approve(t.id)}>
                          Approve
                        </Button>
                        <Button variant="danger" onClick={() => reject(t.id)}>
                          Reject
                        </Button>
                      </span>
                    )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!rows.length && <p className="muted">No transfers</p>}
      </Card>
    </div>
  );
}
