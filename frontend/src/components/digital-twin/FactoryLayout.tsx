import React, { useRef, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Html, Grid, ContactShadows, useGLTF, Clone } from '@react-three/drei';
import * as THREE from 'three';
import type { Machine, SensorReading } from '@/types';
import { clsx } from 'clsx';
import { Badge } from '@/components/ui/Badge';
import { Activity } from 'lucide-react';

interface FactoryLayoutProps {
  machines: Machine[];
  liveSensors: Record<string, SensorReading>;
  onMachineClick: (machine: Machine) => void;
}

const MACHINE_POSITIONS: [number, number, number][] = [
  [-4, 0, -2],
  [0, 0, -2],
  [4, 0, -2],
  [-2, 0, 2],
  [2, 0, 2],
];

const STATUS_COLORS = {
  normal: '#10b981',   // emerald-500
  warning: '#f59e0b',  // amber-500
  critical: '#ef4444', // red-500
  offline: '#6b7280',  // gray-500
};

function MachineModel({ 
  machine, 
  position, 
  sensor, 
  onClick 
}: { 
  machine: Machine, 
  position: [number, number, number], 
  sensor?: SensorReading, 
  onClick: () => void 
}) {
  const meshRef = useRef<THREE.Group>(null);
  const [hovered, setHovered] = useState(false);

  // Rotate machine part based on RPM
  useFrame((_, delta) => {
    if (meshRef.current && sensor && machine.status !== 'offline') {
      // Base rotation speed on RPM, scaled down for visual comfort
      const rpm = sensor.rpm || 0;
      const speed = (rpm / 1000) * delta;
      meshRef.current.rotation.y += speed;
    }
  });

  const color = STATUS_COLORS[machine.status as keyof typeof STATUS_COLORS] || STATUS_COLORS.offline;

  // Determine geometry based on type (simple heuristic)
  
  // Load the enhanced model
  const { scene } = useGLTF('/models/white_mesh.glb');

  return (
    <group position={position} onClick={(e) => { e.stopPropagation(); onClick(); }} onPointerOver={() => setHovered(true)} onPointerOut={() => setHovered(false)}>
      {/* Base */}
      <mesh position={[0, 0.25, 0]} castShadow receiveShadow>
        <boxGeometry args={[1.5, 0.5, 1.5]} />
        <meshStandardMaterial color={hovered ? '#4b5563' : '#374151'} metalness={0.8} roughness={0.2} />
      </mesh>

      {/* Rotating/Main Part */}
      <group ref={meshRef} position={[0, 1, 0]}>
        {/* Illuminate the premium white mesh with the status color */}
        <pointLight distance={4} intensity={hovered ? 8 : 4} color={color} position={[0, 1, 0]} />
        <Clone object={scene} castShadow receiveShadow scale={1.2} position={[0, -0.5, 0]} />
      </group>

      {/* HTML Tooltip */}
      {hovered && (
        <Html position={[0, 2.5, 0]} center zIndexRange={[100, 0]} className="pointer-events-none">
          <div className="bg-background/95 backdrop-blur-md border border-primary/20 shadow-xl rounded-lg overflow-hidden w-64 animate-in fade-in zoom-in-95 duration-200">
            <div className="h-1 w-full" style={{ backgroundColor: color }} />
            <div className="p-3 space-y-2">
              <div className="flex justify-between items-start">
                <div>
                  <h4 className="font-bold text-sm truncate text-foreground">{machine.name}</h4>
                  <p className="text-xs text-muted-foreground">{machine.type}</p>
                </div>
                <Badge variant={machine.status === 'normal' ? 'success' : machine.status === 'warning' ? 'warning' : 'destructive'} className="uppercase text-[10px] scale-90 origin-top-right">
                  {machine.status}
                </Badge>
              </div>
              
              {sensor && (
                <div className="grid grid-cols-2 gap-2 mt-2 pt-2 border-t border-border/50">
                  <div>
                    <p className="text-[10px] text-muted-foreground">Temperature</p>
                    <p className={clsx("text-xs font-mono font-medium", sensor.temperature > 85 ? "text-red-500" : "text-emerald-500")}>
                      {sensor.temperature.toFixed(1)}°C
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] text-muted-foreground">RPM</p>
                    <p className="text-xs font-mono font-medium text-primary">
                      {sensor.rpm.toFixed(0)}
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] text-muted-foreground">Vibration</p>
                    <p className={clsx("text-xs font-mono font-medium", sensor.vibration > 0.45 ? "text-amber-500" : "text-emerald-500")}>
                      {sensor.vibration.toFixed(2)}
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] text-muted-foreground">Pressure</p>
                    <p className="text-xs font-mono font-medium text-foreground">
                      {sensor.pressure.toFixed(1)}
                    </p>
                  </div>
                </div>
              )}
              
              <div className="flex items-center text-[10px] text-primary pt-1">
                <Activity className="w-3 h-3 mr-1" /> Click for details
              </div>
            </div>
          </div>
        </Html>
      )}
    </group>
  );
}

export function FactoryLayout({ machines, liveSensors, onMachineClick }: FactoryLayoutProps) {
  return (
    <div className="relative w-full aspect-[16/9] bg-background rounded-xl overflow-hidden border border-border/50 shadow-inner">
      <Canvas shadows camera={{ position: [0, 8, 12], fov: 45 }}>
        <React.Suspense fallback={null}>
          <color attach="background" args={['#09090b']} /> {/* match dark background */}
          
          <ambientLight intensity={0.4} />
          <directionalLight
            castShadow
            position={[10, 10, 5]}
            intensity={1.5}
            shadow-mapSize={[1024, 1024]}
          />
          <pointLight position={[-10, -10, -10]} intensity={0.5} />

          {/* <Environment preset="city" /> removed to prevent external network fetch failure */}

          <Grid
            infiniteGrid
            fadeDistance={30}
            sectionColor="#333"
            cellColor="#1a1a1a"
            cellSize={1}
            sectionSize={5}
          />

          <ContactShadows position={[0, 0.01, 0]} opacity={0.4} scale={20} blur={2} far={4.5} />

          {machines.map((machine, idx) => (
            <MachineModel
              key={machine.machine_id}
              machine={machine}
              position={MACHINE_POSITIONS[idx % MACHINE_POSITIONS.length]}
              sensor={liveSensors[machine.machine_id]}
              onClick={() => onMachineClick(machine)}
            />
          ))}

          <OrbitControls 
            makeDefault
            minPolarAngle={0} 
            maxPolarAngle={Math.PI / 2.1} 
            minDistance={5}
            maxDistance={30}
            enablePan={true}
          />
        </React.Suspense>
      </Canvas>
    </div>
  );
}
