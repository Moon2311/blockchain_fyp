import { useState, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "../components/ui/Button";
import * as api from "../services/api";

export function RegisterPage() {
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState("Member");
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [err, setErr] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    try {
      await api.register({
        email: email.trim().toLowerCase(),
        name: name.trim(),
        role,
        password,
        password2,
      });
      nav("/login", { replace: true });
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : "Registration failed");
    }
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "2rem",
        background:
          "linear-gradient(165deg, var(--color-bg) 0%, #e8ecf2 100%)",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 420,
          background: "var(--color-bg-elevated)",
          padding: "2rem",
          borderRadius: "var(--radius-lg)",
          border: "1px solid var(--color-border)",
          boxShadow: "var(--shadow-md)",
        }}
      >
        <h1 style={{ marginBottom: "0.35rem" }}>Create account</h1>
        <p className="muted" style={{ marginBottom: "1.25rem" }}>
          Investigator or Member (Admin is created on first backend start)
        </p>
        {err && (
          <p style={{ color: "var(--color-danger)", fontSize: "0.9rem" }}>{err}</p>
        )}
        <form onSubmit={onSubmit} className="stack">
          <Field label="Email">
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={inputStyle}
            />
          </Field>
          <Field label="Display name">
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              style={inputStyle}
            />
          </Field>
          <Field label="Role">
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              style={inputStyle}
            >
              <option value="Investigator">Investigator (Analyst)</option>
              <option value="Member">Member</option>
            </select>
          </Field>
          <Field label="Password">
            <input
              type="password"
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={inputStyle}
            />
          </Field>
          <Field label="Confirm password">
            <input
              type="password"
              minLength={8}
              value={password2}
              onChange={(e) => setPassword2(e.target.value)}
              style={inputStyle}
            />
          </Field>
          <Button variant="primary" type="submit">
            Register
          </Button>
        </form>
        <p style={{ marginTop: "1.25rem" }}>
          <Link to="/login">Back to sign in</Link>
        </p>
      </div>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div>
      <label style={{ display: "block", marginBottom: "0.35rem", fontWeight: 500 }}>
        {label}
      </label>
      {children}
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "0.55rem 0.75rem",
  borderRadius: "var(--radius-md)",
  border: "1px solid var(--color-border-strong)",
  fontFamily: "inherit",
  fontSize: "1rem",
  background: "#fff",
};
