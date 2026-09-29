import React from "react";
import { AlertCircle, CheckCircle2, AlertTriangle, ShieldAlert, Cpu, Wrench } from "lucide-react";
import { MaintenanceRecommendation } from "../../types/prediction";
import { Button } from "../common/Button";
import { RoleGate } from "../common/RoleGate";
import { PRIVILEGED_ROLES } from "../../utils/rbac";

export interface RecommendationPanelProps {
  recommendation?: MaintenanceRecommendation | null;
  emptyMessage?: string;
  onScheduleMaintenance?: () => void;
}

export const RecommendationPanel: React.FC<RecommendationPanelProps> = ({
  recommendation,
  emptyMessage = "No active system recommendations.",
  onScheduleMaintenance,
}) => {
  if (!recommendation) {
    return (
      <div
        style={{
          padding: "var(--space-3) var(--space-4)",
          backgroundColor: "var(--color-surface-raised)",
          border: "1px dashed var(--color-border)",
          borderRadius: "var(--radius-md)",
          textAlign: "center",
          color: "var(--color-text-muted)",
          fontSize: "12px",
        }}
      >
        {emptyMessage}
      </div>
    );
  }

  const normUrgency = (recommendation.urgency || "ROUTINE").toUpperCase();
  let urgencyBg = "var(--color-surface-raised)";
  let urgencyColor = "var(--color-text-secondary)";
  let urgencyBorder = "var(--color-border)";
  let IconComponent = CheckCircle2;

  if (normUrgency === "IMMEDIATE" || normUrgency === "HIGH") {
    urgencyBg = "var(--color-danger-subtle)";
    urgencyColor = "var(--color-danger)";
    urgencyBorder = "var(--color-danger-border)";
    IconComponent = ShieldAlert;
  } else if (normUrgency === "MEDIUM") {
    urgencyBg = "var(--color-warning-subtle)";
    urgencyColor = "var(--color-warning)";
    urgencyBorder = "var(--color-warning-border)";
    IconComponent = AlertTriangle;
  } else if (normUrgency === "LOW") {
    urgencyBg = "var(--color-accent-subtle)";
    urgencyColor = "var(--color-accent)";
    urgencyBorder = "var(--color-accent-border)";
    IconComponent = AlertCircle;
  }

  return (
    <div
      style={{
        backgroundColor: "var(--color-surface-raised)",
        border: `1px solid ${urgencyBorder}`,
        borderRadius: "var(--radius-md)",
        padding: "var(--space-4)",
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-3)",
      }}
    >
      {/* Header: Title, Urgency, Component */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "var(--space-2)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <IconComponent size={16} color={urgencyColor} />
          <span
            style={{
              fontSize: "12px",
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "var(--tracking-wide)",
              color: "var(--color-text-primary)",
            }}
          >
            System Recommendation
          </span>
          <span
            className="text-mono"
            style={{
              fontSize: "10px",
              color: "var(--color-text-muted)",
              backgroundColor: "var(--color-surface)",
              padding: "1px 6px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border-subtle)",
            }}
          >
            {recommendation.action_code}
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span
            style={{
              fontSize: "10px",
              fontWeight: 700,
              padding: "2px 7px",
              borderRadius: "var(--radius-sm)",
              backgroundColor: urgencyBg,
              color: urgencyColor,
              border: `1px solid ${urgencyBorder}`,
              textTransform: "uppercase",
              letterSpacing: "var(--tracking-wider)",
            }}
          >
            {normUrgency} PRIORITY
          </span>
        </div>
      </div>

      {/* Recommendation Narrative */}
      <p
        style={{
          fontSize: "13px",
          color: "var(--color-text-primary)",
          lineHeight: 1.5,
          margin: 0,
        }}
      >
        {recommendation.recommendation_text}
      </p>

      {/* Meta Footer: Reason and Target Component */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "var(--space-2)",
          paddingTop: "var(--space-2)",
          borderTop: "1px solid var(--color-border-subtle)",
          fontSize: "11px",
          color: "var(--color-text-muted)",
        }}
      >
        <div>
          <span style={{ fontWeight: 600 }}>Reason: </span>
          <span>{recommendation.reason}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
          <Cpu size={12} />
          <span>Target: </span>
          <span className="text-mono" style={{ color: "var(--color-text-secondary)", fontWeight: 600 }}>
            {recommendation.target_component}
          </span>
        </div>
      </div>

      {onScheduleMaintenance && (
        <div style={{ display: "flex", justifyContent: "flex-end", paddingTop: "var(--space-2)" }}>
          <RoleGate allowedRoles={PRIVILEGED_ROLES}>
            <Button
              variant="secondary"
              size="sm"
              leftIcon={<Wrench size={12} />}
              onClick={onScheduleMaintenance}
            >
              Schedule Maintenance
            </Button>
          </RoleGate>
        </div>
      )}
    </div>
  );
};
