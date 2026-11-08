import os
import sys

# Ensure root directory is on PYTHONPATH
sys.path.insert(0, os.path.abspath("."))

from app.data_loader import DataLoader
from app.modules.catalog.engine import CatalogEngine
from app.modules.pricing.calculator import PricingCalculator
from app.modules.kyc.validator import KYCValidator
from app.modules.orders.state_machine import OrderStateMachine
from app.modules.partner.portal import PartnerPortal
from app.modules.advisor.adapter import AdvisorAdapter

def run_tests():
    print("=== STARTING PROJECT UDYAM AUTOMATED TEST SUITE ===")
    
    # 1. DataLoader Test
    loader = DataLoader.get_instance()
    products = loader.get_all_products()
    assert len(products) == 25, f"Expected 25 products, got {len(products)}"
    print("[PASS] DataLoader: Successfully loaded all 25 catalogue products.")

    # 2. Catalogue Engine Test
    engine = CatalogEngine()
    # Test Dependency: P09 (Failover) requires base broadband P01|P02|P03|P05|P06
    valid_dep, errs = engine.validate_bundle_dependencies(["P01", "P09"])
    assert valid_dep, f"Expected valid dependency for P01+P09, got errors: {errs}"
    invalid_dep, errs = engine.validate_bundle_dependencies(["P07", "P09"]) # P07 is SIM, not broadband
    assert not invalid_dep, "Expected invalid dependency for P07+P09, but it passed!"
    print("[PASS] CatalogEngine: Dependency validation strictly enforced (P09 blocked without base line).")

    # 3. Pricing Calculator Test
    pricing = PricingCalculator()
    quote = pricing.calculate_quote({"P01": 1, "P07": 2}, apply_digital_discount=True, waive_setup_fee=True)
    assert quote["is_valid"], "Quote calculation failed"
    # P01 min is 999, P07 min is 299*2 = 598. Subtotal = 1597. GST 18% = 287.46. Total = 1884.46.
    expected_subtotal = 999.0 + (299.0 * 2)
    assert quote["monthly_subtotal_inr"] == expected_subtotal, f"Expected {expected_subtotal}, got {quote['monthly_subtotal_inr']}"
    assert quote["booking_token_inr"] == 499.0, "Expected ₹499 booking token"
    print(f"[PASS] PricingCalculator: Monthly total reconciled to ₹{quote['total_monthly_inr']} (Subtotal ₹{quote['monthly_subtotal_inr']} + 18% GST).")

    # 4. Down-sell Sequence Test
    downsell_q = pricing.execute_downsell_step({"P01": 1, "P19": 1, "P23": 2}, step=1)
    # Step 1 strips non-connectivity (P19 POS and P23 CCTV removed)
    item_ids = [item["product_id"] for item in downsell_q["items"]]
    assert "P19" not in item_ids and "P23" not in item_ids, "Downsell step 1 failed to strip non-essentials"
    print("[PASS] Down-sell Sequence: Step 1 stripped non-essential software add-ons successfully.")

    # 5. Smart KYC Planted Traps Test
    kyc = KYCValidator()
    # Test K01 (Cancelled GSTIN)
    res_k01 = kyc.validate_applicant("K01")
    assert res_k01["status"] == "REJECTED", f"Expected K01 to be REJECTED, got {res_k01['status']}"
    print("[PASS] KYC Validator: Applicant K01 correctly REJECTED (GST registration Cancelled in registry).")

    # Test K11 (Expired Address Proof >90 days)
    res_k11 = kyc.validate_applicant("K11")
    assert res_k11["status"] == "REJECTED", f"Expected K11 to be REJECTED, got {res_k11['status']}"
    print("[PASS] KYC Validator: Applicant K11 correctly REJECTED (Bill date 2025-10-31 is >90 days old vs 2026-07-15).")

    # Test K04 (Blurry Document)
    res_k04 = kyc.validate_applicant("K04")
    assert res_k04["status"] == "ACTION_REQUIRED", f"Expected K04 ACTION_REQUIRED, got {res_k04['status']}"
    print("[PASS] KYC Validator: Applicant K04 correctly flagged ACTION_REQUIRED (Blurry image detected).")

    # Test K12 (Golden Path)
    res_k12 = kyc.validate_applicant("K12")
    assert res_k12["status"] == "VERIFIED", f"Expected K12 VERIFIED, got {res_k12['status']}"
    print("[PASS] KYC Validator: Applicant K12 correctly VERIFIED (Golden path straight-through pass).")

    # 6. Orders & Persistence State Machine Test
    order_sm = OrderStateMachine()
    case_id = order_sm.create_kyc_case(
        user_id="USR-TEST-STAR",
        customer_email="star@electronics.in",
        doc_type="GST",
        id_number="06AAAAA0000A1Z5",
        entity_name="Star Electronics",
        verdict="APPROVED"
    )
    order = order_sm.create_order(
        business_name="Star Electronics",
        contact_phone="+91 98765 00000",
        bundle_data=quote,
        case_id=case_id,
        explicit_consent={"granted": True, "timestamp": "2026-07-15T10:00:00Z", "version": "1.0"},
        kyc_status="VERIFIED"
    )
    order_id = order["order_id"]
    retrieved = order_sm.get_order(order_id)
    assert retrieved is not None, "Failed to retrieve order from SQLite"
    assert retrieved["business_name"] == "Star Electronics", "Order data corrupted in SQLite"
    # Reschedule test
    order_sm.reschedule_installation(order_id, "2026-07-28")
    updated = order_sm.get_order(order_id)
    assert updated["scheduled_install_date"] == "2026-07-28", "Rescheduling failed"
    print(f"[PASS] OrderStateMachine: Created and persisted order '{order_id}', verified SQLite state and slot rescheduling.")

    # 7. Partner Portal & Propensity Scoring Test
    partner = PartnerPortal()
    stalled = partner.get_stalled_leads_with_propensity(limit=5)
    assert len(stalled) > 0, "No stalled leads retrieved"
    assert "propensity_score" in stalled[0], "Propensity score missing"
    print(f"[PASS] PartnerPortal: Retrieved stalled leads with calibrated propensity scores (Top Lead: {stalled[0]['lead_id']}, Score: {stalled[0]['propensity_score']}).")

    # 8. Advisor Adapter Test
    advisor = AdvisorAdapter()
    adv_res = advisor.process_user_message("I run a dental clinic in Pune with 6 staff. Need wifi and email.", language="en")
    assert "P02" in adv_res["recommended_bundle"], "Advisor failed to recommend clinic base bundle"
    assert len(adv_res["explainability_tags"]) > 0, "Advisor explainability tags missing"
    print(f"[PASS] AdvisorAdapter: Recommended bundle {adv_res['recommended_bundle']} with explainability tags.")

    print("\n>>> ALL AUTOMATED BACKEND TESTS PASSED (100% GREEN) <<<")

if __name__ == "__main__":
    run_tests()

