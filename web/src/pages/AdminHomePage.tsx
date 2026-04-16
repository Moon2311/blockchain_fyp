import { Link } from "react-router-dom";
import { Card } from "../components/ui/Card";

export function AdminHomePage() {
  return (
    <div className="stack" style={{ paddingTop: "1rem" }}>
      <h1>Administration</h1>
      <div className="grid-2">
        <Card title="Users">
          <Link to="/admin/users">Manage users & roles →</Link>
        </Card>
        <Card title="Assignments">
          <Link to="/admin/assign">Assign evidence →</Link>
        </Card>
        <Card title="Requests">
          <Link to="/admin/requests">Case access requests →</Link>
        </Card>
        <Card title="Audit trail">
          <Link to="/admin/audit">View uploads, verifications & activity →</Link>
        </Card>
      </div>
    </div>
  );
}
