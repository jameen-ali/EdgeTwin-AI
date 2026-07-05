// ─── DashboardLayout Component ────────────────────────────────────────────────
import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { Toaster } from '@/components/ui/Toaster';
import { useSocket } from '@/hooks/useSocket';

export function DashboardLayout() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  useSocket();

  // We could set up an interval to send heartbeats here if we want, but just calling useSocket() connects us.

  return (
    <>
      <div className="flex h-screen overflow-hidden bg-background">
        <Sidebar isOpen={isSidebarOpen} setIsOpen={setIsSidebarOpen} />
        
        <div className="flex w-0 flex-1 flex-col overflow-hidden">
          <Header onMenuClick={() => setIsSidebarOpen(true)} />
          
          <main className="relative flex-1 overflow-y-auto focus:outline-none">
            <div className="mx-auto max-w-7xl">
              <Outlet />
            </div>
          </main>
        </div>
      </div>
      <Toaster />
    </>
  );
}
