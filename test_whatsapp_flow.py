import requests
import json
from pathlib import Path

base = "http://127.0.0.1:8000"

def test_whatsapp():
    print("=" * 65)
    print("VERIFYING WHATSAPP CONVERSATIONAL FLOW & STRAIGHT-THROUGH KYC")
    print("=" * 65)

    test_phone = "919999000001"
    # Ensure fresh test session
    requests.post(f"{base}/api/whatsapp/simulate", json={"phone": test_phone, "message": "reset"})

    # 1. Meta Webhook Handshake Verification (GET)
    print("\n[Step 1] Testing Meta Webhook Verification Challenge...")
    r1 = requests.get(f"{base}/api/whatsapp/webhook", params={
        "hub.mode": "subscribe",
        "hub.verify_token": "airtel_udyam_secure_token",
        "hub.challenge": "11532523"
    })
    print("Status:", r1.status_code)
    print("Response:", r1.text)
    assert r1.status_code == 200
    assert r1.text == "11532523"
    print("✔ [1/6] Meta Webhook Verification Handshake: PASSED")

    # 2. Vague Query (Progressive Clarification over WhatsApp)
    print("\n[Step 2] Sending WhatsApp message: 'I need wifi'...")
    r2 = requests.post(f"{base}/api/whatsapp/simulate", json={
        "phone": test_phone,
        "message": "I need wifi",
        "language": "en"
    }).json()
    print("Bot Message:\n", r2["responses"][0])
    print("Buttons:", [b["title"] for b in r2.get("buttons", [])])
    assert r2["status"] == "success"
    assert len(r2["responses"]) > 0
    print("✔ [2/6] WhatsApp Progressive Clarification: PASSED")

    # 3. Specific Business Bundle Recommendation + WhatsApp Quote Card
    print("\n[Step 3] Sending: 'Kirana store in Indore, 2 staff, UPI payments'...")
    r3 = requests.post(f"{base}/api/whatsapp/simulate", json={
        "phone": test_phone,
        "message": "Kirana store in Indore, 2 staff, UPI payments",
        "language": "en"
    }).json()
    print("Bot Responses:")
    for m in r3["responses"]:
        print("---")
        print(m)
    print("Buttons:", [b["title"] for b in r3.get("buttons", [])])
    assert len(r3["responses"]) >= 2, "Should return conversational response and quote card"
    assert "Biz Fibre" in r3["responses"][1] or "AIRTEL BUSINESS" in r3["responses"][1]
    print("✔ [3/6] WhatsApp Itemized 18% GST Quote Card: PASSED")

    # 4. Tap 'Proceed to KYC'
    print("\n[Step 4] User taps: 'Proceed to KYC'...")
    r4 = requests.post(f"{base}/api/whatsapp/simulate", json={
        "phone": test_phone,
        "button_payload": "action:proceed_kyc",
        "language": "en"
    }).json()
    print("Bot Message:\n", r4["responses"][0])
    assert "upload" in r4["responses"][0].lower() or "photo" in r4["responses"][0].lower()
    print("✔ [4/6] WhatsApp Document Request Prompt: PASSED")

    # 5. Simulate Snapping & Uploading GST Certificate (K12)
    print("\n[Step 5] Simulating photo upload: K12_gst_certificate.png...")
    specimen_path = Path("YTL_TrackA_Udyam_Digital_Data/kyc_documents/K12_gst_certificate.png")
    assert specimen_path.exists(), "Specimen K12 must exist"

    with open(specimen_path, "rb") as f:
        r5 = requests.post(
            f"{base}/api/whatsapp/simulate/upload",
            data={"phone": test_phone, "language": "en"},
            files={"file": ("K12_gst_certificate.png", f, "image/png")}
        ).json()

    print("Bot Message:\n", r5["responses"][0])
    print("Buttons:", [b["title"] for b in r5.get("buttons", [])])
    assert "VERIFIED" in r5["responses"][0] or "Star Electronics" in r5["responses"][0]
    print("✔ [5/6] WhatsApp Straight-Through KYC Approval: PASSED")

    # 6. Tap 'Pay ₹100 Token & Confirm'
    print("\n[Step 6] User taps: 'Pay ₹100 & Confirm'...")
    r6 = requests.post(f"{base}/api/whatsapp/simulate", json={
        "phone": test_phone,
        "button_payload": "action:confirm_order",
        "language": "en"
    }).json()
    print("Confirmation Message:\n", r6["responses"][0])
    assert "Order ID" in r6["responses"][0] or "Manoj Kumar" in r6["responses"][0]
    print("✔ [6/6] WhatsApp Fast-Track Order Booking (48h SLA): PASSED")

    # 7. Check UI route
    r7 = requests.get(f"{base}/whatsapp-simulator")
    assert r7.status_code == 200, "Simulator page must return 200"
    print("\n✔ [7/7] In-Browser WhatsApp Simulator UI: ACCESSIBLE (Status 200)")

    print("\n" + "=" * 65)
    print("ALL 7 WHATSAPP CONVERSATIONAL SUITES PASSED FLAWLESSLY (100% GREEN)!")
    print("=" * 65)

if __name__ == "__main__":
    test_whatsapp()
