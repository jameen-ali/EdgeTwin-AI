import React from "react";
import { PageHeader } from "../components/layout/PageHeader";
import { ScenarioControlPanel } from "../components/mlops/ScenarioControlPanel";

export const ScenariosPage: React.FC = () => {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
      <PageHeader
        title="Chaos & Fault Injection Scenarios"
        description="Controlled synthetic failure injection library used to validate edge safety trips, model sensitivity, and digital twin anomaly detection."
      />
      <ScenarioControlPanel />
    </div>
  );
};
