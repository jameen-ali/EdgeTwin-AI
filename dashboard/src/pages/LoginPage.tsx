import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Layers, ShieldCheck, Lock, User as UserIcon } from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import { Button } from "../components/common/Button";
import { Input } from "../components/common/Input";

export const LoginPage: React.FC = () => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || "/dashboard";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setErrorMsg("Please provide both username and password.");
      return;
    }

    setErrorMsg(null);
    setIsSubmitting(true);

    try {
      await login({ username, password });
      navigate(from, { replace: true });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Authentication failed.";
      setErrorMsg(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const setPreset = (u: string, p: string) => {
    setUsername(u);
    setPassword(p);
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: "var(--color-canvas)",
        padding: "var(--space-6)",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Background Subtle Voltage Line */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: "2px",
          background: "linear-gradient(90deg, transparent 0%, var(--color-accent) 50%, transparent 100%)",
          opacity: 0.8,
        }}
      />

      <div
        style={{
          width: "100%",
          maxWidth: "420px",
          backgroundColor: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-lg)",
          boxShadow: "0 16px 40px rgba(0, 0, 0, 0.7)",
          padding: "var(--space-8)",
          position: "relative",
          zIndex: 10,
        }}
      >
        {/* Header Branding */}
        <div style={{ textAlign: "center", marginBottom: "var(--space-6)" }}>
          <div
            style={{
              width: "48px",
              height: "48px",
              borderRadius: "var(--radius-md)",
              backgroundColor: "var(--color-accent-subtle)",
              border: "1px solid var(--color-accent-border)",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--color-accent)",
              marginBottom: "var(--space-3)",
            }}
          >
            <Layers size={24} />
          </div>

          <h1
            style={{
              fontSize: "20px",
              fontWeight: 700,
              letterSpacing: "var(--tracking-tight)",
              color: "var(--color-text-primary)",
            }}
          >
            EdgeTwin AI
          </h1>
          <p
            style={{
              fontSize: "12px",
              color: "var(--color-text-muted)",
              marginTop: "4px",
              letterSpacing: "var(--tracking-wide)",
              textTransform: "uppercase",
            }}
          >
            Operational Control & Predictive Maintenance
          </p>
        </div>

        {/* Error Alert */}
        {errorMsg && (
          <div
            role="alert"
            style={{
              padding: "10px 12px",
              backgroundColor: "var(--color-danger-subtle)",
              border: "1px solid var(--color-danger-border)",
              borderRadius: "var(--radius-sm)",
              color: "var(--color-danger)",
              fontSize: "12px",
              marginBottom: "var(--space-4)",
              lineHeight: 1.4,
            }}
          >
            {errorMsg}
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          <Input
            label="Operator / Username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="e.g. admin"
            autoComplete="username"
            disabled={isSubmitting}
            required
          />

          <Input
            label="Security Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••••••"
            autoComplete="current-password"
            disabled={isSubmitting}
            required
          />

          <Button
            type="submit"
            variant="primary"
            size="lg"
            isLoading={isSubmitting}
            style={{ width: "100%", marginTop: "var(--space-2)" }}
          >
            Sign In to Console
          </Button>
        </form>

        {/* Dev Quick Presets */}
        <div
          style={{
            marginTop: "var(--space-6)",
            paddingTop: "var(--space-4)",
            borderTop: "1px solid var(--color-border-subtle)",
          }}
        >
          <div
            style={{
              fontSize: "11px",
              fontWeight: 600,
              color: "var(--color-text-muted)",
              textTransform: "uppercase",
              letterSpacing: "var(--tracking-wider)",
              marginBottom: "var(--space-2)",
            }}
          >
            Quick Credentials (Development)
          </div>
          <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setPreset("admin", "Admin123!")}
              leftIcon={<ShieldCheck size={12} />}
            >
              Admin
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setPreset("engineer", "Engineer123!")}
              leftIcon={<Lock size={12} />}
            >
              Engineer
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setPreset("operator", "Operator123!")}
              leftIcon={<UserIcon size={12} />}
            >
              Operator
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
