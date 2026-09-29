import React, { useState, useMemo } from "react";
import { HistoricalAlertItem, HistoricalMaintenanceItem } from "../../types/history";
import { StatusBadge } from "../common/StatusBadge";
import { EmptyState } from "../common/EmptyState";
import { AlertTriangle, Wrench, CheckCircle2, Clock } from "lucide-react";

export interface HistoricalEventTimelineProps {
  alerts: HistoricalAlertItem[];
  maintenance: HistoricalMaintenanceItem[];
}

export const HistoricalEventTimeline: React.FC<HistoricalEventTimelineProps> = ({
  alerts,
  maintenance,
}) => {
  const [activeTab, setActiveTab] = useState<"alerts" | "maintenance">("alerts");
  const [alertFilter, setAlertFilter] = useState<"ALL" | "OPEN" | "ACKNOWLEDGED" | "RESOLVED">("ALL");

  const filteredAlerts = useMemo(() => {
    if (alertFilter === "ALL") return alerts;
    return alerts.filter((a) => a.status === alertFilter);
  }, [alerts, alertFilter]);

  return (
    <div
      style={{
        backgroundColor: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius-lg)",
        padding: "var(--space-4) var(--space-5)",
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-4)",
      }}
    >
      {/* Top Header & Sub-tab Switcher */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "var(--space-3)",
          borderBottom: "1px solid var(--color-border)",
          paddingBottom: "var(--space-3)",
        }}
      >
        <div style={{ display: "flex", gap: "var(--space-2)" }}>
          <button
            type="button"
            onClick={() => setActiveTab("alerts")}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "6px 14px",
              borderRadius: "var(--radius-sm)",
              border: "none",
              backgroundColor: activeTab === "alerts" ? "var(--color-surface-hover)" : "transparent",
              color: activeTab === "alerts" ? "var(--color-text-primary)" : "var(--color-text-muted)",
              fontWeight: activeTab === "alerts" ? 600 : 400,
              fontSize: "13px",
              cursor: "pointer",
            }}
          >
            <AlertTriangle size={15} color={activeTab === "alerts" ? "var(--color-warning)" : undefined} />
            Alerts Timeline ({alerts.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("maintenance")}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "6px 14px",
              borderRadius: "var(--radius-sm)",
              border: "none",
              backgroundColor: activeTab === "maintenance" ? "var(--color-surface-hover)" : "transparent",
              color: activeTab === "maintenance" ? "var(--color-text-primary)" : "var(--color-text-muted)",
              fontWeight: activeTab === "maintenance" ? 600 : 400,
              fontSize: "13px",
              cursor: "pointer",
            }}
          >
            <Wrench size={15} color={activeTab === "maintenance" ? "var(--color-accent)" : undefined} />
            Maintenance Activity ({maintenance.length})
          </button>
        </div>

        {/* Filter buttons if alerts tab */}
        {activeTab === "alerts" && alerts.length > 0 && (
          <div style={{ display: "flex", gap: "6px" }}>
            {(["ALL", "OPEN", "ACKNOWLEDGED", "RESOLVED"] as const).map((st) => {
              const isSelected = alertFilter === st;
              return (
                <button
                  key={st}
                  type="button"
                  onClick={() => setAlertFilter(st)}
                  style={{
                    padding: "3px 8px",
                    borderRadius: "var(--radius-sm)",
                    fontSize: "11px",
                    border: isSelected ? "1px solid var(--color-accent)" : "1px solid var(--color-border)",
                    backgroundColor: isSelected ? "rgba(20, 154, 251, 0.12)" : "transparent",
                    color: isSelected ? "var(--color-text-primary)" : "var(--color-text-muted)",
                    cursor: "pointer",
                  }}
                >
                  {st.charAt(0) + st.slice(1).toLowerCase()}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Alerts View */}
      {activeTab === "alerts" && (
        <div>
          {filteredAlerts.length === 0 ? (
            <EmptyState
              icon={<AlertTriangle size={28} />}
              title="No Incident Alerts"
              description={
                alertFilter === "ALL"
                  ? "No operational alerts were triggered for this machine in the selected window."
                  : `No alerts with status ${alertFilter} exist for this machine.`
              }
            />
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--color-border)", textAlign: "left", color: "var(--color-text-muted)" }}>
                    <th style={{ padding: "8px 12px", fontWeight: 500 }}>ID</th>
                    <th style={{ padding: "8px 12px", fontWeight: 500 }}>Severity</th>
                    <th style={{ padding: "8px 12px", fontWeight: 500 }}>Status</th>
                    <th style={{ padding: "8px 12px", fontWeight: 500 }}>Incident Description</th>
                    <th style={{ padding: "8px 12px", fontWeight: 500 }}>Triggered (UTC)</th>
                    <th style={{ padding: "8px 12px", fontWeight: 500 }}>Resolution</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredAlerts.map((a) => (
                    <tr key={a.id} style={{ borderBottom: "1px solid rgba(255, 255, 255, 0.04)" }}>
                      <td style={{ padding: "10px 12px", fontFamily: "var(--font-mono)", color: "var(--color-text-muted)" }}>
                        #{a.id}
                      </td>
                      <td style={{ padding: "10px 12px" }}>
                        <StatusBadge
                          status={a.severity}
                          size="sm"
                        />
                      </td>
                      <td style={{ padding: "10px 12px" }}>
                        <span
                          style={{
                            fontSize: "11px",
                            fontFamily: "var(--font-mono)",
                            padding: "2px 6px",
                            borderRadius: "var(--radius-sm)",
                            backgroundColor:
                              a.status === "RESOLVED"
                                ? "rgba(19, 239, 149, 0.1)"
                                : a.status === "ACKNOWLEDGED"
                                ? "rgba(254, 117, 14, 0.1)"
                                : "rgba(239, 68, 68, 0.1)",
                            color:
                              a.status === "RESOLVED"
                                ? "var(--color-success)"
                                : a.status === "ACKNOWLEDGED"
                                ? "var(--color-warning)"
                                : "var(--color-danger)",
                          }}
                        >
                          {a.status}
                        </span>
                      </td>
                      <td style={{ padding: "10px 12px", color: "var(--color-text-primary)", maxWidth: "340px" }}>
                        <div>{a.message}</div>
                        <div style={{ fontSize: "11px", color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}>
                          Type: {a.alert_type}
                        </div>
                      </td>
                      <td style={{ padding: "10px 12px", fontFamily: "var(--font-mono)", color: "var(--color-text-secondary)" }}>
                        {new Date(a.triggered_at).toLocaleString([], {
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </td>
                      <td style={{ padding: "10px 12px", fontSize: "11px", color: "var(--color-text-muted)" }}>
                        {a.resolved_at ? (
                          <div style={{ display: "flex", alignItems: "center", gap: "4px", color: "var(--color-success)" }}>
                            <CheckCircle2 size={13} />
                            <span>
                              {new Date(a.resolved_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                              {a.resolved_by ? ` by ${a.resolved_by}` : ""}
                            </span>
                          </div>
                        ) : (
                          <span style={{ color: "var(--color-text-muted)" }}>Unresolved</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Maintenance View */}
      {activeTab === "maintenance" && (
        <div>
          {maintenance.length === 0 ? (
            <EmptyState
              icon={<Wrench size={28} />}
              title="No Maintenance Records"
              description="No work orders, inspections, or component repairs were logged in the selected window."
            />
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--color-border)", textAlign: "left", color: "var(--color-text-muted)" }}>
                    <th style={{ padding: "8px 12px", fontWeight: 500 }}>Work Order</th>
                    <th style={{ padding: "8px 12px", fontWeight: 500 }}>Activity Type</th>
                    <th style={{ padding: "8px 12px", fontWeight: 500 }}>Lifecycle Status</th>
                    <th style={{ padding: "8px 12px", fontWeight: 500 }}>Technician</th>
                    <th style={{ padding: "8px 12px", fontWeight: 500 }}>Action Description</th>
                    <th style={{ padding: "8px 12px", fontWeight: 500 }}>Timing</th>
                  </tr>
                </thead>
                <tbody>
                  {maintenance.map((m) => (
                    <tr key={m.id} style={{ borderBottom: "1px solid rgba(255, 255, 255, 0.04)" }}>
                      <td style={{ padding: "10px 12px", fontFamily: "var(--font-mono)", color: "var(--color-text-muted)" }}>
                        WO-{m.id}
                      </td>
                      <td style={{ padding: "10px 12px", fontWeight: 600, color: "var(--color-text-primary)" }}>
                        {m.event_type}
                      </td>
                      <td style={{ padding: "10px 12px" }}>
                        <span
                          style={{
                            fontSize: "11px",
                            fontFamily: "var(--font-mono)",
                            padding: "2px 6px",
                            borderRadius: "var(--radius-sm)",
                            backgroundColor:
                              m.status === "COMPLETED"
                                ? "rgba(19, 239, 149, 0.1)"
                                : m.status === "IN_PROGRESS"
                                ? "rgba(20, 154, 251, 0.1)"
                                : m.status === "CANCELLED"
                                ? "rgba(113, 113, 122, 0.1)"
                                : "rgba(254, 117, 14, 0.1)",
                            color:
                              m.status === "COMPLETED"
                                ? "var(--color-success)"
                                : m.status === "IN_PROGRESS"
                                ? "var(--color-accent)"
                                : m.status === "CANCELLED"
                                ? "var(--color-text-muted)"
                                : "var(--color-warning)",
                          }}
                        >
                          {m.status}
                        </span>
                      </td>
                      <td style={{ padding: "10px 12px", color: "var(--color-text-secondary)" }}>
                        {m.technician || "Unassigned"}
                      </td>
                      <td style={{ padding: "10px 12px", color: "var(--color-text-primary)", maxWidth: "340px" }}>
                        {m.description}
                        {m.alert_id && (
                          <div style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>
                            Linked Alert #{m.alert_id}
                          </div>
                        )}
                      </td>
                      <td style={{ padding: "10px 12px", fontSize: "11px", color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                          <Clock size={12} />
                          <span>
                            {new Date(m.created_at).toLocaleString([], {
                              month: "short",
                              day: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                        </div>
                        {m.completed_at && (
                          <div style={{ color: "var(--color-success)", marginTop: "2px" }}>
                            Done: {new Date(m.completed_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
