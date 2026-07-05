// ─── Sensor Gauge Component ───────────────────────────────────────────────────
import { clsx } from 'clsx';
import { Card, CardContent } from '@/components/ui/Card';
import { SENSOR_THRESHOLDS } from '@/constants';

export interface SensorGaugeProps {
  value: number;
  sensorType: keyof typeof SENSOR_THRESHOLDS;
  title: string;
  unit: string;
  min?: number;
  max?: number;
  className?: string;
}

export function SensorGauge({
  value,
  sensorType,
  title,
  unit,
  min = 0,
  max,
  className,
}: SensorGaugeProps) {
  const threshold = SENSOR_THRESHOLDS[sensorType];
  
  // Auto-calculate max if not provided, giving 20% headroom above critical
  const actualMax = max ?? (threshold.critical * 1.2);
  
  // Calculate percentage for gauge fill (clamp between 0 and 100)
  const percent = Math.min(Math.max(((value - min) / (actualMax - min)) * 100, 0), 100);
  
  // Determine color based on thresholds
  let color = 'hsl(142 76% 36%)'; // Emerald
  let textClass = 'text-emerald-500';

  if (value >= threshold.critical) {
    color = 'hsl(0 84% 60%)'; // Red
    textClass = 'text-red-500';
  } else if (value >= threshold.warning) {
    color = 'hsl(38 92% 50%)'; // Amber
    textClass = 'text-amber-500';
  }

  // SVG parameters
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  // We want a half-circle (or 3/4 circle). Let's do a 3/4 circle gauge (270 degrees)
  const arcLength = circumference * 0.75;
  const strokeDashoffset = arcLength - (percent / 100) * arcLength;

  return (
    <Card className={clsx('flex flex-col', className)}>
      <CardContent className="p-6 flex flex-col items-center justify-center relative flex-1">
        
        {/* Title */}
        <h3 className="text-sm font-medium text-muted-foreground mb-4 w-full text-left">
          {title}
        </h3>

        {/* SVG Gauge */}
        <div className="relative w-32 h-32 flex items-center justify-center">
          <svg className="w-full h-full -rotate-135" viewBox="0 0 100 100">
            {/* Background Track */}
            <circle
              cx="50"
              cy="50"
              r={radius}
              fill="none"
              stroke="currentColor"
              strokeWidth="8"
              className="text-secondary"
              strokeDasharray={circumference}
              strokeDashoffset={circumference - arcLength}
              strokeLinecap="round"
            />
            {/* Value Track */}
            <circle
              cx="50"
              cy="50"
              r={radius}
              fill="none"
              stroke={color}
              strokeWidth="8"
              strokeDasharray={circumference}
              strokeDashoffset={circumference - arcLength + strokeDashoffset}
              strokeLinecap="round"
              className="transition-all duration-1000 ease-out"
            />
          </svg>
          
          {/* Inner Value Text */}
          <div className="absolute inset-0 flex flex-col items-center justify-center pt-2">
            <span className={clsx('text-2xl font-bold tracking-tight', textClass)}>
              {value.toFixed(1)}
            </span>
            <span className="text-xs text-muted-foreground">{unit}</span>
          </div>
        </div>
        
        {/* Threshold Markers Legend */}
        <div className="w-full flex justify-between px-2 mt-2 text-[10px] text-muted-foreground font-medium">
          <span>{min}</span>
          <span className="text-amber-500/70">{threshold.warning}</span>
          <span className="text-red-500/70">{threshold.critical}</span>
          <span>{Math.round(actualMax)}</span>
        </div>
        
      </CardContent>
    </Card>
  );
}
