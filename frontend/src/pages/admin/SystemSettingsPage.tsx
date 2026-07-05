import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useToast } from '@/hooks/useToast';
import { Save, Bell, Shield, Settings2 } from 'lucide-react';

export default function SystemSettingsPage() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  
  const [thresholds, setThresholds] = useState({
    tempWarning: '75',
    tempCritical: '85',
    vibWarning: '0.45',
    vibCritical: '0.65',
    pressureWarning: '110',
    pressureCritical: '130',
  });

  const handleSave = async () => {
    setLoading(true);
    // Simulate API call
    await new Promise(r => setTimeout(r, 800));
    setLoading(false);
    toast({ title: 'Settings Saved', description: 'System configuration has been updated successfully.' });
  };

  const [activeTab, setActiveTab] = useState('alert');

  return (
    <div className="p-6 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-5xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">System Configuration</h1>
        <p className="text-muted-foreground mt-1">Manage global alert thresholds, security policies, and application settings.</p>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        {/* Sidebar Nav */}
        <div className="flex flex-col gap-2">
          <Button 
            variant={activeTab === 'alert' ? 'secondary' : 'ghost'} 
            className={`justify-start ${activeTab !== 'alert' && 'text-muted-foreground hover:text-foreground'}`}
            onClick={() => setActiveTab('alert')}
          >
            <Bell className="w-4 h-4 mr-2" /> Alert Configuration
          </Button>
          <Button 
            variant={activeTab === 'security' ? 'secondary' : 'ghost'} 
            className={`justify-start ${activeTab !== 'security' && 'text-muted-foreground hover:text-foreground'}`}
            onClick={() => setActiveTab('security')}
          >
            <Shield className="w-4 h-4 mr-2" /> Security & Roles
          </Button>
          <Button 
            variant={activeTab === 'general' ? 'secondary' : 'ghost'} 
            className={`justify-start ${activeTab !== 'general' && 'text-muted-foreground hover:text-foreground'}`}
            onClick={() => setActiveTab('general')}
          >
            <Settings2 className="w-4 h-4 mr-2" /> General Settings
          </Button>
        </div>

        {/* Content */}
        <div className="md:col-span-2 space-y-6">
          {activeTab === 'alert' && (
            <Card>
              <CardHeader>
                <CardTitle>Global Alert Thresholds</CardTitle>
                <CardDescription>Configure the baseline values that trigger automated alerts across the factory.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Temperature Warning (°C)</label>
                    <Input 
                      type="number" 
                      value={thresholds.tempWarning} 
                      onChange={e => setThresholds(p => ({ ...p, tempWarning: e.target.value }))} 
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-destructive">Temperature Critical (°C)</label>
                    <Input 
                      type="number" 
                      className="border-destructive/50 focus-visible:ring-destructive"
                      value={thresholds.tempCritical} 
                      onChange={e => setThresholds(p => ({ ...p, tempCritical: e.target.value }))} 
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Vibration Warning (mm/s)</label>
                    <Input 
                      type="number" step="0.01"
                      value={thresholds.vibWarning} 
                      onChange={e => setThresholds(p => ({ ...p, vibWarning: e.target.value }))} 
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-destructive">Vibration Critical (mm/s)</label>
                    <Input 
                      type="number" step="0.01"
                      className="border-destructive/50 focus-visible:ring-destructive"
                      value={thresholds.vibCritical} 
                      onChange={e => setThresholds(p => ({ ...p, vibCritical: e.target.value }))} 
                    />
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Pressure Warning (PSI)</label>
                    <Input 
                      type="number" 
                      value={thresholds.pressureWarning} 
                      onChange={e => setThresholds(p => ({ ...p, pressureWarning: e.target.value }))} 
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-destructive">Pressure Critical (PSI)</label>
                    <Input 
                      type="number" 
                      className="border-destructive/50 focus-visible:ring-destructive"
                      value={thresholds.pressureCritical} 
                      onChange={e => setThresholds(p => ({ ...p, pressureCritical: e.target.value }))} 
                    />
                  </div>
                </div>

              </CardContent>
            </Card>
          )}

          {activeTab === 'security' && (
            <Card>
              <CardHeader>
                <CardTitle>Security & Roles</CardTitle>
                <CardDescription>Manage password policies, session timeouts, and role-based access.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="text-sm text-muted-foreground p-4 bg-secondary/20 rounded-lg text-center">
                  Security configuration is managed through the central IAM provider.
                </div>
              </CardContent>
            </Card>
          )}

          {activeTab === 'general' && (
            <Card>
              <CardHeader>
                <CardTitle>General Settings</CardTitle>
                <CardDescription>System-wide defaults and branding.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Factory Name</label>
                  <Input defaultValue="EdgeTwin Prime Facility" />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Timezone</label>
                  <Input defaultValue="UTC" />
                </div>
              </CardContent>
            </Card>
          )}
          
          <div className="flex justify-end">
            <Button onClick={handleSave} disabled={loading} size="lg">
              <Save className="w-4 h-4 mr-2" />
              {loading ? 'Saving Changes...' : 'Save Configuration'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
