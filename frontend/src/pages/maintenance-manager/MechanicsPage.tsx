// ─── Mechanics Page ───────────────────────────────────────────────────────────
import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { mechanicService } from '@/services/ticketService';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { DataTable } from '@/components/ui/DataTable';
import { StatusDot } from '@/components/ui/StatusDot';
import { LoadingScreen } from '@/components/layout/LoadingScreen';
import { useToast } from '@/hooks/useToast';
import type { Mechanic } from '@/types';

export default function MechanicsPage() {
  const [searchParams] = useSearchParams();
  const idFilter = searchParams.get('id');

  const { toast } = useToast();
  const [mechanics, setMechanics] = useState<Mechanic[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchMechanics = async () => {
    try {
      setIsLoading(true);
      const data = await mechanicService.getAll();
      
      let filtered = data;
      if (idFilter) {
        filtered = filtered.filter((m) => m.mechanic_id === idFilter);
      }
      
      setMechanics(filtered);
    } catch (error) {
      console.error('Failed to load mechanics:', error);
      toast({
        title: 'Error',
        description: 'Failed to load mechanics data',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMechanics();
  }, [idFilter]);

  if (isLoading) return <LoadingScreen />;

  const columns = [
    {
      header: 'Mechanic',
      cell: (m: Mechanic) => (
        <div>
          <p className="font-medium">{m.name}</p>
          <p className="text-xs text-muted-foreground">{m.email}</p>
        </div>
      )
    },
    {
      header: 'Skill',
      accessorKey: 'skill_type' as keyof Mechanic,
      className: 'font-medium'
    },
    {
      header: 'Status',
      cell: (m: Mechanic) => (
        <div className="flex items-center gap-2">
          <StatusDot status={m.login_status} />
          <span className="capitalize text-sm">{m.login_status}</span>
        </div>
      )
    },
    {
      header: 'Shift',
      accessorKey: 'shift' as keyof Mechanic,
      className: 'capitalize text-sm'
    },
    {
      header: 'Contact',
      accessorKey: 'contact' as keyof Mechanic,
      className: 'text-sm text-muted-foreground hidden sm:table-cell'
    }
  ];

  return (
    <div className="p-6 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Mechanics Directory</h1>
        <p className="text-muted-foreground mt-1">
          {idFilter ? `Showing mechanic ${idFilter}` : 'Manage mechanic schedules, assignments, and availability.'}
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>All Mechanics</CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable
            data={mechanics}
            columns={columns}
            keyExtractor={(m) => m.mechanic_id}
            className="mt-0"
          />
        </CardContent>
      </Card>
    </div>
  );
}
