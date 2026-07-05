// ─── Report Issue Modal ───────────────────────────────────────────────────────
import { useState } from 'react';
import { Camera, Mic, FileVideo2 } from 'lucide-react';
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
import { alertService } from '@/services/ticketService';
import type { Alert } from '@/types';
import { useToast } from '@/hooks/useToast';

export interface ReportIssueModalProps {
  isOpen: boolean;
  onClose: () => void;
  alert: Alert | null;
  onSuccess: () => void;
}

export function ReportIssueModal({ isOpen, onClose, alert, onSuccess }: ReportIssueModalProps) {
  const { user } = useAuth();
  const { toast } = useToast();
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!alert || !user || !description.trim()) return;

    setIsSubmitting(true);
    try {
      await alertService.reportIssue(
        alert.alert_id,
        { description },
        user.user_id,
        user.name
      );
      toast({
        title: 'Issue Reported',
        description: 'A maintenance ticket has been automatically created.',
      });
      onSuccess();
      onClose();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to report issue. Please try again.',
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
          <ModalTitle>Report Issue</ModalTitle>
          <ModalDescription>
            Provide details about the issue with {alert?.machine_name}. This will create a maintenance ticket.
          </ModalDescription>
        </ModalHeader>
        
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">
              Description <span className="text-destructive">*</span>
            </label>
            <textarea
              className="flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              placeholder="Describe what you observed (sounds, smells, visual damage)..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={isSubmitting}
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">Attachments (Optional)</label>
            <div className="flex gap-2">
              <label className="flex-1 cursor-pointer">
                <input type="file" accept="image/*" className="hidden" />
                <Button asChild variant="outline" size="sm" className="w-full pointer-events-none" disabled={isSubmitting}>
                  <div>
                    <Camera className="w-4 h-4 mr-2" /> Photo
                  </div>
                </Button>
              </label>
              
              <label className="flex-1 cursor-pointer">
                <input type="file" accept="video/*" className="hidden" />
                <Button asChild variant="outline" size="sm" className="w-full pointer-events-none" disabled={isSubmitting}>
                  <div>
                    <FileVideo2 className="w-4 h-4 mr-2" /> Video
                  </div>
                </Button>
              </label>

              <Button variant="outline" size="sm" type="button" className="flex-1" disabled={isSubmitting}>
                <Mic className="w-4 h-4 mr-2" /> Voice Note
              </Button>
            </div>
            <p className="text-xs text-muted-foreground pt-1">
              * In this mock prototype, attachments open the file explorer but are not uploaded.
            </p>
          </div>
        </div>

        <ModalFooter>
          <ModalClose asChild>
            <Button variant="ghost" disabled={isSubmitting}>Cancel</Button>
          </ModalClose>
          <Button onClick={handleSubmit} disabled={isSubmitting || !description.trim()} isLoading={isSubmitting}>
            Submit Report
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}
