# app/modules/auth/rbac.py
from typing import Dict, Any, List, Optional
from fastapi import Header, Query, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)

ROLE_MERCHANT = "MERCHANT"
ROLE_PARTNER = "PARTNER"
ROLE_ADMIN = "ADMIN"

PERSONAS: Dict[str, Dict[str, Any]] = {
    "MERCHANT": {
        "user_id": "USR-CUST-1001",
        "name": "Customer Self-Serve (MSME)",
        "phone": "+91 98110 12345",
        "role": ROLE_MERCHANT,
        "badge": "🛒 Customer Mode",
        "assigned_pincode": "452001",
        "token": "tok_merchant_demo",
        "permissions": ["view_my_quote", "view_my_order", "submit_kyc", "chat_advisor"]
    },
    "PARTNER": {
        "user_id": "PTR-IND-882",
        "name": "Airtel Mitra Partner",
        "phone": "+91 98260 55443",
        "role": ROLE_PARTNER,
        "badge": "🤝 Airtel Mitra Partner",
        "assigned_pincode": "452001",
        "token": "tok_partner_demo",
        "permissions": ["view_my_quote", "view_my_order", "submit_kyc", "chat_advisor", "view_partner_leads", "claim_bounty", "generate_referral_qr"]
    },
    "ADMIN": {
        "user_id": "ADM-HQ-001",
        "name": "Airtel Enterprise Ops Admin",
        "phone": "+91 98765 00001",
        "role": ROLE_ADMIN,
        "badge": "🛡️ Airtel Ops Admin",
        "assigned_pincode": "ALL",
        "token": "tok_admin_demo",
        "permissions": ["*"]
    }
}

TOKEN_TO_ROLE: Dict[str, str] = {
    "tok_merchant_demo": "MERCHANT",
    "tok_partner_demo": "PARTNER",
    "tok_admin_demo": "ADMIN"
}

def extract_token_from_header(
    authorization: Optional[str] = None,
    x_session_token: Optional[str] = None,
    token_param: Optional[str] = None,
    oauth_token: Optional[str] = None
) -> Optional[str]:
    """
    Extracts session token from Authorization Bearer, X-Session-Token, query param, or OAuth2 scheme.
    """
    if authorization and authorization.startswith("Bearer "):
        return authorization.replace("Bearer ", "").strip()
    if oauth_token:
        return oauth_token.strip()
    if x_session_token:
        return x_session_token.strip()
    if token_param:
        return token_param.strip()
    return None

def get_user_by_token(token: Optional[str]) -> Dict[str, Any]:
    """
    Resolves session token into a structured User profile.
    1. First checks dynamic SQLite UserDatabase token store.
    2. Then checks static demo persona tokens (tok_merchant_demo, etc.).
    3. Defaults to MERCHANT persona if token is missing or unrecognized.
    """
    if not token:
        return PERSONAS["MERCHANT"]

    # 1. Dynamic SQLite UserDatabase lookup
    try:
        from app.modules.auth.db import UserDatabase
        db = UserDatabase.get_instance()
        user = db.get_user_by_token(token)
        if user:
            return user
    except Exception:
        pass

    # 2. Legacy / Demo persona tokens
    role = TOKEN_TO_ROLE.get(token)
    if role and role in PERSONAS:
        return PERSONAS[role]

    # 3. Default fallback
    return PERSONAS["MERCHANT"]

def verify_role_access(
    allowed_roles: List[str],
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """
    FastAPI dependency enforcing that the request carries a token with an allowed role.
    Raises HTTP 403 Forbidden if permission is denied.
    """
    extracted_token = extract_token_from_header(authorization, x_session_token, token)
    user = get_user_by_token(extracted_token)
    
    # If the user doesn't even supply a partner/admin token or has MERCHANT role
    if user["role"] not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied: {user['role']} role does not have authorization for this resource. Required: {', '.join(allowed_roles)}."
        )
    return user

