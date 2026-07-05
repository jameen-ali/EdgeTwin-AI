// ─── StatusDot Component ──────────────────────────────────────────────────────
import { clsx } from 'clsx';
import type { RiskLevel } from '@/types';

export interface StatusDotProps {
  status: 'online' | 'offline' | 'busy' | 'available' | 'normal' | 'warning' | 'critical' | RiskLevel;
  className?: string;
  animate?: boolean;
}

const colorMap: Record<string, string> = {
  // General status
  online: 'bg-emerald-500',
  offline: 'bg-muted-foreground',
  available: 'bg-emerald-500',
  busy: 'bg-amber-500',
  
  // Machine status
  normal: 'bg-emerald-500',
  warning: 'bg-amber-500',
  critical: 'bg-red-500',
  
  // Risk levels
  low: 'bg-emerald-500',
  medium: 'bg-amber-500',
  high: 'bg-orange-500',
};

export function StatusDot({ status, className, animate = false }: StatusDotProps) {
  const bgColor = colorMap[status] || 'bg-muted-foreground';
  const shouldAnimate = animate || status === 'critical';

  return (
    <span className={clsx('relative flex h-2.5 w-2.5', className)}>
      {shouldAnimate && (
        <span
          className={clsx(
            'absolute inline-flex h-full w-full animate-ping rounded-full opacity-75',
            bgColor
          )}
        />
      )}
      <span className={clsx('relative inline-flex h-2.5 w-2.5 rounded-full', bgColor)} />
    </span>
  );
}
