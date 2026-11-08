"""
End-to-End P0 Test Suite for Airtel SYNC / Project Udyam Digital
Covers:
1. Authentication & Role-Based Access Control (fail closed, no public admin/partner signup, admin create-user)
2. Order Ownership & Partner Isolation (cross-merchant, cross-partner, atomic lead claiming)
3. KYC Verification Security & Consent (auth required, explicit DPDP consent, session binding, KYC case ownership, inactive registry rejection)
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))

import uuid
import requests

BASE_URL = "http://127.0.0.1:8000"

def get_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "X-Session-Token": token,
        "Content-Type": "application/json"
    }

def test_p0_authentication_and_rbac():
    print("\n=======================================================")
    print("TEST SUITE 1: AUTHENTICATION & RBAC ENFORCEMENT")
    print("=======================================================")

    # 1.1 Public registration must NOT accept ADMIN or PARTNER role
    fake_admin_email = f"hack_admin_{uuid.uuid4().hex[:6]}@test.com"
    r = requests.post(f"{BASE_URL}/api/auth/register", json={
        "email": fake_admin_email,
        "password": "Password123!",
        "name": "Attacker",
        "role": "ADMIN"
    })
    assert r.status_code == 403, f"Expected 403 for public ADMIN registration, got {r.status_code}"
    print("[PASS] Public registration as ADMIN is rejected with 403 Forbidden")

    fake_partner_email = f"hack_partner_{uuid.uuid4().hex[:6]}@test.com"
    r = requests.post(f"{BASE_URL}/api/auth/register", json={
        "email": fake_partner_email,
        "password": "Password123!",
        "name": "Attacker",
        "role": "PARTNER"
    })
    assert r.status_code == 403, f"Expected 403 for public PARTNER registration, got {r.status_code}"
    print("[PASS] Public registration as PARTNER is rejected with 403 Forbidden")

    # 1.2 Public registration allows MERCHANT only and returns safe fields
    merchant_email = f"merchant_{uuid.uuid4().hex[:6]}@retailer.in"
    r = requests.post(f"{BASE_URL}/api/auth/register", json={
        "email": merchant_email,
        "password": "MerchantPass123!",
        "name": "Genuine Merchant",
        "role": "MERCHANT",
        "phone": "+91 98765 43210"
    })
    assert r.status_code == 200, f"Merchant registration failed: {r.text}"
    data = r.json()
    user = data["user"]
    assert user["role"] == "MERCHANT"
    assert "password" not in user
    assert "password_hash" not in user
    assert "salt" not in user
    merchant_token = data["access_token"]
    print("[PASS] Public registration creates MERCHANT role with safe returned user fields (no password hash/salt)")

    # 1.3 Admin create-user endpoint requires ADMIN role
    # Unauthenticated
    r = requests.post(f"{BASE_URL}/api/auth/admin/create-user", json={
        "email": f"partner_{uuid.uuid4().hex[:6]}@agency.in",
        "password": "PartnerPass123!",
        "name": "New Mitra",
        "role": "PARTNER",
        "assigned_pincode": "124001"
    })
    assert r.status_code == 401, f"Expected 401 for unauthenticated create-user, got {r.status_code}"
    print("[PASS] Unauthenticated access to /api/auth/admin/create-user fails closed with 401")

    # Merchant trying to create an admin
    r = requests.post(f"{BASE_URL}/api/auth/admin/create-user", json={
        "email": f"partner_{uuid.uuid4().hex[:6]}@agency.in",
        "password": "PartnerPass123!",
        "name": "New Mitra",
        "role": "ADMIN"
    }, headers=get_headers(merchant_token))
    assert r.status_code == 403, f"Expected 403 for merchant invoking create-user, got {r.status_code}"
    print("[PASS] Merchant access to /api/auth/admin/create-user fails closed with 403 Forbidden")

    # Legitimate Admin login
    r_admin = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@airtel.com",
        "password": "airteladmin",
        "role": "ADMIN"
    })
    assert r_admin.status_code == 200
    admin_token = r_admin.json()["access_token"]

    # Legitimate Admin creates Partner
    partner_a_email = f"mitra_a_{uuid.uuid4().hex[:6]}@agency.in"
    r_create = requests.post(f"{BASE_URL}/api/auth/admin/create-user", json={
        "email": partner_a_email,
        "password": "PartnerPass123!",
        "name": "Rohtak Mitra A",
        "role": "PARTNER",
        "assigned_pincode": "124001"
    }, headers=get_headers(admin_token))
    assert r_create.status_code == 200, f"Admin create partner failed: {r_create.text}"
    partner_a_data = r_create.json()
    assert partner_a_data["user"]["role"] == "PARTNER"
    print("[PASS] Authorized admin workflow successfully creates privileged PARTNER account")

def test_p0_order_ownership_and_partner_isolation():
    print("\n=======================================================")
    print("TEST SUITE 2: ORDER OWNERSHIP & PARTNER ISOLATION")
    print("=======================================================")

    # Get admin token
    r_admin = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@airtel.com",
        "password": "airteladmin",
        "role": "ADMIN"
    })
    admin_token = r_admin.json()["access_token"]

    # Create Merchant A and Merchant B
    m_a_email = f"merchant_a_{uuid.uuid4().hex[:6]}@shop.in"
    r_ma = requests.post(f"{BASE_URL}/api/auth/register", json={
        "email": m_a_email, "password": "Password123!", "name": "Merchant Alpha"
    })
    token_ma = r_ma.json()["access_token"]
    user_ma = r_ma.json()["user"]

    m_b_email = f"merchant_b_{uuid.uuid4().hex[:6]}@shop.in"
    r_mb = requests.post(f"{BASE_URL}/api/auth/register", json={
        "email": m_b_email, "password": "Password123!", "name": "Merchant Beta"
    })
    token_mb = r_mb.json()["access_token"]
    user_mb = r_mb.json()["user"]

    # Create Partner 1 (Territory: 124001 Rohtak) and Partner 2 (Territory: 500001 Hyderabad)
    p1_email = f"partner_1_{uuid.uuid4().hex[:6]}@partner.in"
    r_p1 = requests.post(f"{BASE_URL}/api/auth/admin/create-user", json={
        "email": p1_email, "password": "PartnerPass123!", "name": "Partner 1 Rohtak",
        "role": "PARTNER", "assigned_pincode": "124001"
    }, headers=get_headers(admin_token))
    user_p1 = r_p1.json()["user"]
    r_p1_login = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": p1_email, "password": "PartnerPass123!", "role": "PARTNER"
    })
    token_p1 = r_p1_login.json()["access_token"]

    p2_email = f"partner_2_{uuid.uuid4().hex[:6]}@partner.in"
    r_p2 = requests.post(f"{BASE_URL}/api/auth/admin/create-user", json={
        "email": p2_email, "password": "PartnerPass123!", "name": "Partner 2 Hyderabad",
        "role": "PARTNER", "assigned_pincode": "500001"
    }, headers=get_headers(admin_token))
    user_p2 = r_p2.json()["user"]
    r_p2_login = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": p2_email, "password": "PartnerPass123!", "role": "PARTNER"
    })
    token_p2 = r_p2_login.json()["access_token"]

    # Setup valid KYC case for Merchant A (using Active GSTIN from registry)
    r_kyc_a = requests.post(f"{BASE_URL}/api/kyc/verify-extracted", json={
        "gstin": "32TTNXB7384T1ZW",
        "entity_name": "Balaji Dental Care LLP",
        "bill_date": "2020-06-04",
        "consent_granted": True,
        "consent": {
            "granted": True, "timestamp": "2026-06-01T10:00:00Z",
            "version": "v1.0", "purpose": "Statutory Registry Verification"
        }
    }, headers=get_headers(token_ma))
    assert r_kyc_a.status_code == 200
    assert r_kyc_a.json()["verdict"] == "APPROVED"
    case_a_id = r_kyc_a.json()["case_id"]

    # Merchant A creates Order in Rohtak (Pincode: 124001)
    r_order_a = requests.post(f"{BASE_URL}/api/orders/create", json={
        "business_name": "Merchant Alpha Enterprises",
        "installation_address": {
            "line1": "Shop 1, Main Market",
            "city": "Rohtak",
            "pincode": "124001"
        },
        "contact_phone": "+91 98110 11223",
        "case_id": case_a_id,
        "consent": {
            "granted": True,
            "timestamp": "2026-06-01T10:05:00Z",
            "version": "v1.0",
            "purpose": "Subscriber Registration"
        },
        "bundle_data": {
            "product_quantities": {"P01": 1},
            "monthly_recurring_total": 999.0,
            "total_monthly_inr": 1178.82,
            "setup_charges_total": 0.0
        }
    }, headers=get_headers(token_ma))
    assert r_order_a.status_code == 200, f"Order creation failed: {r_order_a.text}"
    order_a = r_order_a.json()
    order_a_id = order_a["order_id"]
    print(f"[PASS] Merchant A created order '{order_a_id}'")

    # 2.1 Cross-Merchant Negative Test: Merchant B attempts to fetch Merchant A's order
    r_get = requests.get(f"{BASE_URL}/api/orders/{order_a_id}", headers=get_headers(token_mb))
    assert r_get.status_code == 403, f"Expected 403 for cross-merchant order access, got {r_get.status_code}"
    print("[PASS] Cross-user access rejected: Merchant B cannot access Merchant A's order (403 Forbidden)")

    # 2.2 Cross-Partner Territory Isolation Test:
    # Partner 2 (Hyderabad 500001) attempts to access Merchant A's order (Rohtak 124001)
    r_p2_order = requests.get(f"{BASE_URL}/api/orders/{order_a_id}", headers=get_headers(token_p2))
    assert r_p2_order.status_code == 403, f"Expected 403 for partner outside territory, got {r_p2_order.status_code}"
    print("[PASS] Partner territory isolation: Partner 2 (Hyderabad) cannot access Rohtak order (403 Forbidden)")

    # Partner 1 (Rohtak 124001 territory) CAN access the order
    r_p1_order = requests.get(f"{BASE_URL}/api/orders/{order_a_id}", headers=get_headers(token_p1))
    assert r_p1_order.status_code == 200, f"Expected 200 for partner in territory, got {r_p1_order.status_code}"
    print("[PASS] Partner 1 (authorized territory 124001) successfully accesses territory order")

    # 2.3 Atomic Lead Claiming and Concurrency Test:
    # Inject an unclaimed lead in Rohtak 124001
    lead_id = f"LD-TEST-{uuid.uuid4().hex[:6].upper()}"
    from app.modules.partner.portal import PartnerPortal
    partner_portal = PartnerPortal()
    partner_portal.record_customer_activity(
        lead_id=lead_id,
        business_name="Rohtak Textile Mart",
        email="textile@rohtak.in",
        phone="+91 98110 99887",
        action="BUNDLE_CUSTOMIZED",
        city="Rohtak",
        pincode="124001",
        monthly_spend_inr=3500.0,
        has_gstin="Y"
    )

    # Negative Test: Partner 2 (Hyderabad 500001) attempts to claim Rohtak lead (Territory violation)
    r_claim_p2 = requests.post(f"{BASE_URL}/api/partner/leads/{lead_id}/claim", headers=get_headers(token_p2))
    assert r_claim_p2.status_code == 403, f"Expected 403 for out-of-territory lead claim, got {r_claim_p2.status_code}"
    print("[PASS] Unauthorized lead claiming rejected: Partner 2 cannot claim lead outside territory (403 Forbidden)")

    # Partner 1 claims the lead successfully
    r_claim_p1 = requests.post(f"{BASE_URL}/api/partner/leads/{lead_id}/claim", headers=get_headers(token_p1))
    assert r_claim_p1.status_code == 200, f"Partner 1 claim failed: {r_claim_p1.text}"
    assert r_claim_p1.json()["status"] == "SUCCESS"
    print("[PASS] Partner 1 successfully claims unclaimed lead in authorized territory")

    # Atomic Conflict Test: Another partner attempts to claim the same already-claimed lead
    # Admin tries or another partner in territory tries: must fail with 409 Conflict
    r_claim_again = requests.post(f"{BASE_URL}/api/partner/leads/{lead_id}/claim", headers=get_headers(admin_token))
    assert r_claim_again.status_code == 409, f"Expected 409 Conflict for double-claiming lead, got {r_claim_again.status_code}"
    print("[PASS] Atomic lead claiming prevents race condition: duplicate claim rejected with 409 Conflict")

    # Lead Call Outreach Removal Test:
    r_call = requests.post(f"{BASE_URL}/api/partner/leads/{lead_id}/call", headers=get_headers(token_p1))
    assert r_call.status_code == 200
    assert r_call.json()["action"] == "CALLED_AND_REMOVED"
    print("[PASS] Outreach call atomically removed lead from active leads pool")

def test_p0_secure_kyc_workflow():
    print("\n=======================================================")
    print("TEST SUITE 3: SECURE KYC WORKFLOW & DPDP COMPLIANCE")
    print("=======================================================")

    # Register Customer 1 and Customer 2
    c1_email = f"kyc_cust1_{uuid.uuid4().hex[:6]}@domain.in"
    r_c1 = requests.post(f"{BASE_URL}/api/auth/register", json={
        "email": c1_email, "password": "Password123!", "name": "Customer One"
    })
    token_c1 = r_c1.json()["access_token"]
    user_c1 = r_c1.json()["user"]

    c2_email = f"kyc_cust2_{uuid.uuid4().hex[:6]}@domain.in"
    r_c2 = requests.post(f"{BASE_URL}/api/auth/register", json={
        "email": c2_email, "password": "Password123!", "name": "Customer Two"
    })
    token_c2 = r_c2.json()["access_token"]
    user_c2 = r_c2.json()["user"]

    # 3.1 Unauthenticated KYC operations must fail closed with 401
    r_unauth_scan = requests.post(f"{BASE_URL}/api/kyc/specimen-scan", json={"applicant_code": "K01", "doc_type": "gst"})
    assert r_unauth_scan.status_code == 401, f"Expected 401 for unauth scan, got {r_unauth_scan.status_code}"
    print("[PASS] Unauthenticated /api/kyc/specimen-scan fails closed with 401 Unauthorized")

    r_unauth_verify = requests.post(f"{BASE_URL}/api/kyc/verify-extracted", json={
        "gstin": "06AAACH7409R1ZZ", "consent_granted": True
    })
    assert r_unauth_verify.status_code == 401, f"Expected 401 for unauth verify, got {r_unauth_verify.status_code}"
    print("[PASS] Unauthenticated /api/kyc/verify-extracted fails closed with 401 Unauthorized")

    # 3.2 Missing DPDP Consent Check:
    r_no_consent = requests.post(f"{BASE_URL}/api/kyc/verify-extracted", json={
        "gstin": "06AAACH7409R1ZZ",
        "entity_name": "Test Entity",
        "consent_granted": False
    }, headers=get_headers(token_c1))
    assert r_no_consent.status_code == 400, f"Expected 400 for missing consent, got {r_no_consent.status_code}"
    assert "consent" in r_no_consent.json()["detail"].lower()
    print("[PASS] KYC verification without explicit DPDP consent is blocked with 400 Bad Request")

    # 3.3 Customer 1 performs valid specimen scan and binds verification session
    r_scan_c1 = requests.post(f"{BASE_URL}/api/kyc/specimen-scan", json={
        "applicant_code": "K01", "doc_type": "gst"
    }, headers=get_headers(token_c1))
    assert r_scan_c1.status_code == 200, f"Expected 200 for specimen scan, got {r_scan_c1.status_code}: {r_scan_c1.text}"
    scan_c1_data = r_scan_c1.json()
    v_session_c1 = scan_c1_data["verification_session_id"]
    print(f"[PASS] Customer 1 generated bound KYC verification session '{v_session_c1}'")

    # 3.4 Cross-Customer Session Spoofing Test:
    # Customer 2 attempts to use Customer 1's verification session id
    r_spoof = requests.post(f"{BASE_URL}/api/kyc/verify-extracted", json={
        "gstin": "37IHKXV5167L1ZS",
        "entity_name": "Vindhya Tours & Travels",
        "verification_session_id": v_session_c1,
        "consent_granted": True,
        "consent": {"granted": True, "purpose": "Testing", "version": "v1.0"}
    }, headers=get_headers(token_c2))
    assert r_spoof.status_code == 403, f"Expected 403 for verification session belonging to another user, got {r_spoof.status_code}"
    print("[PASS] Cross-customer verification session spoofing is blocked with 403 Forbidden")

    # 3.5 Customer 1 completes KYC verification and gets approved case
    r_verify_c1 = requests.post(f"{BASE_URL}/api/kyc/verify-extracted", json={
        "gstin": "32TTNXB7384T1ZW",
        "entity_name": "Balaji Dental Care LLP",
        "bill_date": "2020-06-04",
        "verification_session_id": v_session_c1,
        "consent_granted": True,
        "consent": {"granted": True, "purpose": "Registry Verification", "version": "v1.0"}
    }, headers=get_headers(token_c1))
    assert r_verify_c1.status_code == 200
    c1_case_id = r_verify_c1.json()["case_id"]
    assert r_verify_c1.json()["status"] == "VERIFIED"
    assert r_verify_c1.json()["verdict"] == "APPROVED"
    print(f"[PASS] Customer 1 successfully verified with approved KYC case '{c1_case_id}'")

    # 3.6 Cross-Customer KYC Case Order Spoofing Test:
    # Customer 2 attempts to create an order using Customer 1's approved KYC case
    r_spoof_order = requests.post(f"{BASE_URL}/api/orders/create", json={
        "business_name": "Customer Two Store",
        "installation_address": {
            "line1": "Shop 2",
            "city": "Hyderabad",
            "pincode": "500001"
        },
        "contact_phone": "+91 99887 66554",
        "case_id": c1_case_id, # BELONGS TO CUSTOMER 1!
        "consent": {
            "granted": True,
            "timestamp": "2026-06-01T10:00:00Z",
            "version": "v1.0",
            "purpose": "Subscriber Registration"
        },
        "bundle_data": {
            "product_quantities": {"P01": 1},
            "monthly_recurring_total": 999.0,
            "total_monthly_inr": 1178.82,
            "setup_charges_total": 0.0
        }
    }, headers=get_headers(token_c2))
    assert r_spoof_order.status_code in [400, 403], f"Expected 400 or 403 for using another customer's KYC case, got {r_spoof_order.status_code}"
    print("[PASS] Fraud prevention: Customer 2 blocked from creating order using Customer 1's KYC case")

    # 3.7 Conservative Registry Status Check:
    # Cancelled GSTIN must be rejected conservatively
    r_cancelled_gst = requests.post(f"{BASE_URL}/api/kyc/verify-extracted", json={
        "gstin": "37IHKXV5167L1ZS",
        "entity_name": "Vindhya Tours & Travels",
        "bill_date": "2025-06-07",
        "consent_granted": True,
        "consent": {"granted": True, "purpose": "Testing", "version": "v1.0"}
    }, headers=get_headers(token_c1))
    assert r_cancelled_gst.status_code == 200
    assert r_cancelled_gst.json()["status"] == "REJECTED"
    assert any("Cancelled" in r for r in r_cancelled_gst.json()["reasons"])
    print("[PASS] Cancelled GSTIN rejected conservatively with authoritative REJECTED verdict")

    # Malformed GSTIN check
    r_bad_gst = requests.post(f"{BASE_URL}/api/verify/gstin", json={
        "gstin": "INVALID_GSTIN_123"
    }, headers=get_headers(token_c1))
    assert r_bad_gst.status_code == 400
    assert "Invalid GSTIN format" in r_bad_gst.json()["detail"]
    print("[PASS] Malformed GSTIN rejected conservatively with 400 Bad Request")

    # Verification with non-existent GSTIN produces REJECTED verdict
    r_bad_kyc = requests.post(f"{BASE_URL}/api/kyc/verify-extracted", json={
        "gstin": "99UNKNOWN9999Z9",
        "consent_granted": True,
        "consent": {"granted": True, "purpose": "Testing", "version": "v1.0"}
    }, headers=get_headers(token_c1))
    assert r_bad_kyc.status_code == 200
    assert r_bad_kyc.json()["status"] == "REJECTED"
    print("[PASS] Non-existent GSTIN produces authoritative REJECTED verdict")

    print("\n=======================================================")
    print("ALL P0 SECURITY, RBAC & KYC TESTS PASSED SUCCESSFULLY!")
    print("=======================================================")

if __name__ == "__main__":
    try:
        test_p0_authentication_and_rbac()
        test_p0_order_ownership_and_partner_isolation()
        test_p0_secure_kyc_workflow()
        print("\n\u2705 ALL TEST SUITES COMPLETED WITH ZERO FAILURES.")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n\u274c TEST SUITE FAILURE: {e}")
        sys.exit(1)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n\u274c UNEXPECTED ERROR: {e}")
        sys.exit(1)
