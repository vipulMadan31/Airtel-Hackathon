import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
import uuid
import sqlite3
from app.config import DB_PATH

base = "http://127.0.0.1:8000"

print("--- 1. Testing Mitra Partner Lead Calling & Atomic Removal ---")

# Step 1: Register an individual Mitra Partner
partner_email = f"mitra_call_{uuid.uuid4().hex[:6]}@airtelpartner.in"
partner_pwd = "PartnerCallSecure123!"
r_reg_mitra = requests.post(f"{base}/api/auth/register", json={
    "email": partner_email,
    "password": partner_pwd,
    "name": "Rohtak Central Mitra Lead Caller",
    "role": "PARTNER",
    "phone": "+91 98110 99887"
})
assert r_reg_mitra.status_code == 200, f"Registration failed: {r_reg_mitra.text}"
mitra_token = r_reg_mitra.json()["access_token"]
partner_id = r_reg_mitra.json()["user"]["user_id"]
print(f"Mitra Partner registered: {partner_email} (ID: {partner_id})")

# Step 2: Register a customer
cust_email = f"lead_caller_{uuid.uuid4().hex[:6]}@custbiz.in"
r_cust = requests.post(f"{base}/api/auth/register", json={
    "email": cust_email,
    "password": "CustomerSecure123!",
    "name": "Arjun Retail Store",
    "role": "CUSTOMER",
    "phone": "+91 98110 54321"
})
assert r_cust.status_code == 200
cust_token = r_cust.json()["access_token"]
cust_id = r_cust.json()["user"]["user_id"]

# Step 3: Seed a stalled lead in customer_leads
test_lead_id = f"LD-TEST-{uuid.uuid4().hex[:6].upper()}"
with sqlite3.connect(DB_PATH) as conn:
    conn.execute("""
        INSERT INTO customer_leads (
            lead_id, user_id, business_name, email, phone, city, pincode,
            business_type, employee_count, num_sites, monthly_spend_inr,
            has_gstin, stage_reached, drop_reason, propensity_score, priority,
            is_claimed, recovery_bounty_inr, created_at, last_activity_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 1000.0, datetime('now'), datetime('now'))
    """, (
        test_lead_id, cust_id, "Arjun Electronics Rohtak", cust_email, "+91 98110 54321",
        "Rohtak", "124001", "Retail Electronics", 4, 1, 3500.0,
        "Y", "BUNDLE_CUSTOMIZED", "Customized Bundle (₹3500/mo) • Awaiting Smart KYC",
        85, "HIGH"
    ))
    conn.commit()

print(f"Seeded test lead: {test_lead_id}")

# Step 4: Verify unauthorized access (no token or customer token) is rejected
r_unauth = requests.post(f"{base}/api/partner/leads/{test_lead_id}/call")
assert r_unauth.status_code in [401, 403], f"Expected 401/403 for no token, got {r_unauth.status_code}"

r_cust_call = requests.post(f"{base}/api/partner/leads/{test_lead_id}/call", headers={
    "Authorization": f"Bearer {cust_token}"
})
assert r_cust_call.status_code in [401, 403], f"Expected 401/403 for customer role, got {r_cust_call.status_code}"
print("Pass: Unauthorized access to call lead is cleanly rejected (fail-closed RBAC).")

# Step 5: Mitra Partner fetches leads - test lead MUST be present
r_leads_before = requests.get(f"{base}/api/partner/leads", headers={
    "Authorization": f"Bearer {mitra_token}"
})
assert r_leads_before.status_code == 200
leads_before = r_leads_before.json()
lead_ids_before = [l["lead_id"] for l in leads_before]
assert test_lead_id in lead_ids_before, f"Test lead {test_lead_id} should be in partner leads before call"
print(f"Pass: Test lead {test_lead_id} is visible in Mitra leads feed before call.")

# Step 6: Mitra Partner calls the lead
r_call = requests.post(f"{base}/api/partner/leads/{test_lead_id}/call", headers={
    "Authorization": f"Bearer {mitra_token}"
})
assert r_call.status_code == 200, f"Call endpoint failed: {r_call.text}"
call_data = r_call.json()
assert call_data["status"] == "SUCCESS"
assert call_data["action"] == "CALLED_AND_REMOVED"
assert call_data["lead_id"] == test_lead_id
print("Pass: Call endpoint responded 200 SUCCESS and CALLED_AND_REMOVED.")

# Step 7: Mitra Partner fetches leads again - test lead MUST be ATOMICALLY REMOVED
r_leads_after = requests.get(f"{base}/api/partner/leads", headers={
    "Authorization": f"Bearer {mitra_token}"
})
assert r_leads_after.status_code == 200
leads_after = r_leads_after.json()
lead_ids_after = [l["lead_id"] for l in leads_after]
assert test_lead_id not in lead_ids_after, f"Test lead {test_lead_id} should be atomically removed from partner feed!"
print(f"Pass: Test lead {test_lead_id} was ATOMICALLY REMOVED from the partner leads feed!")

# Step 8: Verify in SQLite DB that it was removed from customer_leads and archived in called_leads
with sqlite3.connect(DB_PATH) as conn:
    row_leads = conn.execute("SELECT * FROM customer_leads WHERE lead_id = ?", (test_lead_id,)).fetchone()
    assert row_leads is None, f"Lead {test_lead_id} still exists in customer_leads table!"

    row_archive = conn.execute("SELECT * FROM called_leads WHERE lead_id = ?", (test_lead_id,)).fetchone()
    assert row_archive is not None, f"Lead {test_lead_id} not found in called_leads archive table!"
    assert row_archive[5] == partner_id, f"Archived caller ID mismatch: {row_archive[5]} != {partner_id}"

print("Pass: SQLite verification confirmed lead deleted from customer_leads and archived in called_leads.")

# Step 9: Subsequent call to same lead returns ALREADY_CALLED
r_call_again = requests.post(f"{base}/api/partner/leads/{test_lead_id}/call", headers={
    "Authorization": f"Bearer {mitra_token}"
})
assert r_call_again.status_code == 200
assert r_call_again.json()["status"] == "ALREADY_CALLED"
print("Pass: Duplicate call gracefully returns ALREADY_CALLED.")

# Step 10: Call non-existent lead returns 404
r_notfound = requests.post(f"{base}/api/partner/leads/LD-NONEXISTENT/call", headers={
    "Authorization": f"Bearer {mitra_token}"
})
assert r_notfound.status_code == 404
print("Pass: Non-existent lead returns 404 NOT FOUND.")

print("\nALL MITRA LEAD CALL & ATOMIC REMOVAL TESTS PASSED SUCCESSFULLY!")
