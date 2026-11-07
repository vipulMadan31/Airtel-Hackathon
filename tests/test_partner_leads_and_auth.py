import requests
import uuid

base = "http://127.0.0.1:8000"

print("--- 1. Testing Mitra Partner Authentication with Individual Credentials ---")
# Register an individual Mitra Partner
partner_email = f"mitra_{uuid.uuid4().hex[:6]}@airtelagency.in"
partner_pwd = "PartnerSecureKey456!"
r_reg_mitra = requests.post(f"{base}/api/auth/register", json={
    "email": partner_email,
    "password": partner_pwd,
    "name": "Rohtak Central Mitra",
    "role": "PARTNER",
    "phone": "+91 98110 55443"
})
assert r_reg_mitra.status_code == 200, f"Registration failed: {r_reg_mitra.text}"
mitra_token = r_reg_mitra.json()["access_token"]
print("Mitra authenticated successfully:", partner_email, "Role: PARTNER")

print("\n--- 2. Testing Enterprise Ops Admin Authentication ---")
r_admin = requests.post(f"{base}/api/auth/login", json={
    "email": "admin@airtel.com",
    "password": "airteladmin",
    "role": "ADMIN"
})
print("Admin login status:", r_admin.status_code)
assert r_admin.status_code == 200, f"Expected 200, got {r_admin.status_code}: {r_admin.text}"
admin_data = r_admin.json()
print("Admin authenticated successfully:", admin_data["user"]["email"], "Role:", admin_data["user"]["role"])
assert admin_data["user"]["role"] == "ADMIN"

print("\n--- 3. Testing Mitra Partner Leads Feed (No TOKEN_PAID) ---")
# Fetch leads using the partner's token
r_leads = requests.get(f"{base}/api/partner/leads", headers={
    "Authorization": f"Bearer {mitra_token}"
})
print("Leads fetch status:", r_leads.status_code)
assert r_leads.status_code == 200
leads = r_leads.json()
print(f"Total leads returned to Mitra: {len(leads)}")

for l in leads:
    print(f"  - Lead ID: {l.get('lead_id')}, Stage: {l.get('stage_reached')}, Business: {l.get('business_name')}")
    assert l.get("stage_reached") not in ["TOKEN_PAID", "ORDER_CONFIRMED", "ACTIVATED"], f"Found paid token lead in feed: {l}"
    assert "paid" not in (l.get("drop_reason") or "").lower(), f"Found paid drop_reason in feed: {l}"

print("Check Passed: ZERO leads with TOKEN_PAID in Mitra feed!")

print("\n--- 4. Testing HTML Form Inputs Have No Hardcoded Default Emails or Passwords ---")
r_html = requests.get(f"{base}/")
assert r_html.status_code == 200
assert 'id="loginMitraEmail" required value="mitra@airtel.com"' not in r_html.text
assert 'id="loginAdminEmail" required value="admin@airtel.com"' not in r_html.text
assert 'id="loginMitraPassword" required value="airtelmitra"' not in r_html.text
assert 'id="loginAdminPassword" required value="airteladmin"' not in r_html.text
print("Check Passed: Default emails and fixed passwords cleanly removed from UI form inputs!")

print("\nALL TESTS PASSED SUCCESSFULLY!")
