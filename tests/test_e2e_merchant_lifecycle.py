"""
End-to-End Enterprise Lifecycle Test for Project Udyam Digital / Airtel SYNC
Tests the complete 11-stage merchant acquisition, onboarding, and retention journey:
Merchant registration → AI recommendation → Catalogue validation → Quote →
Consent → KYC → Order creation → Checkout → Tracking → Support ticket → CSAT.
"""

import os
import sys
import time
import requests
import pytest

sys.path.insert(0, os.path.abspath("."))

BASE_URL = os.environ.get("TEST_BASE_URL", "http://127.0.0.1:8000")


def test_complete_e2e_merchant_lifecycle():
    """
    Executes the full 11-step lifecycle journey for a new MSME merchant.
    """
    session_ts = int(time.time())
    merchant_email = f"ganesh_woodcraft_{session_ts}@business.in"
    merchant_password = "SecureMerchantPassword123!"
    merchant_name = "Ganesh Patil"
    business_name = "Ganesh Woodcraft"
    merchant_phone = "+91 98201 12345"

    # =========================================================================
    # STEP 1: MERCHANT REGISTRATION & AUTHENTICATION
    # =========================================================================
    print("\n--- STEP 1: Merchant Registration ---")
    reg_res = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={
            "email": merchant_email,
            "password": merchant_password,
            "name": merchant_name,
            "phone": merchant_phone,
            "role": "MERCHANT"
        }
    )
    assert reg_res.status_code in [200, 201], f"Registration failed: {reg_res.text}"
    reg_data = reg_res.json()
    assert reg_data.get("status") == "success"
    merchant_token = reg_data.get("access_token")
    assert merchant_token, "Access token missing from registration response"
    user_info = reg_data.get("user", {})
    assert user_info.get("role") == "MERCHANT", "Public registration must only issue MERCHANT role!"
    assert user_info.get("email") == merchant_email

    merchant_headers = {"Authorization": f"Bearer {merchant_token}"}

    # Verify identity via /api/auth/me
    me_res = requests.get(f"{BASE_URL}/api/auth/me", headers=merchant_headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data.get("email") == merchant_email
    assert me_data.get("role") == "MERCHANT"
    merchant_user_id = me_data.get("user_id")
    print(f"Step 1 Passed: Merchant {merchant_email} registered as {merchant_user_id}")

    # =========================================================================
    # STEP 2: CONVERSATIONAL AI RECOMMENDATION
    # =========================================================================
    print("\n--- STEP 2: AI Conversational Recommendation ---")
    advisor_res = requests.post(
        f"{BASE_URL}/api/advisor/chat",
        json={
            "message": "I operate Ganesh Woodcraft in Pune with 8 staff. We have Udyam registration without GST and need fast broadband and cloud backup.",
            "current_profile": {},
            "language": "en"
        }
    )
    assert advisor_res.status_code == 200, f"Advisor chat failed: {advisor_res.text}"
    advisor_data = advisor_res.json()
    assert advisor_data.get("intent") == "recommendation", f"Expected recommendation intent, got: {advisor_data.get('intent')}"
    recommended_bundle = advisor_data.get("recommended_bundle")
    assert recommended_bundle, "Advisor did not return a recommended bundle"
    assert "P01" in recommended_bundle or "P02" in recommended_bundle, "Bundle must contain base connectivity (P01 or P02)"
    profile = advisor_data.get("profile", {})
    assert profile.get("city") == "Pune"
    assert profile.get("city_tier") == 1
    assert profile.get("employee_count") == 8
    assert profile.get("has_gstin") is False
    tags = [t.get("name") for t in advisor_data.get("explainability_tags", [])]
    assert len(tags) > 0, "Advisor must provide explainability tags for recommended items"
    print(f"Step 2 Passed: AI recommended bundle {recommended_bundle} with tags: {tags}")

    # =========================================================================
    # STEP 3: SERVER-SIDE CATALOGUE VALIDATION
    # =========================================================================
    print("\n--- STEP 3: Server-Side Catalogue Validation ---")
    # Validate selected products (P01 Biz Fibre 100 + P19 Cloud POS & Billing)
    selected_skus = {"P01": 1, "P19": 1}
    val_res = requests.post(
        f"{BASE_URL}/api/pricing/validate-order",
        json={
            "product_ids": list(selected_skus.keys()),
            "quantities": selected_skus,
            "city_tier": 1,
            "employee_count": 8,
            "num_sites": 1,
            "has_gstin": False,
            "contract_months": 12
        }
    )
    assert val_res.status_code == 200, f"Catalogue validation failed: {val_res.text}"
    val_data = val_res.json()
    assert val_data.get("is_valid") is True, f"Bundle rejected by catalogue rules: {val_data.get('dependency_errors')}"
    assert len(val_data.get("dependency_errors", [])) == 0
    print("Step 3 Passed: Selected products confirmed eligible under catalogue rules for non-GST merchant")

    # =========================================================================
    # STEP 4: AUTHORITATIVE QUOTATION CALCULATION
    # =========================================================================
    print("\n--- STEP 4: Authoritative Quotation Calculation ---")
    quote_res = requests.post(
        f"{BASE_URL}/api/pricing/quote",
        json={
            "quantities": selected_skus,
            "apply_digital_discount": True,
            "waive_setup_fee": True,
            "city_tier": 1,
            "employee_count": 8,
            "num_sites": 1,
            "has_gstin": False,
            "contract_months": 12
        }
    )
    assert quote_res.status_code == 200, f"Quote computation failed: {quote_res.text}"
    quote = quote_res.json()
    assert quote.get("monthly_subtotal_inr") == 1598.0, f"Expected monthly subtotal 1598.0, got {quote.get('monthly_subtotal_inr')}"
    assert quote.get("gst_18_inr") == 287.64, f"Expected 18% GST 287.64, got {quote.get('gst_18_inr')}"
    assert quote.get("total_monthly_inr") == 1885.64, f"Expected total 1885.64, got {quote.get('total_monthly_inr')}"
    assert quote.get("booking_token_inr") == 499.0, f"Expected token 499.0, got {quote.get('booking_token_inr')}"
    assert quote.get("is_simulated") is True, "Prototype simulation transparency badge must be True"
    print(f"Step 4 Passed: Authoritative quote calculated (Monthly: ₹1,598.00 + GST = ₹1,885.64, Token: ₹499.00)")

    # =========================================================================
    # STEP 5: EXPLICIT CUSTOMER CONSENT (DPDP ACT 2023)
    # =========================================================================
    print("\n--- STEP 5: Explicit Customer Consent ---")
    consent_payload = {
        "granted": True,
        "timestamp": "2026-07-01T10:00:00Z",
        "version": "v1.0",
        "purpose": "DoT Subscriber Identity Verification and Optical Line Installation under DPDP Act 2023",
        "consent_text": "Customer explicitly granted affirmative consent for subscriber KYC and optical line installation."
    }
    assert consent_payload["granted"] is True
    assert "DPDP Act 2023" in consent_payload["purpose"]
    print("Step 5 Passed: Customer affirmative consent constructed and bound under DPDP Act 2023")

    # =========================================================================
    # STEP 6: SERVER-CONTROLLED KYC VERIFICATION
    # =========================================================================
    print("\n--- STEP 6: Server-Controlled KYC Verification ---")
    kyc_res = requests.post(
        f"{BASE_URL}/api/kyc/verify-extracted",
        headers=merchant_headers,
        json={
            "udyam_number": "UDYAM-MH-00-9516696",
            "entity_name": business_name,
            "is_non_gst_mode": True,
            "customer_email": merchant_email,
            "consent_granted": True,
            "consent": consent_payload,
            "bill_date": "2026-05-30"
        }
    )
    assert kyc_res.status_code == 200, f"KYC verification failed: {kyc_res.text}"
    kyc_data = kyc_res.json()
    case_id = kyc_data.get("case_id")
    assert case_id, "KYC Case ID missing from response"
    assert kyc_data.get("verdict") == "APPROVED", f"Expected KYC verdict APPROVED, got {kyc_data.get('verdict')}"

    # Verify case retrieval and ownership
    case_get_res = requests.get(f"{BASE_URL}/api/kyc/cases/{case_id}", headers=merchant_headers)
    assert case_get_res.status_code == 200
    assert case_get_res.json().get("verdict") == "APPROVED"
    print(f"Step 6 Passed: KYC Case {case_id} verified with verdict APPROVED")

    # =========================================================================
    # STEP 7: ORDER CREATION (LINKED TO VERIFIED KYC CASE)
    # =========================================================================
    print("\n--- STEP 7: Order Creation Linked to Verified KYC Case ---")
    order_res = requests.post(
        f"{BASE_URL}/api/orders/create",
        headers=merchant_headers,
        json={
            "business_name": business_name,
            "contact_phone": merchant_phone,
            "customer_email": merchant_email,
            "case_id": case_id,
            "bundle_data": {
                "product_quantities": selected_skus,
                "monthly_recurring_total": 1598.0,
                "total_monthly_inr": 1885.64,
                "setup_charges_total": 0.0,
                "contract_months": 12
            },
            "consent": consent_payload,
            "installation_address": {
                "formatted_address": "Plot 44, Hadapsar Industrial Estate, Pune - 411028, Maharashtra"
            }
        }
    )
    assert order_res.status_code == 200, f"Order creation failed: {order_res.text}"
    order_data = order_res.json()
    order_id = order_data.get("order_id")
    assert order_id, "Order ID missing from response"
    print(f"Step 7 Passed: Order {order_id} created in state machine successfully")

    # =========================================================================
    # STEP 8: CHECKOUT & VERIFIED PAYMENT INTENT
    # =========================================================================
    print("\n--- STEP 8: Checkout & Verified Payment Intent ---")
    # Step 8a: Create server-authoritative payment intent bound to this order
    intent_res = requests.post(
        f"{BASE_URL}/api/payment/create-intent",
        headers=merchant_headers,
        json={
            "order_id": order_id,
            "amount_inr": 499.0,
            "business_name": business_name
        }
    )
    assert intent_res.status_code == 200, f"Payment intent creation failed: {intent_res.text}"
    intent_data = intent_res.json()
    intent_id = intent_data.get("intent_id")
    assert intent_id, "Intent ID missing from payment intent response"
    assert intent_data.get("amount_inr") == 499.0
    assert intent_data.get("status") in ["PENDING", "INITIATED"]

    # Step 8b: Confirm payment through server payment intent
    confirm_res = requests.post(
        f"{BASE_URL}/api/payment/confirm",
        headers=merchant_headers,
        json={
            "order_id": order_id,
            "intent_id": intent_id,
            "payment_method": "UPI_PHONEPE"
        }
    )
    assert confirm_res.status_code == 200, f"Payment confirmation failed: {confirm_res.text}"
    receipt_data = confirm_res.json()
    receipt_number = receipt_data.get("receipt_number")
    assert receipt_number, "Receipt number missing from payment confirmation response"
    assert receipt_data.get("amount_paid_inr") == 499.0
    print(f"Step 8 Passed: Verified payment intent {intent_id} confirmed; Tax Receipt {receipt_number} issued")

    # =========================================================================
    # STEP 9: ORDER TRACKING & CUSTOMER DASHBOARD
    # =========================================================================
    print("\n--- STEP 9: Order Tracking & Customer Dashboard ---")
    # Step 9a: Order Tracking
    track_res = requests.get(f"{BASE_URL}/api/orders/{order_id}", headers=merchant_headers)
    assert track_res.status_code == 200, f"Order tracking failed: {track_res.text}"
    track_data = track_res.json()
    assert track_data.get("order_id") == order_id
    assert track_data.get("token_paid") in [1, True]
    assert track_data.get("kyc_status") == "VERIFIED"
    assert track_data.get("current_milestone") is not None
    assert track_data.get("scheduled_install_date") is not None

    # Step 9b: Customer Dashboard
    dash_res = requests.get(f"{BASE_URL}/api/customer/dashboard", headers=merchant_headers)
    assert dash_res.status_code == 200, f"Dashboard retrieval failed: {dash_res.text}"
    dash_data = dash_res.json()
    assert dash_data.get("customer", {}).get("email") == merchant_email
    assert (dash_data.get("customer", {}).get("id") or dash_data.get("customer", {}).get("user_id")) == merchant_user_id
    active_services = dash_data.get("active_services", [])
    assert len(active_services) > 0, "Customer dashboard must reflect subscribed active services"
    assert any(s.get("product_id") == "P01" for s in active_services)
    billing = dash_data.get("billing_commitment", {})
    assert billing.get("monthly_subtotal_inr") == 1598.0
    assert billing.get("monthly_total_commitment_inr") == 1885.64
    print(f"Step 9 Passed: Tracking verified for {order_id}; Dashboard reflects active services & billing commitment")

    # =========================================================================
    # STEP 10: SUPPORT TICKETING & MILESTONE LIFECYCLE
    # =========================================================================
    print("\n--- STEP 10: Support Ticketing & Milestone Progression ---")
    # Step 10a: Merchant raises priority support ticket
    ticket_res = requests.post(
        f"{BASE_URL}/api/support/tickets",
        headers=merchant_headers,
        json={
            "category": "INSTALLATION",
            "priority": "HIGH",
            "subject": "Installation Slot Confirmation",
            "description": "Requesting confirmation of field engineer arrival time slot for optical fiber drop cable routing at Hadapsar unit."
        }
    )
    assert ticket_res.status_code == 200, f"Ticket raising failed: {ticket_res.text}"
    ticket = ticket_res.json().get("ticket", {})
    ticket_id = ticket.get("ticket_id")
    assert ticket_id, "Ticket ID missing from creation response"
    assert ticket.get("status") == "OPEN"
    assert ticket.get("category") == "INSTALLATION"

    # Step 10b: Admin updates milestone to IN_PROGRESS
    admin_login_res = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@airtel.com", "password": "airteladmin", "role": "ADMIN"}
    )
    assert admin_login_res.status_code == 200
    admin_token = admin_login_res.json().get("access_token")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    patch_res = requests.patch(
        f"{BASE_URL}/api/support/tickets/{ticket_id}",
        headers=admin_headers,
        json={
            "status": "IN_PROGRESS",
            "milestone": "Field engineer assigned (Rajesh Shinde, Pune Circle Hub); dispatched with optical splicing kit."
        }
    )
    assert patch_res.status_code == 200, f"Milestone update failed: {patch_res.text}"
    patched_ticket = patch_res.json().get("ticket", {})
    assert patched_ticket.get("status") == "IN_PROGRESS"
    assert "Rajesh Shinde" in patched_ticket.get("current_milestone", "")

    # Step 10c: Merchant verifies updated ticket
    my_tickets_res = requests.get(f"{BASE_URL}/api/support/tickets", headers=merchant_headers)
    assert my_tickets_res.status_code == 200
    my_tickets = my_tickets_res.json().get("tickets", [])
    matching_ticket = next((t for t in my_tickets if t.get("ticket_id") == ticket_id), None)
    assert matching_ticket is not None
    assert matching_ticket.get("status") == "IN_PROGRESS"
    print(f"Step 10 Passed: Support ticket {ticket_id} raised, transitioned to IN_PROGRESS, and verified by merchant")

    # =========================================================================
    # STEP 11: POST-ACTIVATION CSAT FEEDBACK
    # =========================================================================
    print("\n--- STEP 11: Post-Activation CSAT Feedback ---")
    csat_res = requests.post(
        f"{BASE_URL}/api/support/feedback",
        headers=merchant_headers,
        json={
            "rating": 5,
            "feedback": "Exceptional self-serve onboarding. AI advisor recommended the exact right bundle for our woodwork shop and optical drop was on time.",
            "journey_step": "POST_ACTIVATION"
        }
    )
    assert csat_res.status_code == 200, f"CSAT submission failed: {csat_res.text}"
    csat_data = csat_res.json().get("feedback", {})
    assert csat_data.get("rating") == 5
    assert csat_data.get("is_dissatisfied") == 0
    assert csat_data.get("follow_up_status") in ["NOT_REQUIRED", "SATISFIED"]

    # Verify CSAT feedback appears in customer dashboard
    final_dash_res = requests.get(f"{BASE_URL}/api/customer/dashboard", headers=merchant_headers)
    assert final_dash_res.status_code == 200
    feedbacks = final_dash_res.json().get("customer_feedback", [])
    assert any(fb.get("rating") == 5 for fb in feedbacks)
    print(f"Step 11 Passed: 5-star CSAT submitted and recorded in customer dashboard")

    print("\n=======================================================")
    print("ALL 11 STAGES OF END-TO-END MERCHANT LIFECYCLE PASSED!")
    print("=======================================================\n")


