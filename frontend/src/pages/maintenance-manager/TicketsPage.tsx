// ─── Tickets Page ─────────────────────────────────────────────────────────────
import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import { ticketService } from '@/services/ticketService';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge, ticketBadgeVariant } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { DataTable } from '@/components/ui/DataTable';
import { LoadingScreen } from '@/components/layout/LoadingScreen';
import { AssignMechanicModal } from '@/components/maintenance/AssignMechanicModal';
import { ReviewTicketModal } from '@/components/maintenance/ReviewTicketModal';
import { useAuth } from '@/hooks/useAuth';
import { useToast } from '@/hooks/useToast';
import type { Ticket } from '@/types';

export default function TicketsPage() {
  const [searchParams] = useSearchParams();
  const idFilter = searchParams.get('id');

  const { user } = useAuth();
  const { toast } = useToast();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  // Modal state
  const [isAssignModalOpen, setIsAssignModalOpen] = useState(false);
  const [isReviewModalOpen, setIsReviewModalOpen] = useState(false);
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null);

  const fetchTickets = async () => {
    try {
      setIsLoading(true);
      const data = await ticketService.getAll({ size: 100 }); // Increase size for full view
      
      let filtered = data.items;
      if (idFilter) {
        filtered = filtered.filter((t) => t.ticket_id === idFilter);
      }
      
      setTickets(filtered);
    } catch (error) {
      console.error('Failed to load tickets:', error);
      toast({
        title: 'Error',
        description: 'Failed to load tickets',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTickets();
  }, [idFilter]);

  const handleClose = async (ticketId: string) => {
    if (!user) return;
    try {
      await ticketService.closeTicket(ticketId, user.user_id, user.name);
      toast({
        title: 'Ticket Closed',
        description: 'The ticket has been successfully closed.',
      });
      fetchTickets();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to close ticket.',
        variant: 'destructive',
      });
    }
  };

  if (isLoading) return <LoadingScreen />;

  const columns = [
    {
      header: 'Ticket ID',
      accessorKey: 'ticket_id' as keyof Ticket,
      className: 'font-mono text-xs'
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
      )
    },
    {
      header: 'Time',
      cell: (t: Ticket) => (
        <span className="text-sm text-muted-foreground whitespace-nowrap">
          {formatDistanceToNow(new Date(t.created_at), { addSuffix: true })}
        </span>
      )
    },
    {
      header: 'Actions',
      cell: (t: Ticket) => {
        return (
          <div className="flex gap-2">
            {(t.status === 'open' || (t.status === 'assigned' && !t.mechanic_name)) && (
              <Button
                variant="outline"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedTicket(t);
                  setIsAssignModalOpen(true);
                }}
              >
                Assign Mechanic
              </Button>
            )}
            {t.status === 'repaired' && (
              <Button
                variant="outline"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedTicket(t);
                  setIsReviewModalOpen(true);
                }}
              >
                Review Ticket
              </Button>
            )}
            {t.status === 'reviewed' && (
              <Button
                variant="primary"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  handleClose(t.ticket_id);
                }}
              >
                Close Ticket
              </Button>
            )}
            {t.status !== 'open' && t.status !== 'repaired' && t.status !== 'reviewed' && !(t.status === 'assigned' && !t.mechanic_name) && (
              <Badge variant="outline" className="text-xs">
                {t.status === 'assigned' ? `Assigned: ${t.mechanic_name}` : t.status === 'in_progress' ? 'In Progress' : t.status === 'closed' ? 'Closed' : t.status.replace('_', ' ')}
              </Badge>
            )}
          </div>
        );
      }
    }
  ];

  return (
    <div className="p-6 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Maintenance Tickets</h1>
        <p className="text-muted-foreground mt-1">
          {idFilter ? `Showing ticket ${idFilter}` : 'Manage and assign all active maintenance tickets.'}
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>All Tickets</CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable
            data={tickets}
            columns={columns}
            keyExtractor={(t) => t.ticket_id}
            className="mt-0"
          />
        </CardContent>
      </Card>

      <AssignMechanicModal
        isOpen={isAssignModalOpen}
        onClose={() => setIsAssignModalOpen(false)}
        ticket={selectedTicket}
        onSuccess={fetchTickets}
      />
      
      <ReviewTicketModal
        isOpen={isReviewModalOpen}
        onClose={() => setIsReviewModalOpen(false)}
        ticket={selectedTicket}
        onSuccess={fetchTickets}
      />
    </div>
  );
}
