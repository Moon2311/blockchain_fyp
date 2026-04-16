import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import * as api from "../../services/api";

const navLinkStyle = ({ isActive }: { isActive: boolean }) => ({
  padding: "0.45rem 0.75rem",
  borderRadius: "var(--radius-sm)",
  color: isActive ? "var(--color-primary)" : "var(--color-text-muted)",
  fontWeight: isActive ? 600 : 500,
  background: isActive ? "var(--color-primary-soft)" : "transparent",
  textDecoration: "none",
});

export function AppShell() {
  const { user, setUser } = useAuth();

  async function handleLogout() {
    await api.logout();
    setUser(null);
  }

  if (!user) return <Outlet />;

  const role = user.role;

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <header
        style={{
          height: "var(--nav-height)",
          borderBottom: "1px solid var(--color-border)",
          background: "var(--color-bg-elevated)",
          display: "flex",
          alignItems: "center",
          padding: "0 1.25rem",
          gap: "1rem",
          position: "sticky",
          top: 0,
          zIndex: 10,
          boxShadow: "var(--shadow-sm)",
        }}
      >
        <Link
          to="/dashboard"
          style={{
            fontWeight: 700,
            color: "var(--color-text)",
            textDecoration: "none",
            marginRight: "0.5rem",
          }}
        >
          ChainCustody
        </Link>
        <nav style={{ display: "flex", flexWrap: "wrap", gap: "0.15rem", flex: 1 }}>
          <NavLink to="/dashboard" style={navLinkStyle}>
            Dashboard
          </NavLink>
          <NavLink to="/evidence" style={navLinkStyle}>
            Evidence
          </NavLink>
          {(role === "Admin" || role === "Investigator") && (
            <NavLink to="/upload" style={navLinkStyle}>
              Upload
            </NavLink>
          )}
          <NavLink to="/cases" style={navLinkStyle}>
            Cases
          </NavLink>
          <NavLink to="/transfers" style={navLinkStyle}>
            Transfers
          </NavLink>
          <NavLink to="/alerts" style={navLinkStyle}>
            Alerts
          </NavLink>
          <NavLink to="/verify" style={navLinkStyle}>
            Verify
          </NavLink>
          <NavLink to="/help" style={navLinkStyle}>
            Help
          </NavLink>
          {role === "Admin" && (
            <NavLink to="/admin" style={navLinkStyle}>
              Admin
            </NavLink>
          )}
        </nav>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.75rem",
            fontSize: "0.88rem",
            color: "var(--color-text-muted)",
          }}
        >
          <span
            style={{
              padding: "0.2rem 0.5rem",
              borderRadius: "var(--radius-sm)",
              background: "var(--color-surface)",
              border: "1px solid var(--color-border)",
            }}
          >
            {user.role}
          </span>
          <span>{user.name}</span>
          <button
            type="button"
            onClick={handleLogout}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--color-danger)",
              cursor: "pointer",
              fontWeight: 600,
            }}
          >
            Log out
          </button>
        </div>
      </header>
      <main style={{ flex: 1 }}>
        <div className="container-narrow">
          <Outlet />
        </div>
      </main>
      <footer
        style={{
          padding: "1rem 1.5rem",
          borderTop: "1px solid var(--color-border)",
          fontSize: "0.82rem",
          color: "var(--color-text-subtle)",
          textAlign: "center",
          background: "var(--color-bg-elevated)",
        }}
      >
        Blockchain Chain of Custody — FYP · M. Talha · fa-2022/BS/DFCS/075
      </footer>
    </div>
  );
}
