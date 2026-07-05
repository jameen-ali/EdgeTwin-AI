import { useState, useEffect } from 'react';
import { machineService } from '@/services/machineService';
import { FactoryLayout } from '@/components/digital-twin/FactoryLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Activity, Brain, Server, ShieldAlert } from 'lucide-react';
import type { Machine, SensorReading, MLPrediction } from '@/types';
import { formatDistanceToNow } from 'date-fns';

export default function DigitalTwinDashboard() {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [liveSensors, setLiveSensors] = useState<Record<string, SensorReading>>({});
  const [livePredictions, setLivePredictions] = useState<Record<string, MLPrediction>>({});
  const [selectedMachine, setSelectedMachine] = useState<Machine | null>(null);
  
  useEffect(() => {
    // Initial fetch
    machineService.getAll().then(setMachines).catch(console.error);
  }, []);

  useEffect(() => {
    if (machines.length === 0) return;
    
    const fetchLiveStats = async () => {
      const sensors: Record<string, SensorReading> = {};
      const predictions: Record<string, MLPrediction> = {};
      
      await Promise.all(
        machines.map(async (m) => {
          try {
            // Get latest sensor
            const sData = await machineService.getSensorReadings(m.machine_id, 1);
            if (sData.items.length > 0) {
              sensors[m.machine_id] = sData.items[0];
            }
            // Get latest prediction
            const pData = await machineService.getLatestPrediction(m.machine_id);
            if (pData) {
              predictions[m.machine_id] = pData;
            }
          } catch (e) {
            // silent fail for individual machine errors to avoid breaking the loop
          }
        })
      );
      
      setLiveSensors(sensors);
      setLivePredictions(predictions);
    };

    fetchLiveStats();
    
    // Poll every 5 seconds for realism
    const interval = setInterval(fetchLiveStats, 5000);
    return () => clearInterval(interval);
  }, [machines]);

  const selectedSensor = selectedMachine ? liveSensors[selectedMachine.machine_id] : null;
  const selectedPrediction = selectedMachine ? livePredictions[selectedMachine.machine_id] : null;

  return (
    <div className="p-6 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-3">
            <Server className="w-8 h-8 text-primary" />
            Industrial Digital Twin
          </h1>
          <p className="text-muted-foreground mt-1">Real-time telemetry, AI failure predictions, and factory floor overview.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Floor Layout */}
        <div className="lg:col-span-2 space-y-6">
          <Card className="overflow-hidden bg-card/50 backdrop-blur-xl border-primary/20">
            <CardHeader className="pb-2 border-b border-border/50">
              <CardTitle className="text-lg flex items-center justify-between">
                <span>Factory Floor Layout</span>
                <Badge variant="outline" className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse mr-2" />
                  Live Feed Active
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <FactoryLayout 
                machines={machines} 
                liveSensors={liveSensors} 
                onMachineClick={setSelectedMachine} 
              />
            </CardContent>
          </Card>
        </div>

        {/* Selected Machine AI & Details Panel */}
        <div className="space-y-6">
          {selectedMachine ? (
            <div className="animate-in slide-in-from-right-4 duration-500 space-y-6">
              <Card className="border-primary/50 shadow-[0_0_30px_rgba(var(--primary),0.1)]">
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div>
                      <CardTitle className="text-xl">{selectedMachine.name}</CardTitle>
                      <p className="text-sm text-muted-foreground">{selectedMachine.type}</p>
                    </div>
                    <Badge variant={selectedMachine.status === 'normal' ? 'default' : 'destructive'} className="uppercase">
                      {selectedMachine.status}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-6">
                  
                  {/* Live Sensor Metrics */}
                  <div className="space-y-3">
                    <h4 className="text-sm font-semibold flex items-center text-muted-foreground uppercase tracking-wider">
                      <Activity className="w-4 h-4 mr-2" /> Real-time Telemetry
                    </h4>
                    {selectedSensor ? (
                      <div className="grid grid-cols-2 gap-4">
                        <div className="p-3 rounded-lg bg-secondary/50 border border-border/50">
                          <p className="text-xs text-muted-foreground mb-1">Temperature</p>
                          <p className="text-2xl font-mono">{selectedSensor.temperature.toFixed(1)} <span className="text-sm text-muted-foreground">°C</span></p>
                        </div>
                        <div className="p-3 rounded-lg bg-secondary/50 border border-border/50">
                          <p className="text-xs text-muted-foreground mb-1">Vibration</p>
                          <p className="text-2xl font-mono">{selectedSensor.vibration.toFixed(2)} <span className="text-sm text-muted-foreground">mm/s</span></p>
                        </div>
                      </div>
                    ) : (
                      <div className="text-sm text-muted-foreground p-4 bg-secondary/20 rounded-lg text-center">Waiting for telemetry data...</div>
                    )}
                  </div>

                  {/* AI Prediction Models */}
                  <div className="space-y-3">
                    <h4 className="text-sm font-semibold flex items-center text-primary uppercase tracking-wider">
                      <Brain className="w-4 h-4 mr-2" /> AI Health Prediction
                    </h4>
                    
                    {selectedPrediction ? (
                      <div className="p-4 rounded-xl border border-primary/20 bg-primary/5">
                        <div className="flex justify-between items-end mb-4">
                          <div>
                            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">Health Score</p>
                            <p className="text-4xl font-bold font-mono">{Number(selectedPrediction.health_score).toFixed(1)}<span className="text-xl text-muted-foreground">/100</span></p>
                          </div>
                          {selectedPrediction.health_score < 40 ? (
                            <ShieldAlert className="w-10 h-10 text-red-500 animate-pulse" />
                          ) : (
                            <Activity className="w-10 h-10 text-emerald-500 opacity-50" />
                          )}
                        </div>
                        
                        <div className="space-y-1">
                          <div className="flex justify-between text-xs">
                            <span>Predicted RUL:</span>
                            <span className="font-mono font-medium">{Number(selectedPrediction.rul_hours).toFixed(1)} hrs</span>
                          </div>
                          {selectedPrediction.rul_hours < 48 && (
                            <p className="text-xs text-red-500 mt-2 font-medium">Critical: Maintenance required immediately.</p>
                          )}
                        </div>
                        <div className="mt-4 pt-3 border-t border-primary/10 text-[10px] text-muted-foreground text-right">
                          Model updated {formatDistanceToNow(new Date(selectedPrediction.timestamp), { addSuffix: true })}
                        </div>
                      </div>
                    ) : (
                       <div className="text-sm text-muted-foreground p-4 bg-secondary/20 rounded-lg text-center">No AI prediction available yet.</div>
                    )}
                  </div>
                  
                </CardContent>
              </Card>
            </div>
          ) : (
            <Card className="h-full flex flex-col items-center justify-center p-12 text-center text-muted-foreground bg-secondary/10 border-dashed">
              <Server className="w-12 h-12 mb-4 opacity-20" />
              <h3 className="text-lg font-medium text-foreground mb-2">Select a Machine</h3>
              <p className="text-sm">Click on any machine node in the factory layout to view real-time telemetry and AI health predictions.</p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
