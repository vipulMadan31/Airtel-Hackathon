import json
from app.modules.kyc.validator import KYCValidator
from app.modules.orders.state_machine import OrderStateMachine
from app.modules.payment import PaymentGateway
from app.modules.partner.portal import PartnerPortal

def test_pipeline_end_to_end():
    print("=================================================================")
    print("TESTING FULL PIPELINE: AUTH, NON-GST SAFE MODE, ADDRESS, PAYMENT & FUNNEL")
    print("=================================================================")

    kyc = KYCValidator()
    order_sm = OrderStateMachine()
    payment_gw = PaymentGateway(order_sm=order_sm)
    partner = PartnerPortal()

    # 1. Authorization Arbitration Tests
    # Case 1A: Golden Path STP (Valid GSTIN K12)
    res_k12 = kyc.validate_applicant(
        applicant_code="K12",
        is_non_gst_mode=False
    )
    assert res_k12["status"] == "VERIFIED", f"Expected VERIFIED, got {res_k12['status']}"
    print(f"✔ Golden Path GSTIN (K12): Status={res_k12['status']}, Fast-Track STP Active")

    # Case 1B: Micro Merchant Non-GST Safe Mode (Valid Udyam K03 without GSTIN)
    res_k03 = kyc.validate_applicant(
        applicant_code="K03",
        is_non_gst_mode=True
    )
    assert res_k03["status"] == "VERIFIED", f"Expected VERIFIED, got {res_k03['status']}"
    assert res_k03["is_non_gst_mode"] is True
    print(f"✔ Non-GST Safe Mode (K03): Status={res_k03['status']}, Enterprise Type={res_k03['udyam_details']['enterprise_type']}")

    # Case 1C: Statutory Trap Rejection - Cancelled GSTIN (K01)
    res_k01 = kyc.validate_applicant(
        applicant_code="K01",
        is_non_gst_mode=False
    )
    assert res_k01["status"] == "REJECTED"
    print(f"✔ Cancelled GSTIN Trap (K01): Caught correctly with reasons={res_k01['reasons']}")

    # Case 1D: Action Required - Blurry Document (K04)
    res_k04 = kyc.validate_applicant(
        applicant_code="K04",
        is_non_gst_mode=False
    )
    assert res_k04["status"] == "BLURRY" or "blurry" in str(res_k04['reasons']).lower()
    print(f"✔ Blurry Document Trap (K04): Variance below threshold caught correctly")

    # Case 1E: Expired Bill > 90d (K11)
    res_k11 = kyc.validate_applicant(
        applicant_code="K11",
        is_non_gst_mode=False
    )
    assert res_k11["status"] == "REJECTED" and any("90 days" in r for r in res_k11["reasons"])
    print(f"✔ Expired Address Proof Trap (K11): Caught correctly (>90 days old)")

    # 2. Full Premises Physical Installation Address Submission
    sample_address = {
        "unit_no": "Shop No. 14, Ground Floor",
        "building": "Aggarwal Commercial Complex",
        "street": "Civil Road, Near Subhash Chowk",
        "landmark": "Opposite State Bank ATM",
        "city": "Rohtak",
        "pincode": "124001",
        "on_site_contact": "Amit Sharma (+91 98765 12345)",
        "preferred_slot": "MORNING",
        "formatted_address": "Shop No. 14, Ground Floor, Aggarwal Commercial Complex, Civil Road, Landmark: Opposite State Bank ATM, Rohtak - 124001"
    }

    sample_bundle = {
        "items": [{"product_id": "P02", "name": "Biz Fibre 300", "quantity": 1}],
        "total_monthly_inr": 1768.82
    }

    order = order_sm.create_order(
        business_name="Aggarwal Enterprises",
        contact_phone="+91 98765 12345",
        bundle_data=sample_bundle,
        kyc_status="VERIFIED",
        language="en",
        partner_id="PTR-IND-882",
        installation_address=sample_address
    )

    assert order["order_id"].startswith("UDYAM-")
    assert order["installation_address"]["unit_no"] == "Shop No. 14, Ground Floor"
    assert order["installation_address"]["city"] == "Rohtak"
    assert order["installation_address"]["pincode"] == "124001"
    print(f"✔ Physical Installation Work-Order Created: ID={order['order_id']}, Address={order['installation_address']['formatted_address']}")

    # 3. Priority Token Deposit (₹499)
    intent = payment_gw.create_payment_intent(
        order_id=order["order_id"],
        amount_inr=499.0,
        business_name="Aggarwal Enterprises",
        phone="+91 98765 12345"
    )
    assert intent["amount_inr"] == 499.0
    print(f"✔ ₹499 Payment Intent Created: Txn={intent['txn_id']}, UPI Link={intent['upi_intent_url']}")

    receipt = payment_gw.confirm_payment(
        order_id=order["order_id"],
        txn_id=intent["txn_id"],
        payment_method="UPI_PHONEPE",
        mandate_active=True,
        amount_inr=499.0
    )
    assert receipt["payment_status"] == "SUCCESS"
    assert receipt["sac_code"] == "998411"
    assert receipt["base_amount_inr"] == 422.88
    assert receipt["gst_18_inr"] == 76.12
    print(f"✔ ₹499 Payment Confirmed: Receipt={receipt['receipt_number']}, SAC=998411, Mandate={receipt['mandate_status']}")

    # Verify order reflected in database
    refreshed_order = order_sm.get_order(order["order_id"])
    assert refreshed_order["token_paid"] == 1
    assert refreshed_order["payment_txn_id"] == intent["txn_id"]
    print(f"✔ Order State Updated in DB: token_paid=1, txn_id={refreshed_order['payment_txn_id']}")

    # 4. Funnel Updation & Propensity Recalculation
    p_score = partner.calculate_propensity_score({
        "has_gstin": "Y",
        "monthly_telecom_spend_inr": 3500,
        "num_sites": 2,
        "employee_count": 10
    })
    assert p_score >= 90
    print(f"✔ Funnel Propensity Score Recalculated: {p_score}/100 (High-Confidence Fast-Track)")

    print("\n=================================================================")
    print("ALL AUTHENTICATION, KYC, ADDRESS, PAYMENT & FUNNEL TESTS PASSED!")
    print("=================================================================")

if __name__ == "__main__":
    test_pipeline_end_to_end()
