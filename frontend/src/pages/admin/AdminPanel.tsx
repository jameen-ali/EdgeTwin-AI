// ─── Admin Dashboard ──────────────────────────────────────────────────────────
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, Shield, History, Activity } from 'lucide-react';
import { adminService } from '@/services/analyticsService';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { DataTable } from '@/components/ui/DataTable';
import { LoadingScreen } from '@/components/layout/LoadingScreen';
import { formatDistanceToNow } from 'date-fns';
import type { User, AuditLog } from '@/types';

export default function AdminPanel() {
  const navigate = useNavigate();
  const [users, setUsers] = useState<User[]>([]);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [usersData, logsData] = await Promise.all([
          adminService.getUsers(),
          adminService.getAuditLogs(1, 10)
        ]);
        setUsers(usersData);
        setLogs(logsData.items);
      } catch (error) {
        console.error('Failed to load admin data:', error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, []);

  if (isLoading) return <LoadingScreen />;

  const activeUsers = users.filter(u => u.is_active).length;

  const logColumns = [
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
      ),
      className: 'hidden sm:table-cell'
    },
    {
      header: 'Time',
      cell: (l: AuditLog) => (
        <span className="text-sm text-muted-foreground whitespace-nowrap">
          {formatDistanceToNow(new Date(l.timestamp), { addSuffix: true })}
        </span>
      )
    }
  ];

  return (
    <div className="p-6 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">System Administration</h1>
        <p className="text-muted-foreground mt-1">Manage users, roles, and review security audit logs.</p>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Users</CardTitle>
            <Users className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{users.length}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Users</CardTitle>
            <Activity className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-500">{activeUsers}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">System Health</CardTitle>
            <Shield className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-500">Optimal</div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div className="flex items-center gap-2">
              <History className="h-5 w-5 text-muted-foreground" />
              <CardTitle>Recent Audit Logs</CardTitle>
            </div>
            <button onClick={() => navigate('/admin/logs')} className="text-sm text-primary hover:underline font-medium">
              View All
            </button>
          </CardHeader>
          <CardContent>
            <DataTable
              data={logs}
              columns={logColumns}
              keyExtractor={(l) => l.log_id}
              className="mt-0"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div className="flex items-center gap-2">
              <Users className="h-5 w-5 text-muted-foreground" />
              <CardTitle>User Management</CardTitle>
            </div>
            <button onClick={() => navigate('/admin/users')} className="text-sm text-primary hover:underline font-medium">
              Manage Users
            </button>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {users.slice(0, 5).map(user => (
                <div key={user.user_id} className="flex items-center justify-between p-3 border border-border rounded-lg bg-secondary/10">
                  <div>
                    <p className="font-medium text-sm">{user.name}</p>
                    <p className="text-xs text-muted-foreground">{user.email}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant="outline" className="uppercase text-[10px]">{user.role.replace('_', ' ')}</Badge>
                    {user.is_active ? (
                      <span className="w-2 h-2 rounded-full bg-emerald-500" />
                    ) : (
                      <span className="w-2 h-2 rounded-full bg-red-500" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-muted-foreground" />
              <CardTitle>Machine Fleet</CardTitle>
            </div>
            <button onClick={() => navigate('/admin/machines')} className="text-sm text-primary hover:underline font-medium">
              Manage Machines
            </button>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Configure factory equipment, assign operators, and monitor real-time operational status.
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-muted-foreground" />
              <CardTitle>System Configuration</CardTitle>
            </div>
            <button onClick={() => navigate('/admin/settings')} className="text-sm text-primary hover:underline font-medium">
              Open Settings
            </button>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Configure global alert thresholds, security policies, and application settings.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
