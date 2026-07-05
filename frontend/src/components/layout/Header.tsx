// ─── Header Component ─────────────────────────────────────────────────────────
import { useState } from 'react';
import { Bell, Search, Menu, LogOut, User as UserIcon } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/Button';
import { Avatar, AvatarFallback, getInitials } from '@/components/ui/Avatar';
import { NotificationPanel } from './NotificationPanel';
import { ROLE_LABELS } from '@/constants';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import { useAppSelector } from '@/store';

export interface HeaderProps {
  onMenuClick: () => void;
}

export function Header({ onMenuClick }: HeaderProps) {
  const { user, signOut } = useAuth();
  const [isNotifOpen, setIsNotifOpen] = useState(false);

  const unreadCount = useAppSelector((state) => state.alerts.unreadCount);

  return (
    <>
      <header className="sticky top-0 z-30 flex h-16 w-full items-center justify-between border-b border-border bg-background/80 px-4 backdrop-blur-md sm:px-6 lg:px-8">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            className="lg:hidden p-2 -ml-2"
            onClick={onMenuClick}
          >
            <Menu className="h-5 w-5" />
            <span className="sr-only">Toggle menu</span>
          </Button>

          {/* Optional Search */}
          <div className="hidden md:flex items-center relative">
            <Search className="absolute left-3 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search..."
              className="h-9 w-64 rounded-full border border-border bg-secondary/50 pl-10 pr-4 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary transition-colors"
            />
          </div>
        </div>

        <div className="flex items-center gap-3 sm:gap-4">
          {/* Notifications */}
          <button
            onClick={() => setIsNotifOpen(true)}
            className="relative p-2 text-muted-foreground hover:text-foreground transition-colors rounded-full hover:bg-secondary"
          >
            <Bell className="h-5 w-5" />
            {unreadCount > 0 && (
              <span className="absolute top-1.5 right-1.5 flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75"></span>
                <span className="relative inline-flex h-2 w-2 rounded-full bg-primary"></span>
              </span>
            )}
          </button>

          <div className="h-6 w-px bg-border hidden sm:block" />

          {/* User Menu */}
          <DropdownMenu.Root>
            <DropdownMenu.Trigger asChild>
              <button className="flex items-center gap-3 rounded-full outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background">
                <div className="hidden text-right sm:block">
                  <p className="text-sm font-medium leading-none text-foreground">{user?.name}</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {user?.role ? ROLE_LABELS[user.role] : 'User'}
                  </p>
                </div>
                <Avatar className="h-9 w-9 border-primary/20">
                  <AvatarFallback className="bg-primary/10 text-primary">
                    {user ? getInitials(user.name) : '?'}
                  </AvatarFallback>
                </Avatar>
              </button>
            </DropdownMenu.Trigger>

            <DropdownMenu.Portal>
              <DropdownMenu.Content
                align="end"
                sideOffset={8}
                className="z-50 w-56 overflow-hidden rounded-md border border-border bg-popover p-1 text-popover-foreground shadow-md animate-in data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2"
              >
                <div className="px-2 py-2.5 sm:hidden border-b border-border mb-1">
                  <p className="text-sm font-medium leading-none">{user?.name}</p>
                  <p className="text-xs text-muted-foreground mt-1">{user?.email}</p>
                </div>
                
                <DropdownMenu.Item className="flex cursor-default select-none items-center rounded-sm px-2 py-2 text-sm outline-none transition-colors focus:bg-secondary focus:text-secondary-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50">
                  <UserIcon className="mr-2 h-4 w-4" />
                  <span>Profile Settings</span>
                </DropdownMenu.Item>
                
                <DropdownMenu.Separator className="-mx-1 my-1 h-px bg-muted" />
                
                <DropdownMenu.Item
                  onClick={signOut}
                  className="flex cursor-default select-none items-center rounded-sm px-2 py-2 text-sm outline-none transition-colors focus:bg-destructive/10 focus:text-destructive data-[disabled]:pointer-events-none data-[disabled]:opacity-50"
                >
                  <LogOut className="mr-2 h-4 w-4" />
                  <span>Sign out</span>
                </DropdownMenu.Item>
              </DropdownMenu.Content>
            </DropdownMenu.Portal>
          </DropdownMenu.Root>
        </div>
      </header>

      <NotificationPanel isOpen={isNotifOpen} onClose={() => setIsNotifOpen(false)} />
    </>
  );
}
