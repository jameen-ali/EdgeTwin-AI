// ─── Expense Chart ────────────────────────────────────────────────────────────
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import type { ExpenseSummary } from '@/types';

export interface ExpenseChartProps {
  data: ExpenseSummary[];
  className?: string;
}

export function ExpenseChart({ data, className }: ExpenseChartProps) {
  // Format for chart
  const chartData = data.map(d => ({
    period: d.period,
    cost: d.total_cost,
    tickets: d.ticket_count,
  }));

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-base">Maintenance Expenses</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(217 33% 18%)" vertical={false} />
              <XAxis 
                dataKey="period" 
                stroke="hsl(215 20% 55%)"
                fontSize={12}
                tickLine={false}
                axisLine={false}
                dy={10}
              />
              <YAxis 
                yAxisId="left"
                stroke="hsl(215 20% 55%)"
                fontSize={12}
                tickLine={false}
                axisLine={false}
                tickFormatter={(val) => `$${val/1000}k`}
              />
              <YAxis 
                yAxisId="right"
                orientation="right"
                stroke="hsl(215 20% 55%)"
                fontSize={12}
                tickLine={false}
                axisLine={false}
              />
              <RechartsTooltip
                contentStyle={{
                  backgroundColor: 'hsl(222 47% 10%)',
                  borderColor: 'hsl(217 33% 25%)',
                  borderRadius: '8px',
                }}
                formatter={(value: any, name: any) => {
                  if (name === 'cost' || name === 'Cost') return [`$${Number(value).toLocaleString()}`, 'Cost'];
                  return [value, 'Tickets'];
                }}
              />
              <Legend verticalAlign="top" height={36} />
              <Bar yAxisId="left" dataKey="cost" name="Cost" fill="hsl(0 84% 60%)" radius={[4, 4, 0, 0]} />
              <Bar yAxisId="right" dataKey="tickets" name="Tickets" fill="hsl(217 91% 60%)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
