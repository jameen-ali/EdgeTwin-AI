import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, CheckCircle, Wrench, Play, Pause, AlertTriangle, Info, Clock, Activity, BrainCircuit } from 'lucide-react';
import { ticketService } from '@/services/ticketService';
import { machineService } from '@/services/machineService';
import { Card, CardContent, CardHeader, CardTitle, CardFooter, CardDescription } from '@/components/ui/Card';
import { Badge, ticketBadgeVariant } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { LoadingScreen } from '@/components/layout/LoadingScreen';
import { useAuth } from '@/hooks/useAuth';
import { useToast } from '@/hooks/useToast';
import type { Ticket, Machine, MLPrediction } from '@/types';

export default function TaskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { toast } = useToast();

  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [machine, setMachine] = useState<Machine | null>(null);
  const [prediction, setPrediction] = useState<MLPrediction | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form State
  const [report, setReport] = useState('');
  const [parts, setParts] = useState('');
  const [timeTaken, setTimeTaken] = useState('');
  const [finalStatus, setFinalStatus] = useState('normal');
  
  // Checklist State
  const [checklist, setChecklist] = useState({
    isolatePower: false,
    diagnoseIssue: false,
    replaceParts: false,
    testOperation: false,
  });

  const fetchTicketAndDetails = async () => {
    if (!id) return;
    try {
      setIsLoading(true);
      const data = await ticketService.getAll();
      const found = data.items.find(t => t.ticket_id === id);
      if (found) {
        setTicket(found);
        if (found.repair_report) setReport(found.repair_report);
        if (found.parts_used) setParts(found.parts_used);
        if (found.time_taken_hours) setTimeTaken(found.time_taken_hours.toString());
        
        // Fetch machine details
        const mach = await machineService.getById(found.machine_id);
        setMachine(mach);
        
        // Fetch ML Prediction
        const pred = await machineService.getLatestPrediction(found.machine_id);
        setPrediction(pred);
      }
    } catch (error) {
      console.error('Failed to load ticket details', error);
      toast({ title: 'Error', description: 'Failed to load task details', variant: 'destructive' });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTicketAndDetails();
  }, [id]);

  const handleStartRepair = async () => {
    if (!ticket) return;
    try {
      await ticketService.startTask(ticket.ticket_id);
      toast({ title: 'Repair Started', description: 'Task is now In Progress.' });
      fetchTicketAndDetails();
    } catch (e) {
      toast({ title: 'Error', description: 'Failed to start repair', variant: 'destructive' });
    }
  };

  const handlePauseRepair = async () => {
    if (!ticket) return;
    try {
      await ticketService.pauseTask(ticket.ticket_id);
      toast({ title: 'Repair Paused', description: 'Task has been paused.' });
      fetchTicketAndDetails();
    } catch (e) {
      toast({ title: 'Error', description: 'Failed to pause repair', variant: 'destructive' });
    }
  };

  const handleResumeRepair = async () => {
    if (!ticket) return;
    try {
      await ticketService.resumeTask(ticket.ticket_id);
      toast({ title: 'Repair Resumed', description: 'Task is now In Progress again.' });
      fetchTicketAndDetails();
    } catch (e) {
      toast({ title: 'Error', description: 'Failed to resume repair', variant: 'destructive' });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticket || !user) return;

    if (!checklist.isolatePower || !checklist.diagnoseIssue || !checklist.replaceParts || !checklist.testOperation) {
      toast({ title: 'Incomplete Checklist', description: 'Please complete all steps in the repair checklist.', variant: 'destructive' });
      return;
    }

    setIsSubmitting(true);
    try {
      const fullReport = `Final Machine Status: ${finalStatus.toUpperCase()}\n\n${report}`;
      await ticketService.submitRepairReport(ticket.ticket_id, {
        repair_report: fullReport,
        parts_used: parts,
        time_taken_hours: parseFloat(timeTaken) || 0
      }, user.user_id, user.name);
      
      toast({
        title: 'Report Submitted',
        description: 'The task has been marked as repaired and sent for review.',
      });
      navigate('/mechanic');
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to submit report',
        variant: 'destructive',
      });
      setIsSubmitting(false);
    }
  };

  if (isLoading) return <LoadingScreen />;
  if (!ticket) return <div className="p-8 text-center">Task not found</div>;

  const isReadOnly = ticket.status !== 'assigned' && ticket.status !== 'accepted' && ticket.status !== 'in_progress' && ticket.status !== 'paused';
  const allChecklistDone = Object.values(checklist).every(Boolean);

  return (
    <div className="p-6 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-5xl mx-auto">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)} className="-ml-2">
          <ArrowLeft className="h-4 w-4 mr-2" /> Back
        </Button>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Task Details</h1>
          <p className="text-sm text-muted-foreground mt-1">Ticket {ticket.ticket_id}</p>
        </div>
        <div className="ml-auto flex items-center gap-3">
           <Badge variant={ticketBadgeVariant(ticket.status)} className="text-sm px-3 py-1">
             {ticket.status.replace('_', ' ').toUpperCase()}
           </Badge>
        </div>
      </div>
      
      {/* Action Bar */}
      {!isReadOnly && (
        <Card className="bg-secondary/20 border-primary/20 shadow-sm">
          <CardContent className="p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div>
              <h3 className="font-medium">Repair Actions</h3>
              <p className="text-sm text-muted-foreground">Manage your current repair session.</p>
            </div>
            <div className="flex gap-3">
               {ticket.status === 'accepted' && (
                  <Button onClick={handleStartRepair} className="bg-emerald-600 hover:bg-emerald-700">
                    <Play className="w-4 h-4 mr-2" /> Start Repair
                  </Button>
               )}
               {ticket.status === 'in_progress' && (
                  <Button onClick={handlePauseRepair} variant="outline" className="border-orange-500/50 text-orange-600 hover:bg-orange-500/10">
                    <Pause className="w-4 h-4 mr-2" /> Pause Repair
                  </Button>
               )}
               {ticket.status === 'paused' && (
                  <Button onClick={handleResumeRepair} className="bg-emerald-600 hover:bg-emerald-700">
                    <Play className="w-4 h-4 mr-2" /> Resume Repair
                  </Button>
               )}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 md:grid-cols-3">
        {/* Left Column: Context & Machine Details */}
        <div className="md:col-span-1 space-y-6">
          <Card className="shadow-sm">
            <CardHeader className="pb-3 border-b border-border/50">
              <CardTitle className="text-base flex items-center gap-2">
                <Info className="h-4 w-4 text-primary" /> Issue Details
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 pt-4 text-sm">
              <div>
                <span className="text-muted-foreground block mb-1">Description</span>
                <p className="font-medium">{ticket.description}</p>
              </div>
              <div>
                <span className="text-muted-foreground block mb-1">Reported By</span>
                <p className="font-medium">{ticket.operator_name || 'Operator'}</p>
              </div>
              {ticket.photo_url && (
                <div className="pt-2">
                  <span className="text-muted-foreground block mb-1">Attached Photo</span>
                  <img src={ticket.photo_url} alt="Issue" className="rounded-md border border-border w-full object-cover max-h-48" />
                </div>
              )}
            </CardContent>
          </Card>

          {machine && (
             <Card className="shadow-sm border-blue-500/20 bg-blue-500/5">
               <CardHeader className="pb-3 border-b border-blue-500/10">
                 <CardTitle className="text-base flex items-center gap-2 text-blue-600 dark:text-blue-400">
                   <Activity className="h-4 w-4" /> Machine Status
                 </CardTitle>
               </CardHeader>
               <CardContent className="space-y-3 pt-4 text-sm">
                 <div>
                   <span className="text-muted-foreground block mb-1">Name / ID</span>
                   <p className="font-medium text-foreground">{machine.name}</p>
                   <p className="text-xs text-muted-foreground font-mono">{machine.machine_id}</p>
                 </div>
                 <div className="flex justify-between items-center bg-background/50 p-2 rounded-md">
                   <span className="text-muted-foreground">Health Score</span>
                   <span className={`font-bold ${machine.health_score < 50 ? 'text-destructive' : 'text-emerald-500'}`}>{machine.health_score}%</span>
                 </div>
                 <div className="flex justify-between items-center bg-background/50 p-2 rounded-md">
                   <span className="text-muted-foreground">Status</span>
                   <span className="font-bold capitalize">{machine.status}</span>
                 </div>
               </CardContent>
             </Card>
          )}

          {prediction && (
             <Card className="shadow-sm border-purple-500/30 bg-purple-500/5">
               <CardHeader className="pb-3 border-b border-purple-500/10">
                 <CardTitle className="text-base flex items-center gap-2 text-purple-600 dark:text-purple-400">
                   <BrainCircuit className="h-4 w-4" /> AI Diagnostics
                 </CardTitle>
               </CardHeader>
               <CardContent className="space-y-3 pt-4 text-sm">
                 <div>
                   <span className="text-muted-foreground block mb-1">Predicted Failure</span>
                    <p className="font-medium capitalize text-foreground">{(prediction.failure_type || 'Unknown').replace('_', ' ')}</p>
                 </div>
                 <div>
                   <span className="text-muted-foreground block mb-1">Confidence</span>
                   <div className="flex items-center gap-2 mt-1">
                     <div className="h-2 flex-1 bg-background/80 rounded-full overflow-hidden">
                       <div className="h-full bg-purple-500 rounded-full" style={{ width: `${prediction.confidence * 100}%` }} />
                     </div>
                     <span className="text-xs font-medium">{(prediction.confidence * 100).toFixed(0)}%</span>
                   </div>
                 </div>
               </CardContent>
             </Card>
          )}
        </div>

        {/* Right Column: Checklist & Repair Report */}
        <div className="md:col-span-2 space-y-6">
          <Card className="shadow-sm">
            <CardHeader className="pb-3 border-b border-border/50">
               <CardTitle className="text-base flex items-center gap-2">
                 <AlertTriangle className="h-4 w-4 text-amber-500" /> Mandatory Checklist
               </CardTitle>
               <CardDescription>You must complete all steps before submitting.</CardDescription>
            </CardHeader>
            <CardContent className="pt-4">
               <div className="space-y-3">
                 {[
                   { id: 'isolatePower', label: 'Isolate power and lock out machine' },
                   { id: 'diagnoseIssue', label: 'Diagnose issue & verify AI prediction' },
                   { id: 'replaceParts', label: 'Replace faulty parts and clean area' },
                   { id: 'testOperation', label: 'Test operation & remove lockout' },
                 ].map(item => (
                   <label key={item.id} className="flex items-center gap-3 p-3 rounded-lg border border-border/50 bg-secondary/10 hover:bg-secondary/30 cursor-pointer transition-colors">
                     <input
                       type="checkbox"
                       className="w-5 h-5 rounded border-primary/50 text-primary focus:ring-primary"
                       checked={checklist[item.id as keyof typeof checklist]}
                       onChange={(e) => setChecklist(prev => ({ ...prev, [item.id]: e.target.checked }))}
                       disabled={isReadOnly || ticket.status === 'accepted'}
                     />
                     <span className={`text-sm font-medium transition-all ${checklist[item.id as keyof typeof checklist] ? 'line-through text-muted-foreground' : 'text-foreground'}`}>
                       {item.label}
                     </span>
                   </label>
                 ))}
               </div>
            </CardContent>
          </Card>

          <Card className="shadow-sm">
            <CardHeader className="border-b border-border/50 pb-4">
              <CardTitle className="text-lg flex items-center gap-2">
                <Wrench className="h-5 w-5 text-primary" /> Repair Report
              </CardTitle>
              <CardDescription>Document your work, parts used, and time taken.</CardDescription>
            </CardHeader>
            <form onSubmit={handleSubmit}>
              <CardContent className="space-y-5 pt-6">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Work Done / Notes <span className="text-destructive">*</span></label>
                  <textarea
                    className="flex min-h-[120px] w-full rounded-md border border-input bg-background px-4 py-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50 transition-shadow"
                    placeholder="Describe the repair actions taken in detail..."
                    value={report}
                    onChange={(e) => setReport(e.target.value)}
                    disabled={isReadOnly || isSubmitting || ticket.status === 'accepted'}
                    required
                  />
                </div>
                
                <div className="space-y-2">
                  <label className="text-sm font-medium">Parts Used</label>
                  <textarea
                    className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-4 py-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50 transition-shadow"
                    placeholder="List of parts replaced (e.g. 1x Bearing A20, 2m Cable)"
                    value={parts}
                    onChange={(e) => setParts(e.target.value)}
                    disabled={isReadOnly || isSubmitting || ticket.status === 'accepted'}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium flex items-center gap-2">
                      <Clock className="w-4 h-4 text-muted-foreground"/> Time Taken (Hours) <span className="text-destructive">*</span>
                    </label>
                    <input
                      type="number"
                      step="0.5"
                      min="0.5"
                      className="flex h-11 w-full rounded-md border border-input bg-background px-4 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50 transition-shadow"
                      placeholder="e.g. 2.5"
                      value={timeTaken}
                      onChange={(e) => setTimeTaken(e.target.value)}
                      disabled={isReadOnly || isSubmitting || ticket.status === 'accepted'}
                      required
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <label className="text-sm font-medium flex items-center gap-2">
                      <Activity className="w-4 h-4 text-muted-foreground"/> Final Machine Status <span className="text-destructive">*</span>
                    </label>
                    <select
                      className="flex h-11 w-full rounded-md border border-input bg-background px-4 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50 transition-shadow"
                      value={finalStatus}
                      onChange={(e) => setFinalStatus(e.target.value)}
                      disabled={isReadOnly || isSubmitting || ticket.status === 'accepted'}
                      required
                    >
                      <option value="normal">Normal</option>
                      <option value="warning">Warning</option>
                      <option value="offline">Offline</option>
                    </select>
                  </div>
                </div>
              </CardContent>
              <CardFooter className="flex justify-end pt-4 border-t border-border bg-secondary/10 mt-4 rounded-b-xl gap-3 p-4">
                {!isReadOnly && (
                  <Button 
                    type="submit" 
                    disabled={isSubmitting || !report || !timeTaken || !allChecklistDone || ticket.status === 'accepted'} 
                    className="w-full sm:w-auto h-11 px-8"
                  >
                    {isSubmitting ? (
                      <span className="flex items-center gap-2">
                        <div className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                        Submitting...
                      </span>
                    ) : (
                      <span className="flex items-center gap-2">
                        <CheckCircle className="w-5 h-5" /> 
                        Complete Repair & Submit
                      </span>
                    )}
                  </Button>
                )}
              </CardFooter>
            </form>
          </Card>
        </div>
      </div>
    </div>
  );
}
