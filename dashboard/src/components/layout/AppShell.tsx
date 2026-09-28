import React, { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { TopHeader } from "./TopHeader";

const routeTitleMap: Record<string, string> = {
  "/dashboard": "Fleet Dashboard",
  "/machines": "Connected Machines",
  "/alerts": "Alert Management",
  "/maintenance": "Maintenance Schedule",
  "/scenarios": "Fault Injection Scenarios",
  "/mlops": "MLOps & Model Health",
  "/settings": "Platform Settings",
};

export const AppShell: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  const currentTitle = routeTitleMap[location.pathname] || "Operational Console";

  return (
    <div className="app-shell">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="app-main">
        <TopHeader
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
          pageTitle={currentTitle}
        />
        <main className="app-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
