# tests/test_ownership_and_integrity.py
import requests
import uuid

base = "http://127.0.0.1:8000"

def test_ownership_and_integrity():
    print("=== BEGINNING OWNERSHIP, KYC, PAYMENT & CONSENT INTEGRITY AUDIT ===")

    # 1. Setup User A (Customer A)
    user_a_email = f"user_a_{uuid.uuid4().hex[:6]}@agency.in"
    user_a_phone = "+91 98110 11111"
    r_reg_a = requests.post(f"{base}/api/auth/register", json={
        "email": user_a_email,
        "password": "PasswordA#123",
        "name": "User A Business",
        "role": "MERCHANT",
        "phone": user_a_phone
    })
    assert r_reg_a.status_code == 200, f"Registration A failed: {r_reg_a.text}"
    token_a = r_reg_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    print(f"User A registered: {user_a_email}")

    # 2. Setup User B (Customer B - The Attacker trying IDOR)
    user_b_email = f"user_b_{uuid.uuid4().hex[:6]}@other.in"
    user_b_phone = "+91 98220 22222"
    r_reg_b = requests.post(f"{base}/api/auth/register", json={
        "email": user_b_email,
        "password": "PasswordB#456",
        "name": "User B Business",
        "role": "MERCHANT",
        "phone": user_b_phone
    })
    assert r_reg_b.status_code == 200, f"Registration B failed: {r_reg_b.text}"
    token_b = r_reg_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    print(f"User B registered: {user_b_email}")

    # 3. Setup Admin User
    r_admin_login = requests.post(f"{base}/api/auth/login", json={
        "email": "admin@airtel.com",
        "password": "airteladmin",
        "role": "ADMIN"
    })
    assert r_admin_login.status_code == 200
    token_admin = r_admin_login.json()["access_token"]
    headers_admin = {"Authorization": f"Bearer {token_admin}"}

    # =========================================================================
    # Requirement 6: Make KYC status server-controlled and linked to a verified case
    # =========================================================================
    print("\n--- [Audit 6] Server-Controlled KYC Verification ---")

    # 6a. Attempt to create order by declaring kyc_status: "VERIFIED" without any verified server case
    r_fraud_order = requests.post(f"{base}/api/orders/create", json={
        "business_name": "Fraud Attempt Store",
        "contact_phone": user_a_phone,
        "bundle_data": {
            "product_quantities": {"P01": 1},
            "monthly_recurring_total": 999.0,
            "total_monthly_inr": 1178.82,
            "setup_charges_total": 0.0
        },
        "kyc_status": "VERIFIED",  # Client-asserted bypass attempt
        "consent": {"granted": True, "version": "v1.0"}
    }, headers=headers_a)
    print(f"Order creation with client-asserted 'VERIFIED' status code: {r_fraud_order.status_code}")
    assert r_fraud_order.status_code == 400, f"Expected 400 Bad Request, got {r_fraud_order.status_code}"
    print("  [PASS] Client-asserted kyc_status: VERIFIED strictly rejected by server (HTTP 400)")

    # 6b. Legitimate KYC verification creates server-approved case
    r_kyc_case = requests.post(f"{base}/api/kyc/verify-extracted", json={
        "udyam_number": "UDYAM-TN-00-3866196",
        "entity_name": "Star Electronics",
        "is_non_gst_mode": True,
        "customer_email": user_a_email,
        "consent_granted": True,
        "consent": {
            "granted": True,
            "version": "v1.0",
            "purpose": "Statutory Udyam Verification",
            "timestamp": "2026-07-01T10:00:00Z"
        }
    }, headers=headers_a)
    assert r_kyc_case.status_code == 200
    kyc_case_data = r_kyc_case.json()
    case_a_id = kyc_case_data["case_id"]
    assert kyc_case_data["verdict"] == "APPROVED", f"Expected APPROVED, got: {kyc_case_data}"
    print(f"  [PASS] Server evaluated and approved KYC case: {case_a_id}")

    # =========================================================================
    # Requirement 8: Remove automatic consent-success assumption
    # =========================================================================
    print("\n--- [Audit 8] Explicit Statutory DPDP Consent Enforcement ---")

    # 8a. Attempt to create order with consent omitted / granted=False
    r_no_consent = requests.post(f"{base}/api/orders/create", json={
        "business_name": "User A Business",
        "contact_phone": user_a_phone,
        "bundle_data": {
            "product_quantities": {"P01": 1},
            "monthly_recurring_total": 999.0,
            "total_monthly_inr": 1178.82,
            "setup_charges_total": 0.0
        },
        "case_id": case_a_id,
        "consent": {"granted": False}
    }, headers=headers_a)
    print(f"Order creation without explicit affirmative consent status: {r_no_consent.status_code}")
    assert r_no_consent.status_code == 400
    print("  [PASS] Automatic consent assumption removed: order rejected without explicit consent (HTTP 400)")

    # 8b. Order creation succeeds when explicit affirmative consent is provided
    r_valid_order_a = requests.post(f"{base}/api/orders/create", json={
        "business_name": "User A Business",
        "contact_phone": user_a_phone,
        "bundle_data": {
            "product_quantities": {"P01": 1},
            "monthly_recurring_total": 999.0,
            "total_monthly_inr": 1178.82,
            "setup_charges_total": 0.0
        },
        "case_id": case_a_id,
        "consent": {
            "granted": True,
            "version": "v1.0",
            "purpose": "DoT Subscriber Identity Verification & Optical Line Handover",
            "consent_text": "Customer explicitly provided affirmative consent under DPDP Act 2023 Section 6."
        },
        "customer_email": user_a_email,
        "installation_address": {"formatted_address": "Shop 10, Sector 14, Rohtak - 124001"}
    }, headers=headers_a)
    assert r_valid_order_a.status_code == 200, f"Order creation failed: {r_valid_order_a.text}"
    order_a = r_valid_order_a.json()
    order_a_id = order_a["order_id"]
    print(f"  [PASS] Enterprise order staged with explicit consent and verified KYC case: {order_a_id}")

    # =========================================================================
    # Requirement 7: Replace client-asserted payment success with server-verified intents
    # =========================================================================
    print("\n--- [Audit 7] Server-Verified Payment Intents & Tamper Rejection ---")

    # 7a. Attempt to self-declare payment success with fake transaction ID and ₹1.00 amount
    r_fake_pay = requests.post(f"{base}/api/payment/confirm", json={
        "order_id": order_a_id,
        "txn_id": "CLIENT_FAKE_TXN_9999",
        "amount_inr": 1.00,
        "payment_method": "UPI_TAMPER"
    }, headers=headers_a)
    print(f"Client-asserted payment attempt status: {r_fake_pay.status_code}")
    assert r_fake_pay.status_code == 400, f"Expected 400, got {r_fake_pay.status_code}"
    print("  [PASS] Client-asserted arbitrary transaction ID & amount rejected by server (HTTP 400)")

    # 7b. Server creates payment intent (authoritative amount strictly enforced to ₹499.00)
    r_intent = requests.post(f"{base}/api/payment/create-intent", json={
        "order_id": order_a_id,
        "amount_inr": 5.00  # Client tries to pass 5 rupees; server must enforce 499
    }, headers=headers_a)
    assert r_intent.status_code == 200
    intent_data = r_intent.json()
    intent_id = intent_data["intent_id"]
    assert intent_data["amount_inr"] == 499.0, f"Server failed to enforce ₹499.0: {intent_data['amount_inr']}"
    print(f"  [PASS] Server generated payment intent {intent_id} with enforced ₹499.00 token deposit")

    # 7c. Confirm payment through server payment intent
    r_confirm_pay = requests.post(f"{base}/api/payment/confirm", json={
        "order_id": order_a_id,
        "intent_id": intent_id,
        "payment_method": "UPI_GPAY"
    }, headers=headers_a)
    assert r_confirm_pay.status_code == 200, f"Payment confirm failed: {r_confirm_pay.text}"
    receipt_a = r_confirm_pay.json()
    assert receipt_a["amount_paid_inr"] == 499.0
    print(f"  [PASS] Server-verified payment completed: Receipt {receipt_a['receipt_number']}")

    # =========================================================================
    # Requirement 5: Enforce ownership checks on KYC, orders, receipts, emails, WhatsApp
    # =========================================================================
    print("\n--- [Audit 5] Enforce Strict Ownership Checks Across All Resources ---")

    # 5a. Order Ownership Check: User B cannot access User A's order
    r_idor_order = requests.get(f"{base}/api/orders/{order_a_id}", headers=headers_b)
    print(f"User B accessing Order A status: {r_idor_order.status_code}")
    assert r_idor_order.status_code == 403, f"Expected 403 Forbidden, got {r_idor_order.status_code}"
    print("  [PASS] User B blocked from accessing User A's order (HTTP 403)")

    # 5b. Receipt Ownership Check: User B cannot access User A's tax receipt
    r_idor_receipt = requests.get(f"{base}/api/payment/receipt/{order_a_id}", headers=headers_b)
    print(f"User B accessing Receipt A status: {r_idor_receipt.status_code}")
    assert r_idor_receipt.status_code == 403, f"Expected 403 Forbidden, got {r_idor_receipt.status_code}"
    print("  [PASS] User B blocked from accessing User A's payment receipt (HTTP 403)")

    # 5c. Email Notifications Ownership Check: User B cannot access User A's email notifications
    r_idor_emails = requests.get(f"{base}/api/notifications/emails/{order_a_id}", headers=headers_b)
    print(f"User B accessing Order A email logs status: {r_idor_emails.status_code}")
    assert r_idor_emails.status_code == 403, f"Expected 403 Forbidden, got {r_idor_emails.status_code}"
    print("  [PASS] User B blocked from accessing User A's email notification logs (HTTP 403)")

    # 5d. Reschedule Ownership Check: User B cannot modify User A's installation schedule
    r_idor_reschedule = requests.post(f"{base}/api/orders/{order_a_id}/reschedule", json={
        "new_date": "2026-12-31"
    }, headers=headers_b)
    print(f"User B rescheduling Order A status: {r_idor_reschedule.status_code}")
    assert r_idor_reschedule.status_code == 403
    print("  [PASS] User B blocked from modifying User A's schedule (HTTP 403)")

    # 5e. NPS Ownership Check: User B cannot submit rating for User A's order
    r_idor_nps = requests.post(f"{base}/api/orders/{order_a_id}/nps", json={
        "rating": 1
    }, headers=headers_b)
    print(f"User B submitting NPS on Order A status: {r_idor_nps.status_code}")
    assert r_idor_nps.status_code == 403
    print("  [PASS] User B blocked from submitting NPS on User A's order (HTTP 403)")

    # 5f. WhatsApp Session Ownership Check: User B cannot inspect User A's WhatsApp session
    r_idor_wa = requests.get(f"{base}/api/whatsapp/session/{user_a_phone}", headers=headers_b)
    print(f"User B inspecting User A's WhatsApp session status: {r_idor_wa.status_code}")
    assert r_idor_wa.status_code == 403, f"Expected 403 Forbidden, got {r_idor_wa.status_code}"
    print("  [PASS] User B blocked from inspecting User A's WhatsApp session (HTTP 403)")

    # 5g. KYC Case Ownership Check: User B cannot inspect User A's KYC case
    r_idor_kyc = requests.get(f"{base}/api/kyc/cases/{case_a_id}", headers=headers_b)
    print(f"User B inspecting User A's KYC case status: {r_idor_kyc.status_code}")
    assert r_idor_kyc.status_code == 403, f"Expected 403 Forbidden, got {r_idor_kyc.status_code}"
    print("  [PASS] User B blocked from inspecting User A's KYC case (HTTP 403)")

    # 5h. Legitimate Owner & Admin Verification
    r_owner_order = requests.get(f"{base}/api/orders/{order_a_id}", headers=headers_a)
    assert r_owner_order.status_code == 200
    print("  [PASS] Legitimate Owner (User A) accesses Order A successfully (HTTP 200)")

    r_admin_order = requests.get(f"{base}/api/orders/{order_a_id}", headers=headers_admin)
    assert r_admin_order.status_code == 200
    print("  [PASS] Enterprise Ops Admin accesses Order A successfully (HTTP 200)")

    print("\n=========================================================================")
    print(" ALL REQUIREMENTS (5, 6, 7, 8) AUDITED & VERIFIED SUCCESSFULLY! ")
    print("=========================================================================")

if __name__ == "__main__":
    test_ownership_and_integrity()
