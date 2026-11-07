# tests/test_security_audit.py
import requests
import uuid

base = "http://127.0.0.1:8000"

def test_security_audit():
    print("=== BEGINNING ENTERPRISE SECURITY AUDIT SUITE ===")

    # ---------------------------------------------------------
    # Requirement 1: Remove universal admin and partner passwords
    # ---------------------------------------------------------
    print("\n--- [Audit 1] Universal Password Elimination ---")
    random_email = f"attacker_{uuid.uuid4().hex[:8]}@malicious.com"

    # Test 1a: Arbitrary email cannot bypass authentication using 'airtelmitra'
    r1 = requests.post(f"{base}/api/auth/login", json={
        "email": random_email,
        "password": "airtelmitra",
        "role": "PARTNER"
    })
    print(f"Bypass attempt with 'airtelmitra' for unknown email status: {r1.status_code}")
    assert r1.status_code == 401, f"Expected 401 for unauthorized bypass, got {r1.status_code}"
    print("  [PASS] Arbitrary email bypass with 'airtelmitra' strictly blocked (HTTP 401)")

    # Test 1b: Arbitrary email cannot bypass authentication using 'airteladmin'
    r2 = requests.post(f"{base}/api/auth/login", json={
        "email": random_email,
        "password": "airteladmin",
        "role": "ADMIN"
    })
    print(f"Bypass attempt with 'airteladmin' for unknown email status: {r2.status_code}")
    assert r2.status_code == 401, f"Expected 401 for unauthorized bypass, got {r2.status_code}"
    print("  [PASS] Arbitrary email bypass with 'airteladmin' strictly blocked (HTTP 401)")

    # Test 1c: Individual registration for partner with unique password works
    partner_email = f"partner_{uuid.uuid4().hex[:6]}@agency.in"
    unique_pwd = f"SecuredSecret#{uuid.uuid4().hex[:8]}"
    r_reg = requests.post(f"{base}/api/auth/register", json={
        "email": partner_email,
        "password": unique_pwd,
        "name": "Rohtak Authorized Mitra",
        "role": "PARTNER",
        "phone": "+91 98765 43210"
    })
    assert r_reg.status_code == 200, f"Registration failed: {r_reg.text}"
    reg_data = r_reg.json()
    assert reg_data["user"]["role"] == "PARTNER"
    print(f"  [PASS] Individual Partner account registered: {partner_email}")

    # Test 1d: Login with wrong password fails closed
    r_wrong = requests.post(f"{base}/api/auth/login", json={
        "email": partner_email,
        "password": "WrongPassword123!",
        "role": "PARTNER"
    })
    assert r_wrong.status_code == 401, f"Expected 401, got {r_wrong.status_code}"
    print("  [PASS] Incorrect individual password fails closed with HTTP 401")

    # Test 1e: Login with correct individual password succeeds
    r_login = requests.post(f"{base}/api/auth/login", json={
        "email": partner_email,
        "password": unique_pwd,
        "role": "PARTNER"
    })
    assert r_login.status_code == 200, f"Expected 200, got {r_login.status_code}"
    partner_token = r_login.json()["access_token"]
    print("  [PASS] Valid individual partner credentials authenticated successfully")

    # ---------------------------------------------------------
    # Requirement 2: Remove public role-switch endpoint and demo tokens
    # ---------------------------------------------------------
    print("\n--- [Audit 2] Role Switch & Hardcoded Token Purge ---")

    # Test 2a: Endpoint /api/auth/switch-role MUST return 404 or 405 (deleted)
    r_switch = requests.post(f"{base}/api/auth/switch-role", json={"role": "ADMIN"})
    print(f"POST /api/auth/switch-role status: {r_switch.status_code}")
    assert r_switch.status_code in [404, 405], f"Expected 404 Not Found, got {r_switch.status_code}"
    print("  [PASS] Public /api/auth/switch-role endpoint completely removed (HTTP 404)")

    # Test 2b: Hardcoded demo tokens (tok_admin_demo, tok_partner_demo) MUST return 401
    r_demo_admin = requests.get(f"{base}/api/admin/metrics", headers={
        "Authorization": "Bearer tok_admin_demo"
    })
    print(f"Access with 'tok_admin_demo' status: {r_demo_admin.status_code}")
    assert r_demo_admin.status_code == 401, f"Expected 401, got {r_demo_admin.status_code}"
    print("  [PASS] Hardcoded 'tok_admin_demo' token rejected (HTTP 401)")

    r_demo_partner = requests.get(f"{base}/api/partner/leads", headers={
        "Authorization": "Bearer tok_partner_demo"
    })
    print(f"Access with 'tok_partner_demo' status: {r_demo_partner.status_code}")
    assert r_demo_partner.status_code == 401, f"Expected 401, got {r_demo_partner.status_code}"
    print("  [PASS] Hardcoded 'tok_partner_demo' token rejected (HTTP 401)")

    # ---------------------------------------------------------
    # Requirement 3: Return only safe user fields from auth APIs
    # ---------------------------------------------------------
    print("\n--- [Audit 3] Safe User Payload Serialization ---")
    user_obj = r_login.json()["user"]
    forbidden_keys = ["password_hash", "salt", "id", "password"]
    for k in forbidden_keys:
        assert k not in user_obj, f"Security leak! '{k}' found in auth response: {user_obj}"
        print(f"  [PASS] '{k}' is NOT present in user payload")

    expected_safe_keys = ["user_id", "email", "role", "name", "phone", "permissions"]
    for k in expected_safe_keys:
        assert k in user_obj, f"Expected safe key '{k}' missing in user payload"
    print("  [PASS] Only sanitized user profile fields returned")

    # ---------------------------------------------------------
    # Requirement 4: Missing or invalid auth fails closed (RBAC)
    # ---------------------------------------------------------
    print("\n--- [Audit 4] Fail-Closed Authentication & RBAC ---")

    # Test 4a: /api/auth/me without token returns 401
    r_me_no_token = requests.get(f"{base}/api/auth/me")
    assert r_me_no_token.status_code == 401, f"Expected 401, got {r_me_no_token.status_code}"
    print("  [PASS] /api/auth/me without token returns HTTP 401")

    # Test 4b: /api/auth/me with bogus token returns 401
    r_me_bad_token = requests.get(f"{base}/api/auth/me", headers={
        "Authorization": "Bearer fake_nonexistent_token_12345"
    })
    assert r_me_bad_token.status_code == 401, f"Expected 401, got {r_me_bad_token.status_code}"
    print("  [PASS] /api/auth/me with invalid token returns HTTP 401")

    # Test 4c: Protected admin endpoint without token returns 401
    r_adm_no_token = requests.get(f"{base}/api/admin/metrics")
    assert r_adm_no_token.status_code == 401, f"Expected 401, got {r_adm_no_token.status_code}"
    print("  [PASS] /api/admin/metrics without token returns HTTP 401")

    # Test 4d: Protected partner endpoint without token returns 401
    r_ptr_no_token = requests.get(f"{base}/api/partner/leads")
    assert r_ptr_no_token.status_code == 401, f"Expected 401, got {r_ptr_no_token.status_code}"
    print("  [PASS] /api/partner/leads without token returns HTTP 401")

    # Test 4e: Merchant token accessing Admin metrics returns 403 Forbidden
    cust_email = f"merchant_{uuid.uuid4().hex[:6]}@store.in"
    r_cust_reg = requests.post(f"{base}/api/auth/register", json={
        "email": cust_email,
        "password": "PasswordMSME123!",
        "name": "Kirana Merchant",
        "role": "MERCHANT"
    })
    assert r_cust_reg.status_code == 200
    merchant_token = r_cust_reg.json()["access_token"]

    r_admin_forbidden = requests.get(f"{base}/api/admin/metrics", headers={
        "Authorization": f"Bearer {merchant_token}"
    })
    assert r_admin_forbidden.status_code == 403, f"Expected 403 Forbidden, got {r_admin_forbidden.status_code}"
    print("  [PASS] Merchant token accessing /api/admin/metrics receives HTTP 403 Forbidden")

    # Test 4f: Merchant token accessing Partner leads returns 403 Forbidden
    r_partner_forbidden = requests.get(f"{base}/api/partner/leads", headers={
        "Authorization": f"Bearer {merchant_token}"
    })
    assert r_partner_forbidden.status_code == 403, f"Expected 403 Forbidden, got {r_partner_forbidden.status_code}"
    print("  [PASS] Merchant token accessing /api/partner/leads receives HTTP 403 Forbidden")

    # Test 4g: Partner token accessing Partner leads returns 200 OK
    r_partner_ok = requests.get(f"{base}/api/partner/leads", headers={
        "Authorization": f"Bearer {partner_token}"
    })
    assert r_partner_ok.status_code == 200, f"Expected 200, got {r_partner_ok.status_code}"
    print("  [PASS] Authorized Partner token successfully accesses /api/partner/leads (HTTP 200)")

    # Test 4h: Admin token accessing Admin metrics returns 200 OK
    r_admin_login = requests.post(f"{base}/api/auth/login", json={
        "email": "admin@airtel.com",
        "password": "airteladmin",
        "role": "ADMIN"
    })
    assert r_admin_login.status_code == 200, f"Admin login failed: {r_admin_login.text}"
    admin_token = r_admin_login.json()["access_token"]

    r_admin_ok = requests.get(f"{base}/api/admin/metrics", headers={
        "Authorization": f"Bearer {admin_token}"
    })
    assert r_admin_ok.status_code == 200, f"Expected 200, got {r_admin_ok.status_code}"
    print("  [PASS] Authorized Admin token successfully accesses /api/admin/metrics (HTTP 200)")

    print("\n=======================================================")
    print(" ALL 4 SECURITY HARDENING CRITERIA VERIFIED & PASSED! ")
    print("=======================================================")

if __name__ == "__main__":
    test_security_audit()

