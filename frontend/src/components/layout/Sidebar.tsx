// ─── Sidebar Component ────────────────────────────────────────────────────────
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Settings, 
  Wrench, 
  Users, 
  Activity, 
  Factory, 
  BarChart3, 
  Cpu, 
  X,
  AlertCircle
} from 'lucide-react';
import { clsx } from 'clsx';
import { useAuth } from '@/hooks/useAuth';
import type { UserRole } from '@/types';

export interface SidebarProps {
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
}

// Map roles to their specific navigation items
const NAV_ITEMS: Record<UserRole, Array<{ name: string; path: string; icon: any }>> = {
  operator: [
    { name: 'Dashboard', path: '/operator', icon: LayoutDashboard },
    { name: 'Alerts', path: '/operator/alerts', icon: AlertCircle },
    { name: 'Digital Twin', path: '/digital-twin', icon: Cpu },
  ],
  maintenance_manager: [
    { name: 'Dashboard', path: '/maintenance', icon: LayoutDashboard },
    { name: 'Tickets', path: '/maintenance/tickets', icon: Wrench },
    { name: 'Mechanics', path: '/maintenance/mechanics', icon: Users },
    { name: 'Digital Twin', path: '/digital-twin', icon: Cpu },
  ],
  mechanic: [
    { name: 'My Tasks', path: '/mechanic', icon: Wrench },
  ],
  production_manager: [
    { name: 'Overview', path: '/production', icon: LayoutDashboard },
    { name: 'Schedule', path: '/production/schedule', icon: Factory },
    { name: 'Digital Twin', path: '/digital-twin', icon: Cpu },
  ],
  factory_owner: [
    { name: 'Executive Overview', path: '/owner', icon: LayoutDashboard },
    { name: 'Digital Twin', path: '/digital-twin', icon: Cpu },
  ],
  admin: [
    { name: 'System Overview', path: '/admin', icon: LayoutDashboard },
    { name: 'User Management', path: '/admin/users', icon: Users },
    { name: 'Machine Fleet', path: '/admin/machines', icon: Factory },
    { name: 'Audit Logs', path: '/admin/logs', icon: Activity },
    { name: 'Settings', path: '/admin/settings', icon: Settings },
    { name: 'Digital Twin', path: '/digital-twin', icon: Cpu },
  ],
};

export function Sidebar({ isOpen, setIsOpen }: SidebarProps) {
  const { user } = useAuth();
  
  const role = user?.role as UserRole;
  const items = role ? NAV_ITEMS[role] : [];

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div 
          className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm lg:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          'fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-border bg-card transition-transform duration-300 ease-in-out lg:static lg:translate-x-0',
          isOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="flex h-16 shrink-0 items-center justify-between px-6 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/20 border border-primary/30">
              <Cpu className="h-4 w-4 text-primary" />
            </div>
            <span className="text-lg font-bold text-foreground">EdgeTwin AI</span>
          </div>
          <button 
            className="lg:hidden text-muted-foreground hover:text-foreground"
            onClick={() => setIsOpen(false)}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto p-4">
          <div className="mb-4 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground/70">
            Navigation
          </div>
          {items.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={() => setIsOpen(false)}
                end={item.path === `/${role}` || item.path.endsWith('/admin')} // Exact match for root dashboards
                className={({ isActive }) =>
                  clsx(
                    'group flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-primary/15 text-primary border border-primary/20'
                      : 'text-muted-foreground hover:bg-secondary/80 hover:text-foreground'
                  )
                }
              >
                <Icon className="h-4 w-4 shrink-0" />
                {item.name}
              </NavLink>
            );
          })}
        </nav>

        <div className="border-t border-border p-4">
          <div className="rounded-lg bg-secondary/50 p-4">
            <p className="text-sm font-medium text-foreground">v1.0.0-mock</p>
            <p className="mt-1 text-xs text-muted-foreground">Local Prototype Mode</p>
          </div>
        </div>
      </aside>
    </>
  );
}
