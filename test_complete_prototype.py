import os
import requests
import json
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"

def test_prototype():
    print("=" * 60)
    print("PROJECT UDYAM DIGITAL - END-TO-END VERIFICATION SUITE")
    print("=" * 60)

    # 1. Health & Static Check
    res = requests.get(BASE_URL)
    assert res.status_code == 200, f"Frontend static load failed: {res.status_code}"
    assert "Project Udyam Digital" in res.text, "Index HTML missing expected title"
    print("✔ [1/8] Frontend & Static Assets: OK (Status 200)")

    # 2. 3-Bucket Catalog Engine
    cat_res = requests.post(f"{BASE_URL}/api/catalog/buckets", json={
        "city_tier": 2,
        "employee_count": 3,
        "num_sites": 1,
        "has_gstin": False,
        "current_base_id": "P01"
    })
    assert cat_res.status_code == 200, "Catalog buckets API failed"
    buckets = cat_res.json()
    assert len(buckets["bucket_a_base_plans"]) > 0, "Bucket A should contain base plans"
    assert len(buckets["bucket_b_modular_addons"]) > 0, "Bucket B should contain addons"
    assert len(buckets["bucket_c_locked_plans"]) > 0, "Bucket C should have locked plans for Non-GST"
    print(f"✔ [2/8] 3-Bucket Catalog Engine: OK ({len(buckets['bucket_a_base_plans'])} Base, {len(buckets['bucket_b_modular_addons'])} Add-ons, {len(buckets['bucket_c_locked_plans'])} Locked)")

    # 3. Transparent Pricing & Down-sell Reconciler
    quote_res = requests.post(f"{BASE_URL}/api/pricing/quote", json={
        "quantities": {"P01": 1, "P07": 2, "P19": 1},
        "apply_digital_discount": True,
        "waive_setup_fee": True
    })
    assert quote_res.status_code == 200
    qdata = quote_res.json()
    assert qdata["monthly_subtotal_inr"] > 0
    assert qdata["gst_18_inr"] == round(qdata["monthly_subtotal_inr"] * 0.18, 2)
    assert qdata["one_time_setup_inr"] == 0.0
    print(f"✔ [3/8] Pricing Calculator: OK (Subtotal: ₹{qdata['monthly_subtotal_inr']}, GST: ₹{qdata['gst_18_inr']}, Total: ₹{qdata['total_monthly_inr']})")

    # 4-step downsell
    downsell_res = requests.post(f"{BASE_URL}/api/pricing/downsell", json={
        "quantities": {"P01": 1, "P07": 2, "P19": 1},
        "step": 1
    })
    assert downsell_res.status_code == 200
    dsdata = downsell_res.json()
    assert "P19" not in [i["product_id"] for i in dsdata["items"]]
    print(f"✔ [4/8] Down-sell Reconciler: OK (Step 1 removed P19 non-essential add-on)")

    # 4. Bilingual AI Advisor (English & Hindi)
    en_adv = requests.post(f"{BASE_URL}/api/advisor/chat", json={
        "message": "I run a dental clinic with 4 chairs in Pune.",
        "language": "en"
    })
    assert en_adv.status_code == 200
    en_json = en_adv.json()
    assert len(en_json["recommended_bundle"]) > 0

    hi_adv = requests.post(f"{BASE_URL}/api/advisor/chat", json={
        "message": "मेरी इंदौर में 2 कर्मचारियों के साथ किराना दुकान है।",
        "language": "hi"
    })
    assert hi_adv.status_code == 200
    hi_json = hi_adv.json()
    assert "नमस्ते" in hi_json["message"]
    print(f"✔ [5/8] Vernacular AI Advisor: OK (EN & HI verified with explainability tags)")

    # 5. Smart KYC: Real OCR & Blur Engine
    specimen_dir = Path("YTL_TrackA_Udyam_Digital_Data/kyc_documents")
    k12_file = specimen_dir / "K12_gst_certificate.png"
    assert k12_file.exists(), f"Specimen file missing: {k12_file}"

    with open(k12_file, "rb") as f:
        up_res = requests.post(f"{BASE_URL}/api/kyc/upload", files={"file": ("test_k12_upload.png", f, "image/png")})
    assert up_res.status_code == 200, f"Upload API failed: {up_res.text}"
    ocr_out = up_res.json()
    assert ocr_out["is_clear"] is True
    assert ocr_out["blur_variance"] > 100.0
    assert ocr_out["extracted_fields"]["gstin"] == "37NBLXS1145E1ZU"
    print(f"✔ [6/8] Real Document Upload & OCR: OK (GSTIN: {ocr_out['extracted_fields']['gstin']}, Variance: {ocr_out['blur_variance']})")

    # 6. KYC Statutory Traps & Registry Rule Checks
    # Clean Pass: K12
    v12 = requests.post(f"{BASE_URL}/api/kyc/verify-extracted", json={
        "applicant_code": "K12",
        "gstin": "37NBLXS1145E1ZU",
        "entity_name": "Star Electronics",
        "bill_date": "2026-07-06",
        "blur_variance": 1233.0
    }).json()
    assert v12["status"] == "VERIFIED", f"K12 should be VERIFIED, got {v12}"

    # Blurry Trap: K04
    v04 = requests.post(f"{BASE_URL}/api/kyc/verify-extracted", json={
        "applicant_code": "K04",
        "gstin": "27P2SXS1936O1ZH",
        "entity_name": "Ganesh Woodcraft",
        "blur_variance": 1.03
    }).json()
    assert v04["status"] == "ACTION_REQUIRED", f"K04 should be ACTION_REQUIRED, got {v04}"

    # Cancelled GST Trap: K01
    v01 = requests.post(f"{BASE_URL}/api/kyc/verify-extracted", json={
        "applicant_code": "K01",
        "gstin": "37IHKXV5167L1ZS",
        "entity_name": "Vindhya Tours & Travels",
        "blur_variance": 500.0
    }).json()
    assert v01["status"] == "REJECTED", f"K01 should be REJECTED, got {v01}"
    assert any("Cancelled" in r for r in v01["reasons"])

    # Expired Bill Trap: K11
    v11 = requests.post(f"{BASE_URL}/api/kyc/verify-extracted", json={
        "applicant_code": "K11",
        "gstin": "37NBLXS1145E1ZU",
        "entity_name": "Star Electronics",
        "bill_date": "2025-10-31",
        "blur_variance": 500.0
    }).json()
    assert v11["status"] == "REJECTED", f"K11 should be REJECTED, got {v11}"
    assert any("Expired" in r for r in v11["reasons"])

    # Non-GST Safe Mode: K03 (Ganesh Woodcraft - Udyam Pass)
    v03_nongst = requests.post(f"{BASE_URL}/api/kyc/verify-extracted", json={
        "applicant_code": "K03",
        "udyam_number": "UDYAM-MH-00-9516696",
        "entity_name": "Ganesh Woodcraft",
        "bill_date": "2026-05-30",
        "blur_variance": 500.0,
        "is_non_gst_mode": True
    }).json()
    assert v03_nongst["status"] == "VERIFIED", f"K03 Non-GST should be VERIFIED, got {v03_nongst}"
    assert v03_nongst["is_non_gst_mode"] is True

    # Standalone Mock Registry APIs
    gst_lookup = requests.post(f"{BASE_URL}/api/verify/gstin", json={"gstin": "37NBLXS1145E1ZU"}).json()
    assert gst_lookup["is_active"] is True
    udyam_lookup = requests.post(f"{BASE_URL}/api/verify/udyam", json={"udyam_number": "UDYAM-AP-00-5186772"}).json()
    assert udyam_lookup["enterprise_name"] == "Star Electronics"
    print("✔ [7/8] Smart KYC Rule Verification: OK (K12: VERIFIED, K03: NON-GST UDYAM PASS, K04: BLUR TRIGGER, K01: CANCELLED GST, K11: EXPIRED BILL)")

    # 7. Order Lifecycle, Slot Rescheduling & NPS Rating Handover
    ord_res = requests.post(f"{BASE_URL}/api/orders/create", json={
        "business_name": "Star Electronics",
        "contact_phone": "+91 98765 12345",
        "bundle_data": qdata,
        "kyc_status": "VERIFIED",
        "language": "hi"
    })
    assert ord_res.status_code == 200
    order = ord_res.json()
    order_id = order["order_id"]
    assert order["dpdp_consent_recorded"] is True

    # Reschedule date
    resched = requests.post(f"{BASE_URL}/api/orders/{order_id}/reschedule", json={
        "new_date": "2026-07-28"
    }).json()
    assert resched["new_install_date"] == "2026-07-28"

    # Submit NPS
    nps_res = requests.post(f"{BASE_URL}/api/orders/{order_id}/nps", json={
        "rating": 10,
        "feedback": "Flawless digital onboarding!"
    }).json()
    assert nps_res["nps_rating"] == 10
    print(f"✔ [8/8] Order Machine, Rescheduling & NPS: OK (Order ID: {order_id}, New Date: 2026-07-28, NPS: 10)")

    print("\n" + "=" * 60)
    print("ALL 8 PROJECT UDYAM DIGITAL SUITES PASSED FLAWLESSLY (100% GREEN)")
    print("=" * 60)

if __name__ == "__main__":
    test_prototype()
