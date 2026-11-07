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
        "name": "Rajesh Gupta (Rajesh Kirana)",
        "phone": "+91 98110 12345",
        "role": ROLE_MERCHANT,
        "badge": "🛒 Customer Mode",
        "assigned_pincode": "452001",
        "token": "tok_merchant_demo",
        "permissions": ["view_my_quote", "view_my_order", "submit_kyc", "chat_advisor"]
    },
    "PARTNER": {
        "user_id": "PTR-IND-882",
        "name": "Vikram Telecom (Mitra Channel Partner)",
        "phone": "+91 98260 55443",
        "role": ROLE_PARTNER,
        "badge": "🤝 Mitra Channel Partner",
        "assigned_pincode": "452001",
        "token": "tok_partner_demo",
        "permissions": ["view_my_quote", "view_my_order", "submit_kyc", "chat_advisor", "view_partner_leads", "claim_bounty", "generate_referral_qr"]
    },
    "ADMIN": {
        "user_id": "ADM-HQ-001",
        "name": "Priya Sharma (Airtel Enterprise Ops Lead)",
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
    Enterprise macro metrics and funnel conversion telemetry matching Airtel SYNC Case Study specs.
    """
    return {
        "funnel_metrics": {
            "total_inbound_leads": 5000,
            "contacted": 2840,
            "needs_assessed": 1974,
            "quote_accepted": 861,
            "kyc_submitted": 512,
            "activated": 368,
            "conversion_rate_percent": 7.36,
            "projected_digital_conversion_rate_percent": 24.8
        },
        "operational_efficiency": {
            "legacy_tta_days": 17.6,
            "udyam_digital_tta_days": 1.8,
            "legacy_cac_inr": 15000,
            "udyam_digital_cac_inr": 3450,
            "cost_reduction_percent": 77.0
        },
        "segment_distribution": {
            "micro_retail_55_pct": {"leads": 2750, "avg_arpu_inr": 1850, "churn_risk": "Medium (Reduced via AirFiber)"},
            "professional_offices_25_pct": {"leads": 1250, "avg_arpu_inr": 4800, "churn_risk": "Low (High Static IP retention)"},
            "small_multisite_15_pct": {"leads": 750, "avg_arpu_inr": 14200, "churn_risk": "Very Low (<3% on SD-WAN)"},
            "small_manufacturers_5_pct": {"leads": 250, "avg_arpu_inr": 28500, "churn_risk": "Low (Dedicated Leased Line SLA)"}
        },
        "manual_escalations_queue": [
            {
                "escalation_id": "ESC-2026-081",
                "business_name": "Ganesh Woodcraft",
                "issue": "Low OCR Laplacian Blur Variance (1.03) - Re-upload pending",
                "assigned_agent": "Airtel Tier-2 Support (Indore)",
                "sla_remaining_hours": 6,
                "escalation_type": "STATUTORY_OCR_BLUR"
            },
            {
                "escalation_id": "ESC-2026-082",
                "business_name": "Vindhya Tours & Travels",
                "issue": "GSTIN Cancelled on 2025-11-20 - Non-GST Udyam Switch Advised",
                "assigned_agent": "Field Mitra Executive (Bhopal)",
                "sla_remaining_hours": 12,
                "escalation_type": "STATUTORY_REGISTRY_TRAP"
            },
            {
                "escalation_id": "ESC-SLA-007",
                "business_name": "Saffron Dental Care LLP",
                "issue": "Mitra Partner 4-Hour SLA Expired (Unclaimed) - Fast-Track Tele-Sales Assigned",
                "assigned_agent": "Central Outbound Queue (Pan-India HQ)",
                "sla_remaining_hours": 0.5,
                "escalation_type": "PARTNER_4H_SLA_BREACH"
            }
        ]
    }

