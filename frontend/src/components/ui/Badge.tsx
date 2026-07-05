// ─── Badge Component ──────────────────────────────────────────────────────────
import { clsx } from 'clsx';
import type { RiskLevel, TicketStatus, AlertSeverity, MachineStatus } from '@/types';

export interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'low' | 'medium' | 'high' | 'critical' | 'success' | 'info' | 'warning' | 'outline' | 'destructive';
  size?: 'sm' | 'md';
  className?: string;
}

const variantClasses: Record<string, string> = {
  default:  'bg-secondary text-secondary-foreground border-border',
  low:      'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  medium:   'bg-amber-500/15 text-amber-400 border-amber-500/30',
  high:     'bg-orange-500/15 text-orange-400 border-orange-500/30',
  critical: 'bg-red-500/15 text-red-400 border-red-500/30',
  success:  'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  info:     'bg-blue-500/15 text-blue-400 border-blue-500/30',
  warning:  'bg-amber-500/15 text-amber-400 border-amber-500/30',
  outline:  'bg-transparent text-foreground border-border',
  destructive: 'bg-destructive/15 text-destructive border-destructive/30',
};

export function Badge({ children, variant = 'default', size = 'sm', className }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center font-medium border rounded-full whitespace-nowrap',
        size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs',
        variantClasses[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}

// Convenience mappers
export function riskBadgeVariant(risk: RiskLevel): BadgeProps['variant'] {
  return risk;
}

export function statusBadgeVariant(status: MachineStatus): BadgeProps['variant'] {
  const map: Record<MachineStatus, BadgeProps['variant']> = {
    normal: 'success',
    warning: 'warning',
    critical: 'critical',
    offline: 'default',
  };
  return map[status];
}

export function ticketBadgeVariant(status: TicketStatus): BadgeProps['variant'] {
  const map: Record<TicketStatus, BadgeProps['variant']> = {
    open: 'critical',
    assigned: 'info',
    accepted: 'info',
    in_progress: 'warning',
    paused: 'default',
    repaired: 'medium',
    reviewed: 'info',
    closed: 'success',
  };
  return map[status];
}

export function alertBadgeVariant(severity: AlertSeverity): BadgeProps['variant'] {
  return severity;
}
