// ─── User Management Page ─────────────────────────────────────────────────────
import { useState, useEffect } from 'react';
import { adminService } from '@/services/analyticsService';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { DataTable } from '@/components/ui/DataTable';
import { LoadingScreen } from '@/components/layout/LoadingScreen';
import { format } from 'date-fns';
import { useToast } from '@/hooks/useToast';
import type { User } from '@/types';
import { UserPlus, Ban, Edit2, CheckCircle } from 'lucide-react';
import { UserModal } from '@/components/admin/UserModal';
import { Input } from '@/components/ui/Input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select';

export default function UserManagementPage() {
  const { toast } = useToast();
  const [users, setUsers] = useState<User[]>([]);
  const [filteredUsers, setFilteredUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | undefined>(undefined);
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState('all');

  const fetchUsers = async () => {
    try {
      setIsLoading(true);
      const data = await adminService.getUsers();
      setUsers(data);
      setFilteredUsers(data);
    } catch (error) {
      console.error('Failed to load users:', error);
      toast({ title: 'Error', description: 'Failed to load users', variant: 'destructive' });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  useEffect(() => {
    let result = users;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      result = result.filter(u => u.name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q));
    }
    if (roleFilter !== 'all') {
      result = result.filter(u => u.role === roleFilter);
    }
    setFilteredUsers(result);
  }, [searchQuery, roleFilter, users]);

  const handleDeactivate = async (userId: string, currentStatus: boolean) => {
    try {
      if (currentStatus) {
        await adminService.deactivateUser(userId);
        toast({ title: 'User Deactivated', description: 'The user account has been deactivated.' });
      } else {
        await adminService.updateUser(userId, { is_active: true });
        toast({ title: 'User Activated', description: 'The user account has been activated.' });
      }
      fetchUsers();
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to deactivate user.', variant: 'destructive' });
    }
  };

  if (isLoading) return <LoadingScreen />;

  const columns = [
    {
      header: 'Name',
      cell: (u: User) => (
        <div>
          <p className="font-medium">{u.name}</p>
          <p className="text-xs text-muted-foreground">{u.email}</p>
        </div>
      )
    },
    {
      header: 'Role',
      cell: (u: User) => (
        <Badge variant="outline" className="uppercase text-[10px]">
          {u.role.replace('_', ' ')}
        </Badge>
      )
    },
    {
      header: 'Status',
      cell: (u: User) => (
        <Badge variant={u.is_active ? 'success' : 'destructive'} className="text-[10px] uppercase">
          {u.is_active ? 'Active' : 'Inactive'}
        </Badge>
      )
    },
    {
      header: 'Created',
      cell: (u: User) => (
        <span className="text-sm text-muted-foreground">
          {format(new Date(u.created_at), 'MMM d, yyyy')}
        </span>
      ),
      className: 'hidden md:table-cell'
    },
    {
      header: 'Actions',
      cell: (u: User) => (
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              setSelectedUser(u);
              setModalOpen(true);
            }}
          >
            <Edit2 className="w-4 h-4 mr-1" /> Edit
          </Button>
          <Button
            variant={u.is_active ? "destructive" : "outline"}
            size="sm"
            disabled={u.role === 'admin'}
            onClick={(e) => {
              e.stopPropagation();
              if (confirm(`Are you sure you want to ${u.is_active ? 'deactivate' : 'activate'} ${u.name}?`)) {
                handleDeactivate(u.user_id, u.is_active);
              }
            }}
          >
            {u.is_active ? <Ban className="w-4 h-4 mr-1" /> : <CheckCircle className="w-4 h-4 mr-1" />}
            {u.is_active ? 'Deactivate' : 'Activate'}
          </Button>
        </div>
      )
    }
  ];

  const roles = [
    { value: 'all', label: 'All Roles' },
    { value: 'operator', label: 'Operator' },
    { value: 'mechanic', label: 'Mechanic' },
    { value: 'maintenance_manager', label: 'Maintenance' },
    { value: 'production_manager', label: 'Production' },
    { value: 'factory_owner', label: 'Owner' },
    { value: 'admin', label: 'Admin' },
  ];

  return (
    <div className="p-6 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-5xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">User Management</h1>
          <p className="text-muted-foreground mt-1">Manage system access and RBAC roles.</p>
        </div>
        <Button onClick={() => { setSelectedUser(undefined); setModalOpen(true); }}>
          <UserPlus className="w-4 h-4 mr-2" /> Add User
        </Button>
      </div>

      <div className="flex gap-4 items-center">
        <div className="w-64">
          <Input 
            placeholder="Search users..." 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <div className="w-48">
          <Select value={roleFilter} onValueChange={setRoleFilter}>
            <SelectTrigger>
              <SelectValue placeholder="All Roles" />
            </SelectTrigger>
            <SelectContent>
              {roles.map(role => (
                <SelectItem key={role.value} value={role.value}>
                  {role.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Directory</CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable
            data={filteredUsers}
            columns={columns}
            keyExtractor={(u) => u.user_id}
            className="mt-0"
          />
        </CardContent>
      </Card>
      
      <UserModal 
        isOpen={modalOpen} 
        onClose={() => setModalOpen(false)} 
        user={selectedUser}
        onSuccess={fetchUsers}
      />
    </div>
  );
}
