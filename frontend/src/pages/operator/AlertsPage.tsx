// ─── Alerts Page ────────────────────────────────────────────────────────────
import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import { alertService } from '@/services/ticketService';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge, alertBadgeVariant } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { DataTable } from '@/components/ui/DataTable';
import { LoadingScreen } from '@/components/layout/LoadingScreen';
import { ReportIssueModal } from '@/components/operator/ReportIssueModal';
import { useAuth } from '@/hooks/useAuth';
import { useToast } from '@/hooks/useToast';
import type { Alert } from '@/types';

export default function AlertsPage() {
  const [searchParams] = useSearchParams();
  const machineFilter = searchParams.get('machine');
  const idFilter = searchParams.get('id');

  const { user } = useAuth();
  const { toast } = useToast();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  // Modal state
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);

  const fetchAlerts = async () => {
    try {
      setIsLoading(true);
      const data = await alertService.getAll();
      
      // Filter logic
      let filtered = data;
      if (machineFilter) {
        filtered = filtered.filter((a) => a.machine_id === machineFilter);
      }
      if (idFilter) {
        filtered = filtered.filter((a) => a.alert_id === idFilter);
      }
      
      setAlerts(filtered);
    } catch (error) {
      console.error('Failed to load alerts:', error);
      toast({
        title: 'Error',
        description: 'Failed to load alerts',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, [machineFilter, idFilter]);

  const handleIgnore = async (alertId: string) => {
    if (!user) return;
    try {
      await alertService.ignoreAlert(alertId, user.user_id, user.name);
      toast({
        title: 'Alert Ignored',
        description: 'The alert has been marked as ignored.',
      });
      fetchAlerts();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to ignore alert.',
        variant: 'destructive',
      });
    }
  };

  if (isLoading) return <LoadingScreen />;

  const columns = [
    {
      header: 'Alert ID',
      accessorKey: 'alert_id' as keyof Alert,
      className: 'font-mono text-sm'
    },
    {
      header: 'Machine',
      accessorKey: 'machine_name' as keyof Alert,
      className: 'font-medium'
    },
    {
      header: 'Severity',
      cell: (a: Alert) => (
        <Badge variant={alertBadgeVariant(a.severity)}>
          {a.severity.toUpperCase()}
        </Badge>
      )
    },
    {
      header: 'Status',
      cell: (a: Alert) => (
        <span className="capitalize">{a.status}</span>
      )
    },
    {
      header: 'Time',
      cell: (a: Alert) => (
        <span className="text-sm text-muted-foreground whitespace-nowrap">
          {formatDistanceToNow(new Date(a.triggered_at), { addSuffix: true })}
        </span>
      )
    },
    {
      header: 'Actions',
      cell: (a: Alert) => {
        if (a.status !== 'pending' && a.status !== 'escalated') {
          return <span className="text-sm text-muted-foreground capitalize">{a.operator_response}</span>;
        }
        
        return (
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                setSelectedAlert(a);
                setIsReportModalOpen(true);
              }}
            >
              Report Issue
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                handleIgnore(a.alert_id);
              }}
            >
              Ignore
            </Button>
          </div>
        );
      }
    }
  ];

  return (
    <div className="p-6 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">System Alerts</h1>
        <p className="text-muted-foreground mt-1">
          {machineFilter ? `Showing alerts for machine ${machineFilter}` : 'Review and acknowledge AI-generated anomalies.'}
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Alert History</CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable
            data={alerts}
            columns={columns}
            keyExtractor={(a) => a.alert_id}
            className="mt-0"
          />
        </CardContent>
      </Card>

      <ReportIssueModal
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
        alert={selectedAlert}
        onSuccess={fetchAlerts}
      />
    </div>
  );
}
