// ─── Sensor Trend Chart ───────────────────────────────────────────────────────
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { format } from 'date-fns';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { SENSOR_THRESHOLDS } from '@/constants';
import type { SensorReading } from '@/types';

export interface SensorTrendChartProps {
  data: SensorReading[];
  sensorType: keyof typeof SENSOR_THRESHOLDS;
  title: string;
  unit: string;
  color?: string;
  className?: string;
}

export function SensorTrendChart({
  data,
  sensorType,
  title,
  unit,
  color = 'hsl(199 89% 48%)', // primary
  className,
}: SensorTrendChartProps) {
  const threshold = SENSOR_THRESHOLDS[sensorType];

  // Format data for Recharts (reverse to show chronological if they came newest-first)
  // Assume data is sorted oldest to newest if it's a trend, but typically backend returns newest first
  // Let's ensure it's sorted by time ascending for the chart
  const chartData = [...data]
    .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
    .map((d) => ({
      time: format(new Date(d.timestamp), 'HH:mm'),
      value: d[sensorType],
    }));

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[200px] w-full mt-4">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(217 33% 18%)" vertical={false} />
              <XAxis
                dataKey="time"
                stroke="hsl(215 20% 55%)"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                minTickGap={30}
              />
              <YAxis
                stroke="hsl(215 20% 55%)"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                domain={['auto', 'auto']}
                tickFormatter={(val) => `${val}${unit}`}
              />
              <RechartsTooltip
                contentStyle={{
                  backgroundColor: 'hsl(222 47% 10%)',
                  borderColor: 'hsl(217 33% 25%)',
                  borderRadius: '8px',
                  fontSize: '12px',
                }}
                itemStyle={{ color }}
              />
              {/* Threshold Lines */}
              {threshold && (
                <>
                  <ReferenceLine
                    y={threshold.warning}
                    stroke="hsl(38 92% 50%)"
                    strokeDasharray="3 3"
                    opacity={0.5}
                  />
                  <ReferenceLine
                    y={threshold.critical}
                    stroke="hsl(0 84% 60%)"
                    strokeDasharray="3 3"
                    opacity={0.5}
                  />
                </>
              )}
              <Line
                type="monotone"
                dataKey="value"
                name={title}
                stroke={color}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: color, strokeWidth: 0 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
