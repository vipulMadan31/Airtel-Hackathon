import os
import sys
sys.path.insert(0, os.path.abspath("."))
import requests

base = "http://127.0.0.1:8000"

def test_email_notification_and_post_kyc_order():
    # 1. Verify frontend index.html
    res = requests.get(base + "/")
    assert res.status_code == 200
    assert "openPaymentModalFromQuoteBtn" not in res.text, "openPaymentModalFromQuoteBtn should be removed!"
    assert "id=\"t-token-btn\"" not in res.text, "t-token-btn should be removed!"
    print("Check 1 Passed: 499 pre-KYC payment option cleanly removed from quoteCard.")

    # 2. Test notification test-email endpoint
    test_res = requests.post(base + "/api/notifications/test-email", json={"recipient_email": "phantomroasting@gmail.com"})
    print("Check 2 Test Email Endpoint Status:", test_res.status_code)
    assert test_res.status_code == 200
    data = test_res.json()
    print("Sender email:", data.get("sender_email"))
    print("Dispatch status:", data.get("dispatch_status"))
    print("Error message:", data.get("error_message"))
    assert data.get("sender_email") == "vipul23600@iiitd.ac.in", "Sender should be vipul23600@iiitd.ac.in"
    print("Check 2 Passed: Real email dispatch correctly configured with vipul23600@iiitd.ac.in!")

    # 3. Authenticate customer
    login_res = requests.post(f"{base}/api/auth/login", json={
        "email": "customer@business.in",
        "password": "customer123",
        "role": "MERCHANT"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 4. Generate Server-Verified KYC Case
    kyc_res = requests.post(f"{base}/api/kyc/verify-extracted", json={
        "udyam_number": "UDYAM-TN-00-3866196",
        "entity_name": "Star Electronics",
        "is_non_gst_mode": True,
        "customer_email": "phantomroasting@gmail.com",
        "consent_granted": True,
        "consent": {
            "granted": True,
            "timestamp": "2026-07-01T10:00:00Z",
            "version": "v1.0",
            "purpose": "Statutory Udyam Verification"
        }
    }, headers=headers)
    assert kyc_res.status_code == 200
    kyc_data = kyc_res.json()
    case_id = kyc_data["case_id"]
    assert kyc_data["verdict"] == "APPROVED"
    print("Check 3 Passed: Server KYC Case generated and approved:", case_id)

    # 5. Create Order with Server-Verified Case and Explicit DPDP Consent
    order_res = requests.post(f"{base}/api/orders/create", json={
        "business_name": "Vipul Clinic Testing",
        "contact_phone": "+91 95181 06076",
        "bundle_data": {
            "product_quantities": {"P01": 1},
            "monthly_recurring_total": 999.0,
            "total_monthly_inr": 1178.82,
            "setup_charges_total": 0.0,
            "contract_months": 12
        },
        "case_id": case_id,
        "consent": {
            "granted": True,
            "purpose": "DoT Identity Verification and Optical Line Installation under DPDP Act 2023",
            "version": "v1.0",
            "consent_text": "Customer explicitly granted affirmative consent for subscriber KYC and optical line installation."
        },
        "customer_email": "phantomroasting@gmail.com",
        "installation_address": {"formatted_address": "Shop 2, Red Cross Market, Rohtak - 124001"}
    }, headers=headers)
    assert order_res.status_code == 200, f"Order creation failed: {order_res.text}"
    order = order_res.json()
    order_id = order["order_id"]
    print("Created post-KYC order:", order_id)

    # 6. Create Server Payment Intent
    intent_res = requests.post(f"{base}/api/payment/create-intent", json={
        "order_id": order_id,
        "amount_inr": 499.0
    }, headers=headers)
    assert intent_res.status_code == 200
    intent_data = intent_res.json()
    intent_id = intent_data["intent_id"]
    print("Server Payment Intent created:", intent_id, "Authoritative Amount:", intent_data["amount_inr"])

    # 7. Confirm payment via server payment intent
    pay_res = requests.post(f"{base}/api/payment/confirm", json={
        "order_id": order_id,
        "intent_id": intent_id,
        "payment_method": "UPI_GPAY"
    }, headers=headers)
    assert pay_res.status_code == 200, f"Payment failed: {pay_res.text}"
    receipt = pay_res.json()
    print("Payment confirmed for post-KYC order, receipt generated:", receipt.get("receipt_number"))
    assert receipt.get("amount_paid_inr") == 499.0

    # 8. Verify email was updated for this order
    notif_res = requests.get(f"{base}/api/notifications/emails/{order_id}", headers=headers)
    assert notif_res.status_code == 200
    notifs = notif_res.json().get("notifications", [])
    print(f"Total notifications recorded for order {order_id}:", len(notifs))
    assert len(notifs) >= 2, "Expected initial order creation email + payment confirmed email"
    latest_notif = notifs[0]
    print("Latest notification status:", latest_notif.get("status"))
    print("Latest notification amount paid:", latest_notif.get("amount_paid_inr"))
    assert latest_notif.get("amount_paid_inr") == 499.0
    print("Check Passed: 499 payment and receipt cleanly work post-KYC!")
    print("\nALL VERIFICATION TESTS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    test_email_notification_and_post_kyc_order()
