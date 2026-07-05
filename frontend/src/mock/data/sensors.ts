// ─── Sensor Readings Generator ────────────────────────────────────────────────
// Generates realistic time-series sensor data for each machine over the past 24 hours.

import type { SensorReading } from '@/types';

interface SensorProfile {
  tempBase: number;  tempVar: number;
  vibBase: number;   vibVar: number;
  pressBase: number; pressVar: number;
  currentBase: number; currentVar: number;
  rpmBase: number;   rpmVar: number;
  noiseBase: number; noiseVar: number;
}

const PROFILES: Record<string, SensorProfile> = {
  'MCH-001': { tempBase: 52, tempVar: 8, vibBase: 2.1, vibVar: 1.2, pressBase: 5.5, pressVar: 1.5, currentBase: 10, currentVar: 3, rpmBase: 2400, rpmVar: 300, noiseBase: 65, noiseVar: 8 },
  'MCH-002': { tempBase: 60, tempVar: 12, vibBase: 4.2, vibVar: 2.0, pressBase: 3.0, pressVar: 1.0, currentBase: 8, currentVar: 2, rpmBase: 1200, rpmVar: 200, noiseBase: 72, noiseVar: 10 },
  'MCH-003': { tempBase: 48, tempVar: 5, vibBase: 1.5, vibVar: 0.8, pressBase: 9.0, pressVar: 1.5, currentBase: 14, currentVar: 3, rpmBase: 800, rpmVar: 100, noiseBase: 58, noiseVar: 6 },
  'MCH-004': { tempBase: 78, tempVar: 15, vibBase: 6.5, vibVar: 3.0, pressBase: 10.5, pressVar: 2.5, currentBase: 17, currentVar: 4, rpmBase: 3200, rpmVar: 400, noiseBase: 85, noiseVar: 12 },
  'MCH-005': { tempBase: 92, tempVar: 10, vibBase: 9.0, vibVar: 3.5, pressBase: 11.0, pressVar: 2.0, currentBase: 19, currentVar: 3, rpmBase: 3500, rpmVar: 200, noiseBase: 92, noiseVar: 8 },
  'MCH-006': { tempBase: 55, tempVar: 10, vibBase: 3.0, vibVar: 1.5, pressBase: 4.0, pressVar: 1.0, currentBase: 12, currentVar: 3, rpmBase: 1800, rpmVar: 250, noiseBase: 70, noiseVar: 9 },
  'MCH-007': { tempBase: 45, tempVar: 6, vibBase: 1.8, vibVar: 0.7, pressBase: 4.5, pressVar: 1.0, currentBase: 9, currentVar: 2, rpmBase: 2000, rpmVar: 200, noiseBase: 60, noiseVar: 5 },
  'MCH-008': { tempBase: 68, tempVar: 14, vibBase: 5.0, vibVar: 2.5, pressBase: 8.0, pressVar: 2.0, currentBase: 15, currentVar: 4, rpmBase: 1600, rpmVar: 300, noiseBase: 78, noiseVar: 10 },
};

function rand(base: number, variance: number): number {
  return +(base + (Math.random() - 0.5) * 2 * variance).toFixed(2);
}

export function generateSensorReadings(
  machineId: string,
  count: number = 96, // 24h at 15-min intervals
): SensorReading[] {
  const profile = PROFILES[machineId] || PROFILES['MCH-001'];
  const now = Date.now();
  const intervalMs = 15 * 60_000; // 15 minutes

  return Array.from({ length: count }, (_, i) => ({
    reading_id: `SR-${machineId}-${String(i).padStart(4, '0')}`,
    machine_id: machineId,
    timestamp: new Date(now - (count - 1 - i) * intervalMs).toISOString(),
    temperature: rand(profile.tempBase, profile.tempVar),
    vibration: rand(profile.vibBase, profile.vibVar),
    pressure: rand(profile.pressBase, profile.pressVar),
    current: rand(profile.currentBase, profile.currentVar),
    rpm: Math.round(rand(profile.rpmBase, profile.rpmVar)),
    noise_level: rand(profile.noiseBase, profile.noiseVar),
  }));
}

// Pre-generated readings for immediate use (latest reading per machine)
export function getLatestReading(machineId: string): SensorReading {
  const readings = generateSensorReadings(machineId, 1);
  return readings[0];
}
