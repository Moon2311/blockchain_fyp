import { useEffect, useState } from "react";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { apiGet, apiPostJson } from "../services/api";

export function AdminUsersPage() {
  const [users, setUsers] = useState<Record<string, { name: string; role: string }>>(
    {}
  );
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState("Member");

  const load = () =>
    apiGet<{ users: Record<string, { name: string; role: string }> }>(
      "/admin/summary"
    ).then((r) => setUsers(r.users));

  useEffect(() => {
    load().catch(() => {});
  }, []);

  async function addUser(e: React.FormEvent) {
    e.preventDefault();
    try {
      await apiPostJson("/admin/users", { email, password, name, role });
      setEmail("");
      setPassword("");
      setName("");
      await load();
    } catch (ex) {
      alert(ex instanceof Error ? ex.message : "Failed");
    }
  }

  return (
    <div className="stack" style={{ paddingTop: "1rem" }}>
      <h1>Users</h1>
      <Card title="Accounts">
        <table style={{ width: "100%", fontSize: "0.9rem" }}>
          <thead>
            <tr style={{ textAlign: "left" }}>
              <th>Email</th>
              <th>Name</th>
              <th>Role</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(users).map(([em, d]) => (
              <tr key={em}>
                <td>{em}</td>
                <td>{d.name}</td>
                <td>{d.role}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      <Card title="Add user">
        <form onSubmit={addUser} className="stack">
          <input
            placeholder="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            style={{ padding: "0.45rem" }}
          />
          <input
            placeholder="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={{ padding: "0.45rem" }}
          />
          <input
            placeholder="display name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            style={{ padding: "0.45rem" }}
          />
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            style={{ padding: "0.45rem", maxWidth: 200 }}
          >
            <option value="Member">Member</option>
            <option value="Investigator">Investigator</option>
            <option value="Admin">Admin</option>
          </select>
          <Button type="submit">Add</Button>
        </form>
      </Card>
    </div>
  );
}
