import { useState } from 'react';
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
import { useAuth } from '@/hooks/useAuth';
import { ticketService } from '@/services/ticketService';
import type { Ticket } from '@/types';
import { useToast } from '@/hooks/useToast';

export interface ReviewTicketModalProps {
  isOpen: boolean;
  onClose: () => void;
  ticket: Ticket | null;
  onSuccess: () => void;
}

export function ReviewTicketModal({ isOpen, onClose, ticket, onSuccess }: ReviewTicketModalProps) {
  const { user } = useAuth();
  const { toast } = useToast();
  const [cost, setCost] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleReview = async () => {
    if (!ticket || !user) return;
    const costValue = parseFloat(cost);
    if (isNaN(costValue)) {
      toast({ title: 'Error', description: 'Please enter a valid cost', variant: 'destructive' });
      return;
    }

    setIsSubmitting(true);
    try {
      await ticketService.reviewAndAddCost(ticket.ticket_id, costValue, user.user_id, user.name);
      toast({ title: 'Reviewed', description: 'Ticket reviewed and cost added.' });
      onSuccess();
      onClose();
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to review ticket', variant: 'destructive' });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <ModalContent>
        <ModalHeader>
          <ModalTitle>Review Ticket</ModalTitle>
          <ModalDescription>Review repair and enter final repair cost.</ModalDescription>
        </ModalHeader>
        <div className="py-4 space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">Repair Report</label>
            <p className="text-sm text-muted-foreground p-3 border rounded-md">{ticket?.repair_report || 'No report provided'}</p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Parts Used</label>
              <p className="text-sm text-muted-foreground p-3 border rounded-md">{ticket?.parts_used || 'None'}</p>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Time Taken (Hours)</label>
              <p className="text-sm text-muted-foreground p-3 border rounded-md">{ticket?.time_taken_hours || 0}</p>
            </div>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">Repair Cost ($)</label>
            <input
              type="number"
              className="flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
              placeholder="e.g. 150.00"
              value={cost}
              onChange={(e) => setCost(e.target.value)}
            />
          </div>
        </div>
        <ModalFooter>
          <ModalClose asChild>
            <Button variant="ghost" disabled={isSubmitting}>Cancel</Button>
          </ModalClose>
          <Button onClick={handleReview} disabled={isSubmitting || !cost} isLoading={isSubmitting}>
            Approve & Save
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}
