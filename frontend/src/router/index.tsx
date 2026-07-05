import { lazy, Suspense } from 'react';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { ProtectedRoute, RoleRoute, GuestRoute } from './guards';
import { LoadingScreen } from '@/components/layout/LoadingScreen';
import { DashboardLayout } from '@/components/layout/DashboardLayout';

// Lazy-loaded pages
const LoginPage              = lazy(() => import('@/pages/auth/LoginPage'));
const OperatorDashboard      = lazy(() => import('@/pages/operator/OperatorDashboard'));
const MachineDetailPage      = lazy(() => import('@/pages/operator/MachineDetailPage'));
const AlertsPage             = lazy(() => import('@/pages/operator/AlertsPage'));
const MechanicDashboard      = lazy(() => import('@/pages/mechanic/MechanicDashboard'));
const TaskDetailPage         = lazy(() => import('@/pages/mechanic/TaskDetailPage'));
const MaintenanceDashboard   = lazy(() => import('@/pages/maintenance-manager/MaintenanceDashboard'));
const TicketsPage            = lazy(() => import('@/pages/maintenance-manager/TicketsPage'));
const MechanicsPage          = lazy(() => import('@/pages/maintenance-manager/MechanicsPage'));
const ProductionDashboard    = lazy(() => import('@/pages/production-manager/ProductionDashboard'));
const ProductionSchedulePage = lazy(() => import('@/pages/production-manager/ProductionSchedulePage'));
const OwnerDashboard         = lazy(() => import('@/pages/factory-owner/OwnerDashboard'));
const AdminPanel             = lazy(() => import('@/pages/admin/AdminPanel'));
const UserManagementPage     = lazy(() => import('@/pages/admin/UserManagementPage'));
const MachineManagementPage  = lazy(() => import('@/pages/admin/MachineManagementPage'));
const SystemSettingsPage     = lazy(() => import('@/pages/admin/SystemSettingsPage'));
const AuditLogsPage          = lazy(() => import('@/pages/admin/AuditLogsPage'));
const DigitalTwinDashboard   = lazy(() => import('@/pages/digital-twin/DigitalTwinDashboard'));
const NotFound               = lazy(() => import('@/pages/NotFound'));

const router = createBrowserRouter([
  // Guest routes
  {
    element: <GuestRoute />,
    children: [
      { path: '/login', element: <LoginPage /> },
    ],
  },

  // Protected routes (all authenticated users)
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <DashboardLayout />,
        children: [
          // Operator
          {
            element: <RoleRoute allowedRoles={['operator']} />,
            children: [
              { path: '/operator', element: <OperatorDashboard /> },
              { path: '/operator/twin/:id', element: <MachineDetailPage /> },
              { path: '/operator/alerts', element: <AlertsPage /> },
            ],
          },
          // Mechanic
          {
            element: <RoleRoute allowedRoles={['mechanic']} />,
            children: [
              { path: '/mechanic', element: <MechanicDashboard /> },
              { path: '/mechanic/task/:id', element: <TaskDetailPage /> },
            ],
          },
          // Maintenance Manager
          {
            element: <RoleRoute allowedRoles={['maintenance_manager']} />,
            children: [
              { path: '/maintenance', element: <MaintenanceDashboard /> },
              { path: '/maintenance/tickets', element: <TicketsPage /> },
              { path: '/maintenance/mechanics', element: <MechanicsPage /> },
            ],
          },
          // Production Manager
          {
            element: <RoleRoute allowedRoles={['production_manager']} />,
            children: [
              { path: '/production', element: <ProductionDashboard /> },
              { path: '/production/schedule', element: <ProductionSchedulePage /> },
            ],
          },
          // Factory Owner
          {
            element: <RoleRoute allowedRoles={['factory_owner']} />,
            children: [
              { path: '/owner', element: <OwnerDashboard /> },
            ],
          },
          // System Administrator
          {
            element: <RoleRoute allowedRoles={['admin']} />,
            children: [
              { path: '/admin', element: <AdminPanel /> },
              { path: '/admin/users', element: <UserManagementPage /> },
              { path: '/admin/machines', element: <MachineManagementPage /> },
              { path: '/admin/settings', element: <SystemSettingsPage /> },
              { path: '/admin/logs', element: <AuditLogsPage /> },
            ],
          },
          {
            path: '/digital-twin',
            element: <DigitalTwinDashboard />,
          },
        ],
      },
    ],
  },

  // Redirects & 404
  { path: '/', element: <ProtectedRoute />, children: [{ index: true, element: <div /> }] },
  { path: '*', element: <NotFound /> },
]);

export function AppRouter() {
  return (
    <Suspense fallback={<LoadingScreen />}>
      <RouterProvider router={router} />
    </Suspense>
  );
}
