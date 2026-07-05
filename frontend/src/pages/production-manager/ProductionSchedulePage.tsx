// ─── Production Schedule Page ─────────────────────────────────────────────────
import { useState, useEffect } from 'react';
import { Calendar, PlayCircle, PauseCircle, AlertTriangle } from 'lucide-react';
import { analyticsService } from '@/services/analyticsService';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { LoadingScreen } from '@/components/layout/LoadingScreen';
import { format } from 'date-fns';
import { useToast } from '@/hooks/useToast';
import type { ProductionSchedule } from '@/mock/data/production-schedules';
import { useAppDispatch, useAppSelector } from '@/store';
import { fetchProductionData } from '@/store/productionSlice';

export default function ProductionSchedulePage() {
  const { toast } = useToast();
  const dispatch = useAppDispatch();
  const { schedules, status } = useAppSelector(state => state.production);
  
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => {
    if (status === 'idle') {
      dispatch(fetchProductionData());
    }
  }, [status, dispatch]);

  const handleUpdateStatus = async (id: string, newStatus: ProductionSchedule['status'], reason?: string) => {
    setActionLoading(id);
    try {
      await analyticsService.updateScheduleStatus(id, newStatus, reason);
      toast({ title: 'Success', description: `Schedule status updated to ${newStatus}` });
      dispatch(fetchProductionData());
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to update status', variant: 'destructive' });
    } finally {
      setActionLoading(null);
    }
  };

  if (status === 'loading' || status === 'idle') return <LoadingScreen />;

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'in_progress': return <Badge variant="success">IN PROGRESS</Badge>;
      case 'delayed': return <Badge variant="warning">DELAYED</Badge>;
      case 'cancelled': return <Badge variant="critical">CANCELLED</Badge>;
      case 'completed': return <Badge variant="default">COMPLETED</Badge>;
      default: return <Badge variant="outline">{status.toUpperCase()}</Badge>;
    }
  };

  return (
    <div className="p-6 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-5xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Production Schedules</h1>
          <p className="text-muted-foreground mt-1">Manage manufacturing orders and optimize against machine downtime.</p>
        </div>
      </div>

      <div className="space-y-4">
        {schedules.map((schedule) => (
          <Card key={schedule.schedule_id} className={`transition-all ${schedule.status === 'cancelled' ? 'border-red-500/50 bg-red-500/5' : schedule.status === 'delayed' ? 'border-amber-500/50 bg-amber-500/5' : ''}`}>
            <CardHeader className="pb-3 border-b border-border">
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-3">
                    <CardTitle className="text-xl">{schedule.product}</CardTitle>
                    {getStatusBadge(schedule.status)}
                  </div>
                  <p className="text-sm font-mono text-muted-foreground mt-1">
                    Order: {schedule.schedule_id} | Target: {schedule.units_planned || 1000} units
                  </p>
                </div>
                
                <div className="flex gap-2">
                  {schedule.status === 'in_progress' && (
                    <Button 
                      variant="outline" 
                      size="sm"
                      className="text-amber-500 border-amber-500/50 hover:bg-amber-500/10"
                      onClick={() => handleUpdateStatus(schedule.schedule_id, 'delayed', 'Material shortage')}
                      disabled={actionLoading === schedule.schedule_id}
                      isLoading={actionLoading === schedule.schedule_id}
                    >
                      <PauseCircle className="h-4 w-4 mr-2" /> Mark Delayed
                    </Button>
                  )}
                  {schedule.status === 'delayed' && (
                    <Button 
                      variant="outline" 
                      size="sm"
                      className="text-emerald-500 border-emerald-500/50 hover:bg-emerald-500/10"
                      onClick={() => handleUpdateStatus(schedule.schedule_id, 'in_progress')}
                      disabled={actionLoading === schedule.schedule_id}
                      isLoading={actionLoading === schedule.schedule_id}
                    >
                      <PlayCircle className="h-4 w-4 mr-2" /> Resume Production
                    </Button>
                  )}
                  {schedule.status !== 'cancelled' && schedule.status !== 'completed' && (
                    <Button 
                      variant="destructive" 
                      size="sm"
                      onClick={() => handleUpdateStatus(schedule.schedule_id, 'cancelled', 'Machine breakdown')}
                      disabled={actionLoading === schedule.schedule_id}
                      isLoading={actionLoading === schedule.schedule_id}
                    >
                      <AlertTriangle className="h-4 w-4 mr-2" /> Cancel
                    </Button>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-4 grid gap-6 md:grid-cols-2">
              <div className="space-y-4">
                <div>
                  <h4 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                    <Calendar className="h-4 w-4" /> Schedule Timeline
                  </h4>
                  <div className="mt-2 grid grid-cols-2 gap-4">
                    <div className="bg-secondary/30 p-3 rounded-md">
                      <p className="text-xs text-muted-foreground">Start Date</p>
                      <p className="font-medium text-sm mt-0.5">{format(new Date(schedule.planned_start || (schedule as any).start_time || Date.now()), 'PPP')}</p>
                    </div>
                    <div className="bg-secondary/30 p-3 rounded-md">
                      <p className="text-xs text-muted-foreground">End Date</p>
                      <p className="font-medium text-sm mt-0.5">{format(new Date(schedule.planned_end || (schedule as any).end_time || Date.now()), 'PPP')}</p>
                    </div>
                  </div>
                </div>

                {schedule.delay_reason && (
                  <div className="bg-red-500/10 border border-red-500/20 p-3 rounded-md">
                    <p className="text-xs text-red-500/80 font-medium uppercase tracking-wide">Delay Reason</p>
                    <p className="text-sm text-red-500 mt-0.5">{schedule.delay_reason}</p>
                  </div>
                )}
              </div>

              <div>
                <h4 className="text-sm font-medium text-muted-foreground mb-3">Assigned Machine</h4>
                <div className="space-y-2">
                  <div className="flex items-center justify-between p-2 border border-border rounded-md bg-background">
                    <span className="font-medium text-sm">{schedule.machine_name}</span>
                    <span className="text-xs font-mono text-muted-foreground">{schedule.machine_id || 'MCH-' + Math.floor(Math.random() * 1000)}</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
