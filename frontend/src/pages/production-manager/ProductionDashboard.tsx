import { useState, useEffect } from 'react';
import { Factory, TrendingDown, AlertTriangle, CheckCircle, Activity, BrainCircuit, ArrowRightLeft, CalendarClock } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/Card';
import { Badge, riskBadgeVariant } from '@/components/ui/Badge';
import { DataTable } from '@/components/ui/DataTable';
import { Button } from '@/components/ui/Button';
import { LoadingScreen } from '@/components/layout/LoadingScreen';
import { useToast } from '@/hooks/useToast';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ZAxis } from 'recharts';
import type { RiskOverview, ProductionImpact } from '@/types';
import { useAppDispatch, useAppSelector } from '@/store';
import { fetchProductionData, reallocateProductionLoad } from '@/store/productionSlice';

export default function ProductionDashboard() {
  const { toast } = useToast();
  const dispatch = useAppDispatch();
  
  const { stats, riskData, impactData, status } = useAppSelector(state => state.production);

  // Modals state
  const [showReallocateModal, setShowReallocateModal] = useState(false);
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [selectedMachine, setSelectedMachine] = useState<string>('');
  const [targetMachine, setTargetMachine] = useState<string>('');

  useEffect(() => {
    if (status === 'idle') {
      dispatch(fetchProductionData());
    }
  }, [status, dispatch]);

  if (status === 'loading' || status === 'idle' || !stats) return <LoadingScreen />;

  const handleReallocate = async () => {
    if (!selectedMachine || !targetMachine) {
      toast({ title: 'Validation Error', description: 'Please select both source and target machines.', variant: 'destructive' });
      return;
    }
    try {
      await dispatch(reallocateProductionLoad({ source: selectedMachine, target: targetMachine })).unwrap();
      toast({ title: 'Production Reallocated', description: 'Load successfully shifted to healthy machines.' });
      setShowReallocateModal(false);
      setSelectedMachine('');
      setTargetMachine('');
    } catch (e) {
      toast({ title: 'Error', description: 'Failed to reallocate load', variant: 'destructive' });
    }
  };

  const handleScheduleAdjust = () => {
    toast({ title: 'Schedule Adjusted', description: 'Maintenance window has been updated.' });
    setShowScheduleModal(false);
  };

  const riskColumns = [
    {
      header: 'Machine',
      cell: (r: RiskOverview) => (
        <div>
          <p className="font-medium text-foreground">{r.machine_name}</p>
          <p className="text-xs text-muted-foreground">{r.location}</p>
        </div>
      )
    },
    {
      header: 'Risk Level',
      cell: (r: RiskOverview) => (
        <Badge variant={riskBadgeVariant(r.risk_level)} className="uppercase px-2">
          {r.risk_level}
        </Badge>
      )
    },
    {
      header: 'Health',
      cell: (r: RiskOverview) => (
        <span className={`font-medium ${r.health_score < 50 ? 'text-destructive' : r.health_score < 75 ? 'text-amber-500' : 'text-emerald-500'}`}>
          {r.health_score}%
        </span>
      )
    },
    {
      header: 'RUL',
      accessorKey: 'rul_hours' as keyof RiskOverview,
      cell: (r: RiskOverview) => (
        <span className="text-sm font-medium">{r.rul_hours} hrs</span>
      )
    },
    {
      header: 'Action',
      cell: (r: RiskOverview) => (
        <Button 
          variant="outline" 
          size="sm" 
          onClick={(e) => {
             e.stopPropagation();
             setSelectedMachine(r.machine_id);
             setShowReallocateModal(true);
          }}
        >
          Reallocate
        </Button>
      )
    }
  ];

  // Map risk data to scatter chart for Risk Matrix
  const riskMatrixData = riskData.map(r => ({
    name: r.machine_name,
    health: r.health_score,
    rul: r.rul_hours,
    risk: r.risk_level === 'critical' ? 4 : r.risk_level === 'high' ? 3 : r.risk_level === 'medium' ? 2 : 1,
    fill: r.risk_level === 'critical' ? '#ef4444' : r.risk_level === 'high' ? '#f97316' : r.risk_level === 'medium' ? '#eab308' : '#22c55e'
  }));

  const aiRecommendations = riskData.filter(r => r.risk_level === 'high' || r.risk_level === 'critical').map(r => ({
    machine: r.machine_name,
    action: `Reallocate load from ${r.machine_name} immediately to prevent critical failure within ${r.rul_hours} hours.`
  }));

  return (
    <div className="p-6 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Production Management</h1>
          <p className="text-muted-foreground mt-1">Monitor fleet health, risk forecasts, and optimize production flow.</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" className="border-primary text-primary hover:bg-primary/10" onClick={() => setShowScheduleModal(true)}>
            <CalendarClock className="w-4 h-4 mr-2" /> Adjust Schedule
          </Button>
          <Button onClick={() => setShowReallocateModal(true)}>
            <ArrowRightLeft className="w-4 h-4 mr-2" /> Reallocate Load
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Uptime Status</CardTitle>
            <Factory className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.machines_operational}/{stats.total_machines}</div>
            <p className="text-xs text-muted-foreground">Machines currently active</p>
          </CardContent>
        </Card>
        
        <Card className={`shadow-sm ${stats.machines_critical > 0 ? 'border-destructive/50 bg-destructive/5' : ''}`}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-destructive">At Risk (Critical & High)</CardTitle>
            <AlertTriangle className={`h-4 w-4 ${stats.machines_critical > 0 ? 'text-destructive' : 'text-muted-foreground'}`} />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${stats.machines_critical > 0 ? 'text-destructive' : ''}`}>
              {riskData.filter(r => r.risk_level === 'critical' || r.risk_level === 'high').length}
            </div>
            <p className="text-xs text-muted-foreground">Require immediate attention</p>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Expected Downtime</CardTitle>
            <TrendingDown className="h-4 w-4 text-orange-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-500">
              {impactData.reduce((acc, curr) => acc + curr.downtime_hours, 0).toFixed(1)} hrs
            </div>
            <p className="text-xs text-muted-foreground">Projected total downtime</p>
          </CardContent>
        </Card>

        <Card className="shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">System Health</CardTitle>
            <Activity className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-500">{stats.avg_health_score.toFixed(1)}%</div>
            <p className="text-xs text-muted-foreground">Average fleet health score</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Risk Overview Table */}
        <Card className="lg:col-span-2 shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between border-b border-border/50 pb-4">
            <CardTitle>Fleet Risk Overview</CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
            <DataTable
              data={riskData}
              columns={riskColumns}
              keyExtractor={(r) => r.machine_id}
              className="mt-0"
            />
          </CardContent>
        </Card>

        {/* AI Recommendations */}
        <Card className="lg:col-span-1 shadow-sm border-primary/20 bg-primary/5">
          <CardHeader className="border-b border-primary/10 pb-4">
            <CardTitle className="flex items-center gap-2 text-primary">
              <BrainCircuit className="h-5 w-5" /> AI Recommendations
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4 space-y-4">
            {aiRecommendations.length > 0 ? (
              aiRecommendations.map((rec, idx) => (
                <div key={idx} className="bg-background rounded-lg p-3 border border-border text-sm flex gap-3">
                  <AlertTriangle className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
                  <p className="text-muted-foreground"><strong className="text-foreground">{rec.machine}:</strong> {rec.action}</p>
                </div>
              ))
            ) : (
              <div className="text-center text-muted-foreground py-8">
                <CheckCircle className="h-8 w-8 text-emerald-500/50 mx-auto mb-2" />
                <p>No critical recommendations.</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Risk Matrix Chart */}
        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle>Risk Matrix</CardTitle>
            <CardDescription>Health Score vs Remaining Useful Life (RUL)</CardDescription>
          </CardHeader>
          <CardContent className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                <XAxis type="number" dataKey="rul" name="RUL (hrs)" unit="h" stroke="hsl(var(--muted-foreground))" />
                <YAxis type="number" dataKey="health" name="Health Score" unit="%" stroke="hsl(var(--muted-foreground))" domain={[0, 100]} />
                <ZAxis type="number" dataKey="risk" range={[100, 400]} />
                <Tooltip cursor={{ strokeDasharray: '3 3' }} contentStyle={{ backgroundColor: 'hsl(var(--background))', borderColor: 'hsl(var(--border))', borderRadius: '8px' }} />
                <Scatter name="Machines" data={riskMatrixData} fill="#8884d8" />
              </ScatterChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Production Impact */}
        <Card className="shadow-sm">
          <CardHeader>
            <CardTitle>Production Impact</CardTitle>
            <CardDescription>Estimated production loss percentage</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            {impactData.map((p) => (
              <div key={p.machine_id} className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="font-medium text-foreground">{p.machine_name}</span>
                  <span className="text-muted-foreground">{p.production_loss_percent}% Loss ({p.downtime_hours} hrs downtime)</span>
                </div>
                <div className="w-full h-2 bg-secondary rounded-full overflow-hidden">
                  <div 
                    className={`h-full ${p.production_loss_percent > 10 ? 'bg-destructive' : p.production_loss_percent > 5 ? 'bg-amber-500' : 'bg-primary'}`}
                    style={{ width: `${Math.min(p.production_loss_percent * 5, 100)}%` }} 
                  />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Modals */}
      {showReallocateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 animate-in fade-in">
          <Card className="w-full max-w-md shadow-lg border-border">
            <CardHeader>
              <CardTitle>Reallocate Production Load</CardTitle>
              <CardDescription>Shift production from at-risk machines to healthy ones.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-1 block">Source Machine</label>
                <select 
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:ring-2 focus:ring-primary focus:outline-none"
                  value={selectedMachine}
                  onChange={(e) => setSelectedMachine(e.target.value)}
                >
                  <option value="">Select machine...</option>
                  {riskData.filter(r => r.risk_level === 'high' || r.risk_level === 'critical').map(r => (
                    <option key={r.machine_id} value={r.machine_id}>{r.machine_name} (Risk: {r.risk_level})</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">Target Machine</label>
                <select 
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:ring-2 focus:ring-primary focus:outline-none"
                  value={targetMachine}
                  onChange={(e) => setTargetMachine(e.target.value)}
                >
                  <option value="">Select healthy machine...</option>
                  {riskData.filter(r => r.risk_level === 'low').map(r => (
                    <option key={r.machine_id} value={r.machine_id}>{r.machine_name} (Capacity Available)</option>
                  ))}
                </select>
              </div>
            </CardContent>
            <CardFooter className="flex justify-end gap-2 bg-secondary/20 pt-4 rounded-b-xl border-t border-border">
              <Button variant="ghost" onClick={() => setShowReallocateModal(false)}>Cancel</Button>
              <Button onClick={handleReallocate}>Confirm Reallocation</Button>
            </CardFooter>
          </Card>
        </div>
      )}

      {showScheduleModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 animate-in fade-in">
          <Card className="w-full max-w-md shadow-lg border-border">
            <CardHeader>
              <CardTitle>Adjust Maintenance Schedule</CardTitle>
              <CardDescription>Modify scheduled downtime for machinery.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-1 block">Select Machine</label>
                <select className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:ring-2 focus:ring-primary focus:outline-none">
                  {riskData.map(r => (
                    <option key={r.machine_id} value={r.machine_id}>{r.machine_name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">New Maintenance Window</label>
                <input type="datetime-local" className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:ring-2 focus:ring-primary focus:outline-none" />
              </div>
            </CardContent>
            <CardFooter className="flex justify-end gap-2 bg-secondary/20 pt-4 rounded-b-xl border-t border-border">
              <Button variant="ghost" onClick={() => setShowScheduleModal(false)}>Cancel</Button>
              <Button onClick={handleScheduleAdjust}>Save Schedule</Button>
            </CardFooter>
          </Card>
        </div>
      )}
    </div>
  );
}
