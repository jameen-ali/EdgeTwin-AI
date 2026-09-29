import React from "react";
import { FleetHistoryResponse } from "../../types/history";
import { formatNumber } from "../../utils/formatters";
import { Card } from "../common/Card";
import { StatusBadge } from "../common/StatusBadge";
import { ShieldCheck, AlertTriangle, Cpu, Wrench } from "lucide-react";

export interface FleetAnalyticsSectionProps {
  data: FleetHistoryResponse;
  onSelectMachine: (machineId: string) => void;
}

export const FleetAnalyticsSection: React.FC<FleetAnalyticsSectionProps> = ({
  data,
  onSelectMachine,
}) => {
  const { total_machines, avg_fleet_health, health_distribution, risk_distribution, machine_summaries } = data;

  const totalAlerts = machine_summaries.reduce((acc, m) => acc + m.alert_count, 0);
  const totalMaintenance = machine_summaries.reduce((acc, m) => acc + m.maintenance_count, 0);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
      {/* Fleet KPI Summary Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "var(--space-4)",
        }}
      >
        <Card>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "var(--radius-md)",
                backgroundColor: "rgba(20, 154, 251, 0.12)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--color-accent)",
              }}
            >
              <Cpu size={20} />
            </div>
            <div>
              <div style={{ fontSize: "11px", color: "var(--color-text-muted)", textTransform: "uppercase" }}>
                Total Fleet Assets
              </div>
              <div style={{ fontSize: "20px", fontWeight: 700, color: "var(--color-text-primary)", fontFamily: "var(--font-mono)" }}>
                {total_machines} Machines
              </div>
            </div>
          </div>
        </Card>

        <Card>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "var(--radius-md)",
                backgroundColor: "rgba(19, 239, 149, 0.12)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--color-success)",
              }}
            >
              <ShieldCheck size={20} />
            </div>
            <div>
              <div style={{ fontSize: "11px", color: "var(--color-text-muted)", textTransform: "uppercase" }}>
                Fleet Avg Health
              </div>
              <div style={{ fontSize: "20px", fontWeight: 700, color: "var(--color-text-primary)", fontFamily: "var(--font-mono)" }}>
                {avg_fleet_health !== null ? `${formatNumber(avg_fleet_health, 1)}%` : "—"}
              </div>
            </div>
          </div>
        </Card>

        <Card>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "var(--radius-md)",
                backgroundColor: "rgba(254, 117, 14, 0.12)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--color-warning)",
              }}
            >
              <AlertTriangle size={20} />
            </div>
            <div>
              <div style={{ fontSize: "11px", color: "var(--color-text-muted)", textTransform: "uppercase" }}>
                Incident Alarms in Window
              </div>
              <div style={{ fontSize: "20px", fontWeight: 700, color: "var(--color-text-primary)", fontFamily: "var(--font-mono)" }}>
                {totalAlerts} Alerts
              </div>
            </div>
          </div>
        </Card>

        <Card>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "var(--radius-md)",
                backgroundColor: "rgba(140, 154, 196, 0.12)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--color-accent)",
              }}
            >
              <Wrench size={20} />
            </div>
            <div>
              <div style={{ fontSize: "11px", color: "var(--color-text-muted)", textTransform: "uppercase" }}>
                Maintenance Actions
              </div>
              <div style={{ fontSize: "20px", fontWeight: 700, color: "var(--color-text-primary)", fontFamily: "var(--font-mono)" }}>
                {totalMaintenance} Events
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Distribution Meters */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "var(--space-4)" }}>
        {/* Health Distribution */}
        <div
          style={{
            backgroundColor: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-lg)",
            padding: "var(--space-4)",
          }}
        >
          <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--color-text-primary)", marginBottom: "var(--space-3)" }}>
            Fleet Health Distribution
          </div>
          {/* Progress bar container */}
          <div
            style={{
              height: "12px",
              borderRadius: "var(--radius-sm)",
              backgroundColor: "rgba(255, 255, 255, 0.05)",
              display: "flex",
              overflow: "hidden",
              marginBottom: "var(--space-3)",
            }}
          >
            {total_machines > 0 && (
              <>
                <div style={{ width: `${(health_distribution.healthy / total_machines) * 100}%`, backgroundColor: "var(--color-success)" }} />
                <div style={{ width: `${(health_distribution.warning / total_machines) * 100}%`, backgroundColor: "var(--color-warning)" }} />
                <div style={{ width: `${(health_distribution.critical / total_machines) * 100}%`, backgroundColor: "var(--color-danger)" }} />
                <div style={{ width: `${(health_distribution.offline / total_machines) * 100}%`, backgroundColor: "var(--color-text-muted)" }} />
              </>
            )}
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}>
            <span>Healthy: <strong style={{ color: "var(--color-success)" }}>{health_distribution.healthy}</strong></span>
            <span>Warning: <strong style={{ color: "var(--color-warning)" }}>{health_distribution.warning}</strong></span>
            <span>Critical: <strong style={{ color: "var(--color-danger)" }}>{health_distribution.critical}</strong></span>
            <span>Offline: <strong style={{ color: "var(--color-text-muted)" }}>{health_distribution.offline}</strong></span>
          </div>
        </div>

        {/* Risk Distribution */}
        <div
          style={{
            backgroundColor: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-lg)",
            padding: "var(--space-4)",
          }}
        >
          <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--color-text-primary)", marginBottom: "var(--space-3)" }}>
            Model Failure Risk Bands ($t^*=0.160$)
          </div>
          <div
            style={{
              height: "12px",
              borderRadius: "var(--radius-sm)",
              backgroundColor: "rgba(255, 255, 255, 0.05)",
              display: "flex",
              overflow: "hidden",
              marginBottom: "var(--space-3)",
            }}
          >
            {total_machines > 0 && (
              <>
                <div style={{ width: `${(risk_distribution.low / total_machines) * 100}%`, backgroundColor: "var(--color-success)" }} />
                <div style={{ width: `${(risk_distribution.medium / total_machines) * 100}%`, backgroundColor: "var(--color-accent)" }} />
                <div style={{ width: `${(risk_distribution.high / total_machines) * 100}%`, backgroundColor: "var(--color-warning)" }} />
                <div style={{ width: `${(risk_distribution.critical / total_machines) * 100}%`, backgroundColor: "var(--color-danger)" }} />
              </>
            )}
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}>
            <span>Low: <strong style={{ color: "var(--color-success)" }}>{risk_distribution.low}</strong></span>
            <span>Med: <strong style={{ color: "var(--color-accent)" }}>{risk_distribution.medium}</strong></span>
            <span>High: <strong style={{ color: "var(--color-warning)" }}>{risk_distribution.high}</strong></span>
            <span>Critical: <strong style={{ color: "var(--color-danger)" }}>{risk_distribution.critical}</strong></span>
          </div>
        </div>
      </div>

      {/* Machine Summaries Table */}
      <div
        style={{
          backgroundColor: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-lg)",
          padding: "var(--space-4) var(--space-5)",
        }}
      >
        <div style={{ fontSize: "14px", fontWeight: 600, color: "var(--color-text-primary)", marginBottom: "var(--space-3)" }}>
          Machine Operational Performance Retrospective
        </div>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--color-border)", textAlign: "left", color: "var(--color-text-muted)" }}>
                <th style={{ padding: "8px 12px", fontWeight: 500 }}>Machine Asset</th>
                <th style={{ padding: "8px 12px", fontWeight: 500 }}>Type</th>
                <th style={{ padding: "8px 12px", fontWeight: 500 }}>Location</th>
                <th style={{ padding: "8px 12px", fontWeight: 500 }}>State</th>
                <th style={{ padding: "8px 12px", fontWeight: 500 }}>Health Index</th>
                <th style={{ padding: "8px 12px", fontWeight: 500 }}>Failure Risk p(fail)</th>
                <th style={{ padding: "8px 12px", fontWeight: 500 }}>Alarms in Window</th>
                <th style={{ padding: "8px 12px", fontWeight: 500 }}>Maintenance</th>
                <th style={{ padding: "8px 12px", fontWeight: 500 }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {machine_summaries.map((m) => (
                <tr key={m.machine_id} style={{ borderBottom: "1px solid rgba(255, 255, 255, 0.04)" }}>
                  <td style={{ padding: "10px 12px", fontWeight: 600, color: "var(--color-accent)" }}>
                    {m.machine_id}
                  </td>
                  <td style={{ padding: "10px 12px", color: "var(--color-text-secondary)" }}>
                    {m.machine_type}
                  </td>
                  <td style={{ padding: "10px 12px", color: "var(--color-text-muted)" }}>
                    {m.location || "Plant Floor"}
                  </td>
                  <td style={{ padding: "10px 12px" }}>
                    <StatusBadge
                      status={m.operating_state}
                      size="sm"
                    />
                  </td>
                  <td style={{ padding: "10px 12px", fontFamily: "var(--font-mono)" }}>
                    {m.health_score !== null ? (
                      <span
                        style={{
                          fontWeight: 700,
                          color:
                            m.health_score >= 80
                              ? "var(--color-success)"
                              : m.health_score >= 60
                              ? "var(--color-warning)"
                              : "var(--color-danger)",
                        }}
                      >
                        {formatNumber(m.health_score, 1)}%
                      </span>
                    ) : (
                      <span style={{ color: "var(--color-text-muted)" }}>—</span>
                    )}
                  </td>
                  <td style={{ padding: "10px 12px", fontFamily: "var(--font-mono)" }}>
                    {m.failure_probability !== null ? (
                      <span
                        style={{
                          fontWeight: 600,
                          color: m.failure_probability >= 0.16 ? "var(--color-danger)" : "var(--color-text-secondary)",
                        }}
                      >
                        {(m.failure_probability * 100).toFixed(1)}%
                      </span>
                    ) : (
                      <span style={{ color: "var(--color-text-muted)" }}>—</span>
                    )}
                  </td>
                  <td style={{ padding: "10px 12px", fontFamily: "var(--font-mono)" }}>
                    {m.alert_count > 0 ? (
                      <span style={{ color: "var(--color-warning)", fontWeight: 600 }}>
                        {m.alert_count} alert{m.alert_count > 1 ? "s" : ""}
                      </span>
                    ) : (
                      <span style={{ color: "var(--color-text-muted)" }}>0</span>
                    )}
                  </td>
                  <td style={{ padding: "10px 12px", fontFamily: "var(--font-mono)" }}>
                    {m.maintenance_count > 0 ? (
                      <span style={{ color: "var(--color-accent)", fontWeight: 600 }}>
                        {m.maintenance_count}
                      </span>
                    ) : (
                      <span style={{ color: "var(--color-text-muted)" }}>0</span>
                    )}
                  </td>
                  <td style={{ padding: "10px 12px" }}>
                    <button
                      type="button"
                      onClick={() => onSelectMachine(m.machine_id)}
                      style={{
                        padding: "3px 8px",
                        borderRadius: "var(--radius-sm)",
                        border: "1px solid var(--color-border)",
                        backgroundColor: "var(--color-surface-hover)",
                        color: "var(--color-accent)",
                        fontSize: "11px",
                        cursor: "pointer",
                      }}
                    >
                      View History →
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
