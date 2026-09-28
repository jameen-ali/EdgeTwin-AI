import React from "react";
import { Activity, GitBranch, Database, ShieldAlert } from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/common/Card";
import { MetricGrid } from "../components/common/MetricGrid";
import { Metric } from "../components/common/Metric";

export const MLOpsPage: React.FC = () => {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
      <PageHeader
        title="MLOps & Model Governance"
        description="Champion model tracking, feature drift monitoring (PSI / KS), prediction latency SLAs, and calibration health."
      />

      <MetricGrid columns={4}>
        <Metric
          label="Champion Model"
          value="XGBoost v1"
          unit="calibrated"
          status="success"
          icon={<GitBranch size={18} />}
        />
        <Metric
          label="Decision Cutoff"
          value="0.160"
          unit="t*"
          status="normal"
          icon={<ShieldAlert size={18} />}
        />
        <Metric
          label="Inference Latency"
          value="18.4"
          unit="ms p95"
          status="success"
          icon={<Activity size={18} />}
        />
        <Metric
          label="Registry Status"
          value="Active"
          unit="MLflow"
          status="success"
          icon={<Database size={18} />}
        />
      </MetricGrid>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: "var(--space-4)" }}>
        <Card title="Feature Drift & PSI Monitoring" subtitle="Phase 6 — MLOps Infrastructure (T-060)">
          <div style={{ padding: "var(--space-4)", color: "var(--color-text-secondary)", fontSize: "13px", lineHeight: 1.5 }}>
            <p>
              Automated Population Stability Index (PSI) and Kolmogorov-Smirnov drift statistics will be computed across rolling 24-hour ingestion windows against the baseline training distribution.
            </p>
            <div
              style={{
                marginTop: "var(--space-4)",
                padding: "var(--space-3)",
                backgroundColor: "var(--color-surface-raised)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                fontFamily: "var(--font-mono)",
                fontSize: "12px",
              }}
            >
              Baseline Dataset: data/interim/splits/train.csv (8,000 samples)
              <br />
              Monitoring Metric: PSI &lt; 0.10 (Stable) | KS p-val &gt; 0.05
            </div>
          </div>
        </Card>

        <Card title="Model Calibration & Registry" subtitle="Calibrated failure risk (Isotonic)">
          <div style={{ padding: "var(--space-4)", color: "var(--color-text-secondary)", fontSize: "13px", lineHeight: 1.5 }}>
            <p>
              XGBoost champion model produces calibrated posterior probabilities P(fail | x).
              Calibrated threshold t* = 0.16 yields optimal utility at 10:1 false-negative to false-alarm penalty ratio.
            </p>
            <div
              style={{
                marginTop: "var(--space-4)",
                padding: "var(--space-3)",
                backgroundColor: "var(--color-surface-raised)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                fontFamily: "var(--font-mono)",
                fontSize: "12px",
              }}
            >
              Model Artifact: models/champion_xgboost.pkl
              <br />
              Explainer: TreeSHAP (Interventional, 100 background samples)
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};
