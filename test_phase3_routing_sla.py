from app.modules.partner.portal import PartnerPortal
from app.modules.auth.rbac import get_admin_telemetry

def test_routing_and_sla():
    portal = PartnerPortal()

    print("=================================================================")
    print("TESTING PHASE 3: 4-TIER HIERARCHICAL ROUTING & 4-HOUR SLA ESCALATION")
    print("=================================================================")

    # Test 1: Level 1 Exact 6-Digit Pincode Match
    r1 = portal.resolve_partner_for_lead(pincode="452001", city="Indore", tier=2)
    assert r1["routing_level"] == 1
    assert r1["routing_tier"] == "EXACT_PIN"
    assert r1["partner_id"] == "PTR-IND-882"
    assert "Airtel Mitra Partner" in r1["partner_name"]
    assert r1["sla_hours"] == 4.0
    print(f"✔ Level 1 (Exact PIN): {r1['routing_label']} -> {r1['partner_name']} ({r1['partner_id']}), SLA: {r1['sla_hours']}h")

    # Test 2: Level 2 3-Digit Postal District Prefix Match
    r2 = portal.resolve_partner_for_lead(pincode="201305", city="Greater Noida", tier=1)
    assert r2["routing_level"] == 2
    assert r2["routing_tier"] == "DISTRICT_PREFIX"
    assert r2["partner_id"] == "PTR-NOI-101"
    assert r2["sla_hours"] == 4.0
    print(f"✔ Level 2 (District Prefix): {r2['routing_label']} -> {r2['partner_name']} ({r2['partner_id']}), SLA: {r2['sla_hours']}h")

    # Test 3: Level 3 City / Regional Pool Match
    r3 = portal.resolve_partner_for_lead(pincode=None, city="Pune", tier=1)
    assert r3["routing_level"] == 3
    assert r3["routing_tier"] == "CITY_POOL"
    assert r3["partner_id"] == "PTR-PUN-303"
    print(f"✔ Level 3 (City Pool): {r3['routing_label']} -> {r3['partner_name']} ({r3['partner_id']})")

    # Test 4: Level 4 Central Enterprise Ops Pool Fallback
    r4 = portal.resolve_partner_for_lead(pincode="799001", city="Remote Village", tier=3)
    assert r4["routing_level"] == 4
    assert r4["routing_tier"] == "CENTRAL_OPS"
    assert r4["partner_id"] == "ADM-HQ-001"
    assert r4["sla_hours"] == 24.0
    print(f"✔ Level 4 (Central Ops Fallback): {r4['routing_label']} -> {r4['partner_name']} ({r4['partner_id']}), SLA: {r4['sla_hours']}h")

    # Test 5: Fast-Track Geo-Routing & 4-Hour SLA in Live Customer Queue
    leads = portal.get_stalled_leads_with_propensity(limit=15)
    assert len(leads) > 0

    top_lead = leads[0]
    assert top_lead["is_real_time"] is True
    assert top_lead["propensity_score"] >= 70
    assert "left" in top_lead["sla_remaining"] or top_lead["sla_remaining"] == "Locked"
    assert top_lead["sla_status"] in ["ACTIVE", "WARNING", "CLAIMED"]
    print(f"✔ Live Fast-Track Lead [{top_lead['lead_id']} - {top_lead['business_name']}]: Propensity={top_lead['propensity_score']}, Status={top_lead['sla_status']}, SLA={top_lead['sla_remaining']}")

    # Test 6: Admin Exception Desk Integration & Real Telemetry Structure
    admin_telemetry = get_admin_telemetry()
    assert "funnel_metrics" in admin_telemetry
    assert "operational_efficiency" in admin_telemetry
    assert "segment_distribution" in admin_telemetry
    assert "manual_escalations_queue" in admin_telemetry

    escalations = admin_telemetry["manual_escalations_queue"]
    assert isinstance(escalations, list)
    print(f"✔ Admin Escalation Desk: Verified structure with {len(escalations)} live exception leads")

    print("\n=================================================================")
    print("PHASE 3 HIERARCHICAL ROUTING & 4-HOUR SLA VALIDATED 100% GREEN!")
    print("=================================================================")

if __name__ == "__main__":
    test_routing_and_sla()
