import { useEffect, useState } from "react";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { apiGet, apiPostJson } from "../services/api";

export function AdminAssignPage() {
  type AssignPayload = {
    cases: Array<{ id: number; case_number: string; title: string }>;
    assignable_emails: string[];
    assignments: Array<Record<string, unknown>>;
  };

  const [data, setData] = useState<AssignPayload | null>(null);
  const [evidenceId, setEvidenceId] = useState("");
  const [assignee, setAssignee] = useState("");
  const [role, setRole] = useState("Investigator");

  const load = () => apiGet<AssignPayload>("/admin/assign").then(setData);

  useEffect(() => {
    load().catch(() => {});
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await apiPostJson("/admin/assign", {
        evidence_id: Number(evidenceId),
        assignee_username: assignee,
        assignee_role: role,
      });
      await load();
    } catch (ex) {
      alert(ex instanceof Error ? ex.message : "Failed");
    }
  }

  if (!data) return <p className="muted">Loading…</p>;

  return (
    <div className="stack" style={{ paddingTop: "1rem" }}>
      <h1>Assign evidence</h1>
      <Card title="New assignment">
        <form onSubmit={submit} className="stack">
          <input
            type="number"
            min={1}
            placeholder="Evidence ID"
            value={evidenceId}
            onChange={(e) => setEvidenceId(e.target.value)}
            required
            style={{ padding: "0.45rem", width: 160 }}
          />
          <select
            value={assignee}
            onChange={(e) => setAssignee(e.target.value)}
            required
            style={{ padding: "0.45rem", maxWidth: 320 }}
          >
            <option value="">User…</option>
            {data.assignable_emails.map((u) => (
              <option key={u} value={u}>
                {u}
              </option>
            ))}
          </select>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            style={{ padding: "0.45rem" }}
          >
            <option value="Investigator">Investigator</option>
            <option value="Viewer">Viewer</option>
            <option value="Member">Member (legacy)</option>
          </select>
          <Button type="submit">Save</Button>
        </form>
      </Card>
      <Card title="Current assignments">
        <table style={{ width: "100%", fontSize: "0.88rem" }}>
          <thead>
            <tr>
              <th>Evidence</th>
              <th>Assignee</th>
              <th>Role</th>
            </tr>
          </thead>
          <tbody>
            {data.assignments.map((a) => (
              <tr key={String(a.id)}>
                <td>#{String(a.evidence_id)}</td>
                <td>{String(a.assignee_username)}</td>
                <td>{String(a.assignee_role)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
