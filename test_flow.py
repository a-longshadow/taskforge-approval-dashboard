import json, sys, time, requests
from pathlib import Path

SERVER = "http://127.0.0.1:8080"
PAYLOAD_PATH = Path("_temp/build-payload.json")

if not PAYLOAD_PATH.exists():
    print("Payload file not found:", PAYLOAD_PATH)
    sys.exit(1)

payload_full = json.loads(PAYLOAD_PATH.read_text())
if isinstance(payload_full, list):
    payload = payload_full[0]["railway_payload"]
else:
    payload = payload_full  # already minimal form

exec_id = payload["execution_id"]
print("▶ Using execution_id:", exec_id)

# 1) store-tasks
r = requests.post(f"{SERVER}/store-tasks", json=payload)
assert r.status_code == 200, r.text
print("store-tasks ✅")

# 2) get-tasks
r = requests.get(f"{SERVER}/get-tasks/{exec_id}")
assert r.status_code == 200, r.text
resp_get = r.json()
assert resp_get["total_tasks"] == payload["total_tasks"], "Mismatch in task count"
print("get-tasks ✅")

# 3) submit-approval (approve all)
approved_tasks = resp_get["monday_tasks"]
for t in approved_tasks:
    t["approved"] = True

approval_payload = {
    "execution_id": exec_id,
    "monday_tasks_with_approval": approved_tasks
}

r = requests.post(f"{SERVER}/submit-approval", json=approval_payload)
assert r.status_code == 200, r.text
print("submit-approval ✅")

# 4) get-approved should return approved list then self-destruct
r = requests.get(f"{SERVER}/get-approved", params={"execution_id": exec_id})
assert r.status_code == 200, r.text
resp_approved = r.json()
assert resp_approved["approved_count"] == payload["total_tasks"], "Approved count mismatch"
print("get-approved ✅ (received)")

# Call again to ensure self-destruct yields 404
r = requests.get(f"{SERVER}/get-approved", params={"execution_id": exec_id})
assert r.status_code == 404, "Self-destruct failed, expected 404"
print("self-destruct ✅")

print("All integration steps passed ✔️") 