import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  Activity,
  AlertOctagon,
  AlertTriangle,
  CheckCircle2,
  Database,
  GitBranch,
  Info,
  RefreshCw,
  Search,
  ShieldAlert,
  Sliders,
} from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/common/Card";
import { DataTable, Column } from "../components/common/DataTable";
import { MetricGrid } from "../components/common/MetricGrid";
import { Metric } from "../components/common/Metric";
import { LoadingState } from "../components/common/LoadingState";
import { ErrorState } from "../components/common/ErrorState";
import { EmptyState } from "../components/common/EmptyState";
import { Button } from "../components/common/Button";
import { api } from "../api/client";
import { FeatureDrift, MLOpsOverview } from "../types/mlops";
import { formatDateTime } from "../utils/formatters";
import { ModelLifecyclePanel } from "../components/mlops/ModelLifecyclePanel";
import { ScenarioControlPanel } from "../components/mlops/ScenarioControlPanel";

export const MLOpsPage: React.FC = () => {
  const [overview, setOverview] = useState<MLOpsOverview | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filter controls
  const [activeTab, setActiveTab] = useState<"drift" | "lifecycle" | "scenarios">("drift");
  const [windowHours, setWindowHours] = useState<number>(24);
  const [feedbackWindowDays, setFeedbackWindowDays] = useState<number | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [searchFeature, setSearchFeature] = useState<string>("");

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.mlops.getOverview({
        window_hours: windowHours,
        window_days: feedbackWindowDays || undefined,
      });
      setOverview(data);
    } catch (err: any) {
      setError(err?.message || "Failed to load MLOps monitoring overview.");
    } finally {
      setIsLoading(false);
    }
  }, [windowHours, feedbackWindowDays]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Filtered feature list
  const filteredFeatures = useMemo(() => {
    if (!overview?.drift?.features) return [];
    return overview.drift.features.filter((f) => {
      // Status filter
      if (statusFilter !== "ALL" && f.status !== statusFilter) {
        return false;
      }
      // Search query filter
      if (
        searchFeature.trim() &&
        !f.feature_name.toLowerCase().includes(searchFeature.toLowerCase())
      ) {
        return false;
      }
      return true;
    });
  }, [overview, statusFilter, searchFeature]);

  // Status badge helper
  const renderStatusBadge = (status: string) => {
    switch (status) {
      case "STABLE":
        return (
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "4px",
              padding: "2px 8px",
              borderRadius: "var(--radius-sm)",
              fontSize: "11px",
              fontWeight: 600,
              backgroundColor: "rgba(19, 239, 149, 0.12)",
              color: "var(--color-success)",
              border: "1px solid rgba(19, 239, 149, 0.25)",
            }}
          >
            ● STABLE
          </span>
        );
      case "WATCH":
        return (
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "4px",
              padding: "2px 8px",
              borderRadius: "var(--radius-sm)",
              fontSize: "11px",
              fontWeight: 600,
              backgroundColor: "rgba(254, 117, 14, 0.12)",
              color: "var(--color-warning)",
              border: "1px solid rgba(254, 117, 14, 0.25)",
            }}
          >
            ▲ WATCH
          </span>
        );
      case "DRIFT":
        return (
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "4px",
              padding: "2px 8px",
              borderRadius: "var(--radius-sm)",
              fontSize: "11px",
              fontWeight: 600,
              backgroundColor: "rgba(239, 68, 68, 0.12)",
              color: "var(--color-danger)",
              border: "1px solid rgba(239, 68, 68, 0.25)",
            }}
          >
            ■ DRIFT
          </span>
        );
      default:
        return (
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "4px",
              padding: "2px 8px",
              borderRadius: "var(--radius-sm)",
              fontSize: "11px",
              fontWeight: 600,
              backgroundColor: "rgba(113, 113, 122, 0.15)",
              color: "var(--color-text-muted)",
              border: "1px solid rgba(113, 113, 122, 0.25)",
            }}
          >
            ○ INSUFFICIENT
          </span>
        );
    }
  };

  const featureColumns: Column<FeatureDrift>[] = [
    {
      key: "feature_name",
      header: "Feature",
      render: (feat: FeatureDrift) => (
        <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
          <span style={{ fontWeight: 600, color: "var(--color-text-primary)" }}>
            {feat.feature_name}
          </span>
          <span
            style={{
              fontSize: "11px",
              fontFamily: "var(--font-mono)",
              color: feat.feature_type === "categorical" ? "var(--color-accent)" : "var(--color-text-muted)",
            }}
          >
            {feat.feature_type}
          </span>
        </div>
      ),
    },
    {
      key: "psi",
      header: "PSI",
      render: (feat: FeatureDrift) => {
        if (feat.psi === null || feat.psi === undefined) return <span style={{ color: "var(--color-text-muted)" }}>—</span>;
        let color = "var(--color-success)";
        if (feat.psi >= 0.25) color = "var(--color-danger)";
        else if (feat.psi >= 0.10) color = "var(--color-warning)";
        return (
          <span style={{ fontFamily: "var(--font-mono)", fontWeight: 600, color }}>
            {feat.psi.toFixed(4)}
          </span>
        );
      },
    },
    {
      key: "ks_statistic",
      header: "KS Stat (D)",
      render: (feat: FeatureDrift) => {
        if (feat.feature_type === "categorical") {
          return <span style={{ color: "var(--color-text-muted)", fontSize: "12px" }}>N/A (Categorical)</span>;
        }
        if (feat.ks_statistic === null || feat.ks_statistic === undefined) {
          return <span style={{ color: "var(--color-text-muted)" }}>—</span>;
        }
        let color = "var(--color-text-primary)";
        if (feat.ks_statistic >= 0.15) color = "var(--color-danger)";
        else if (feat.ks_statistic >= 0.08) color = "var(--color-warning)";
        return (
          <span style={{ fontFamily: "var(--font-mono)", fontWeight: 500, color }}>
            {feat.ks_statistic.toFixed(4)}
          </span>
        );
      },
    },
    {
      key: "ks_p_value",
      header: "KS p-value",
      render: (feat: FeatureDrift) => {
        if (feat.feature_type === "categorical") {
          return <span style={{ color: "var(--color-text-muted)", fontSize: "12px" }}>N/A</span>;
        }
        if (feat.ks_p_value === null || feat.ks_p_value === undefined) {
          return <span style={{ color: "var(--color-text-muted)" }}>—</span>;
        }
        const color = feat.ks_p_value < 0.05 ? "var(--color-warning)" : "var(--color-text-secondary)";
        return (
          <span style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color }}>
            {feat.ks_p_value < 0.0001 ? "<0.0001" : feat.ks_p_value.toFixed(4)}
          </span>
        );
      },
    },
    {
      key: "missing_pct",
      header: "Missing Rate",
      render: (feat: FeatureDrift) => (
        <span style={{ fontSize: "12px", fontFamily: "var(--font-mono)", color: "var(--color-text-secondary)" }}>
          Ref: {feat.missing_reference_pct.toFixed(1)}% | Curr: {feat.missing_current_pct.toFixed(1)}%
        </span>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (feat: FeatureDrift) => renderStatusBadge(feat.status),
    },
    {
      key: "message",
      header: "Diagnostic Summary",
      render: (feat: FeatureDrift) => (
        <span style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
          {feat.message}
        </span>
      ),
    },
  ];

  if (isLoading && !overview) {
    return <LoadingState message="Computing feature drift statistics (PSI / KS) and feedback metrics..." />;
  }

  if (error && !overview) {
    return <ErrorState message={error} onRetry={fetchData} />;
  }

  const drift = overview?.drift;
  const perf = overview?.performance;

  // Map overall status to metric visual status
  let overallStatusColor: "success" | "warning" | "danger" | "normal" = "normal";
  if (drift?.overall_status === "STABLE") overallStatusColor = "success";
  else if (drift?.overall_status === "WATCH") overallStatusColor = "warning";
  else if (drift?.overall_status === "DRIFT") overallStatusColor = "danger";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
      {/* Page Header with Model Metadata & Controls */}
      <PageHeader
        title="MLOps & Model Monitoring"
        description="Feature distribution drift (PSI / KS) vs training baseline and feedback-based operational validation."
        actions={
          <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "center" }}>
            <select
              value={windowHours}
              onChange={(e) => setWindowHours(Number(e.target.value))}
              aria-label="Telemetry Window"
              style={{
                padding: "8px 12px",
                borderRadius: "var(--radius-sm)",
                backgroundColor: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                color: "var(--color-text-primary)",
                fontSize: "13px",
                fontFamily: "var(--font-sans)",
              }}
            >
              <option value={6}>Past 6 Hours</option>
              <option value={24}>Past 24 Hours</option>
              <option value={72}>Past 72 Hours (3d)</option>
              <option value={168}>Past 7 Days</option>
            </select>
            <Button
              variant="secondary"
              size="sm"
              leftIcon={<RefreshCw size={14} />}
              onClick={fetchData}
              disabled={isLoading}
            >
              Refresh
            </Button>
          </div>
        }
      />

      {/* Sub-tab Navigation */}
      <div
        style={{
          display: "flex",
          gap: "var(--space-2)",
          borderBottom: "1px solid var(--color-border)",
          paddingBottom: "var(--space-2)",
        }}
      >
        <button
          type="button"
          onClick={() => setActiveTab("drift")}
          style={{
            padding: "8px 16px",
            borderRadius: "var(--radius-sm)",
            border: "none",
            backgroundColor: activeTab === "drift" ? "var(--color-surface-raised)" : "transparent",
            color: activeTab === "drift" ? "var(--color-accent)" : "var(--color-text-secondary)",
            fontWeight: 600,
            fontSize: "13px",
            cursor: "pointer",
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
          }}
        >
          <Activity size={15} />
          Drift & Performance Monitoring
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("lifecycle")}
          style={{
            padding: "8px 16px",
            borderRadius: "var(--radius-sm)",
            border: "none",
            backgroundColor: activeTab === "lifecycle" ? "var(--color-surface-raised)" : "transparent",
            color: activeTab === "lifecycle" ? "var(--color-accent)" : "var(--color-text-secondary)",
            fontWeight: 600,
            fontSize: "13px",
            cursor: "pointer",
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
          }}
        >
          <GitBranch size={15} />
          Model Lifecycle & Governance
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("scenarios")}
          style={{
            padding: "8px 16px",
            borderRadius: "var(--radius-sm)",
            border: "none",
            backgroundColor: activeTab === "scenarios" ? "var(--color-surface-raised)" : "transparent",
            color: activeTab === "scenarios" ? "var(--color-accent)" : "var(--color-text-secondary)",
            fontWeight: 600,
            fontSize: "13px",
            cursor: "pointer",
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
          }}
        >
          <Sliders size={15} />
          Scenario Control
        </button>
      </div>

      {activeTab === "lifecycle" ? (
        <ModelLifecyclePanel />
      ) : activeTab === "scenarios" ? (
        <ScenarioControlPanel />
      ) : (
        <>
      {/* Model & Reference Governance Banner */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: "var(--space-4)",
          padding: "var(--space-3) var(--space-4)",
          backgroundColor: "var(--color-surface-raised)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-md)",
          fontSize: "12px",
          color: "var(--color-text-secondary)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <GitBranch size={15} color="var(--color-accent)" />
          <span>Champion Model:</span>
          <span style={{ fontWeight: 600, color: "var(--color-text-primary)" }}>
            {overview?.model_version || "v1.2-xgb"}
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <Database size={15} color="var(--color-accent)" />
          <span>Training Baseline:</span>
          <span style={{ fontWeight: 600, color: "var(--color-text-primary)" }}>
            {drift?.reference_version || "v1.0-train-split"} ({drift?.reference_sample_count || 6897} samples, 42 machines)
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <ShieldAlert size={15} color="var(--color-warning)" />
          <span>Decision Cutoff:</span>
          <span style={{ fontWeight: 600, color: "var(--color-text-primary)", fontFamily: "var(--font-mono)" }}>
            t* = {overview?.operational_threshold.toFixed(3) || "0.160"}
          </span>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: "6px", color: "var(--color-text-muted)" }}>
          <Activity size={14} />
          <span>Evaluated: {overview ? formatDateTime(overview.last_evaluated_at) : "—"}</span>
        </div>
      </div>

      {/* Top Level Operational KPIs */}
      <MetricGrid columns={4}>
        <Metric
          label="Overall Drift Status"
          value={drift?.overall_status || "—"}
          unit={`${drift?.drifting_features_count || 0} Drifting | ${drift?.watch_features_count || 0} Watch`}
          status={overallStatusColor}
          icon={<Sliders size={18} />}
        />
        <Metric
          label="Labeled Feedback"
          value={String(perf?.total_feedback || 0)}
          unit={`Conf: ${perf?.confirmed_count || 0} | False: ${perf?.false_alarm_count || 0} | Inc: ${perf?.inconclusive_count || 0}`}
          status="normal"
          icon={<CheckCircle2 size={18} />}
        />
        <Metric
          label="Running Precision"
          value={perf?.precision !== null && perf?.precision !== undefined ? `${(perf.precision * 100).toFixed(1)}%` : "—"}
          unit={perf?.status === "SUFFICIENT" ? "TP / (TP + FP)" : "Insufficient Data"}
          status={perf?.precision && perf.precision >= 0.70 ? "success" : "normal"}
          icon={<CheckCircle2 size={18} />}
        />
        <Metric
          label="False-Alarm Rate"
          value={perf?.false_alarm_rate !== null && perf?.false_alarm_rate !== undefined ? `${(perf.false_alarm_rate * 100).toFixed(1)}%` : "—"}
          unit={perf?.status === "SUFFICIENT" ? "FP / Total Inspections" : "Insufficient Data"}
          status={perf?.false_alarm_rate && perf.false_alarm_rate > 0.30 ? "warning" : "normal"}
          icon={<AlertTriangle size={18} />}
        />
      </MetricGrid>

      {/* Drift Alerts Banner (if any features in DRIFT or WATCH) */}
      {drift?.drift_alerts && drift.drift_alerts.length > 0 && (
        <Card title="Active Model & Feature Drift Alerts" subtitle="Operational distribution shift exceeding project monitoring thresholds">
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)", padding: "var(--space-3)" }}>
            {drift.drift_alerts.map((alert, idx) => (
              <div
                key={idx}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "var(--space-3)",
                  padding: "var(--space-3) var(--space-4)",
                  backgroundColor: alert.severity === "CRITICAL" ? "rgba(239, 68, 68, 0.08)" : "rgba(254, 117, 14, 0.08)",
                  border: `1px solid ${alert.severity === "CRITICAL" ? "rgba(239, 68, 68, 0.3)" : "rgba(254, 117, 14, 0.3)"}`,
                  borderRadius: "var(--radius-md)",
                }}
              >
                {alert.severity === "CRITICAL" ? (
                  <AlertOctagon size={20} color="var(--color-danger)" style={{ flexShrink: 0, marginTop: "2px" }} />
                ) : (
                  <AlertTriangle size={20} color="var(--color-warning)" style={{ flexShrink: 0, marginTop: "2px" }} />
                )}
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                    <span style={{ fontWeight: 600, color: alert.severity === "CRITICAL" ? "var(--color-danger)" : "var(--color-warning)" }}>
                      {alert.feature_name}
                    </span>
                    <span
                      style={{
                        padding: "1px 6px",
                        borderRadius: "var(--radius-sm)",
                        fontSize: "10px",
                        fontWeight: 700,
                        backgroundColor: alert.severity === "CRITICAL" ? "var(--color-danger)" : "var(--color-warning)",
                        color: "#000",
                      }}
                    >
                      {alert.severity}
                    </span>
                    <span style={{ fontSize: "12px", fontFamily: "var(--font-mono)", color: "var(--color-text-secondary)" }}>
                      {alert.metric} = {alert.value.toFixed(4)} (Threshold: {alert.threshold})
                    </span>
                  </div>
                  <p style={{ margin: 0, fontSize: "13px", color: "var(--color-text-primary)", lineHeight: 1.4 }}>
                    {alert.message}
                  </p>
                  <p style={{ margin: "4px 0 0 0", fontSize: "12px", color: "var(--color-text-muted)" }}>
                    Action: {alert.recommendation}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Feature Drift Monitoring Table */}
      <Card
        title="Feature Distribution Drift Assessment"
        subtitle={`Evaluated across ${drift?.current_sample_count || 0} observations against training reference (${drift?.features.length || 0} features)`}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          {/* Status Tabs and Search */}
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              justifyContent: "space-between",
              alignItems: "center",
              gap: "var(--space-3)",
              borderBottom: "1px solid var(--color-border)",
              paddingBottom: "var(--space-3)",
            }}
          >
            {/* Status Filter Tabs */}
            <div style={{ display: "flex", gap: "var(--space-1)" }}>
              {[
                { id: "ALL", label: `All (${drift?.features.length || 0})` },
                { id: "DRIFT", label: `Drifting (${drift?.drifting_features_count || 0})` },
                { id: "WATCH", label: `Watch (${drift?.watch_features_count || 0})` },
                { id: "STABLE", label: `Stable (${drift?.stable_features_count || 0})` },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setStatusFilter(tab.id)}
                  style={{
                    padding: "6px 12px",
                    borderRadius: "var(--radius-sm)",
                    border: "none",
                    background: statusFilter === tab.id ? "var(--color-accent)" : "transparent",
                    color: statusFilter === tab.id ? "#000" : "var(--color-text-secondary)",
                    fontWeight: statusFilter === tab.id ? 600 : 400,
                    fontSize: "12px",
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Feature Search */}
            <div style={{ position: "relative", width: "240px" }}>
              <Search
                size={14}
                style={{
                  position: "absolute",
                  left: "10px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  color: "var(--color-text-muted)",
                }}
              />
              <input
                type="text"
                placeholder="Search features..."
                value={searchFeature}
                onChange={(e) => setSearchFeature(e.target.value)}
                style={{
                  width: "100%",
                  padding: "6px 10px 6px 32px",
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: "var(--color-surface)",
                  border: "1px solid var(--color-border)",
                  color: "var(--color-text-primary)",
                  fontSize: "12px",
                }}
              />
            </div>
          </div>

          {/* Features Table */}
          {filteredFeatures.length === 0 ? (
            <EmptyState
              title="No Monitored Features Match Filter"
              description="Adjust the status filter or search query to inspect feature drift results."
            />
          ) : (
            <DataTable<FeatureDrift>
              columns={featureColumns}
              data={filteredFeatures}
              keyExtractor={(feat) => feat.feature_name}
            />
          )}

          {/* Reference Baseline Footnote */}
          <div
            style={{
              padding: "var(--space-3)",
              backgroundColor: "rgba(20, 154, 251, 0.04)",
              border: "1px solid rgba(20, 154, 251, 0.15)",
              borderRadius: "var(--radius-sm)",
              fontSize: "12px",
              color: "var(--color-text-secondary)",
              lineHeight: 1.5,
            }}
          >
            <strong>Statistical Methodology:</strong> Continuous features use decile quantile binning (10 bins) derived
            exclusively from <code>train.csv</code> for Population Stability Index (PSI) and two-sample Kolmogorov-Smirnov
            (KS) tests. Categorical features evaluate category frequency shift via categorical PSI. Operational heuristics:
            PSI &lt; 0.10 (STABLE), 0.10 ≤ PSI &lt; 0.25 (WATCH), PSI ≥ 0.25 (DRIFT).
          </div>
        </div>
      </Card>

      {/* Operator Feedback & Model Performance Section */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: "var(--space-4)" }}>
        {/* Field Verification Performance Card */}
        <Card
          title="Field Ground-Truth Performance"
          subtitle="Observed outcomes recorded by technicians following alert triage"
          action={
            <div style={{ display: "flex", gap: "4px" }}>
              {[
                { label: "All Time", days: null },
                { label: "30 Days", days: 30 },
                { label: "7 Days", days: 7 },
              ].map((opt, i) => (
                <button
                  key={i}
                  onClick={() => setFeedbackWindowDays(opt.days)}
                  style={{
                    padding: "4px 8px",
                    borderRadius: "var(--radius-sm)",
                    border: "none",
                    background: feedbackWindowDays === opt.days ? "var(--color-accent)" : "rgba(255,255,255,0.06)",
                    color: feedbackWindowDays === opt.days ? "#000" : "var(--color-text-secondary)",
                    fontSize: "11px",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          }
        >
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)", padding: "var(--space-2)" }}>
            {/* Feedback Breakdown Progress Bar */}
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "6px" }}>
                <span>Submissions Breakdown</span>
                <span style={{ color: "var(--color-text-muted)" }}>Total: {perf?.total_feedback || 0}</span>
              </div>
              {perf && perf.total_feedback > 0 ? (
                <div
                  style={{
                    display: "flex",
                    height: "8px",
                    borderRadius: "4px",
                    overflow: "hidden",
                    backgroundColor: "var(--color-surface-raised)",
                  }}
                >
                  <div
                    style={{
                      width: `${(perf.confirmed_count / perf.total_feedback) * 100}%`,
                      backgroundColor: "var(--color-success)",
                    }}
                    title={`Confirmed: ${perf.confirmed_count}`}
                  />
                  <div
                    style={{
                      width: `${(perf.false_alarm_count / perf.total_feedback) * 100}%`,
                      backgroundColor: "var(--color-warning)",
                    }}
                    title={`False Alarm: ${perf.false_alarm_count}`}
                  />
                  <div
                    style={{
                      width: `${(perf.inconclusive_count / perf.total_feedback) * 100}%`,
                      backgroundColor: "var(--color-text-muted)",
                    }}
                    title={`Inconclusive: ${perf.inconclusive_count}`}
                  />
                </div>
              ) : (
                <div
                  style={{
                    height: "8px",
                    borderRadius: "4px",
                    backgroundColor: "rgba(255,255,255,0.05)",
                  }}
                />
              )}

              <div style={{ display: "flex", gap: "var(--space-4)", marginTop: "8px", fontSize: "12px" }}>
                <span style={{ color: "var(--color-success)" }}>
                  ● Confirmed (TP): {perf?.confirmed_count || 0}
                </span>
                <span style={{ color: "var(--color-warning)" }}>
                  ▲ False Alarms (FP): {perf?.false_alarm_count || 0}
                </span>
                <span style={{ color: "var(--color-text-muted)" }}>
                  ○ Inconclusive: {perf?.inconclusive_count || 0}
                </span>
              </div>
            </div>

            {/* Evaluation Metrics */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr 1fr",
                gap: "var(--space-3)",
                padding: "var(--space-3)",
                backgroundColor: "var(--color-surface)",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-border)",
              }}
            >
              <div>
                <span style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>Precision</span>
                <div style={{ fontSize: "18px", fontWeight: 700, color: "var(--color-text-primary)", fontFamily: "var(--font-mono)" }}>
                  {perf?.precision !== null && perf?.precision !== undefined ? `${(perf.precision * 100).toFixed(1)}%` : "—"}
                </div>
                <span style={{ fontSize: "10px", color: "var(--color-text-muted)" }}>TP / (TP + FP)</span>
              </div>
              <div>
                <span style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>Recall (Field)</span>
                <div style={{ fontSize: "18px", fontWeight: 700, color: "var(--color-text-primary)", fontFamily: "var(--font-mono)" }}>
                  {perf?.recall !== null && perf?.recall !== undefined ? `${(perf.recall * 100).toFixed(1)}%` : "—"}
                </div>
                <span style={{ fontSize: "10px", color: "var(--color-text-muted)" }}>TP / (TP + FN)</span>
              </div>
              <div>
                <span style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>False Alarm Rate</span>
                <div style={{ fontSize: "18px", fontWeight: 700, color: "var(--color-text-primary)", fontFamily: "var(--font-mono)" }}>
                  {perf?.false_alarm_rate !== null && perf?.false_alarm_rate !== undefined ? `${(perf.false_alarm_rate * 100).toFixed(1)}%` : "—"}
                </div>
                <span style={{ fontSize: "10px", color: "var(--color-text-muted)" }}>FP / Total</span>
              </div>
            </div>

            <p style={{ margin: 0, fontSize: "12px", color: "var(--color-text-secondary)", lineHeight: 1.4 }}>
              {perf?.note}
            </p>
          </div>
        </Card>

        {/* Scientific Governance & Non-Retraining Policy Card */}
        <Card title="MLOps Governance & Invariant Policies" subtitle="Operational safeguards preserving model stability">
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)", padding: "var(--space-2)", fontSize: "13px", color: "var(--color-text-secondary)", lineHeight: 1.5 }}>
            <div style={{ display: "flex", gap: "8px", alignItems: "flex-start" }}>
              <Info size={16} color="var(--color-accent)" style={{ flexShrink: 0, marginTop: "2px" }} />
              <p style={{ margin: 0 }}>
                <strong>Monitoring vs Retraining:</strong> Session S23 strictly observes distribution drift and
                records field outcomes. <strong>Automatic retraining is forbidden</strong> to prevent feedback loops
                and unverified model parameter changes in production.
              </p>
            </div>

            <div style={{ display: "flex", gap: "8px", alignItems: "flex-start" }}>
              <AlertTriangle size={16} color="var(--color-warning)" style={{ flexShrink: 0, marginTop: "2px" }} />
              <p style={{ margin: 0 }}>
                <strong>Drift Does Not Equal Failure:</strong> Statistical drift (PSI / KS) measures physical
                or seasonal operating state shifts. It serves as an investigative warning signal and must not be
                conflated with immediate machine degradation or component failure.
              </p>
            </div>

            <div style={{ display: "flex", gap: "8px", alignItems: "flex-start" }}>
              <CheckCircle2 size={16} color="var(--color-success)" style={{ flexShrink: 0, marginTop: "2px" }} />
              <p style={{ margin: 0 }}>
                <strong>Frozen Invariants:</strong> XGBoost champion <code>v1.2-xgb</code>, Platt sigmoid calibration,
                cost-optimized cutoff <code>t* = 0.160</code>, and Layer 4 Health Score composite formulas remain 100% frozen.
              </p>
            </div>
          </div>
        </Card>
      </div>
      </>
      )}
    </div>
  );
};
