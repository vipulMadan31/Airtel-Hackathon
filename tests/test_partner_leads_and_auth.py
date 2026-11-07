import requests

base = "http://127.0.0.1:8000"

print("--- 1. Testing Arbitrary Email Mitra Partner Authentication ---")
# Test 1a: Custom email logging in as Mitra Partner
r_mitra = requests.post(f"{base}/api/auth/login", json={
    "email": "my.own.partner.email@gmail.com",
    "password": "airtelmitra",
    "role": "PARTNER"
})
print("Custom Mitra Partner status:", r_mitra.status_code)
assert r_mitra.status_code == 200, f"Expected 200, got {r_mitra.status_code}: {r_mitra.text}"
mitra_data = r_mitra.json()
mitra_token = mitra_data["access_token"]
print("Mitra authenticated successfully:", mitra_data["user"]["email"], "Role:", mitra_data["user"]["role"])
assert mitra_data["user"]["role"] == "PARTNER"

print("\n--- 2. Testing Arbitrary Email Admin Authentication ---")
# Test 2a: Custom email logging in as Admin
r_admin = requests.post(f"{base}/api/auth/login", json={
    "email": "my.custom.admin@somedomain.org",
    "password": "airteladmin",
    "role": "ADMIN"
})
print("Custom Admin status:", r_admin.status_code)
assert r_admin.status_code == 200, f"Expected 200, got {r_admin.status_code}: {r_admin.text}"
admin_data = r_admin.json()
print("Admin authenticated successfully:", admin_data["user"]["email"], "Role:", admin_data["user"]["role"])
assert admin_data["user"]["role"] == "ADMIN"

print("\n--- 3. Testing Mitra Partner Leads Feed (No TOKEN_PAID) ---")
# Fetch leads using the custom partner's token
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

print("\n--- 4. Testing HTML Form Inputs Have No Hardcoded Default Emails ---")
r_html = requests.get(f"{base}/")
assert r_html.status_code == 200
assert 'id="loginMitraEmail" required value="mitra@airtel.com"' not in r_html.text
assert 'id="loginAdminEmail" required value="admin@airtel.com"' not in r_html.text
assert 'placeholder="Enter any partner email' in r_html.text
assert 'placeholder="Enter any admin email' in r_html.text
print("Check Passed: Default emails cleanly removed from UI form inputs!")

print("\nALL TESTS PASSED SUCCESSFULLY!")
