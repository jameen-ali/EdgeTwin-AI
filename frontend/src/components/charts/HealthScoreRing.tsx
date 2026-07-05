// ─── Health Score Ring ────────────────────────────────────────────────────────
import { Cell, Pie, PieChart, ResponsiveContainer } from 'recharts';
import { clsx } from 'clsx';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';

export interface HealthScoreRingProps {
  score: number;
  className?: string;
}

export function HealthScoreRing({ score, className }: HealthScoreRingProps) {
  // Determine color based on score
  let color = 'hsl(142 76% 36%)'; // Emerald (Good)
  if (score < 50) color = 'hsl(0 84% 60%)'; // Red (Critical)
  else if (score < 75) color = 'hsl(38 92% 50%)'; // Amber (Warning)

  const data = [
    { name: 'Health', value: score },
    { name: 'Degradation', value: 100 - score },
  ];

  return (
    <Card className={clsx('flex flex-col', className)}>
      <CardHeader className="items-center pb-0">
        <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
          Machine Health Score
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 pb-0">
        <div className="h-[200px] w-full relative flex items-center justify-center">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={70}
                outerRadius={85}
                startAngle={90}
                endAngle={-270}
                dataKey="value"
                stroke="none"
              >
                <Cell key="health" fill={color} />
                <Cell key="empty" fill="hsl(217 33% 18%)" /> {/* border/input color as track */}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <span className="text-4xl font-bold tracking-tighter" style={{ color }}>
              {score.toFixed(1)}<span className="text-xl opacity-50">%</span>
            </span>
            <span className="text-xs text-muted-foreground mt-1 font-medium">OVERALL</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
