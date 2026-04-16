import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";

export function AdminRoute() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="container-narrow" style={{ paddingTop: "3rem" }}>
        <p className="muted">Loading…</p>
      </div>
    );
  }

  if (!user || user.role !== "Admin") {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
}
