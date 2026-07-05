// ─── Machine Detail Page ──────────────────────────────────────────────────────
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Cpu, AlertTriangle } from 'lucide-react';
import { machineService } from '@/services/machineService';
import { alertService } from '@/services/ticketService';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge, riskBadgeVariant } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { LoadingScreen } from '@/components/layout/LoadingScreen';
import { SensorGauge } from '@/components/charts/SensorGauge';
import { SensorTrendChart } from '@/components/charts/SensorTrendChart';
import { HealthScoreRing } from '@/components/charts/HealthScoreRing';
import type { Machine, SensorReading, MLPrediction, Alert } from '@/types';
import { SENSOR_THRESHOLDS } from '@/constants';

export default function MachineDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [machine, setMachine] = useState<Machine | null>(null);
  const [sensors, setSensors] = useState<SensorReading[]>([]);
  const [prediction, setPrediction] = useState<MLPrediction | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!id) return;

    const fetchData = async () => {
      try {
        const [mach, sensRes, pred, alrts] = await Promise.all([
          machineService.getById(id),
          machineService.getSensorReadings(id, 24), // last 24 readings
          machineService.getLatestPrediction(id),
          alertService.getAll({ status: 'active' }),
        ]);

        setMachine(mach);
        setSensors(sensRes.items);
        setPrediction(pred);
        setAlerts(alrts.filter(a => a.machine_id === id));
      } catch (error) {
        console.error('Failed to load machine data:', error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, [id]);

  if (isLoading) return <LoadingScreen />;
  if (!machine) return <div className="p-8 text-center text-muted-foreground">Machine not found</div>;

  const latestSensor = sensors[0] || {} as SensorReading;

  return (
    <div className="p-6 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => navigate(-1)} className="-ml-2">
            <ArrowLeft className="h-4 w-4 mr-2" /> Back
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold tracking-tight">{machine.name}</h1>
              <Badge variant={machine.status === 'critical' ? 'critical' : machine.status === 'warning' ? 'warning' : 'success'}>
                {machine.status.toUpperCase()}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              {machine.machine_id} • {machine.location} • {machine.type}
            </p>
          </div>
        </div>
        
        <div className="flex gap-2">
          {alerts.length > 0 && (
            <Button variant="destructive" onClick={() => navigate(`/operator/alerts?machine=${machine.machine_id}`)}>
              <AlertTriangle className="h-4 w-4 mr-2" /> View {alerts.length} Alerts
            </Button>
          )}
          <Button variant="outline" onClick={() => window.print()}>
            Report Issue
          </Button>
        </div>
      </div>

      <div className="grid gap-6 grid-cols-1 lg:grid-cols-3">
        {/* Left Column: Digital Twin & Health */}
        <div className="lg:col-span-1 space-y-6">
          <HealthScoreRing score={machine.health_score} />

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <Cpu className="h-4 w-4 text-primary" /> AI Prediction
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {prediction ? (
                <>
                  <div className="flex justify-between items-center py-2 border-b border-border">
                    <span className="text-sm text-muted-foreground">Risk Level</span>
                    <Badge variant={riskBadgeVariant(prediction.risk_level)} className="uppercase">
                      {prediction.risk_level}
                    </Badge>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b border-border">
                    <span className="text-sm text-muted-foreground">Remaining Useful Life (RUL)</span>
                    <span className="text-sm font-medium">{prediction.rul_hours} hrs</span>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b border-border">
                    <span className="text-sm text-muted-foreground">Predicted Failure</span>
                    <span className="text-sm font-medium">{prediction.failure_type}</span>
                  </div>
                  <div className="flex justify-between items-center py-2">
                    <span className="text-sm text-muted-foreground">Confidence</span>
                    <span className="text-sm font-medium">{(prediction.confidence * 100).toFixed(1)}%</span>
                  </div>
                </>
              ) : (
                <div className="text-center text-sm text-muted-foreground py-4">No prediction available</div>
              )}
            </CardContent>
          </Card>

          {/* 2D Digital Twin Schema */}
          <Card className="overflow-hidden">
            <CardHeader className="bg-secondary/20 pb-3 border-b border-border">
              <CardTitle className="text-sm font-medium">2D Digital Twin Schema</CardTitle>
            </CardHeader>
            <CardContent className="p-0 relative bg-secondary/5 h-[300px] flex items-center justify-center">
              {/* Abstract Machine SVG Representation */}
              <div className="relative w-[80%] h-[80%] max-w-[250px]">
                <svg viewBox="0 0 100 100" className="w-full h-full text-border drop-shadow-md">
                  <rect x="20" y="20" width="60" height="60" rx="4" fill="currentColor" opacity="0.3" />
                  <circle cx="50" cy="50" r="15" fill="currentColor" opacity="0.5" />
                  <path d="M 20 50 L 5 50 M 80 50 L 95 50 M 50 20 L 50 5 M 50 80 L 50 95" stroke="currentColor" strokeWidth="3" />
                </svg>

                {/* Sensor Hotspots */}
                <div className="absolute top-[10%] left-[45%]">
                  <div className="relative group cursor-help">
                    <span className="absolute flex h-4 w-4 -translate-x-1/2 -translate-y-1/2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-4 w-4 bg-blue-500 border-2 border-background"></span>
                    </span>
                    <div className="absolute bottom-6 left-1/2 -translate-x-1/2 hidden group-hover:block whitespace-nowrap bg-popover text-popover-foreground text-xs px-2 py-1 rounded shadow-md z-10">
                      Vibration: {latestSensor.vibration} mm/s
                    </div>
                  </div>
                </div>

                <div className="absolute top-[75%] left-[25%]">
                  <div className="relative group cursor-help">
                    <span className="absolute flex h-4 w-4 -translate-x-1/2 -translate-y-1/2">
                      {latestSensor.temperature >= SENSOR_THRESHOLDS.temperature.warning && (
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                      )}
                      <span className={`relative inline-flex rounded-full h-4 w-4 border-2 border-background ${latestSensor.temperature >= SENSOR_THRESHOLDS.temperature.critical ? 'bg-red-500' : latestSensor.temperature >= SENSOR_THRESHOLDS.temperature.warning ? 'bg-amber-500' : 'bg-emerald-500'}`}></span>
                    </span>
                    <div className="absolute bottom-6 left-1/2 -translate-x-1/2 hidden group-hover:block whitespace-nowrap bg-popover text-popover-foreground text-xs px-2 py-1 rounded shadow-md z-10">
                      Temp: {latestSensor.temperature} °C
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Sensors & Analytics */}
        <div className="lg:col-span-2 space-y-6">
          <Tabs defaultValue="realtime">
            <TabsList className="grid w-[300px] grid-cols-2">
              <TabsTrigger value="realtime">Real-time Gauges</TabsTrigger>
              <TabsTrigger value="history">Historical Trends</TabsTrigger>
            </TabsList>
            
            <TabsContent value="realtime" className="mt-4">
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                <SensorGauge
                  title="Temperature"
                  value={latestSensor.temperature || 0}
                  sensorType="temperature"
                  unit="°C"
                />
                <SensorGauge
                  title="Vibration"
                  value={latestSensor.vibration || 0}
                  sensorType="vibration"
                  unit="mm/s"
                />
                <SensorGauge
                  title="Pressure"
                  value={latestSensor.pressure || 0}
                  sensorType="pressure"
                  unit="psi"
                />
                <SensorGauge
                  title="Current"
                  value={latestSensor.current || 0}
                  sensorType="current"
                  unit="A"
                />
                <SensorGauge
                  title="RPM"
                  value={latestSensor.rpm || 0}
                  sensorType="rpm"
                  unit="rpm"
                />
                <SensorGauge
                  title="Noise Level"
                  value={latestSensor.noise_level || 0}
                  sensorType="noise_level"
                  unit="dB"
                />
              </div>
            </TabsContent>
            
            <TabsContent value="history" className="mt-4 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <SensorTrendChart
                  data={sensors}
                  sensorType="temperature"
                  title="Temperature Trend"
                  unit="°C"
                  color="hsl(14 94% 63%)"
                />
                <SensorTrendChart
                  data={sensors}
                  sensorType="vibration"
                  title="Vibration Trend"
                  unit="mm/s"
                  color="hsl(280 65% 60%)"
                />
                <SensorTrendChart
                  data={sensors}
                  sensorType="pressure"
                  title="Pressure Trend"
                  unit="psi"
                  color="hsl(199 89% 48%)"
                />
                <SensorTrendChart
                  data={sensors}
                  sensorType="current"
                  title="Current Trend"
                  unit="A"
                  color="hsl(43 96% 56%)"
                />
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}
