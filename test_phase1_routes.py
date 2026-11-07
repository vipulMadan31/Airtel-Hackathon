from pathlib import Path
from app.main import (
    serve_mitra_portal,
    serve_ops_portal,
    switch_role,
    SwitchRoleRequest,
    get_partner_commissions,
    get_partner_leads,
    get_admin_metrics,
    STATIC_DIR
)

def test_routes_and_views():
    # 1. Test index.html contains decoupled views
    index_path = STATIC_DIR / "index.html"
    assert index_path.exists(), "index.html must exist in STATIC_DIR"
    html_root = index_path.read_text(encoding="utf-8")
    assert 'id="customerView"' in html_root, "customerView must be in index.html"
    assert 'id="mitraView"' in html_root, "mitraView must be in index.html"
    assert 'id="opsView"' in html_root, "opsView must be in index.html"
    assert "Project Udyam Digital" in html_root
    print("✔ STATIC_DIR/index.html contains decoupled customerView, mitraView, and opsView")

    # 2. Test /mitra route handler
    mitra_resp = serve_mitra_portal()
    assert Path(mitra_resp.path) == index_path
    assert 'id="mitraView"' in html_root
    assert "Airtel Mitra Partner (PTR-IND-882)" in html_root
    print("✔ serve_mitra_portal() returns FileResponse pointing to index.html with dedicated Mitra Portal")

    # 3. Test /ops & /admin route handler
    ops_resp = serve_ops_portal()
    assert Path(ops_resp.path) == index_path
    assert 'id="opsView"' in html_root
    assert "Airtel Enterprise Operations Lead" in html_root
    print("✔ serve_ops_portal() returns FileResponse pointing to index.html with dedicated Ops Center")

    # 4. Test RBAC Switch Role
    res_switch_partner = switch_role(SwitchRoleRequest(role="PARTNER"))
    assert res_switch_partner["status"] == "success"
    assert res_switch_partner["user"]["role"] == "PARTNER"
    p_token = res_switch_partner["token"]
    print(f"✔ switch_role(PARTNER) returned token: {p_token}")

    # 5. Test Partner Commissions & Leads with Partner Token
    comm_json = get_partner_commissions(authorization=f"Bearer {p_token}")
    assert comm_json["partner_id"] == "PTR-IND-882"
    assert comm_json["active_referrals_count"] >= 20
    print(f"✔ get_partner_commissions(): {comm_json['partner_name']} - Active: {comm_json['active_referrals_count']}, Trail: ₹{comm_json['monthly_recurring_trail_inr']}")

    leads_json = get_partner_leads(authorization=f"Bearer {p_token}")
    assert len(leads_json) > 0
    first_lead = leads_json[0]
    assert "propensity_score" in first_lead
    print(f"✔ get_partner_leads(): Loaded {len(leads_json)} leads, Top: {first_lead['business_name']} (Propensity: {first_lead['propensity_score']})")

    # 6. Test Admin Telemetry with Admin Token
    res_switch_admin = switch_role(SwitchRoleRequest(role="ADMIN"))
    a_token = res_switch_admin["token"]

    admin_json = get_admin_metrics(authorization=f"Bearer {a_token}")
    assert admin_json["funnel_metrics"]["total_inbound_leads"] == 5000
    assert admin_json["funnel_metrics"]["projected_digital_conversion_rate_percent"] > 20
    print(f"✔ get_admin_metrics(): Inbound {admin_json['funnel_metrics']['total_inbound_leads']} leads, Conv Rate: {admin_json['funnel_metrics']['projected_digital_conversion_rate_percent']}%")

    # 7. Test app.js router functions existence
    app_js_path = STATIC_DIR / "app.js"
    assert app_js_path.exists()
    app_js = app_js_path.read_text(encoding="utf-8")
    assert "function navigateToView(" in app_js
    assert "function initViewRouter(" in app_js
    assert "function loadPartnerViewData(" in app_js
    assert "function loadOpsViewData(" in app_js
    assert "updateRoleSwitcherUI" in app_js
    print("✔ app.js verified: navigateToView, initViewRouter, loadPartnerViewData, loadOpsViewData all implemented")

    print("\n=======================================================")
    print("PHASE 1 ROUTE & VIEW SEPARATION VALIDATED 100% GREEN!")
    print("=======================================================")

if __name__ == "__main__":
    test_routes_and_views()
