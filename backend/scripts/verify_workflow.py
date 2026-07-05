import asyncio
import httpx
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"

async def verify_workflow():
    print("Starting automated workflow verification...")
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # 1. Login as admin to get token
        login_data = {"username": "admin@edgetwin.ai", "password": "password"}
        resp = await client.post("/auth/login", data=login_data)
        if resp.status_code != 200:
            print("❌ Admin login failed")
            return
        admin_token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {admin_token}"}
        print("✅ Admin login successful")

        # 2. Get Users
        resp = await client.get("/admin/users", headers=headers)
        if resp.status_code != 200:
            print("❌ Get users failed")
            return
        users = resp.json()
        print("✅ Get users successful")

        operator = next((u for u in users if u["role"] == "operator"), None)
        mechanic = next((u for u in users if u["role"] == "mechanic"), None)
        manager = next((u for u in users if u["role"] == "maintenance_manager"), None)

        if not operator or not mechanic or not manager:
            print("❌ Required roles missing in DB")
            return

        # 3. Create a ticket (simulate operator reporting issue)
        # First get a machine and alert
        resp = await client.get("/machines", headers=headers)
        machines = resp.json()
        machine = machines[0]
        
        # We need an alert ID. Let's get active alerts
        resp = await client.get("/alerts?status=pending", headers=headers)
        alerts = resp.json()
        
        if not alerts:
             # Just use a dummy uuid if no pending alert
             print("⚠️ No pending alerts, skipping ticket creation test")
        else:
            alert_id = alerts[0]["alert_id"]
            # Operator Login
            resp = await client.post("/auth/login", data={"username": operator["email"], "password": "password"})
            op_token = resp.json()["access_token"]
            op_headers = {"Authorization": f"Bearer {op_token}"}
            
            # Report issue
            payload = {
                "description": "Test Workflow issue",
                "operator_id": operator["user_id"]
            }
            resp = await client.post(f"/alerts/{alert_id}/report", json=payload, headers=op_headers)
            if resp.status_code != 200:
                print(f"❌ Report issue failed: {resp.text}")
            else:
                ticket_id = resp.json()["ticket_id"]
                print("✅ Report issue successful")
                
                # Manager assigns mechanic
                resp = await client.post("/auth/login", data={"username": manager["email"], "password": "password"})
                mgr_token = resp.json()["access_token"]
                mgr_headers = {"Authorization": f"Bearer {mgr_token}"}
                
                resp = await client.put(f"/tickets/{ticket_id}", json={
                    "mechanic_id": mechanic["user_id"],
                    "manager_id": manager["user_id"],
                    "status": "assigned"
                }, headers=mgr_headers)
                
                if resp.status_code == 200:
                     print("✅ Assign mechanic successful")
                else:
                     print(f"❌ Assign mechanic failed: {resp.text}")
                     
    print("\n🎉 Automated workflow verification completed!")

if __name__ == "__main__":
    asyncio.run(verify_workflow())
