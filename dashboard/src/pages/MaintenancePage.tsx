import React from "react";
import { Wrench, Calendar, Plus } from "lucide-react";
import { PageHeader } from "../components/layout/PageHeader";
import { Card } from "../components/common/Card";
import { EmptyState } from "../components/common/EmptyState";
import { Button } from "../components/common/Button";
import { RoleGate } from "../components/common/RoleGate";
import { PRIVILEGED_ROLES } from "../utils/rbac";

export const MaintenancePage: React.FC = () => {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
      <PageHeader
        title="Maintenance Workflow"
        description="Prescriptive maintenance recommendations, scheduled inspections, work orders, and technician feedback loop."
        actions={
          <RoleGate allowedRoles={PRIVILEGED_ROLES}>
            <Button variant="primary" size="sm" leftIcon={<Plus size={14} />}>
              Create Work Order
            </Button>
          </RoleGate>
        }
      />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "var(--space-4)" }}>
        <Card title="Upcoming Scheduled Maintenance" subtitle="Preventive cycles">
          <EmptyState
            title="No pending work orders"
            description="No routine or corrective maintenance tasks are currently queued for any machine asset."
            icon={<Calendar size={22} />}
          />
        </Card>

        <Card title="Technician Feedback History" subtitle="Ground-truth failure verification">
          <EmptyState
            title="No maintenance feedback records"
            description="Inspection and component replacement feedback logged by engineers will appear here for model calibration."
            icon={<Wrench size={22} />}
          />
        </Card>
      </div>
    </div>
  );
};
