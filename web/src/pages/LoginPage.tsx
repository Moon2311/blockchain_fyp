import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { useAuth } from "../hooks/useAuth";
import * as api from "../services/api";

export function LoginPage() {
  const nav = useNavigate();
  const { user, loading, setUser } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    try {
      const { user } = await api.login(email.trim().toLowerCase(), password);
      setUser(user);
      nav("/dashboard", { replace: true });
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : "Login failed");
    }
  }

  if (loading) {
    return (
      <div className="container-narrow" style={{ paddingTop: "3rem" }}>
        <p className="muted">Loading…</p>
      </div>
    );
  }
  if (user) {
    return <Navigate to="/dashboard" replace />;
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
          maxWidth: 400,
          background: "var(--color-bg-elevated)",
          padding: "2rem",
          borderRadius: "var(--radius-lg)",
          border: "1px solid var(--color-border)",
          boxShadow: "var(--shadow-md)",
        }}
      >
        <h1 style={{ marginBottom: "0.35rem" }}>Sign in</h1>
        <p className="muted" style={{ marginBottom: "1.5rem" }}>
          ChainCustody — digital forensics custody
        </p>
        {err && (
          <p style={{ color: "var(--color-danger)", fontSize: "0.9rem" }}>{err}</p>
        )}
        <form onSubmit={onSubmit} className="stack">
          <div>
            <label
              htmlFor="email"
              style={{ display: "block", marginBottom: "0.35rem", fontWeight: 500 }}
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              style={inputStyle}
            />
          </div>
          <div>
            <label
              htmlFor="pw"
              style={{ display: "block", marginBottom: "0.35rem", fontWeight: 500 }}
            >
              Password
            </label>
            <input
              id="pw"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              style={inputStyle}
            />
          </div>
          <Button variant="primary" type="submit">
            Sign in
          </Button>
        </form>
        <p style={{ marginTop: "1.25rem", fontSize: "0.92rem" }}>
          <Link to="/register">Create an account</Link>
        </p>
      </div>
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
