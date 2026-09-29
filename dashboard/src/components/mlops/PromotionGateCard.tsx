import React, { useState } from "react";
import {
  CheckCircle2,
  XCircle,
  ArrowUpRight,
  ArrowDownRight,
  Award,
  AlertTriangle,
} from "lucide-react";
import { Card } from "../common/Card";
import { Button } from "../common/Button";
import { RoleGate } from "../common/RoleGate";
import { ADMIN_ONLY } from "../../utils/rbac";
import { api } from "../../api/client";
import { PromotionGate, PromotionResult } from "../../types/mlops";

export interface PromotionGateCardProps {
  gate: PromotionGate | null;
  isLoading: boolean;
  onRefresh: () => void;
  onPromoted?: (result: PromotionResult) => void;
}

export const PromotionGateCard: React.FC<PromotionGateCardProps> = ({
  gate,
  isLoading,
  onRefresh,
  onPromoted,
}) => {
  const [isPromoting, setIsPromoting] = useState<boolean>(false);
  const [showConfirm, setShowConfirm] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!gate) {
    return (
      <Card title="Champion/Challenger Promotion Gate" subtitle="Governed technical comparison and validation">
        <div style={{ padding: "var(--space-4)", textAlign: "center", color: "var(--color-text-muted)", fontSize: "13px" }}>
          {isLoading ? "Evaluating promotion gate..." : "No active challenger candidate registered in model registry."}
        </div>
      </Card>
    );
  }

  const handlePromote = async () => {
    setIsPromoting(true);
    setErrorMessage(null);
    try {
      const result = await api.retrain.promote();
      setShowConfirm(false);
      if (onPromoted) {
        onPromoted(result);
      }
      onRefresh();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to promote challenger to champion.";
      setErrorMessage(msg);
    } finally {
      setIsPromoting(false);
    }
  };

  const renderDelta = (delta: number | null, isHigherBetter: boolean = true) => {
    if (delta === null || delta === undefined) return <span style={{ color: "var(--color-text-muted)" }}>—</span>;
    const isPositive = delta > 0;
    const isZero = Math.abs(delta) < 1e-4;

    if (isZero) {
      return <span style={{ color: "var(--color-text-muted)", fontSize: "12px" }}>0.00 pp</span>;
    }

    const isGood = isHigherBetter ? isPositive : !isPositive;
    const color = isGood ? "var(--color-success)" : "var(--color-danger)";
    const Icon = isPositive ? ArrowUpRight : ArrowDownRight;

    return (
      <span style={{ color, fontSize: "12px", display: "inline-flex", alignItems: "center", gap: "2px", fontWeight: 600 }}>
        <Icon size={14} />
        {isPositive ? "+" : ""}
        {(delta * 100).toFixed(2)} pp
      </span>
    );
  };

  return (
    <Card
      title="Champion/Challenger Promotion Gate"
      subtitle={`Comparing Challenger v${gate.challenger_version} vs Champion v${gate.champion_version} on validation split (zero test access)`}
      action={
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "4px",
              padding: "4px 10px",
              borderRadius: "var(--radius-sm)",
              fontSize: "12px",
              fontWeight: 700,
              backgroundColor: gate.gate_passed ? "rgba(19, 239, 149, 0.12)" : "rgba(239, 68, 68, 0.12)",
              color: gate.gate_passed ? "var(--color-success)" : "var(--color-danger)",
              border: `1px solid ${gate.gate_passed ? "rgba(19, 239, 149, 0.3)" : "rgba(239, 68, 68, 0.3)"}`,
            }}
          >
            {gate.gate_passed ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
            {gate.gate_passed ? "GATE PASSED" : "GATE BLOCKED"}
          </span>
        </div>
      }
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
        {/* Metric Comparison Grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: "var(--space-3)",
            padding: "var(--space-3)",
            backgroundColor: "var(--color-surface)",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-border)",
          }}
        >
          {/* Val Recall */}
          <div>
            <div style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>Val Recall at t*=0.160</div>
            <div style={{ display: "flex", alignItems: "baseline", gap: "8px", marginTop: "4px" }}>
              <span style={{ fontSize: "18px", fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--color-text-primary)" }}>
                {gate.challenger_val_recall !== null ? `${(gate.challenger_val_recall * 100).toFixed(1)}%` : "—"}
              </span>
              <span style={{ fontSize: "12px", color: "var(--color-text-muted)" }}>
                (champ: {gate.champion_val_recall !== null ? `${(gate.champion_val_recall * 100).toFixed(1)}%` : "—"})
              </span>
            </div>
            <div style={{ marginTop: "4px" }}>{renderDelta(gate.recall_delta, true)}</div>
          </div>

          {/* Val Precision */}
          <div>
            <div style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>Val Precision at t*=0.160</div>
            <div style={{ display: "flex", alignItems: "baseline", gap: "8px", marginTop: "4px" }}>
              <span style={{ fontSize: "18px", fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--color-text-primary)" }}>
                {gate.challenger_val_precision !== null ? `${(gate.challenger_val_precision * 100).toFixed(1)}%` : "—"}
              </span>
              <span style={{ fontSize: "12px", color: "var(--color-text-muted)" }}>
                (champ: {gate.champion_val_precision !== null ? `${(gate.champion_val_precision * 100).toFixed(1)}%` : "—"})
              </span>
            </div>
            <div style={{ marginTop: "4px" }}>{renderDelta(gate.precision_delta, true)}</div>
          </div>

          {/* Val PR-AUC */}
          <div>
            <div style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>Val PR-AUC</div>
            <div style={{ display: "flex", alignItems: "baseline", gap: "8px", marginTop: "4px" }}>
              <span style={{ fontSize: "18px", fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--color-text-primary)" }}>
                {gate.challenger_val_pr_auc !== null ? gate.challenger_val_pr_auc.toFixed(4) : "—"}
              </span>
              <span style={{ fontSize: "12px", color: "var(--color-text-muted)" }}>
                (champ: {gate.champion_val_pr_auc !== null ? gate.champion_val_pr_auc.toFixed(4) : "—"})
              </span>
            </div>
            <div style={{ marginTop: "4px" }}>{renderDelta(gate.pr_auc_delta, true)}</div>
          </div>
        </div>

        {/* Hard Gates Checklist */}
        <div>
          <div style={{ fontSize: "12px", fontWeight: 600, color: "var(--color-text-primary)", marginBottom: "var(--space-2)" }}>
            Hard Promotion Criteria Checklist (All 6 Required)
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-2)" }}>
            {/* Recall Protection */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "8px 12px",
                backgroundColor: "var(--color-surface)",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-border)",
                fontSize: "12px",
              }}
            >
              {gate.checks_passed.some((c) => c.startsWith("recall_protection")) ? (
                <CheckCircle2 size={16} color="var(--color-success)" />
              ) : (
                <XCircle size={16} color="var(--color-danger)" />
              )}
              <span>Recall Protection (Recall ≥ Champion − 0.05)</span>
            </div>

            {/* Precision Floor */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "8px 12px",
                backgroundColor: "var(--color-surface)",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-border)",
                fontSize: "12px",
              }}
            >
              {gate.checks_passed.some((c) => c.startsWith("precision_floor")) ? (
                <CheckCircle2 size={16} color="var(--color-success)" />
              ) : (
                <XCircle size={16} color="var(--color-danger)" />
              )}
              <span>Precision Floor (Precision ≥ 0.10)</span>
            </div>

            {/* Feature Contract */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "8px 12px",
                backgroundColor: "var(--color-surface)",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-border)",
                fontSize: "12px",
              }}
            >
              {gate.checks_passed.some((c) => c.startsWith("feature_contract")) ? (
                <CheckCircle2 size={16} color="var(--color-success)" />
              ) : (
                <XCircle size={16} color="var(--color-danger)" />
              )}
              <span>Feature Contract (Exactly 14 Features)</span>
            </div>

            {/* Calibration Contract */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "8px 12px",
                backgroundColor: "var(--color-surface)",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-border)",
                fontSize: "12px",
              }}
            >
              {gate.checks_passed.some((c) => c.startsWith("calibration_contract")) ? (
                <CheckCircle2 size={16} color="var(--color-success)" />
              ) : (
                <XCircle size={16} color="var(--color-danger)" />
              )}
              <span>Calibration Policy (Sigmoid Platt Scaling)</span>
            </div>

            {/* Threshold Contract */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "8px 12px",
                backgroundColor: "var(--color-surface)",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-border)",
                fontSize: "12px",
              }}
            >
              {gate.checks_passed.some((c) => c.startsWith("threshold_contract")) ? (
                <CheckCircle2 size={16} color="var(--color-success)" />
              ) : (
                <XCircle size={16} color="var(--color-danger)" />
              )}
              <span>Operational Threshold (Frozen t* = 0.160)</span>
            </div>

            {/* Technical Inference Gate */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "8px 12px",
                backgroundColor: "var(--color-surface)",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-border)",
                fontSize: "12px",
              }}
            >
              {gate.checks_passed.some((c) => c.startsWith("technical_inference_gate")) ? (
                <CheckCircle2 size={16} color="var(--color-success)" />
              ) : (
                <XCircle size={16} color="var(--color-danger)" />
              )}
              <span>Inference Contract (Schema, Bounds, Risk Bands)</span>
            </div>
          </div>
        </div>

        {/* Gate Narrative Verdict */}
        <div style={{ fontSize: "12px", color: "var(--color-text-secondary)", lineHeight: 1.4 }}>
          <strong>Verdict Narrative:</strong> {gate.gate_reason}
        </div>

        {errorMessage && (
          <div
            style={{
              padding: "var(--space-3)",
              backgroundColor: "rgba(239, 68, 68, 0.1)",
              border: "1px solid rgba(239, 68, 68, 0.3)",
              borderRadius: "var(--radius-sm)",
              color: "var(--color-danger)",
              fontSize: "13px",
              display: "flex",
              gap: "var(--space-2)",
              alignItems: "center",
            }}
          >
            <AlertTriangle size={16} />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Promotion Action */}
        <RoleGate allowedRoles={ADMIN_ONLY}>
          <div style={{ display: "flex", justifyContent: "flex-end", alignItems: "center", gap: "var(--space-3)", borderTop: "1px solid var(--color-border)", paddingTop: "var(--space-3)" }}>
            {showConfirm ? (
              <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                <span style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
                  Are you sure you want to promote v{gate.challenger_version} to production champion?
                </span>
                <Button variant="ghost" size="sm" onClick={() => setShowConfirm(false)} disabled={isPromoting}>
                  Cancel
                </Button>
                <Button variant="primary" size="sm" onClick={handlePromote} disabled={isPromoting}>
                  {isPromoting ? "Promoting..." : "Confirm Promotion"}
                </Button>
              </div>
            ) : (
              <Button
                variant="primary"
                onClick={() => setShowConfirm(true)}
                disabled={!gate.gate_passed}
                title={!gate.gate_passed ? "Promotion is blocked until all hard gate criteria pass" : undefined}
              >
                <Award size={14} style={{ marginRight: "6px" }} />
                Promote Challenger v{gate.challenger_version} to Champion
              </Button>
            )}
          </div>
        </RoleGate>
      </div>
    </Card>
  );
};
