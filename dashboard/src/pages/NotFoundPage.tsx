import React from "react";
import { Link } from "react-router-dom";
import { AlertCircle, ArrowLeft } from "lucide-react";
import { Button } from "../components/common/Button";

export const NotFoundPage: React.FC = () => {
  return (
    <div
      style={{
        minHeight: "60vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        textAlign: "center",
        gap: "var(--space-4)",
        padding: "var(--space-8)",
      }}
    >
      <div
        style={{
          width: "48px",
          height: "48px",
          borderRadius: "var(--radius-md)",
          backgroundColor: "var(--color-surface-raised)",
          border: "1px solid var(--color-border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "var(--color-warning)",
        }}
      >
        <AlertCircle size={24} />
      </div>

      <div>
        <h1
          style={{
            fontSize: "24px",
            fontWeight: 700,
            letterSpacing: "var(--tracking-tight)",
            color: "var(--color-text-primary)",
          }}
        >
          404 — Operational Route Not Found
        </h1>
        <p
          style={{
            fontSize: "13px",
            color: "var(--color-text-muted)",
            marginTop: "6px",
            maxWidth: "400px",
          }}
        >
          The requested console path does not correspond to an active operational module in EdgeTwin AI.
        </p>
      </div>

      <Link to="/dashboard">
        <Button variant="secondary" size="md" leftIcon={<ArrowLeft size={16} />}>
          Return to Fleet Dashboard
        </Button>
      </Link>
    </div>
  );
};
