import requests

base = "http://127.0.0.1:8000"

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

# 3. Test that payment modal and receipt are still accessible after KYC order creation
order_res = requests.post(base + "/api/orders/create", json={
    "business_name": "Vipul Clinic Testing",
    "contact_phone": "+91 95181 06076",
    "bundle_data": {
        "items": [{"name": "Airtel Biz Fibre 100", "price_inr": 899.0}],
        "total_monthly_inr": 1060.82
    },
    "kyc_status": "VERIFIED",
    "customer_email": "phantomroasting@gmail.com",
    "installation_address": {"formatted_address": "Shop 2, Red Cross Market, Rohtak - 124001"}
})
assert order_res.status_code == 200
order = order_res.json()
order_id = order["order_id"]
print("Created post-KYC order:", order_id)

# 4. Confirm payment of 499 token for this real order
pay_res = requests.post(base + "/api/payment/confirm", json={
    "order_id": order_id,
    "txn_id": "TXN-UPI-POST-KYC-123",
    "payment_method": "UPI_GPAY",
    "amount_inr": 499.0
})
assert pay_res.status_code == 200
receipt = pay_res.json()
print("Payment confirmed for post-KYC order, receipt generated:", receipt.get("receipt_number"))
assert receipt.get("amount_paid_inr") == 499.0

# 5. Verify email was updated for this order
notif_res = requests.get(base + f"/api/notifications/emails/{order_id}")
assert notif_res.status_code == 200
notifs = notif_res.json().get("notifications", [])
print(f"Total notifications recorded for order {order_id}:", len(notifs))
assert len(notifs) >= 2, "Expected initial order creation email + payment confirmed email"
latest_notif = notifs[0]
print("Latest notification status:", latest_notif.get("status"))
print("Latest notification amount paid:", latest_notif.get("amount_paid_inr"))
assert latest_notif.get("amount_paid_inr") == 499.0
print("Check 3 & 4 Passed: 499 payment and receipt cleanly work post-KYC!")
print("\nALL VERIFICATION TESTS COMPLETED SUCCESSFULLY!")
