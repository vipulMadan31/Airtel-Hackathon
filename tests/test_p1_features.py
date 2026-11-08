"""
Comprehensive Automated Tests for P1: Product Experience, Conversion and Operational Improvements.
Covers:
1. Regional Language Support (Marathi, Extensible dictionary architecture)
2. Micro-Business & Non-GST Onboarding Journey
3. Data-Driven Admin & Partner Dashboards with multi-dimensional filters and CSV export
4. Post-Activation Retention and Customer Support (Dashboard, Ticketing lifecycle, CSAT feedback & outreach queue)
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))

import requests
import pytest
from app.modules.advisor.service import AdvisorService
from app.modules.advisor.nlu import NLUParser

BASE_URL = "http://127.0.0.1:8000"


# --- HELPERS ---
def get_auth_token(email: str, password: str) -> str:
    res = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


# =========================================================================
# 1. REGIONAL LANGUAGE SUPPORT TESTS (MARATHI & EXTENSIBLE ARCHITECTURE)
# =========================================================================
def test_marathi_nlu_and_advisor_flow():
    """Verify Marathi keywords, location detection, and native scripted responses."""
    advisor = AdvisorService()
    parser = NLUParser()

    # Test 1: Marathi Greeting
    res1 = advisor.process_user_message(
        user_message="नमस्कार, मला माझ्या दुकानासाठी इंटरनेट कनेक्शन हवे आहे",
        language="mr"
    )
    assert res1 is not None
    assert "नमस्कार" in res1["message"] or "Airtel Business" in res1["message"]

    # Test 2: Marathi business type and scale detection without location
    entities = parser.extract_entities("माझे पुण्यात किराणा दुकान आहे आणि 3 कर्मचारी आहेत")
    assert entities.get("business_type") in ["kirana", "retail"]
    assert entities.get("city") == "Pune"
    assert entities.get("employee_count") == 3

    # Test 3: Marathi Downsell request
    res_downsell = advisor.process_user_message(
        user_message="हे खूप महाग आहे, कृपया भाडे कमी करा",
        current_profile={"language": "mr", "current_bundle": {"P01": 1, "P19": 1}},
        language="mr"
    )
    assert res_downsell["intent"] == "downsell_request"
    assert "कमी" in res_downsell["message"] or "भाडे" in res_downsell["message"] or "Understood" in res_downsell["message"]


# =========================================================================
# 2. MICRO-BUSINESS & NON-GST ONBOARDING JOURNEY TESTS
# =========================================================================
def test_micro_business_safe_mode_flow():
    """Verify micro-business onboarding without GST registration."""
    advisor = AdvisorService()

    # Kirana store with no GST
    res = advisor.process_user_message(
        user_message="I have a small kirana store, no GSTIN, 2 workers in Indore 452001",
        current_profile={"has_gstin": False},
        language="en"
    )
    bundle = res.get("recommended_bundle") or {}

    # Verify no enterprise GST-only products are recommended (e.g. P05 ILL or P21 Firewall)
    assert "P05" not in bundle
    assert "P21" not in bundle
    # If bundle recommended, verify base retail product is selected
    if bundle:
        assert any(p in bundle for p in ["P01", "P04"])
        assert res["quotation"]["monthly_subtotal_inr"] > 0


# =========================================================================
# 3. DATA-DRIVEN ADMIN & PARTNER DASHBOARD TESTS
# =========================================================================
def test_data_driven_admin_metrics_with_filters():
    """Verify admin metrics calculation from database and multi-dimensional filter support."""
    admin_token = get_auth_token("admin@airtel.com", "airteladmin")

    # Fetch default metrics
    res = requests.get(f"{BASE_URL}/api/admin/metrics", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()

    assert "funnel_metrics" in data
    assert "operational_efficiency" in data
    assert "kyc_breakdown" in data
    assert "partner_performance" in data
    assert "retention_and_support" in data

    # Verify metrics are numeric and real
    assert isinstance(data["funnel_metrics"]["total_inbound_leads"], int)
    assert isinstance(data["kyc_breakdown"]["total_kyc_failures"], int)
    assert isinstance(data["retention_and_support"]["active_subscribers"], int)

    # Test with multi-dimensional filters
    res_filtered = requests.get(
        f"{BASE_URL}/api/admin/metrics?date_preset=30d&segment=kirana&location=indore&stage=ACTIVE",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_filtered.status_code == 200
    filtered_data = res_filtered.json()
    assert "funnel_metrics" in filtered_data


def test_partner_dashboard_metrics_isolation():
    """Verify partner metrics are isolated to the authenticated partner."""
    partner_token = get_auth_token("mitra@airtel.com", "airtelmitra")

    res = requests.get(f"{BASE_URL}/api/partner/metrics", headers={"Authorization": f"Bearer {partner_token}"})
    assert res.status_code == 200
    data = res.json()

    assert data["partner_id"] == "PTR-IND-882"
    assert "partner_leads_claimed" in data
    assert "partner_orders_attributed" in data
    assert "monthly_recurring_trail_inr" in data


def test_admin_csv_report_export():
    """Verify authorized operators can download leads CSV export."""
    admin_token = get_auth_token("admin@airtel.com", "airteladmin")

    res = requests.get(
        f"{BASE_URL}/api/admin/reports/export.csv?date_preset=all",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    assert "text/csv" in res.headers.get("content-type", "")
    assert "Business Name" in res.text or "Business_Name" in res.text or "Lead ID" in res.text

    # Unauthorized customer cannot export
    cust_token = get_auth_token("customer@business.in", "customer123")
    res_unauth = requests.get(
        f"{BASE_URL}/api/admin/reports/export.csv",
        headers={"Authorization": f"Bearer {cust_token}"}
    )
    assert res_unauth.status_code == 403


# =========================================================================
# 4. POST-ACTIVATION RETENTION & CUSTOMER SUPPORT TESTS
# =========================================================================
def test_customer_dashboard_endpoint():
    """Verify customer dashboard returns active subscriptions, billing, and tickets."""
    cust_token = get_auth_token("customer@business.in", "customer123")

    res = requests.get(f"{BASE_URL}/api/customer/dashboard", headers={"Authorization": f"Bearer {cust_token}"})
    assert res.status_code == 200
    data = res.json()

    assert "customer" in data
    assert "active_services" in data
    assert "billing_commitment" in data
    assert "support_tickets" in data
    assert data["customer"]["email"] == "customer@business.in"


def test_support_ticket_lifecycle_and_ownership():
    """Verify support ticket creation, retrieval, milestone updating, and ownership checks."""
    cust_token = get_auth_token("customer@business.in", "customer123")

    # 1. Create a support ticket
    res = requests.post(
        f"{BASE_URL}/api/support/tickets",
        headers={"Authorization": f"Bearer {cust_token}"},
        json={
            "category": "CONNECTIVITY",
            "priority": "HIGH",
            "description": "Optical ONT fiber indicator showing flashing amber light; speed degraded to 2Mbps."
        }
    )
    assert res.status_code == 200
    ticket = res.json()["ticket"]
    ticket_id = ticket["ticket_id"]
    assert ticket["status"] == "OPEN"
    assert ticket["category"] == "CONNECTIVITY"

    # 2. Retrieve customer's tickets
    res_list = requests.get(f"{BASE_URL}/api/support/tickets", headers={"Authorization": f"Bearer {cust_token}"})
    assert res_list.status_code == 200
    tickets = res_list.json()["tickets"]
    assert any(t["ticket_id"] == ticket_id for t in tickets)

    # 3. Update ticket milestone (Admin action)
    admin_token = get_auth_token("admin@airtel.com", "airteladmin")
    res_patch = requests.patch(
        f"{BASE_URL}/api/support/tickets/{ticket_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "status": "IN_PROGRESS",
            "milestone": "Field technician assigned and dispatched"
        }
    )
    assert res_patch.status_code == 200
    updated = res_patch.json()["ticket"]
    assert updated["status"] == "IN_PROGRESS"
    assert "Field technician" in updated["current_milestone"]


def test_post_activation_feedback_and_retention_flagging():
    """Verify CSAT feedback collection and automated proactive retention queue flagging for low ratings."""
    cust_token = get_auth_token("customer@business.in", "customer123")

    # 1. Submit low rating feedback (<= 3)
    res_feedback = requests.post(
        f"{BASE_URL}/api/support/feedback",
        headers={"Authorization": f"Bearer {cust_token}"},
        json={
            "rating": 2,
            "feedback": "Installation survey was delayed by 2 days; need priority resolution.",
            "journey_step": "POST_ACTIVATION"
        }
    )
    assert res_feedback.status_code == 200
    fb_data = res_feedback.json()["feedback"]
    assert fb_data["is_dissatisfied"] == 1
    assert fb_data["follow_up_status"] == "PENDING_RETENTION_OUTREACH"

    # 2. Verify admin retention queue reflects low rating
    admin_token = get_auth_token("admin@airtel.com", "airteladmin")
    res_retention = requests.get(f"{BASE_URL}/api/admin/retention", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_retention.status_code == 200
    ret_data = res_retention.json()

    assert "dissatisfied_customers_queue" in ret_data
    queue = ret_data["dissatisfied_customers_queue"]
    assert any(c["rating"] == 2 for c in queue)
