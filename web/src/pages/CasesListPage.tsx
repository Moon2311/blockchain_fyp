import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Card } from "../components/ui/Card";
import { useAuth } from "../hooks/useAuth";
import { apiGet } from "../services/api";

type CaseRow = {
  id: number;
  case_number: string;
  title: string;
  created_by: string;
  created_at: string | null;
};

export function CasesListPage() {
  const { user } = useAuth();
  const [cases, setCases] = useState<CaseRow[]>([]);
  const canCreate =
    user?.role === "Admin" || user?.role === "Investigator";

  useEffect(() => {
    apiGet<{ cases: CaseRow[] }>("/cases").then((r) => setCases(r.cases));
  }, []);

  return (
    <div className="stack" style={{ paddingTop: "1rem" }}>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1 style={{ margin: 0 }}>Cases</h1>
        {canCreate && (
          <Link to="/cases/new" style={{ fontWeight: 600 }}>
            + New case
          </Link>
        )}
      </div>
      <Card>
        <ul style={{ margin: 0, paddingLeft: "1.2rem" }}>
          {cases.map((c) => (
            <li key={c.id} style={{ marginBottom: "0.5rem" }}>
              <Link to={`/cases/${c.id}`}>
                <strong>{c.case_number}</strong> — {c.title}
              </Link>
              <span className="muted" style={{ marginLeft: "0.5rem" }}>
                {c.created_by}
              </span>
            </li>
          ))}
          {!cases.length && <li className="muted">No cases yet</li>}
        </ul>
      </Card>
    </div>
  );
}
