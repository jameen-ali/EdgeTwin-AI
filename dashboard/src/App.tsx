import React from "react";
import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./hooks/useAuth";
import { AppShell } from "./components/layout/AppShell";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { MachinesPage } from "./pages/MachinesPage";
import { AlertsPage } from "./pages/AlertsPage";
import { MaintenancePage } from "./pages/MaintenancePage";
import { ScenariosPage } from "./pages/ScenariosPage";
import { MLOpsPage } from "./pages/MLOpsPage";
import { SettingsPage } from "./pages/SettingsPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { LoadingState } from "./components/common/LoadingState";

export const ProtectedRoute: React.FC<{ children: React.ReactElement }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "var(--color-canvas)",
        }}
      >
        <LoadingState message="Verifying security credentials..." size={32} />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
};

export const App: React.FC = () => {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="machines" element={<MachinesPage />} />
        <Route path="alerts" element={<AlertsPage />} />
        <Route path="maintenance" element={<MaintenancePage />} />
        <Route path="scenarios" element={<ScenariosPage />} />
        <Route path="mlops" element={<MLOpsPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
};
