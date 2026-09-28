import React, { useEffect } from "react";
import { X } from "lucide-react";
import { IconButton } from "./IconButton";

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  maxWidth?: string;
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  footer,
  maxWidth = "520px",
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(0, 0, 0, 0.75)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "var(--space-4)",
        zIndex: 50,
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth,
          backgroundColor: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-lg)",
          boxShadow: "0 12px 32px rgba(0, 0, 0, 0.8)",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "var(--space-4) var(--space-5)",
            borderBottom: "1px solid var(--color-border-subtle)",
          }}
        >
          <h2
            id="modal-title"
            style={{
              fontSize: "15px",
              fontWeight: 600,
              color: "var(--color-text-primary)",
              letterSpacing: "var(--tracking-tight)",
            }}
          >
            {title}
          </h2>
          <IconButton
            icon={<X size={16} />}
            aria-label="Close dialog"
            size="sm"
            onClick={onClose}
          />
        </div>

        <div style={{ padding: "var(--space-5)", overflowY: "auto", maxHeight: "70vh" }}>
          {children}
        </div>

        {footer && (
          <div
            style={{
              padding: "var(--space-4) var(--space-5)",
              borderTop: "1px solid var(--color-border-subtle)",
              backgroundColor: "var(--color-surface-raised)",
              display: "flex",
              alignItems: "center",
              justifyContent: "flex-end",
              gap: "var(--space-3)",
            }}
          >
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};
