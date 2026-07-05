// ─── Maintenance Dashboard ──────────────────────────────────────────────────
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Wrench, Users, Clock, CheckCircle } from 'lucide-react';
import { ticketService, mechanicService } from '@/services/ticketService';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge, ticketBadgeVariant } from '@/components/ui/Badge';
import { DataTable } from '@/components/ui/DataTable';
import { StatusDot } from '@/components/ui/StatusDot';
import { LoadingScreen } from '@/components/layout/LoadingScreen';
import { formatDistanceToNow } from 'date-fns';
import type { Ticket, Mechanic } from '@/types';

export default function MaintenanceDashboard() {
  const navigate = useNavigate();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [mechanics, setMechanics] = useState<Mechanic[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [ticketsData, mechanicsData] = await Promise.all([
          ticketService.getAll(),
          mechanicService.getAll()
        ]);
        // Default pagination gets page 1, size 20
        setTickets(ticketsData.items);
        setMechanics(mechanicsData);
      } catch (error) {
        console.error('Failed to load maintenance data:', error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, []);

  if (isLoading) return <LoadingScreen />;

  // Aggregate metrics
  const openTickets = tickets.filter(t => t.status === 'open').length;
  const inProgressTickets = tickets.filter(t => t.status === 'assigned' || t.status === 'in_progress').length;
  const requireReview = tickets.filter(t => t.status === 'repaired').length;
  const availableMechanics = mechanics.filter(m => m.login_status === 'available').length;

  const ticketColumns = [
    {
      header: 'Ticket ID',
      accessorKey: 'ticket_id' as keyof Ticket,
      className: 'font-mono text-xs hidden sm:table-cell'
    },
    {
      header: 'Machine',
      accessorKey: 'machine_name' as keyof Ticket,
      className: 'font-medium'
    },
    {
      header: 'Status',
      cell: (t: Ticket) => (
        <Badge variant={ticketBadgeVariant(t.status)}>
          {t.status.replace('_', ' ').toUpperCase()}
        </Badge>
      )
    },
    {
      header: 'Mechanic',
      cell: (t: Ticket) => (
        <span className={t.mechanic_name ? '' : 'text-muted-foreground italic'}>
          {t.mechanic_name || 'Unassigned'}
        </span>
      ),
      className: 'hidden md:table-cell'
    },
    {
      header: 'Created',
      cell: (t: Ticket) => (
        <span className="text-sm text-muted-foreground whitespace-nowrap">
          {formatDistanceToNow(new Date(t.created_at), { addSuffix: true })}
        </span>
      ),
      className: 'hidden lg:table-cell'
    }
  ];

  const mechanicColumns = [
    {
      header: 'Name',
      cell: (m: Mechanic) => (
        <div>
          <p className="font-medium">{m.name}</p>
          <p className="text-xs text-muted-foreground">{m.skill_type}</p>
        </div>
      )
    },
    {
      header: 'Status',
      cell: (m: Mechanic) => (
        <div className="flex items-center gap-2">
          <StatusDot status={m.login_status} />
          <span className="capitalize text-sm">{m.login_status}</span>
        </div>
      )
    },
    {
      header: 'Shift',
      accessorKey: 'shift' as keyof Mechanic,
      className: 'text-sm capitalize hidden sm:table-cell'
    }
  ];

  return (
    <div className="p-6 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Maintenance Overview</h1>
        <p className="text-muted-foreground mt-1">Manage repair tickets and mechanic workload.</p>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className={openTickets > 0 ? 'border-red-500/50 bg-red-500/5' : ''}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Open Tickets</CardTitle>
            <Wrench className={`h-4 w-4 ${openTickets > 0 ? 'text-red-500' : 'text-muted-foreground'}`} />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${openTickets > 0 ? 'text-red-500' : ''}`}>
              {openTickets}
            </div>
            <p className="text-xs text-muted-foreground">Unassigned issues</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">In Progress</CardTitle>
            <Clock className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-amber-500">{inProgressTickets}</div>
            <p className="text-xs text-muted-foreground">Currently being repaired</p>
          </CardContent>
        </Card>

        <Card className={requireReview > 0 ? 'border-blue-500/50 bg-blue-500/5' : ''}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Needs Review</CardTitle>
            <CheckCircle className={`h-4 w-4 ${requireReview > 0 ? 'text-blue-500' : 'text-muted-foreground'}`} />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${requireReview > 0 ? 'text-blue-500' : ''}`}>
              {requireReview}
            </div>
            <p className="text-xs text-muted-foreground">Repairs pending manager approval</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Available Mechanics</CardTitle>
            <Users className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-500">
              {availableMechanics} / {mechanics.length}
            </div>
            <p className="text-xs text-muted-foreground">Ready for new assignments</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Recent Tickets Table */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent Tickets</CardTitle>
            <button 
              onClick={() => navigate('/maintenance/tickets')}
              className="text-sm text-primary hover:underline font-medium"
            >
              View All
            </button>
          </CardHeader>
          <CardContent>
            <DataTable
              data={tickets.slice(0, 5)} // Show top 5
              columns={ticketColumns}
              keyExtractor={(t) => t.ticket_id}
              onRowClick={(t) => navigate(`/maintenance/tickets?id=${t.ticket_id}`)}
              className="mt-0"
            />
          </CardContent>
        </Card>

        {/* Mechanics Status */}
        <Card className="lg:col-span-1">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Mechanics Shift</CardTitle>
            <button 
              onClick={() => navigate('/maintenance/mechanics')}
              className="text-sm text-primary hover:underline font-medium"
            >
              Manage
            </button>
          </CardHeader>
          <CardContent>
            <DataTable
              data={mechanics}
              columns={mechanicColumns}
              keyExtractor={(m) => m.mechanic_id}
              onRowClick={(m) => navigate(`/maintenance/mechanics?id=${m.mechanic_id}`)}
              className="mt-0"
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
