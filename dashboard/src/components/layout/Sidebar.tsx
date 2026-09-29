import React from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Cpu,
  AlertTriangle,
  Wrench,
  Zap,
  Activity,
  History,
  Settings,
  LogOut,
  Shield,
  Layers,
} from "lucide-react";
import { useAuth } from "../../hooks/useAuth";

export interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

interface NavItem {
  to: string;
  label: string;
  icon: React.ReactNode;
}

const navItems: NavItem[] = [
  { to: "/dashboard", label: "Dashboard", icon: <LayoutDashboard size={18} /> },
  { to: "/machines", label: "Machines", icon: <Cpu size={18} /> },
  { to: "/alerts", label: "Alerts", icon: <AlertTriangle size={18} /> },
  { to: "/maintenance", label: "Maintenance", icon: <Wrench size={18} /> },
  { to: "/history", label: "History", icon: <History size={18} /> },
  { to: "/scenarios", label: "Scenarios", icon: <Zap size={18} /> },
  { to: "/mlops", label: "MLOps", icon: <Activity size={18} /> },
  { to: "/settings", label: "Settings", icon: <Settings size={18} /> },
];

export const Sidebar: React.FC<SidebarProps> = ({ isOpen = false, onClose }) => {
  const { user, role, logout } = useAuth();

  return (
    <aside className={`app-sidebar ${isOpen ? "open" : ""}`}>
      {/* Brand Header */}
      <div
        style={{
          height: "56px",
          display: "flex",
          alignItems: "center",
          gap: "10px",
          padding: "0 var(--space-5)",
          borderBottom: "1px solid var(--color-border)",
        }}
      >
        <div
          style={{
            width: "28px",
            height: "28px",
            borderRadius: "var(--radius-sm)",
            backgroundColor: "var(--color-accent-subtle)",
            border: "1px solid var(--color-accent-border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "var(--color-accent)",
          }}
        >
          <Layers size={16} />
        </div>
        <div>
          <div
            style={{
              fontSize: "14px",
              fontWeight: 700,
              letterSpacing: "var(--tracking-tight)",
              color: "var(--color-text-primary)",
              lineHeight: 1.1,
            }}
          >
            EDGETWIN
          </div>
          <div
            style={{
              fontSize: "10px",
              fontWeight: 600,
              letterSpacing: "var(--tracking-wider)",
              color: "var(--color-accent)",
              textTransform: "uppercase",
            }}
          >
            INDUSTRIAL AI
          </div>
        </div>
      </div>

      {/* Navigation Items */}
      <nav
        style={{
          flex: 1,
          padding: "var(--space-3) var(--space-2)",
          display: "flex",
          flexDirection: "column",
          gap: "2px",
          overflowY: "auto",
        }}
      >
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            onClick={onClose}
            style={({ isActive }) => ({
              display: "flex",
              alignItems: "center",
              gap: "10px",
              padding: "8px 12px",
              borderRadius: "var(--radius-sm)",
              fontSize: "13px",
              fontWeight: isActive ? 600 : 500,
              color: isActive ? "var(--color-text-primary)" : "var(--color-text-muted)",
              backgroundColor: isActive ? "var(--color-surface-strong)" : "transparent",
              borderLeft: isActive ? "2px solid var(--color-accent)" : "2px solid transparent",
              transition: "all var(--transition-fast)",
            })}
          >
            {item.icon}
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* User / Session Footer */}
      <div
        style={{
          padding: "var(--space-3) var(--space-4)",
          borderTop: "1px solid var(--color-border)",
          backgroundColor: "var(--color-surface-subtle)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px", minWidth: 0 }}>
          <div
            style={{
              width: "28px",
              height: "28px",
              borderRadius: "var(--radius-full)",
              backgroundColor: "var(--color-surface-strong)",
              border: "1px solid var(--color-border)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--color-text-secondary)",
              flexShrink: 0,
            }}
          >
            <Shield size={14} />
          </div>
          <div style={{ minWidth: 0, overflow: "hidden" }}>
            <div
              style={{
                fontSize: "12px",
                fontWeight: 600,
                color: "var(--color-text-primary)",
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {user?.username || "Operator"}
            </div>
            <div
              style={{
                fontSize: "10px",
                color: "var(--color-text-muted)",
                letterSpacing: "var(--tracking-wide)",
                textTransform: "uppercase",
              }}
            >
              {role || "OPERATOR"}
            </div>
          </div>
        </div>

        <button
          onClick={logout}
          aria-label="Sign out"
          title="Sign out"
          style={{
            padding: "6px",
            borderRadius: "var(--radius-sm)",
            color: "var(--color-text-muted)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transition: "color var(--transition-fast)",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = "var(--color-danger)")}
          onMouseLeave={(e) => (e.currentTarget.style.color = "var(--color-text-muted)")}
        >
          <LogOut size={16} />
        </button>
      </div>
    </aside>
  );
};
