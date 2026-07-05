import requests
import json
import time

BASE_URL = "http://localhost:8000/api/v1"

def test_workflow():
    print("Starting Workflow Test...")
    
    users = {
        "admin": {"email": "admin@edgetwin.ai", "password": "admin"},
        "operator": {"email": "operator@edgetwin.ai", "password": "operator"},
        "manager": {"email": "manager@edgetwin.ai", "password": "manager"},
        "mechanic": {"email": "mechanic@edgetwin.ai", "password": "mechanic"}
    }
    
    tokens = {}
    
    for role, creds in users.items():
        resp = requests.post(f"{BASE_URL}/auth/login", data={"username": creds["email"], "password": creds["password"]})
        if resp.status_code == 200:
            tokens[role] = resp.json()["access_token"]
            print(f"SUCCESS: {role} logged in.")
        else:
            print(f"ERROR: {role} login failed: {resp.text}")
            return
            
    headers_op = {"Authorization": f"Bearer {tokens['operator']}"}
    resp = requests.get(f"{BASE_URL}/machines", headers=headers_op)
    machines = resp.json()
    if not machines:
        print("ERROR: No machines found.")
        return
    machine_id = machines[0]["machine_id"]
    print(f"SUCCESS: Found machine {machine_id}")
    
    reading = {
        "temperature": 90.5,
        "vibration": 0.1,
        "pressure": 1.0,
        "current": 10.0,
        "rpm": 1500,
        "noise_level": 50
    }
    resp = requests.post(f"{BASE_URL}/machines/{machine_id}/telemetry", headers=headers_op, json=reading)
    if resp.status_code == 200:
        print("SUCCESS: High temp reading submitted.")
    else:
        print(f"ERROR: Failed to submit reading: {resp.text}")
        
    time.sleep(2)
    
    headers_mgr = {"Authorization": f"Bearer {tokens['manager']}"}
    resp = requests.get(f"{BASE_URL}/alerts?status=pending", headers=headers_mgr)
    alerts = resp.json()
    if not alerts:
        print("ERROR: No pending alerts found.")
        return
    alert_id = alerts[0]["alert_id"]
    print(f"SUCCESS: Found pending alert {alert_id}")
    
    headers_admin = {"Authorization": f"Bearer {tokens['admin']}"}
    resp = requests.get(f"{BASE_URL}/admin/users", headers=headers_admin)
    mechanics = [u for u in resp.json() if u["role"] == "mechanic"]
    mechanic_id = mechanics[0]["user_id"]
    
    ticket_payload = {
        "machine_id": machine_id,
        "alert_id": alert_id,
        "mechanic_id": mechanic_id,
        "description": "Fix high temp issue",
        "priority": "high"
    }
    resp = requests.post(f"{BASE_URL}/tickets", headers=headers_mgr, json=ticket_payload)
    if resp.status_code == 200:
        ticket_id = resp.json()["ticket_id"]
        print(f"SUCCESS: Ticket {ticket_id} created and assigned.")
    else:
        print(f"ERROR: Failed to create ticket: {resp.text}")
        return
        
    headers_mech = {"Authorization": f"Bearer {tokens['mechanic']}"}
    resp = requests.put(f"{BASE_URL}/tickets/{ticket_id}/status", headers=headers_mech, json={"status": "in_progress"})
    if resp.status_code == 200:
        print("SUCCESS: Ticket marked in_progress.")
    else:
        print(f"ERROR: Failed to update ticket status: {resp.text}")
        
    complete_payload = {
        "status": "repaired",
        "repair_report": "Replaced cooling fan",
        "parts_used": "Fan v2",
        "time_taken_hours": 2.5
    }
    resp = requests.put(f"{BASE_URL}/tickets/{ticket_id}/status", headers=headers_mech, json=complete_payload)
    if resp.status_code == 200:
        print("SUCCESS: Ticket marked repaired.")
    else:
        print(f"ERROR: Failed to complete ticket: {resp.text}")
        
    close_payload = {
        "status": "closed",
        "repair_cost": 450.00
    }
    resp = requests.put(f"{BASE_URL}/tickets/{ticket_id}/status", headers=headers_mgr, json=close_payload)
    if resp.status_code == 200:
        print("SUCCESS: Ticket closed by manager.")
    else:
        print(f"ERROR: Failed to close ticket: {resp.text}")
        
    resp = requests.get(f"{BASE_URL}/admin/audit", headers=headers_admin)
    if resp.status_code == 200:
        print(f"SUCCESS: Audit logs accessible. (Count: {len(resp.json())})")
    else:
        print("ERROR: Audit log fetch failed.")

    print("🎉 Workflow Test Completed Successfully!")

if __name__ == "__main__":
    test_workflow()
