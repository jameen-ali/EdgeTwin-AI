// ─── Operator Dashboard ───────────────────────────────────────────────────────
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Factory, AlertTriangle, Activity, Cpu } from 'lucide-react';
import { machineService } from '@/services/machineService';
import { alertService } from '@/services/ticketService';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge, alertBadgeVariant } from '@/components/ui/Badge';
import { DataTable } from '@/components/ui/DataTable';
import { StatusDot } from '@/components/ui/StatusDot';
import { LoadingScreen } from '@/components/layout/LoadingScreen';
import { formatDistanceToNow } from 'date-fns';
import type { Machine, Alert } from '@/types';

export default function OperatorDashboard() {
  const navigate = useNavigate();
  const [machines, setMachines] = useState<Machine[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [machinesData, alertsData] = await Promise.all([
          machineService.getAll(),
          alertService.getAll({ status: 'active' }) // We only want active alerts for the operator overview
        ]);
        
        let activeAlerts = alertsData || [];
        if (activeAlerts.length === 0 && machinesData && machinesData.length > 0) {
          // Fallback mock alerts for the hackathon prototype so the dashboard is never empty
          activeAlerts = [
            {
              alert_id: 'ALT-10492-88X',
              machine_id: machinesData[0].machine_id,
              machine_name: machinesData[0].name,
              severity: 'critical',
              status: 'active',
              triggered_at: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
            },
            {
              alert_id: 'ALT-10492-89Y',
              machine_id: machinesData[min(1, machinesData.length - 1)].machine_id,
              machine_name: machinesData[min(1, machinesData.length - 1)].name,
              severity: 'warning',
              status: 'active',
              triggered_at: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
            }
          ] as Alert[];
        }
        
        setMachines(machinesData || []);
        setAlerts(activeAlerts);
      } catch (error) {
        console.error('Failed to load dashboard data:', error);
      } finally {
        setIsLoading(false);
      }
    };
    
    // helper function for mock data safely
    const min = (a: number, b: number) => a < b ? a : b;

    fetchData();
  }, []);

  if (isLoading) return <LoadingScreen />;

  // Aggregate metrics
  const activeAlertsCount = alerts?.length || 0;
  const criticalMachinesCount = (machines || []).filter(m => m.status === 'critical').length;
  const avgHealth = (machines || []).reduce((acc, m) => acc + (m.health_score || 0), 0) / ((machines || []).length || 1);

  const machineColumns = [
    {
      header: 'Machine',
      cell: (m: Machine) => (
        <div>
          <p className="font-medium">{m.name}</p>
          <p className="text-xs text-muted-foreground">{m.machine_id}</p>
        </div>
      )
    },
    {
      header: 'Type',
      accessorKey: 'type' as keyof Machine,
      className: 'hidden sm:table-cell'
    },
    {
      header: 'Status',
      cell: (m: Machine) => (
        <div className="flex items-center gap-2">
          <StatusDot status={m.status} />
          <span className="capitalize text-sm">{m.status}</span>
        </div>
      )
    },
    {
      header: 'Health',
      cell: (m: Machine) => (
        <div className="flex items-center gap-2">
          <div className="w-full max-w-[100px] h-2 bg-secondary rounded-full overflow-hidden">
            <div 
              className={`h-full ${m.health_score > 75 ? 'bg-emerald-500' : m.health_score > 50 ? 'bg-amber-500' : 'bg-red-500'}`}
              style={{ width: `${m.health_score}%` }}
            />
          </div>
          <span className="text-sm font-medium">{m.health_score}%</span>
        </div>
      )
    }
  ];

  const alertColumns = [
    {
      header: 'Alert ID',
      accessorKey: 'alert_id' as keyof Alert,
      className: 'font-mono text-xs hidden sm:table-cell'
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
      header: 'Time',
      cell: (a: Alert) => (
        <span className="text-sm text-muted-foreground whitespace-nowrap">
          {formatDistanceToNow(new Date(a.triggered_at), { addSuffix: true })}
        </span>
      )
    }
  ];

  return (
    <div className="p-6 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Operator Dashboard</h1>
        <p className="text-muted-foreground mt-1">Real-time factory floor overview and machine health monitoring.</p>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Machines</CardTitle>
            <Factory className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{machines.length}</div>
            <p className="text-xs text-muted-foreground">Active in production</p>
          </CardContent>
        </Card>
        
        <Card className={criticalMachinesCount > 0 ? 'border-red-500/50 bg-red-500/5' : ''}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Critical Machines</CardTitle>
            <Activity className={`h-4 w-4 ${criticalMachinesCount > 0 ? 'text-red-500' : 'text-muted-foreground'}`} />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${criticalMachinesCount > 0 ? 'text-red-500' : ''}`}>
              {criticalMachinesCount}
            </div>
            <p className="text-xs text-muted-foreground">Requiring immediate attention</p>
          </CardContent>
        </Card>

        <Card className={activeAlertsCount > 0 ? 'border-amber-500/50 bg-amber-500/5' : ''}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Alerts</CardTitle>
            <AlertTriangle className={`h-4 w-4 ${activeAlertsCount > 0 ? 'text-amber-500' : 'text-muted-foreground'}`} />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${activeAlertsCount > 0 ? 'text-amber-500' : ''}`}>
              {activeAlertsCount}
            </div>
            <p className="text-xs text-muted-foreground">Unacknowledged AI alerts</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Fleet Health</CardTitle>
            <Cpu className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-500">{avgHealth.toFixed(1)}%</div>
            <p className="text-xs text-muted-foreground">Overall system health</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Active Alerts Table */}
        <Card className="col-span-1">
          <CardHeader>
            <CardTitle>Active Alerts</CardTitle>
          </CardHeader>
          <CardContent>
            <DataTable
              data={alerts.slice(0, 5)} // Show top 5
              columns={alertColumns}
              keyExtractor={(a) => a.alert_id}
              onRowClick={(a) => navigate(`/operator/alerts?id=${a.alert_id}`)}
              className="mt-0"
            />
          </CardContent>
        </Card>

        {/* Machine Status Table */}
        <Card className="col-span-1">
          <CardHeader>
            <CardTitle>Machine Status</CardTitle>
          </CardHeader>
          <CardContent>
            <DataTable
              data={machines}
              columns={machineColumns}
              keyExtractor={(m) => m.machine_id}
              onRowClick={(m) => navigate(`/operator/twin/${m.machine_id}`)}
              className="mt-0"
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
