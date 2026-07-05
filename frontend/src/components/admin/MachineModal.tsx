import { useState, useEffect } from 'react';
import { Modal, ModalContent, ModalHeader, ModalTitle } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select';
import { machineService } from '@/services/machineService';
import { adminService } from '@/services/analyticsService';
import { useToast } from '@/hooks/useToast';
import type { Machine, User } from '@/types';

interface MachineModalProps {
  isOpen: boolean;
  onClose: () => void;
  machine?: Machine;
  onSuccess: () => void;
}

const STATUS_OPTIONS = [
  { value: 'operational', label: 'Operational' },
  { value: 'maintenance', label: 'Maintenance' },
  { value: 'offline', label: 'Offline' },
];

export function MachineModal({ isOpen, onClose, machine, onSuccess }: MachineModalProps) {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [operators, setOperators] = useState<User[]>([]);
  
  const [formData, setFormData] = useState({
    name: '',
    type: '',
    location: '',
    status: 'operational',
    assigned_operator_id: '',
  });

  useEffect(() => {
    if (isOpen) {
      adminService.getUsers('operator').then(setOperators).catch(console.error);
    }
  }, [isOpen]);

  useEffect(() => {
    if (machine) {
      setFormData({
        name: machine.name,
        type: machine.type,
        location: machine.location || '',
        status: machine.status,
        assigned_operator_id: machine.assigned_operator_id || '',
      });
    } else {
      setFormData({
        name: '',
        type: '',
        location: '',
        status: 'operational',
        assigned_operator_id: '',
      });
    }
  }, [machine, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const payload = {
        name: formData.name,
        type: formData.type,
        location: formData.location || undefined,
        status: formData.status as any,
        assigned_operator_id: formData.assigned_operator_id || null, // allow null to unassign
      };

      if (machine) {
        await machineService.updateMachine(machine.machine_id, payload);
        toast({ title: 'Success', description: 'Machine updated successfully' });
      } else {
        await machineService.createMachine(payload);
        toast({ title: 'Success', description: 'Machine created successfully' });
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
          <ModalTitle>{machine ? 'Edit Machine' : 'Add Machine'}</ModalTitle>
        </ModalHeader>
      <form onSubmit={handleSubmit} className="space-y-4 pt-4">
        <div>
          <label className="block text-sm font-medium mb-1">Machine Name</label>
          <Input 
            required 
            value={formData.name}
            onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
            placeholder="e.g. CNC Lathe Alpha"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium mb-1">Type</label>
          <Input 
            required 
            value={formData.type}
            onChange={(e) => setFormData(prev => ({ ...prev, type: e.target.value }))}
            placeholder="e.g. CNC Machine"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Location</label>
          <Input 
            value={formData.location}
            onChange={(e) => setFormData(prev => ({ ...prev, location: e.target.value }))}
            placeholder="e.g. Floor 1, Section A"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Status</label>
          <Select
            value={formData.status}
            onValueChange={(val) => setFormData(prev => ({ ...prev, status: val }))}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select status" />
            </SelectTrigger>
            <SelectContent>
              {STATUS_OPTIONS.map(opt => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Assigned Operator</label>
          <Select
            value={formData.assigned_operator_id}
            onValueChange={(val) => setFormData(prev => ({ ...prev, assigned_operator_id: val }))}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select operator" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">Unassigned</SelectItem>
              {operators.map(op => (
                <SelectItem key={op.user_id} value={op.user_id}>
                  {op.name}
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
            {loading ? 'Saving...' : 'Save Machine'}
          </Button>
        </div>
      </form>
      </ModalContent>
    </Modal>
  );
}