def test_dissatisfied_csat_triggers_retention_queue():
    """
    Verifies that when a merchant gives a low CSAT rating (<= 3),
    the system automatically flags them for proactive retention outreach
    and surfaces them on the Admin Ops Retention Queue.
    """
    session_ts = int(time.time())
    merchant_email = f"dissatisfied_merchant_{session_ts}@business.in"

    # Register merchant
    reg_res = requests.post(
        f"{BASE_URL}/api/auth/register",
        json={
            "email": merchant_email,
            "password": "Password123!",
            "name": "Sunil Verma",
            "phone": "+91 98111 22334",
            "role": "MERCHANT"
        }
    )
    assert reg_res.status_code in [200, 201]
    merchant_token = reg_res.json()["access_token"]
    merchant_headers = {"Authorization": f"Bearer {merchant_token}"}

    # Submit low rating feedback (2 stars)
    fb_res = requests.post(
        f"{BASE_URL}/api/support/feedback",
        headers=merchant_headers,
        json={
            "rating": 2,
            "feedback": "Installation technician arrived 3 hours after scheduled slot; router configuration was rushed.",
            "journey_step": "POST_ACTIVATION"
        }
    )
    assert fb_res.status_code == 200
    fb_data = fb_res.json().get("feedback", {})
    assert fb_data.get("rating") == 2
    assert fb_data.get("is_dissatisfied") == 1
    assert fb_data.get("follow_up_status") == "PENDING_RETENTION_OUTREACH"

    # Verify Admin Retention Queue displays the customer
    admin_login_res = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@airtel.com", "password": "airteladmin", "role": "ADMIN"}
    )
    assert admin_login_res.status_code == 200
    admin_token = admin_login_res.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    retention_res = requests.get(f"{BASE_URL}/api/admin/retention", headers=admin_headers)
    assert retention_res.status_code == 200
    retention_queue = retention_res.json().get("dissatisfied_customers_queue", [])
    matching_entry = next((e for e in retention_queue if e.get("customer_email") == merchant_email), None)
    assert matching_entry is not None, f"Dissatisfied customer {merchant_email} not found in admin retention queue"
    assert matching_entry.get("rating") == 2
    assert matching_entry.get("follow_up_status") == "PENDING_RETENTION_OUTREACH"
    assert matching_entry.get("customer_phone") == "+91 98111 22334"
    print(f"Dissatisfied CSAT Retention Test Passed: Merchant {merchant_email} queued for executive outreach.")


if __name__ == "__main__":
    test_complete_e2e_merchant_lifecycle()
    test_dissatisfied_csat_triggers_retention_queue()
