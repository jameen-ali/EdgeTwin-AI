"""
EdgeTwin AI — IoT Sensor Simulator
====================================
Simulates high-frequency telemetry data for all registered machines.
Sends data via HTTP POST to the FastAPI ingestion endpoint.

Usage:
  python iot/edge_agent/sensor_simulator.py
"""

import time
import random
import requests
import os
import sys
from datetime import datetime, timezone
import json

# Setup
API_URL = os.environ.get("VITE_API_URL", "http://localhost:8000") + "/api/v1"
ADMIN_EMAIL = "admin@edgetwin.ai"
ADMIN_PASS = "Admin@EdgeTwin24!"

def get_token():
    print("🔑 Authenticating as System Admin...")
    response = requests.post(f"{API_URL}/auth/login", data={
        "username": ADMIN_EMAIL,
        "password": ADMIN_PASS
    })
    if response.status_code != 200:
        print("❌ Auth failed:", response.text)
        sys.exit(1)
    return response.json()["access_token"]

def get_machines(token: str):
    print("📡 Fetching registered machines...")
    response = requests.get(f"{API_URL}/machines", headers={"Authorization": f"Bearer {token}"})
    if response.status_code != 200:
        print("❌ Failed to fetch machines:", response.text)
        sys.exit(1)
    return response.json()

def generate_reading(machine: dict):
    """Generate realistic telemetry data based on machine type and current status."""
    status = machine.get("status", "normal")
    type_ = machine.get("type", "").lower()
    
    # Base values
    temp_base = 45.0
    vib_base = 2.0
    pressure_base = 100.0
    rpm_base = 1500.0
    noise_base = 75.0
    current_base = 15.0
    
    # Add noise based on status
    if status == "warning":
        temp_base += 15.0
        vib_base += 1.5
    elif status == "critical":
        temp_base += 35.0
        vib_base += 4.0
        noise_base += 15.0
        
    return {
        "machine_id": machine["machine_id"],
        "temperature": round(temp_base + random.uniform(-2, 2), 2),
        "vibration": round(vib_base + random.uniform(-0.5, 0.5), 2),
        "pressure": round(pressure_base + random.uniform(-5, 5), 2),
        "current": round(current_base + random.uniform(-1, 1), 2),
        "rpm": round(rpm_base + random.uniform(-50, 50), 2),
        "noise_level": round(noise_base + random.uniform(-3, 3), 2),
    }

def run_simulation():
    print("🚀 Starting EdgeTwin AI Sensor Simulator...")
    token = get_token()
    machines = get_machines(token)
    
    if not machines:
        print("⚠️ No machines found. Run database seeder first.")
        sys.exit(1)
        
    print(f"✅ Found {len(machines)} machines. Beginning telemetry stream (1 reading / 5 seconds)...\n")
    
    try:
        while True:
            for machine in machines:
                # If machine is offline, skip
                if machine.get("status") == "offline":
                    continue
                    
                reading = generate_reading(machine)
                try:
                    res = requests.post(
                        f"{API_URL}/machines/{machine['machine_id']}/sensors",
                        json=reading,
                        # No auth header needed if we leave it open, but let's pass it anyway
                        # since the endpoint doesn't strictly require it right now in our implementation,
                        # but it's good practice.
                        headers={"Authorization": f"Bearer {token}"}
                    )
                    if res.status_code == 200:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📡 Sent {machine['name']}: {reading['temperature']}°C, {reading['vibration']}mm/s")
                    else:
                        print(f"❌ Failed to send for {machine['name']}: {res.status_code}")
                except Exception as e:
                    print(f"❌ Connection error: {e}")
                    
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n🛑 Simulation stopped.")

if __name__ == "__main__":
    run_simulation()
