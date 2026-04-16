import { useEffect, useState } from "react";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { useAuth } from "../hooks/useAuth";
import { apiGet, apiPostJson } from "../services/api";

type AlertRow = {
  id: number;
  level: string;
  message: string;
  acknowledged: boolean;
};

export function AlertsPage() {
  const { user } = useAuth();
  const [rows, setRows] = useState<AlertRow[]>([]);

  const load = () =>
    apiGet<{ alerts: AlertRow[] }>("/alerts").then((r) => setRows(r.alerts));

  useEffect(() => {
    load().catch(() => {});
  }, []);

  async function ack(id: number) {
    try {
      await apiPostJson(`/alerts/${id}/ack`, {});
      await load();
    } catch (ex) {
      alert(ex instanceof Error ? ex.message : "Failed");
    }
  }

  const canAck = user?.role === "Admin" || user?.role === "Investigator";

  return (
    <div className="stack" style={{ paddingTop: "1rem" }}>
      <h1>Security alerts</h1>
      <Card>
        <ul style={{ margin: 0, paddingLeft: "1rem" }}>
          {rows.map((a) => (
            <li key={a.id} style={{ marginBottom: "0.75rem" }}>
              <span style={{ fontWeight: 600 }}>{a.level}</span> — {a.message}
              {canAck && !a.acknowledged && (
                <>
                  {" "}
                  <Button variant="secondary" onClick={() => ack(a.id)}>
                    Acknowledge
                  </Button>
                </>
              )}
            </li>
          ))}
          {!rows.length && <li className="muted">No alerts</li>}
        </ul>
      </Card>
    </div>
  );
}
