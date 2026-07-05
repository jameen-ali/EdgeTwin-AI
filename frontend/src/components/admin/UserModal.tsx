import { useState, useEffect } from 'react';
import { Modal, ModalContent, ModalHeader, ModalTitle } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select';
import { adminService } from '@/services/analyticsService';
import { useToast } from '@/hooks/useToast';
import type { User } from '@/types';

interface UserModalProps {
  isOpen: boolean;
  onClose: () => void;
  user?: User;
  onSuccess: () => void;
}

const ROLES = [
  { value: 'operator', label: 'Machine Operator' },
  { value: 'mechanic', label: 'Mechanic' },
  { value: 'maintenance_manager', label: 'Maintenance Manager' },
  { value: 'production_manager', label: 'Production Manager' },
  { value: 'factory_owner', label: 'Factory Owner' },
  { value: 'admin', label: 'System Admin' },
];

export function UserModal({ isOpen, onClose, user, onSuccess }: UserModalProps) {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    role: 'operator',
  });

  useEffect(() => {
    if (user) {
      setFormData({
        name: user.name,
        email: user.email,
        password: '',
        role: user.role,
      });
    } else {
      setFormData({
        name: '',
        email: '',
        password: '',
        role: 'operator',
      });
    }
  }, [user, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (user) {
        // Edit mode (password change not supported here for now)
        await adminService.updateUser(user.user_id, {
          name: formData.name,
          email: formData.email,
          // note: backend doesn't support changing role via this endpoint currently, but we can pass it if we update schema
        });
        toast({ title: 'Success', description: 'User updated successfully' });
      } else {
        // Create mode
        if (!formData.password) {
          toast({ title: 'Error', description: 'Password is required', variant: 'destructive' });
          setLoading(false);
          return;
        }
        await adminService.createUser({
          name: formData.name,
          email: formData.email,
          password: formData.password,
          role: formData.role as any,
        });
        toast({ title: 'Success', description: 'User created successfully' });
      }
      onSuccess();
      onClose();
    } catch (error: any) {
      const detail = error.response?.data?.detail;
      const message = Array.isArray(detail) ? detail.map((e: any) => e.msg).join(', ') : (detail || 'An error occurred');
      toast({ 
        title: 'Error', 
        description: message, 
        variant: 'destructive' 
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <ModalContent>
        <ModalHeader>
          <ModalTitle>{user ? 'Edit User' : 'Add User'}</ModalTitle>
        </ModalHeader>
      <form onSubmit={handleSubmit} className="space-y-4 pt-4">
        <div>
          <label className="block text-sm font-medium mb-1">Full Name</label>
          <Input 
            required 
            value={formData.name}
            onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
            placeholder="John Doe"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium mb-1">Email Address</label>
          <Input 
            required 
            type="email"
            value={formData.email}
            onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
            placeholder="john@edgetwin.ai"
          />
        </div>

        {!user && (
          <div>
            <label className="block text-sm font-medium mb-1">Password</label>
            <Input 
              required 
              type="password"
              value={formData.password}
              onChange={(e) => setFormData(prev => ({ ...prev, password: e.target.value }))}
            />
          </div>
        )}

        <div>
          <label className="block text-sm font-medium mb-1">Role</label>
          <Select
            value={formData.role}
            onValueChange={(val) => setFormData(prev => ({ ...prev, role: val }))}
            disabled={!!user} // Disable role change in edit for now to prevent breaking mechanic DB link
          >
            <SelectTrigger>
              <SelectValue placeholder="Select a role" />
            </SelectTrigger>
            <SelectContent>
              {ROLES.map(role => (
                <SelectItem key={role.value} value={role.value}>
                  {role.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex justify-end gap-3 pt-4 border-t mt-6">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={loading}>
            {loading ? 'Saving...' : 'Save User'}
          </Button>
        </div>
      </form>
      </ModalContent>
    </Modal>
  );
}
