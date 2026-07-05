// ─── Mechanic Dashboard ───────────────────────────────────────────────────────
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Wrench, CheckCircle, Activity, Camera } from 'lucide-react';
import { ticketService, mechanicService } from '@/services/ticketService';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/Card';
import { Badge, ticketBadgeVariant } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { LoadingScreen } from '@/components/layout/LoadingScreen';
import { formatDistanceToNow } from 'date-fns';
import { useAuth } from '@/hooks/useAuth';
import type { Ticket } from '@/types';
import { useToast } from '@/hooks/useToast';

export default function MechanicDashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { toast } = useToast();
  
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchMyTickets = async () => {
    if (!user) return;
    try {
      setIsLoading(true);
      const data = await mechanicService.getMyTickets(user.user_id);
      setTickets(data);
    } catch (error) {
      console.error('Failed to load tickets:', error);
      toast({
        title: 'Error',
        description: 'Failed to load your assignments',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMyTickets();
  }, [user]);

  const handleAcceptTask = async (ticketId: string) => {
    if (!user) return;
    try {
      await ticketService.acceptTask(ticketId, user.user_id, user.name);
      toast({ title: 'Task Accepted', description: 'Status updated to Accepted.' });
      fetchMyTickets();
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to accept task', variant: 'destructive' });
    }
  };

  const handleRejectTask = async (ticketId: string) => {
    if (!user) return;
    try {
      await ticketService.rejectTask(ticketId, user.user_id);
      toast({ title: 'Task Rejected', description: 'Task has been returned to manager.' });
      fetchMyTickets();
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to reject task', variant: 'destructive' });
    }
  };

  if (isLoading) return <LoadingScreen />;

  // Find active task
  const activeTask = tickets.find(t => t.status === 'assigned' || t.status === 'accepted' || t.status === 'in_progress' || t.status === 'paused');
  // Past tasks
  const completedTasks = tickets.filter(t => !['open', 'assigned', 'accepted', 'in_progress', 'paused'].includes(t.status));

  return (
    <div className="p-6 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-4xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Mechanic Dashboard</h1>
        <p className="text-muted-foreground mt-1">View your current assignment and task history.</p>
      </div>

      {/* Current Task */}
      <div>
        <h2 className="text-xl font-semibold tracking-tight mb-4 flex items-center gap-2">
          <Activity className="h-5 w-5 text-primary" /> Current Assignment
        </h2>
        {activeTask ? (
          <Card className="border-primary/50 shadow-md">
            <CardHeader className="bg-primary/5 pb-4 border-b border-border">
              <div className="flex justify-between items-start">
                <div>
                  <CardTitle className="text-xl">{activeTask.machine_name}</CardTitle>
                  <CardDescription className="mt-1 font-mono text-xs">{activeTask.ticket_id} • {activeTask.machine_id}</CardDescription>
                </div>
                <Badge variant={ticketBadgeVariant(activeTask.status)} className="text-sm">
                  {activeTask.status.replace('_', ' ').toUpperCase()}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="pt-6 space-y-4">
              <div>
                <h4 className="text-sm font-medium text-muted-foreground">Issue Description</h4>
                <p className="mt-1 text-sm">{activeTask.description}</p>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-secondary/30 p-3 rounded-lg">
                  <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Reported By</h4>
                  <p className="mt-1 text-sm font-medium">{activeTask.operator_name}</p>
                </div>
                <div className="bg-secondary/30 p-3 rounded-lg">
                  <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Created</h4>
                  <p className="mt-1 text-sm font-medium">{formatDistanceToNow(new Date(activeTask.created_at), { addSuffix: true })}</p>
                </div>
              </div>

              {activeTask.photo_url && (
                <div>
                  <h4 className="text-sm font-medium text-muted-foreground mb-2 flex items-center gap-2">
                    <Camera className="h-4 w-4" /> Attached Photo
                  </h4>
                  <img src={activeTask.photo_url} alt="Issue" className="max-h-48 rounded-md border border-border object-cover" />
                </div>
              )}
            </CardContent>
            <CardFooter className="bg-secondary/10 border-t border-border p-4 flex justify-end gap-3">
              {activeTask.status === 'assigned' ? (
                <>
                  <Button variant="outline" onClick={() => handleRejectTask(activeTask.ticket_id)}>
                    Reject Job
                  </Button>
                  <Button onClick={() => handleAcceptTask(activeTask.ticket_id)}>
                    Accept Job
                  </Button>
                </>
              ) : (
                <Button onClick={() => navigate(`/mechanic/task/${activeTask.ticket_id}`)}>
                  {activeTask.status === 'accepted' ? 'Start Repair' : 'Resume / Continue Repair'}
                </Button>
              )}
            </CardFooter>
          </Card>
        ) : (
          <Card className="border-dashed">
            <CardContent className="flex flex-col items-center justify-center py-12 text-center">
              <CheckCircle className="h-12 w-12 text-emerald-500/50 mb-4" />
              <h3 className="text-lg font-medium">No Active Assignments</h3>
              <p className="text-sm text-muted-foreground max-w-sm mt-1">
                You are currently marked as available. The maintenance manager will assign tasks here.
              </p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* History */}
      <div className="pt-4">
        <h2 className="text-xl font-semibold tracking-tight mb-4 flex items-center gap-2">
          <Wrench className="h-5 w-5 text-muted-foreground" /> Recent Work
        </h2>
        {completedTasks.length === 0 ? (
          <p className="text-sm text-muted-foreground italic">No past tasks found.</p>
        ) : (
          <div className="space-y-3">
            {completedTasks.slice(0, 5).map((task) => (
              <Card key={task.ticket_id} className="hover:bg-secondary/20 transition-colors cursor-pointer" onClick={() => navigate(`/mechanic/task/${task.ticket_id}`)}>
                <div className="flex items-center justify-between p-4">
                  <div>
                    <h4 className="font-medium">{task.machine_name}</h4>
                    <p className="text-xs text-muted-foreground font-mono mt-0.5">{task.ticket_id}</p>
                  </div>
                  <div className="text-right">
                    <Badge variant={ticketBadgeVariant(task.status)} className="mb-1">
                      {task.status.replace('_', ' ').toUpperCase()}
                    </Badge>
                    <p className="text-xs text-muted-foreground">
                      {task.closed_at 
                        ? formatDistanceToNow(new Date(task.closed_at), { addSuffix: true })
                        : formatDistanceToNow(new Date(task.created_at), { addSuffix: true })
                      }
                    </p>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
