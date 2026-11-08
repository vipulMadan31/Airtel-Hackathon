"""
Comprehensive Test Suite for Requirement 4 & Requirement 5
4. Catalogue Eligibility & Authoritative Pricing
5. Clearly Separated Simulated vs Real Operations

Validates:
- Invalid SKUs are rejected (400 / ValueError)
- Missing or unverified GSTIN blocks GST-mandatory products (e.g., P03, P10)
- City-tier restrictions strictly enforced (e.g. P03 requires Tier-1)
- Site count restrictions strictly enforced from catalogue (e.g. P10 requires min 3 sites)
- Contract duration violations rejected (e.g. P06 requires min 24 months)
- Manipulated prices and fake setup fee waivers submitted at checkout are rejected (400)
- Unauthorized discount codes are rejected (400)
- Server-side validate_and_price_order() returns authoritative quote
- Checkout API recalculates everything server-side and stores authoritative figures
- Simulated operations are clearly tagged with is_simulated=True, mode='DEMO_SIMULATED', and notices
- No fake real engineer names/phone numbers are fabricated (uses generic simulated assignment)
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))

import uuid
import pytest
import requests

BASE_URL = "http://127.0.0.1:8000"

def get_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "X-Session-Token": token,
        "Content-Type": "application/json"
    }

def register_user(role="MERCHANT", email=None, name="Test User"):
    email = email or f"test_{uuid.uuid4().hex[:8]}@example.com"
    r = requests.post(f"{BASE_URL}/api/auth/register", json={
        "email": email,
        "password": "Password123!",
        "name": name,
        "role": role,
        "phone": "+91 98765 00000"
    })
    assert r.status_code == 200, f"Registration failed: {r.text}"
    data = r.json()
    token = data.get("access_token") or data.get("token")
    return token, data.get("user")

def get_verified_kyc(token):
    # 1. Specimen scan to initiate bound verification session
    r_scan = requests.post(f"{BASE_URL}/api/kyc/specimen-scan", headers=get_headers(token), json={
        "applicant_code": "K01",
        "doc_type": "gst"
    })
    assert r_scan.status_code == 200, f"Specimen scan failed: {r_scan.text}"
    v_session = r_scan.json()["verification_session_id"]

    # 2. Verify extracted with explicit DPDP consent
    r_verify = requests.post(f"{BASE_URL}/api/kyc/verify-extracted", headers=get_headers(token), json={
        "gstin": "32TTNXB7384T1ZW",
        "entity_name": "Balaji Dental Care LLP",
        "bill_date": "2020-06-04",
        "verification_session_id": v_session,
        "consent_granted": True,
        "consent": {
            "granted": True,
            "purpose": "Statutory GSTIN/Udyam Registry Verification under DPDP Act 2023",
            "version": "v1.0"
        }
    })
    assert r_verify.status_code == 200, f"KYC verify failed: {r_verify.text}"
    res = r_verify.json()
    assert res["status"] == "VERIFIED"
    assert res["verdict"] == "APPROVED"
    return res["case_id"]


def test_quote_rejection_invalid_sku():
    """Authoritative order validation rejects unknown product IDs."""
    r = requests.post(f"{BASE_URL}/api/pricing/validate-order", json={
        "quantities": {"P999_INVALID": 1},
        "city": "Delhi",
        "pincode": "110001",
        "employee_count": 10,
        "num_sites": 1,
        "contract_months": 12
    })
    assert r.status_code == 400
    assert "Invalid product SKU" in r.json()["detail"] or "does not exist" in r.json()["detail"]


def test_gstin_restriction_enforcement():
    """Products requiring GSTIN (e.g., P03, P10) are rejected if GST status is unconfirmed/false."""
    # Attempt to order P03 with has_gstin = False
    r_false = requests.post(f"{BASE_URL}/api/pricing/validate-order", json={
        "quantities": {"P03": 1},  # Biz Fibre 1Gbps (requires GSTIN)
        "city": "Delhi",
        "pincode": "110001",
        "employee_count": 25,
        "num_sites": 1,
        "has_gstin": False,
        "contract_months": 12
    })
    assert r_false.status_code == 400
    assert "Requires active GSTIN verification" in r_false.json()["detail"]

    # Attempt to order P03 with has_gstin = None / omitted (must fail closed)
    r_unknown = requests.post(f"{BASE_URL}/api/pricing/validate-order", json={
        "quantities": {"P03": 1},
        "city": "Delhi",
        "pincode": "110001",
        "employee_count": 25,
        "num_sites": 1,
        "has_gstin": None,
        "contract_months": 12
    })
    assert r_unknown.status_code == 400
    assert "Requires active GSTIN verification" in r_unknown.json()["detail"]


def test_city_tier_restriction():
    """Products restricted to Tier 1 cities cannot be ordered in Tier 2/3 locations."""
    # P03 requires Tier 1; Jaipur is Tier 2
    r = requests.post(f"{BASE_URL}/api/pricing/validate-order", json={
        "quantities": {"P03": 1},
        "city": "Jaipur",  # Tier 2
        "pincode": "302001",
        "employee_count": 25,
        "num_sites": 1,
        "has_gstin": True,
        "contract_months": 12
    })
    assert r.status_code == 400
    assert "Tier-1" in r.json()["detail"] or "Tier-2" in r.json()["detail"]


def test_catalogue_minimum_sites_and_dependencies():
    """Managed SD-WAN (P10) requires at least 3 sites and a base connectivity product."""
    # 1. Failing dependency: P10 without base connectivity (P01/P02/P03)
    r_dep = requests.post(f"{BASE_URL}/api/pricing/validate-order", json={
        "quantities": {"P10": 1},
        "city": "Delhi",
        "pincode": "110001",
        "employee_count": 30,
        "num_sites": 3,
        "has_gstin": True,
        "contract_months": 24
    })
    assert r_dep.status_code == 400
    assert "Invalid bundle" in r_dep.json()["detail"] or "base connectivity" in r_dep.json()["detail"]

    # 2. Failing site count: P10 with only 2 sites (Catalogue strictly requires min_sites=3)
    r_sites = requests.post(f"{BASE_URL}/api/pricing/validate-order", json={
        "quantities": {"P01": 1, "P10": 1},
        "city": "Delhi",
        "pincode": "110001",
        "employee_count": 30,
        "num_sites": 2,  # Catalogue specifies 3
        "has_gstin": True,
        "contract_months": 24
    })
    assert r_sites.status_code == 400
    assert "Requires at least 3 business locations" in r_sites.json()["detail"] or "locations" in r_sites.json()["detail"]


def test_minimum_contract_months_restriction():
    """Products with minimum contract periods reject shorter durations."""
    # P06 (Dedicated Cloud Connect) requires min_contract_months = 24
    r = requests.post(f"{BASE_URL}/api/pricing/validate-order", json={
        "quantities": {"P01": 1, "P06": 1},
        "city": "Delhi",
        "pincode": "110001",
        "employee_count": 20,
        "num_sites": 1,
        "has_gstin": True,
        "contract_months": 12  # Below required 24 months
    })
    assert r.status_code == 400
    assert "minimum contract duration of 24 months" in r.json()["detail"] or "contract duration" in r.json()["detail"].lower()


def test_checkout_rejects_price_tampering_and_unauthorized_discounts():
    """Checkout API strictly recalculates and detects manipulated client pricing and discounts."""
    token, user = register_user()
    kyc_case_id = get_verified_kyc(token)

    consent_payload = {
        "granted": True,
        "timestamp": "2026-06-01T10:00:00Z",
        "version": "v1.0",
        "purpose": "Subscriber Registration"
    }
    address_payload = {
        "line1": "Shop 4, Market Lane, Connaught Place",
        "city": "Delhi",
        "pincode": "110001"
    }

    # 1. Tampered monthly total (Client claims P01 costs ₹100 instead of ₹999)
    tampered_order = {
        "business_name": "Test Kirana",
        "contact_phone": "+91 98765 00000",
        "installation_address": address_payload,
        "case_id": kyc_case_id,
        "consent": consent_payload,
        "bundle_data": {
            "product_quantities": {"P01": 1},
            "monthly_recurring_total": 100.0,  # FAKE: catalogue price is 999.0
            "setup_charges_total": 0.0,
            "contract_months": 12
        }
    }
    r = requests.post(f"{BASE_URL}/api/orders/create", headers=get_headers(token), json=tampered_order)
    assert r.status_code == 400
    assert "Manipulated price detected" in r.json()["detail"] or "Price manipulation" in r.json()["detail"]

    # 2. Tampered setup fee (Client claims P01 setup fee is ₹250 instead of catalogue ₹0.0)
    tampered_setup = {
        "business_name": "Test Kirana",
        "contact_phone": "+91 98765 00000",
        "installation_address": address_payload,
        "case_id": kyc_case_id,
        "consent": consent_payload,
        "bundle_data": {
            "product_quantities": {"P01": 1},
            "monthly_recurring_total": 999.0,
            "setup_charges_total": 250.0,  # FAKE: catalogue setup is 0.0
            "contract_months": 12,
            "waive_setup_fee": False
        }
    }
    r_setup = requests.post(f"{BASE_URL}/api/orders/create", headers=get_headers(token), json=tampered_setup)
    assert r_setup.status_code == 400
    assert "Manipulated setup fee detected" in r_setup.json()["detail"] or "setup fee" in r_setup.json()["detail"].lower()

    # 3. Unauthorized discount code
    fake_promo_order = {
        "business_name": "Test Kirana",
        "contact_phone": "+91 98765 00000",
        "installation_address": address_payload,
        "case_id": kyc_case_id,
        "consent": consent_payload,
        "bundle_data": {
            "product_quantities": {"P01": 1},
            "monthly_recurring_total": 999.0,
            "setup_charges_total": 0.0,
            "discount_code": "HACKER_50_OFF",
            "contract_months": 12
        }
    }
    r_promo = requests.post(f"{BASE_URL}/api/orders/create", headers=get_headers(token), json=fake_promo_order)
    assert r_promo.status_code == 400
    assert "Unauthorized discount code" in r_promo.json()["detail"] or "discount code" in r_promo.json()["detail"].lower()


def test_authoritative_order_creation_and_simulation_tags():
    """Checkout succeeds with valid catalogue inputs and clearly labels operations as DEMO / SIMULATED."""
    token, user = register_user()
    kyc_case_id = get_verified_kyc(token)

    consent_payload = {
        "granted": True,
        "timestamp": "2026-06-01T10:00:00Z",
        "version": "v1.0",
        "purpose": "Subscriber Registration"
    }
    address_payload = {
        "line1": "Shop 4, Market Lane, Connaught Place",
        "city": "Delhi",
        "pincode": "110001"
    }

    # Legitimate order for P01 (Biz Fibre 100)
    # Catalogue: P01 = 999.0 recurring, 0.0 setup
    order_payload = {
        "business_name": "Authentic Kirana Store",
        "contact_phone": "+91 98765 11111",
        "installation_address": address_payload,
        "case_id": kyc_case_id,
        "consent": consent_payload,
        "bundle_data": {
            "product_quantities": {"P01": 1},
            "monthly_recurring_total": 999.0,
            "setup_charges_total": 0.0,
            "contract_months": 12
        }
    }
    r = requests.post(f"{BASE_URL}/api/orders/create", headers=get_headers(token), json=order_payload)
    assert r.status_code == 200, f"Order creation failed: {r.text}"
    order = r.json()

    order_id = order["order_id"]
    bundle = order["bundle"]
    assert bundle["monthly_subtotal_inr"] == 999.0
    assert bundle["one_time_setup_inr"] == 0.0

    # Verify simulation labels & no fake real engineer identity
    assert order.get("is_simulated") is True
    assert "SIMULATED" in order.get("order_mode", "")
    assert "DEMO / SIMULATED" in order.get("simulation_notice", "")
    assert "SIMULATED / DEMO" in order.get("engineer_name", "")
    assert "DEMO" in order.get("engineer_phone", "")

    # Check order fetch endpoint preserves simulation tags
    r_fetch = requests.get(f"{BASE_URL}/api/orders/{order_id}", headers=get_headers(token))
    assert r_fetch.status_code == 200
    fetched_order = r_fetch.json()
    assert fetched_order.get("is_simulated") is True
    assert "SIMULATED" in fetched_order.get("simulation_notice", "")


def test_payment_and_network_simulation_transparency():
    """Network feasibility and payment gateway responses clearly disclose simulation status."""
    # 1. Network feasibility simulation notice
    r_feas = requests.post(f"{BASE_URL}/api/catalog/feasibility", json={"pincode": "110001", "city": "Delhi"})
    assert r_feas.status_code == 200
    feas_data = r_feas.json()
    assert feas_data.get("is_simulated") is True
    assert feas_data.get("mode") == "DEMO_SIMULATED"
    assert "DEMO / SIMULATED" in feas_data.get("simulation_notice", "")

    # 2. Payment intent & confirmation simulation disclosure on real order
    token, user = register_user()
    kyc_case_id = get_verified_kyc(token)

    consent_payload = {
        "granted": True,
        "timestamp": "2026-06-01T10:00:00Z",
        "version": "v1.0",
        "purpose": "Subscriber Registration"
    }
    address_payload = {
        "line1": "Shop 4, Market Lane, Connaught Place",
        "city": "Delhi",
        "pincode": "110001"
    }

    order_payload = {
        "business_name": "Authentic Kirana Store",
        "contact_phone": "+91 98765 11111",
        "installation_address": address_payload,
        "case_id": kyc_case_id,
        "consent": consent_payload,
        "bundle_data": {
            "product_quantities": {"P01": 1},
            "monthly_recurring_total": 999.0,
            "setup_charges_total": 0.0,
            "contract_months": 12
        }
    }
    r_order = requests.post(f"{BASE_URL}/api/orders/create", headers=get_headers(token), json=order_payload)
    assert r_order.status_code == 200
    order_id = r_order.json()["order_id"]

    r_intent = requests.post(f"{BASE_URL}/api/payment/create-intent", headers=get_headers(token), json={
        "order_id": order_id,
        "amount_inr": 499.0
    })
    assert r_intent.status_code == 200, f"Intent creation failed: {r_intent.text}"
    intent_data = r_intent.json()
    assert intent_data.get("is_simulated") is True
    assert intent_data.get("mode") == "DEMO_SIMULATED"
    assert "DEMO / SIMULATED" in intent_data.get("simulation_notice", "")

    # 3. Payment confirmation simulation disclosure
    r_confirm = requests.post(f"{BASE_URL}/api/payment/confirm", headers=get_headers(token), json={
        "order_id": order_id,
        "intent_id": intent_data["intent_id"]
    })
    assert r_confirm.status_code == 200, f"Confirm failed: {r_confirm.text}"
    confirm_data = r_confirm.json()
    receipt = confirm_data.get("receipt") or confirm_data
    assert receipt.get("is_simulated") is True
    assert receipt.get("mode") == "DEMO_SIMULATED"
    assert "DEMO / SIMULATED" in receipt.get("simulation_notice", "")
