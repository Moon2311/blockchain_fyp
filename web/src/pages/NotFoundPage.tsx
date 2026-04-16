import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="container-narrow" style={{ paddingTop: "3rem" }}>
      <h1>Page not found</h1>
      <p className="muted">
        <Link to="/dashboard">Back to dashboard</Link>
      </p>
    </div>
  );
}