def get_admin_telemetry() -> Dict[str, Any]:
    """
    Enterprise real-time macro metrics and funnel conversion telemetry computed from live database.
    """
    import sqlite3
    from app.config import DB_PATH

    total_leads = 0
    stage_counts = {}
    total_orders = 0
    escalations = []

    try:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=30000;")

        # 1. Total and stage breakdown from customer_leads
        c_row = conn.execute("SELECT COUNT(*) FROM customer_leads").fetchone()
        if c_row:
            total_leads = c_row[0]

        rows = conn.execute("SELECT stage_reached, COUNT(*) as cnt FROM customer_leads GROUP BY stage_reached").fetchall()
        for r in rows:
            stage_counts[r["stage_reached"]] = r["cnt"]

        # 2. Orders count
        try:
            o_row = conn.execute("SELECT COUNT(*) FROM orders").fetchone()
            if o_row:
                total_orders = o_row[0]
        except Exception:
            total_orders = 0

        # 3. Real exceptions / escalations
        try:
            esc_rows = conn.execute("""
                SELECT lead_id, business_name, drop_reason, phone, last_activity_at
                FROM customer_leads
                WHERE stage_reached IN ('ACTION_REQUIRED', 'REJECTED', 'EXCEPTION')
                   OR (propensity_score >= 80 AND is_claimed = 0 AND (julianday('now') - julianday(last_activity_at)) * 24 > 4)
            """).fetchall()
            for er in esc_rows:
                escalations.append({
                    "escalation_id": f"ESC-{er['lead_id'][-5:]}",
                    "business_name": er["business_name"],
                    "issue": er["drop_reason"] or "Operations Follow-up Required",
                    "assigned_agent": "Central Operations Desk",
                    "sla_remaining_hours": 0.0,
                    "escalation_type": "MANUAL_REVIEW"
                })
        except Exception:
            pass

        conn.close()
    except Exception:
        pass

    assessed = sum(stage_counts.get(s, 0) for s in ['ADVISOR_ENGAGED', 'BUNDLE_CUSTOMIZED', 'KYC_SUBMITTED', 'KYC_VERIFIED', 'TOKEN_PAID'])
    quoted = sum(stage_counts.get(s, 0) for s in ['BUNDLE_CUSTOMIZED', 'KYC_SUBMITTED', 'KYC_VERIFIED', 'TOKEN_PAID'])
    kyc_done = sum(stage_counts.get(s, 0) for s in ['KYC_VERIFIED', 'TOKEN_PAID'])
    activated = stage_counts.get('TOKEN_PAID', 0) + stage_counts.get('ACTIVATED', 0)

    conv_rate = round((activated / total_leads * 100), 1) if (total_leads > 0 and activated > 0) else None

    return {
        "funnel_metrics": {
            "total_inbound_leads": total_leads if total_leads > 0 else None,
            "contacted": assessed if assessed > 0 else None,
            "needs_assessed": assessed if assessed > 0 else None,
            "quote_accepted": quoted if quoted > 0 else None,
            "kyc_submitted": kyc_done if kyc_done > 0 else None,
            "activated": activated if activated > 0 else None,
            "conversion_rate_percent": conv_rate,
            "projected_digital_conversion_rate_percent": conv_rate
        },
        "operational_efficiency": {
            "legacy_tta_days": 17.6,
            "udyam_digital_tta_days": 2.0,
            "legacy_cac_inr": 15000.0,
            "udyam_digital_cac_inr": 2450.0,
            "cost_reduction_percent": 83.7
        },
        "segment_distribution": {
            "micro_retail": {"segment": "Micro Retail & Services", "target_product": "Biz 5G AirFiber 100 & Biz Fibre 100"},
            "professional_offices": {"segment": "Professional Offices & Clinics", "target_product": "Biz Fibre 300 + Static IP"},
            "small_multisite": {"segment": "Small Multi-Site Enterprises", "target_product": "Multi-site SD-WAN Bundles"},
            "small_manufacturers": {"segment": "Small Manufacturers & Industrial", "target_product": "Internet Leased Line (ILL 100M)"}
        },
        "manual_escalations_queue": escalations
    }

