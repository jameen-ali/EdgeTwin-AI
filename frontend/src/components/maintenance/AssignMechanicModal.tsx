// ─── Assign Mechanic Modal ──────────────────────────────────────────────────
import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/Button';
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalTitle,
  ModalDescription,
  ModalFooter,
  ModalClose,
} from '@/components/ui/Modal';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select';
import { useAuth } from '@/hooks/useAuth';
import { ticketService, mechanicService } from '@/services/ticketService';
import type { Ticket, Mechanic } from '@/types';
import { useToast } from '@/hooks/useToast';
import { StatusDot } from '@/components/ui/StatusDot';

export interface AssignMechanicModalProps {
  isOpen: boolean;
  onClose: () => void;
  ticket: Ticket | null;
  onSuccess: () => void;
}

export function AssignMechanicModal({ isOpen, onClose, ticket, onSuccess }: AssignMechanicModalProps) {
  const { user } = useAuth();
  const { toast } = useToast();
  const [mechanics, setMechanics] = useState<Mechanic[]>([]);
  const [selectedMechanicId, setSelectedMechanicId] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingMechanics, setIsLoadingMechanics] = useState(true);

  useEffect(() => {
    if (isOpen) {
      loadMechanics();
    }
  }, [isOpen]);

  const loadMechanics = async () => {
    setIsLoadingMechanics(true);
    try {
      const data = await mechanicService.getAll();
      setMechanics(data);
    } catch (error) {
      console.error('Failed to load mechanics', error);
    } finally {
      setIsLoadingMechanics(false);
    }
  };

  const handleAssign = async () => {
    if (!ticket || !user || !selectedMechanicId) return;

    setIsSubmitting(true);
    try {
      await ticketService.assignMechanic(
        ticket.ticket_id,
        selectedMechanicId,
        user.user_id,
        user.name
      );
      toast({
        title: 'Mechanic Assigned',
        description: 'The ticket has been successfully assigned.',
      });
      onSuccess();
      onClose();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to assign mechanic.',
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <ModalContent>
        <ModalHeader>
          <ModalTitle>Assign Mechanic</ModalTitle>
          <ModalDescription>
            Assign a mechanic to repair ticket {ticket?.ticket_id} for {ticket?.machine_name}.
          </ModalDescription>
        </ModalHeader>
        
        <div className="py-4 space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">Select Mechanic</label>
            <Select value={selectedMechanicId} onValueChange={setSelectedMechanicId} disabled={isSubmitting || isLoadingMechanics}>
              <SelectTrigger>
                <SelectValue placeholder={isLoadingMechanics ? "Loading..." : "Select a mechanic..."} />
              </SelectTrigger>
              <SelectContent>
                {mechanics.map((m) => (
                  <SelectItem key={m.mechanic_id} value={m.mechanic_id} disabled={m.login_status !== 'available'}>
                    <div className="flex items-center justify-between w-full min-w-[200px]">
                      <span className="flex items-center gap-2">
                        <StatusDot status={m.login_status} />
                        {m.name} ({m.skill_type})
                      </span>
                      {m.login_status !== 'available' && <span className="text-xs text-muted-foreground capitalize">{m.login_status}</span>}
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <ModalFooter>
          <ModalClose asChild>
            <Button variant="ghost" disabled={isSubmitting}>Cancel</Button>
          </ModalClose>
          <Button onClick={handleAssign} disabled={isSubmitting || !selectedMechanicId} isLoading={isSubmitting}>
            Assign
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}
