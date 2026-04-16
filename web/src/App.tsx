import { Navigate, Route, Routes } from "react-router-dom";
import { AdminRoute } from "./components/auth/AdminRoute";
import { AppShell } from "./components/layout/AppShell";
import { useAuth } from "./hooks/useAuth";
import { AdminAssignPage } from "./pages/AdminAssignPage";
import { AdminAuditPage } from "./pages/AdminAuditPage";
import { AdminHomePage } from "./pages/AdminHomePage";
import { AdminRequestsPage } from "./pages/AdminRequestsPage";
import { AdminUsersPage } from "./pages/AdminUsersPage";
import { AlertsPage } from "./pages/AlertsPage";
import { CaseDetailPage } from "./pages/CaseDetailPage";
import { CaseNewPage } from "./pages/CaseNewPage";
import { CaseReportPage } from "./pages/CaseReportPage";
import { CasesListPage } from "./pages/CasesListPage";
import { DashboardPage } from "./pages/DashboardPage";
import { EvidenceDetailPage } from "./pages/EvidenceDetailPage";
import { EvidenceListPage } from "./pages/EvidenceListPage";
import { EvidenceTimelinePage } from "./pages/EvidenceTimelinePage";
import { HelpIndexPage } from "./pages/HelpIndexPage";
import { HelpTopicPage } from "./pages/HelpTopicPage";
import { LoginPage } from "./pages/LoginPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { RegisterPage } from "./pages/RegisterPage";
import { TransfersPage } from "./pages/TransfersPage";
import { UploadPage } from "./pages/UploadPage";
import { VerifyPage } from "./pages/VerifyPage";

function ProtectedLayout() {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="container-narrow" style={{ paddingTop: "3rem" }}>
        <p className="muted">Loading…</p>
      </div>
    );
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return <AppShell />;
}

function HomeEntry() {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="container-narrow" style={{ paddingTop: "3rem" }}>
        <p className="muted">Loading…</p>
      </div>
    );
  }
  if (user) return <Navigate to="/dashboard" replace />;
  return <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomeEntry />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route element={<ProtectedLayout />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/evidence" element={<EvidenceListPage />} />
        <Route path="/evidence/:evidence_id" element={<EvidenceDetailPage />} />
        <Route
          path="/evidence/:evidence_id/timeline"
          element={<EvidenceTimelinePage />}
        />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/verify" element={<VerifyPage />} />
        <Route path="/cases" element={<CasesListPage />} />
        <Route path="/cases/new" element={<CaseNewPage />} />
        <Route path="/cases/:case_id" element={<CaseDetailPage />} />
        <Route path="/cases/:case_id/report" element={<CaseReportPage />} />
        <Route path="/transfers" element={<TransfersPage />} />
        <Route path="/alerts" element={<AlertsPage />} />
        <Route path="/help" element={<HelpIndexPage />} />
        <Route path="/help/:slug" element={<HelpTopicPage />} />

        <Route path="/admin" element={<AdminRoute />}>
          <Route index element={<AdminHomePage />} />
          <Route path="users" element={<AdminUsersPage />} />
          <Route path="assign" element={<AdminAssignPage />} />
          <Route path="requests" element={<AdminRequestsPage />} />
          <Route path="audit" element={<AdminAuditPage />} />
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
