import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { api, clearToken, isAuthenticated } from "./api/client";
import AdminDataSourcesPage from "./pages/AdminDataSourcesPage";
import AdminTrainingExportPage from "./pages/AdminTrainingExportPage";
import AdminTrainingSampleDetailPage from "./pages/AdminTrainingSampleDetailPage";
import AdminTrainingSamplesPage from "./pages/AdminTrainingSamplesPage";
import DashboardPage from "./pages/DashboardPage";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import NewReviewPage from "./pages/NewReviewPage";
import ReviewHistoryPage from "./pages/ReviewHistoryPage";
import ReviewResultPage from "./pages/ReviewResultPage";
import SignupPage from "./pages/SignupPage";
import TemplatesPage from "./pages/TemplatesPage";

function ProtectedRoute({ children }) {
  const [status, setStatus] = useState(() => (isAuthenticated() ? "checking" : "unauthenticated"));

  useEffect(() => {
    let ignore = false;

    if (!isAuthenticated()) {
      setStatus("unauthenticated");
      return undefined;
    }

    setStatus("checking");
    api
      .me()
      .then(() => {
        if (!ignore) setStatus("authenticated");
      })
      .catch(() => {
        clearToken();
        if (!ignore) setStatus("unauthenticated");
      });

    return () => {
      ignore = true;
    };
  }, []);

  if (status === "checking") {
    return <div className="auth-check-screen">로그인 상태를 확인하고 있습니다...</div>;
  }

  return status === "authenticated" ? children : <Navigate to="/login" replace />;
}

function HomeRoute() {
  return isAuthenticated() ? <Navigate to="/dashboard" replace /> : <LandingPage />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomeRoute />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/reviews/new"
        element={
          <ProtectedRoute>
            <NewReviewPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/reviews/history"
        element={
          <ProtectedRoute>
            <ReviewHistoryPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/reviews/:id"
        element={
          <ProtectedRoute>
            <ReviewResultPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/templates"
        element={
          <ProtectedRoute>
            <TemplatesPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/data-sources"
        element={
          <ProtectedRoute>
            <AdminDataSourcesPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/training-samples"
        element={
          <ProtectedRoute>
            <AdminTrainingSamplesPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/training-samples/:id"
        element={
          <ProtectedRoute>
            <AdminTrainingSampleDetailPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/training-export"
        element={
          <ProtectedRoute>
            <AdminTrainingExportPage />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
