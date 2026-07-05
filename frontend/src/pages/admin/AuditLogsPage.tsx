// ─── Audit Logs Page ──────────────────────────────────────────────────────────
import { useState, useEffect } from 'react';
import { adminService } from '@/services/analyticsService';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { DataTable } from '@/components/ui/DataTable';
import { LoadingScreen } from '@/components/layout/LoadingScreen';
import { format } from 'date-fns';
import { useToast } from '@/hooks/useToast';
import type { AuditLog } from '@/types';
import { History } from 'lucide-react';

export default function AuditLogsPage() {
  const { toast } = useToast();
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchLogs = async () => {
    try {
      setIsLoading(true);
      const data = await adminService.getAuditLogs(1, 100);
      setLogs(data.items);
    } catch (error) {
      console.error('Failed to load audit logs:', error);
      toast({ title: 'Error', description: 'Failed to load audit logs', variant: 'destructive' });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  if (isLoading) return <LoadingScreen />;

  const columns = [
    {
      header: 'Time',
      cell: (l: AuditLog) => (
        <span className="text-sm text-muted-foreground whitespace-nowrap">
          {format(new Date(l.timestamp), 'MMM d, HH:mm:ss')}
        </span>
      )
    },
    {
      header: 'Action',
      accessorKey: 'action' as keyof AuditLog,
      className: 'font-medium'
    },
    {
      header: 'User',
      accessorKey: 'user_name' as keyof AuditLog,
    },
    {
      header: 'Entity',
      cell: (l: AuditLog) => (
        <span className="text-muted-foreground">{l.entity_type}: {l.entity_id}</span>
      )
    },
    {
      header: 'IP Address',
      accessorKey: 'ip_address' as keyof AuditLog,
      className: 'font-mono text-xs hidden sm:table-cell text-muted-foreground'
    }
  ];

  return (
    <div className="p-6 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-6xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Audit Logs</h1>
          <p className="text-muted-foreground mt-1">Review system activities and security events.</p>
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center gap-2">
          <History className="w-5 h-5 text-muted-foreground" />
          <CardTitle>System Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable
            data={logs}
            columns={columns}
            keyExtractor={(l) => l.log_id}
            className="mt-0"
          />
        </CardContent>
      </Card>
    </div>
  );
}
