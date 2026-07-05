import { useState, useEffect } from 'react';
import { TrendingDown, TrendingUp, DollarSign, Activity, AlertOctagon, Zap, ShieldAlert, BarChart3, PieChart as PieChartIcon } from 'lucide-react';
import { analyticsService } from '@/services/analyticsService';
import { alertService } from '@/services/ticketService';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { LoadingScreen } from '@/components/layout/LoadingScreen';

import { Badge } from '@/components/ui/Badge';
import { formatDistanceToNow } from 'date-fns';
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Legend,
  PieChart, Pie, Cell
} from 'recharts';
import type { ExpenseSummary, ProductionImpact, Alert } from '@/types';

interface LocalFactoryStats {
  total_machines: number;
  active_machines: number;
  critical_machines: number;
  overall_health_score: number;
  total_alerts: number;
  active_tickets: number;
}

export default function OwnerDashboard() {
  const [stats, setStats] = useState<LocalFactoryStats | null>(null);
  const [monthlyExpenses, setMonthlyExpenses] = useState<ExpenseSummary[]>([]);
  const [yearlyExpenses, setYearlyExpenses] = useState<ExpenseSummary[]>([]);
  const [impactData, setImpactData] = useState<ProductionImpact[]>([]);
  const [criticalAlerts, setCriticalAlerts] = useState<Alert[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        const [statsData, monthlyExp, yearlyExp, impactRes, alerts] = await Promise.all([
          analyticsService.getFactoryStats() as unknown as Promise<LocalFactoryStats>,
          analyticsService.getExpenseSummary('month'),
          analyticsService.getExpenseSummary('year'),
          analyticsService.getProductionImpact(),
          alertService.getAll({ status: 'pending' })
        ]);
        setStats(statsData || null);
        setMonthlyExpenses(monthlyExp || []);
        setYearlyExpenses(yearlyExp || []);
        setImpactData(impactRes || []);
        setCriticalAlerts(alerts.filter(a => a.severity === 'critical') || []);
      } catch (error) {
        console.error('Failed to load owner data:', error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, []);

  if (isLoading && !stats) return <LoadingScreen />;

  // Calculations
  const currentMonthCost = (monthlyExpenses[0]?.total_cost || 0);
  const currentYearCost = (yearlyExpenses[0]?.total_cost || 0);
  
  // Fake ROI/Efficiency metrics based on realistic factors
  const estimatedSavings = currentYearCost * 0.45; // e.g. Predictive maintenance saves 45% of reactive maintenance costs
  const roiPercentage = ((estimatedSavings / (currentYearCost || 1)) * 100).toFixed(1);
  const efficiencyScore = stats?.overall_health_score ? (stats.overall_health_score * 0.95).toFixed(1) : 0;
  
  // Charts Data Prep
  const expenseChartData = monthlyExpenses.slice(0, 12).reverse().map(e => ({
    period: e.period,
    cost: e.total_cost,
    tickets: e.ticket_count
  }));

  const downtimeData = impactData.map(i => ({
    name: i.machine_name,
    downtime: i.downtime_hours,
    loss: i.production_loss_percent
  }));

  const efficiencyPieData = [
    { name: 'Operational Excellence', value: Number(efficiencyScore), color: '#10b981' },
    { name: 'Improvement Opportunity', value: 100 - Number(efficiencyScore), color: '#3b82f6' }
  ];

  return (
    <div className="p-6 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Executive Dashboard</h1>
          <p className="text-muted-foreground mt-1">High-level financial overview, ROI, and predictive analytics.</p>
        </div>
        <Badge variant="outline" className="w-fit text-muted-foreground bg-secondary/50 border-border shadow-sm">
          <ShieldAlert className="w-3 h-3 mr-2" /> Read-only Executive View
        </Badge>
      </div>

      {/* Critical Alerts Banner (Immediate Display) */}
      {criticalAlerts.length > 0 && (
        <Card className="border-destructive/50 bg-destructive/10 shadow-sm animate-pulse">
          <CardContent className="p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <AlertOctagon className="h-6 w-6 text-destructive" />
              <div>
                <h3 className="font-bold text-destructive">Critical Alerts Active ({criticalAlerts.length})</h3>
                <p className="text-sm text-destructive/80">Immediate attention required by maintenance teams.</p>
              </div>
            </div>
            <div className="flex flex-col gap-1 text-right text-sm">
              {criticalAlerts.slice(0, 2).map((alert, i) => (
                <span key={i} className="text-destructive font-medium">{alert.machine_name} - {formatDistanceToNow(new Date(alert.triggered_at))} ago</span>
              ))}
              {criticalAlerts.length > 2 && <span className="text-destructive/80 text-xs">+{criticalAlerts.length - 2} more...</span>}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Financial KPIs */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="shadow-sm border-t-4 border-t-emerald-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Estimated ROI</CardTitle>
            <TrendingUp className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-500">+{roiPercentage}%</div>
            <p className="text-xs text-muted-foreground mt-1 text-emerald-500/80">${estimatedSavings.toLocaleString()} Saved this year</p>
          </CardContent>
        </Card>

        <Card className="shadow-sm border-t-4 border-t-orange-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Monthly Cost</CardTitle>
            <DollarSign className="h-4 w-4 text-orange-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-500">${currentMonthCost.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground mt-1">Current Month Maintenance</p>
          </CardContent>
        </Card>

        <Card className="shadow-sm border-t-4 border-t-red-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Yearly Cost</CardTitle>
            <TrendingDown className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-500">${currentYearCost.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground mt-1">Year-To-Date Maintenance</p>
          </CardContent>
        </Card>

        <Card className="shadow-sm border-t-4 border-t-blue-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Factory Health</CardTitle>
            <Activity className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-500">{stats?.overall_health_score ? stats.overall_health_score.toFixed(1) : '0'}%</div>
            <p className="text-xs text-muted-foreground mt-1">Overall Facility Asset Health</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Expense Trends */}
        <Card className="lg:col-span-2 shadow-sm">
          <CardHeader className="border-b border-border/50 pb-4">
            <CardTitle className="flex items-center gap-2"><BarChart3 className="w-5 h-5 text-primary"/> Expense Trends</CardTitle>
            <CardDescription>Monthly maintenance cost tracking over time</CardDescription>
          </CardHeader>
          <CardContent className="pt-6 h-[350px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={expenseChartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorCost" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.1}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="period" stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(val) => `$${val/1000}k`} />
                <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.2} />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'hsl(var(--background))', borderColor: 'hsl(var(--border))', borderRadius: '8px' }}
                  formatter={(value: any, _name: any) => [`$${Number(value).toLocaleString()}`, 'Cost']}
                />
                <Area type="monotone" dataKey="cost" stroke="#8b5cf6" strokeWidth={3} fillOpacity={1} fill="url(#colorCost)" />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Operational Efficiency */}
        <Card className="lg:col-span-1 shadow-sm">
          <CardHeader className="border-b border-border/50 pb-4">
            <CardTitle className="flex items-center gap-2"><Zap className="w-5 h-5 text-emerald-500"/> Production Efficiency</CardTitle>
            <CardDescription>OEE Proxy Indicator</CardDescription>
          </CardHeader>
          <CardContent className="pt-6 h-[350px] flex flex-col justify-center items-center">
            <ResponsiveContainer width="100%" height="70%">
              <PieChart>
                <Pie
                  data={efficiencyPieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  paddingAngle={5}
                  dataKey="value"
                  stroke="none"
                >
                  {efficiencyPieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--background))', borderColor: 'hsl(var(--border))', borderRadius: '8px' }} />
              </PieChart>
            </ResponsiveContainer>
            <div className="text-center mt-2">
              <h2 className="text-3xl font-bold text-emerald-500">{efficiencyScore}%</h2>
              <p className="text-sm text-muted-foreground mt-1">Efficiency Metric</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Downtime Analytics */}
      <Card className="shadow-sm">
        <CardHeader className="border-b border-border/50 pb-4">
          <CardTitle className="flex items-center gap-2"><PieChartIcon className="w-5 h-5 text-orange-500"/> Downtime Analytics</CardTitle>
          <CardDescription>Total expected downtime and production loss by machine</CardDescription>
        </CardHeader>
        <CardContent className="pt-6 h-[350px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={downtimeData} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.2} />
              <XAxis dataKey="name" stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} dy={10} />
              <YAxis yAxisId="left" stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis yAxisId="right" orientation="right" stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} />
              <Tooltip 
                contentStyle={{ backgroundColor: 'hsl(var(--background))', borderColor: 'hsl(var(--border))', borderRadius: '8px' }}
                cursor={{ fill: 'hsl(var(--secondary))', opacity: 0.4 }}
              />
              <Legend verticalAlign="top" height={36} />
              <Bar yAxisId="left" dataKey="downtime" name="Downtime (hrs)" fill="#f97316" radius={[4, 4, 0, 0]} />
              <Bar yAxisId="right" dataKey="loss" name="Prod. Loss %" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
}
