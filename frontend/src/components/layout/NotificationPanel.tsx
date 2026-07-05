// ─── NotificationPanel Component ──────────────────────────────────────────────
import { Bell, X, Check, CircleAlert, CheckCircle2, Factory, Wrench } from 'lucide-react';
import { clsx } from 'clsx';
import { Button } from '@/components/ui/Button';
import type { Notification } from '@/types';
import { useAppSelector, useAppDispatch } from '@/store';
import { markAllRead, markNotificationRead } from '@/store/alertSlice';
import { formatDistanceToNow } from 'date-fns';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';

export function NotificationPanel({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const { dashboardRoute } = useAuth();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const notifications = useAppSelector((state) => state.alerts.notifications);
  const unreadCount = useAppSelector((state) => state.alerts.unreadCount);

  const handleMarkAllRead = () => {
    dispatch(markAllRead());
  };

  const handleMarkRead = (id: string) => {
    dispatch(markNotificationRead(id));
  };

  const handleNotificationClick = (n: Notification) => {
    handleMarkRead(n.id);
    navigate(dashboardRoute);
    onClose();
  };

  const getIcon = (type: Notification['type']) => {
    switch (type) {
      case 'alert_new':
      case 'alert_escalated':
        return <CircleAlert className="w-5 h-5 text-destructive" />;
      case 'ticket_assigned':
      case 'ticket_updated':
        return <Wrench className="w-5 h-5 text-amber-500" />;
      case 'ticket_closed':
        return <CheckCircle2 className="w-5 h-5 text-emerald-500" />;
      case 'risk_update':
      default:
        return <Factory className="w-5 h-5 text-blue-500" />;
    }
  };

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-background/50 backdrop-blur-sm transition-opacity"
          onClick={onClose}
        />
      )}

      {/* Slide-over panel */}
      <div
        className={clsx(
          'fixed inset-y-0 right-0 z-50 w-full max-w-sm transform bg-card shadow-xl transition-transform duration-300 ease-in-out border-l border-border',
          isOpen ? 'translate-x-0' : 'translate-x-full'
        )}
      >
        <div className="flex h-full flex-col">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-border px-4 py-4 sm:px-6">
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-semibold text-foreground">Notifications</h2>
              {unreadCount > 0 && (
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary text-[10px] font-bold text-primary-foreground">
                  {unreadCount}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <Button variant="ghost" size="sm" onClick={handleMarkAllRead} className="h-8 text-xs">
                  <Check className="mr-1 h-3.5 w-3.5" />
                  Mark all read
                </Button>
              )}
              <Button variant="ghost" size="sm" onClick={onClose} className="h-8 w-8 p-0">
                <X className="h-4 w-4" />
                <span className="sr-only">Close panel</span>
              </Button>
            </div>
          </div>

          {/* List */}
          <div className="flex-1 overflow-y-auto p-4 sm:px-6">
            {notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                <Bell className="h-12 w-12 opacity-20 mb-4" />
                <p>No notifications yet</p>
              </div>
            ) : (
              <div className="space-y-4">
                {notifications.map((notification) => (
                  <div
                    key={notification.id}
                    className={clsx(
                      'relative flex gap-4 rounded-lg p-4 transition-colors hover:bg-secondary/50',
                      !notification.read && 'bg-secondary/20'
                    )}
                  >
                    {!notification.read && (
                      <div className="absolute left-2 top-1/2 -translate-y-1/2 h-1.5 w-1.5 rounded-full bg-primary" />
                    )}
                    <div className="mt-1">{getIcon(notification.type)}</div>
                    <div
                      className="flex-1 cursor-pointer"
                      onClick={() => handleNotificationClick(notification)}
                    >
                      <p className={clsx('text-sm font-medium', !notification.read ? 'text-foreground' : 'text-muted-foreground')}>
                        {notification.title}
                      </p>
                      <p className="mt-1 text-sm text-muted-foreground line-clamp-2">
                        {notification.message}
                      </p>
                      <p className="mt-2 text-xs text-muted-foreground/60">
                        {formatDistanceToNow(new Date(notification.timestamp), { addSuffix: true })}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
