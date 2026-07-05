import { useState, useEffect } from 'react';
import { machineService } from '@/services/machineService';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { DataTable } from '@/components/ui/DataTable';
import { LoadingScreen } from '@/components/layout/LoadingScreen';
import { useToast } from '@/hooks/useToast';
import type { Machine } from '@/types';
import { Plus, Edit2, Settings, Trash2 } from 'lucide-react';
import { MachineModal } from '@/components/admin/MachineModal';

export default function MachineManagementPage() {
  const { toast } = useToast();
  const [machines, setMachines] = useState<Machine[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedMachine, setSelectedMachine] = useState<Machine | undefined>(undefined);

  const fetchMachines = async () => {
    try {
      setIsLoading(true);
      const data = await machineService.getAll();
      setMachines(data);
    } catch (error) {
      console.error('Failed to load machines:', error);
      toast({ title: 'Error', description: 'Failed to load machines', variant: 'destructive' });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMachines();
  }, []);

  if (isLoading) return <LoadingScreen />;

  const columns = [
    {
      header: 'Machine',
      cell: (m: Machine) => (
        <div>
          <p className="font-medium">{m.name}</p>
          <p className="text-xs text-muted-foreground">{m.type}</p>
        </div>
      )
    },
    {
      header: 'Status',
      cell: (m: Machine) => {
        const colors: Record<string, string> = {
          operational: 'success',
          maintenance: 'warning',
          offline: 'destructive'
        };
        return (
          <Badge variant={(colors[m.status] as any) || 'default'} className="uppercase text-[10px]">
            {m.status}
          </Badge>
        );
      }
    },
    {
      header: 'Location',
      accessorKey: 'location' as keyof Machine,
    },
    {
      header: 'Actions',
      cell: (m: Machine) => (
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              setSelectedMachine(m);
              setModalOpen(true);
            }}
          >
            <Edit2 className="w-4 h-4 mr-1" /> Edit
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              toast({ title: 'Info', description: 'Settings modal not implemented yet.' });
            }}
          >
            <Settings className="w-4 h-4 mr-1" /> Config
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={async (e) => {
              e.stopPropagation();
              try {
                await machineService.deleteMachine(m.machine_id);
                toast({ title: 'Success', description: 'Machine deleted successfully' });
                fetchMachines();
              } catch (error) {
                toast({ title: 'Error', description: 'Failed to delete machine', variant: 'destructive' });
              }
            }}
          >
            <Trash2 className="w-4 h-4 mr-1" /> Delete
          </Button>
        </div>
      )
    }
  ];

  return (
    <div className="p-6 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-5xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Machine Management</h1>
          <p className="text-muted-foreground mt-1">Configure factory equipment and manage statuses.</p>
        </div>
        <Button onClick={() => { setSelectedMachine(undefined); setModalOpen(true); }}>
          <Plus className="w-4 h-4 mr-2" /> Add Machine
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Fleet Directory</CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable
            data={machines}
            columns={columns}
            keyExtractor={(m) => m.machine_id}
            className="mt-0"
          />
        </CardContent>
      </Card>
      
      <MachineModal 
        isOpen={modalOpen} 
        onClose={() => setModalOpen(false)} 
        machine={selectedMachine}
        onSuccess={fetchMachines}
      />
    </div>
  );
}
