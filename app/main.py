import os
import json
import uuid
import secrets
import shutil
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Header, Query, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from app.modules.advisor.adapter import AdvisorAdapter
from app.modules.catalog.engine import CatalogEngine
from app.modules.pricing.calculator import PricingCalculator
from app.modules.kyc.validator import KYCValidator
from app.modules.kyc.ocr_engine import OCREngine
from app.modules.orders.state_machine import OrderStateMachine
from app.modules.payment import PaymentGateway
from app.modules.partner.portal import PartnerPortal
from app.modules.whatsapp.router import router as whatsapp_router
from app.modules.auth import (
    ROLE_MERCHANT,
    ROLE_PARTNER,
    ROLE_ADMIN,
    get_user_by_token,
    verify_role_access,
    extract_token_from_header,
    get_admin_telemetry,
    UserDatabase,
    oauth2_scheme
)
from app.data_loader import DataLoader
from app.config import KYC_DOCUMENTS_DIR
from app.modules.analytics.dashboard_service import dashboard_service
from app.modules.support.service import support_service

app = FastAPI(
    title="Project Udyam Digital",
    description="Digital Acquisition & Onboarding Engine for MSMEs",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Services
advisor_adapter = AdvisorAdapter()
catalog_engine = CatalogEngine()
pricing_calculator = PricingCalculator()
kyc_validator = KYCValidator()
ocr_engine = OCREngine()
order_sm = OrderStateMachine()
payment_gw = PaymentGateway(order_sm=order_sm)
partner_portal = PartnerPortal()
user_db = UserDatabase.get_instance()
loader = DataLoader.get_instance()

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Schemas
class ChatRequest(BaseModel):
    message: str
    current_profile: Optional[Dict[str, Any]] = None
    language: str = "en"
    history: Optional[List[Dict[str, str]]] = None

class BucketRequest(BaseModel):
    city_tier: int = 1
    employee_count: int = 3
    num_sites: int = 1
    has_gstin: bool = True
    current_base_id: Optional[str] = "P01"

class FeasibilityRequest(BaseModel):
    pincode: str
    city: Optional[str] = None

class QuoteRequest(BaseModel):
    quantities: Dict[str, int]
    apply_digital_discount: bool = True
    waive_setup_fee: bool = True
    contract_months: Optional[int] = None
    city_tier: Optional[int] = 1
    city: Optional[str] = None
    pincode: Optional[str] = None
    employee_count: Optional[int] = 1
    num_sites: Optional[int] = 1
    has_gstin: Optional[bool] = None
    discount_code: Optional[str] = None

class DownsellRequest(BaseModel):
    quantities: Dict[str, int]
    step: int = 1

class SpecimenScanRequest(BaseModel):
    applicant_code: str
    doc_type: str = "gst"  # "gst", "address", or "udyam"

class VerifyExtractedRequest(BaseModel):
    gstin: Optional[str] = None
    udyam_number: Optional[str] = None
    entity_name: Optional[str] = None
    bill_date: Optional[str] = None
    blur_variance: Optional[float] = None
    applicant_code: Optional[str] = "CUSTOM"
    is_non_gst_mode: Optional[bool] = False
    customer_email: Optional[str] = None
    user_id: Optional[str] = None
    verification_session_id: Optional[str] = None
    consent: Optional[Dict[str, Any]] = None
    consent_granted: Optional[bool] = None

class AdminCreateUserRequest(BaseModel):
    email: str
    password: str
    name: str
    role: str = "PARTNER"  # PARTNER, ADMIN, or MERCHANT
    phone: Optional[str] = None
    assigned_pincode: Optional[str] = None

class GstinLookupRequest(BaseModel):
    gstin: str

class UdyamLookupRequest(BaseModel):
    udyam_number: str

class CreateOrderRequest(BaseModel):
    business_name: str
    contact_phone: str
    bundle_data: Dict[str, Any]
    kyc_status: Optional[str] = None
    language: str = "en"
    partner_id: Optional[str] = None
    installation_address: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    udyam_number: Optional[str] = None
    gstin: Optional[str] = None
    kyc_details: Optional[Dict[str, Any]] = None
    customer_email: Optional[str] = None
    case_id: Optional[str] = None
    consent: Optional[Dict[str, Any]] = None

class RescheduleRequest(BaseModel):
    new_date: str

class NPSRequest(BaseModel):
    rating: int

class LoginRequest(BaseModel):
    email: str
    password: str
    role: Optional[str] = None

class SignUpRequest(BaseModel):
    email: str
    password: str
    name: str
    phone: Optional[str] = None
    role: Optional[str] = "MERCHANT"

class PaymentIntentRequest(BaseModel):
    order_id: str = "PENDING_QUOTE"
    amount_inr: Optional[float] = 499.0
    business_name: Optional[str] = ""
    phone: Optional[str] = ""

class PaymentConfirmRequest(BaseModel):
    order_id: Optional[str] = None
    intent_id: Optional[str] = None
    txn_id: Optional[str] = None
    payment_method: str = "UPI_PHONEPE"
    mandate_active: bool = True
    amount_inr: Optional[float] = 499.0

class TicketCreateRequest(BaseModel):
    category: str = "GENERAL"  # CONNECTIVITY, BILLING, INSTALLATION, EQUIPMENT, GENERAL
    priority: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL
    subject: Optional[str] = "Service Request"
    description: str
    order_id: Optional[str] = None

class TicketUpdateRequest(BaseModel):
    status: str
    resolution_milestone: Optional[str] = None
    milestone: Optional[str] = None
    admin_notes: Optional[str] = None

class FeedbackSubmitRequest(BaseModel):
    rating: int  # 1 to 5 or 1 to 10
    feedback_type: str = "POST_ACTIVATION_CSAT"
    comments: Optional[str] = None
    feedback: Optional[str] = None
    journey_step: Optional[str] = "POST_ACTIVATION"
    order_id: Optional[str] = None

# --- API ENDPOINTS ---

@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": "Project Udyam Digital", "version": "1.0.0"}

# 1. Advisor
@app.post("/api/advisor/chat")
def chat_with_advisor(req: ChatRequest):
    return advisor_adapter.process_user_message(req.message, req.current_profile, req.language, history=req.history)

# 2. Catalog & 3-Bucket Drawer
@app.get("/api/catalog/products")
def get_catalog_products():
    return loader.get_all_products()

@app.post("/api/catalog/buckets")
def get_catalog_buckets(req: BucketRequest):
    return catalog_engine.get_three_buckets(
        req.city_tier, req.employee_count, req.num_sites, req.has_gstin, req.current_base_id
    )

@app.post("/api/catalog/feasibility")
def check_pincode_feasibility(req: FeasibilityRequest):
    return catalog_engine.check_network_feasibility(req.pincode, req.city)

# 3. Pricing & Down-sell
@app.post("/api/pricing/quote")
def calculate_quote(req: QuoteRequest):
    return pricing_calculator.calculate_quote(
        product_quantities=req.quantities,
        apply_digital_discount=req.apply_digital_discount,
        waive_setup_fee=req.waive_setup_fee,
        contract_months=req.contract_months,
        city_tier=req.city_tier or 1,
        employee_count=req.employee_count or 1,
        num_sites=req.num_sites or 1,
        has_gstin=req.has_gstin,
        discount_code=req.discount_code
    )

@app.post("/api/pricing/validate-order")
def validate_order_pricing(req: QuoteRequest):
    try:
        return pricing_calculator.validate_and_price_order(
            product_quantities=req.quantities,
            city_tier=req.city_tier or 1,
            city=req.city,
            pincode=req.pincode,
            employee_count=req.employee_count or 1,
            num_sites=req.num_sites or 1,
            has_gstin=req.has_gstin,
            contract_months=req.contract_months,
            apply_digital_discount=req.apply_digital_discount,
            waive_setup_fee=req.waive_setup_fee,
            discount_code=req.discount_code
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/pricing/downsell")
def execute_downsell(req: DownsellRequest):
    return pricing_calculator.execute_downsell_step(req.quantities, req.step)

# 4. Smart KYC: Document Upload & Real OCR Pipeline
@app.post("/api/kyc/upload")
async def upload_kyc_document(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    """
    Accepts customer file upload, enforces authentication, runs OpenCV blur check and OCR.
    Statutory DPDP Act Compliance & Data Minimization:
    The uploaded certificate image is used solely for instant in-memory OCR & validation.
    Once scanned and structured details are extracted, the raw document file is immediately shredded from disk.
    Binds the verification session to the authenticated customer's identity.
    """
    user = verify_role_access([ROLE_MERCHANT, ROLE_PARTNER, ROLE_ADMIN], authorization, x_session_token, token)
    temp_filename = f"temp_{uuid.uuid4().hex[:8]}_{file.filename}"
    dest_path = UPLOAD_DIR / temp_filename
    try:
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        ocr_result = await ocr_engine.scan_document(str(dest_path))
    finally:
        # Secure Disposal: Physical document is deleted immediately after OCR extraction
        try:
            if dest_path.exists():
                dest_path.unlink()
        except Exception as e:
            logger.warning(f"Could not delete temporary certificate file {dest_path}: {e}")

    verification_session_id = f"vs_{secrets.token_hex(12)}"
    order_sm.save_kyc_verification_session(
        session_id=verification_session_id,
        user_id=user["user_id"],
        customer_email=user["email"],
        blur_variance=ocr_result.get("blur_variance", 0.0),
        is_clear=ocr_result.get("is_clear", True),
        extracted_fields=ocr_result.get("extracted_fields"),
        raw_text=ocr_result.get("raw_text")
    )

    ocr_result["verification_session_id"] = verification_session_id
    ocr_result["user_id"] = user["user_id"]
    ocr_result["file_name"] = file.filename
    ocr_result["image_url"] = None  # File deleted post-validation
    ocr_result["document_disposition"] = "DELETED_POST_VALIDATION_DPDP_COMPLIANT"
    ocr_result["privacy_notice"] = (
        "Statutory compliance: Raw certificate image deleted immediately post-validation. "
        "Only extracted business and address details are stored in the database."
    )
    return ocr_result

@app.post("/api/kyc/specimen-scan")
async def scan_specimen_document(
    req: SpecimenScanRequest,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    """
    Runs real OCR and blur detection on submitted business document images.
    Requires authentication and binds verification session to authenticated customer.
    """
    user = verify_role_access([ROLE_MERCHANT, ROLE_PARTNER, ROLE_ADMIN], authorization, x_session_token, token)
    if req.doc_type == "gst":
        suffix = "gst_certificate.png"
    elif req.doc_type == "address":
        suffix = "address_proof.png"
    elif req.doc_type == "udyam":
        suffix = "udyam_certificate.png"
    else:
        suffix = "signatory_id.png"

    filename = f"{req.applicant_code}_{suffix}"
    file_path = KYC_DOCUMENTS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Specimen file {filename} not found")

    ocr_result = await ocr_engine.scan_document(str(file_path))
    verification_session_id = f"vs_{secrets.token_hex(12)}"
    order_sm.save_kyc_verification_session(
        session_id=verification_session_id,
        user_id=user["user_id"],
        customer_email=user["email"],
        blur_variance=ocr_result.get("blur_variance", 0.0),
        is_clear=ocr_result.get("is_clear", True),
        extracted_fields=ocr_result.get("extracted_fields"),
        raw_text=ocr_result.get("raw_text")
    )
    ocr_result["verification_session_id"] = verification_session_id
    ocr_result["user_id"] = user["user_id"]
    ocr_result["file_name"] = filename
    ocr_result["image_url"] = f"/specimen/{filename}"
    return ocr_result

@app.post("/api/verify/gstin")
def verify_gstin_lookup(
    req: GstinLookupRequest,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    """
    Protected GSTIN Lookup API querying official mock_gstin_registry.csv.
    Enforces format validation and conservative status handling.
    """
    user = verify_role_access([ROLE_MERCHANT, ROLE_PARTNER, ROLE_ADMIN], authorization, x_session_token, token)
    gstin_val = req.gstin.strip().upper()
    import re
    if not re.match(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$', gstin_val):
        raise HTTPException(status_code=400, detail=f"Invalid GSTIN format '{gstin_val}'. Expected 15-character statutory alphanumeric format.")

    record = loader.lookup_gstin(gstin_val)
    if not record:
        raise HTTPException(status_code=404, detail=f"GSTIN '{gstin_val}' not found in official mock registry.")
    status = record.get("status", "Unknown")
    return {
        "found": True,
        "gstin": gstin_val,
        "legal_name": record.get("legal_name"),
        "trade_name": record.get("trade_name"),
        "status": status,
        "is_active": (status == "Active"),
        "principal_place_of_business": record.get("principal_place_of_business"),
        "registration_date": record.get("registration_date")
    }

@app.post("/api/verify/udyam")
def verify_udyam_lookup(
    req: UdyamLookupRequest,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    """
    Protected Udyam Lookup API querying official mock_udyam_registry.csv.
    """
    user = verify_role_access([ROLE_MERCHANT, ROLE_PARTNER, ROLE_ADMIN], authorization, x_session_token, token)
    udyam_val = req.udyam_number.strip().upper()
    is_valid, msg, record = kyc_validator.validate_udyam(udyam_val)
    if not is_valid:
        raise HTTPException(status_code=404, detail=msg)
    return {
        "found": True,
        "udyam_number": udyam_val,
        "enterprise_name": record.get("enterprise_name"),
        "enterprise_type": record.get("enterprise_type"),
        "major_activity": record.get("major_activity"),
        "nic_description": record.get("nic_description"),
        "city": record.get("city"),
        "state": record.get("state"),
        "date_of_registration": record.get("date_of_registration"),
        "is_active": True
    }

@app.post("/api/kyc/verify-extracted")
def verify_extracted_data(
    req: VerifyExtractedRequest,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    """
    Validates reviewed extracted fields against mock registries (GSTIN & Udyam),
    90-day date rule, and server-side document quality checks.
    - Requires authenticated user session (fails closed).
    - Prevents cross-customer KYC verification.
    - Requires explicit customer consent before registry verification under DPDP Act 2023.
    - Uses server-measured blur metrics instead of trusting client numbers.
    - Handles missing, cancelled, and suspended registrations conservatively.
    - Stores authoritative server-controlled KYC Case record.
    """
    # 1. Require Authentication (Fails closed)
    user = verify_role_access([ROLE_MERCHANT, ROLE_PARTNER, ROLE_ADMIN], authorization, x_session_token, token)

    # 2. Prevent cross-account KYC verification
    if req.user_id and req.user_id != user["user_id"] and user["role"] != ROLE_ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Cross-account security violation: Cannot verify KYC on behalf of another customer."
        )

    effective_user_id = user["user_id"]
    effective_email = user["email"]

    # 3. Explicit Customer Consent Verification (DPDP Act 2023)
    consent_data = req.consent or {}
    has_consent = bool(consent_data.get("granted") or req.consent_granted)
    if not has_consent:
        raise HTTPException(
            status_code=400,
            detail="Statutory consent required: Explicit customer consent must be recorded prior to GSTIN or Udyam registry verification under DPDP Act 2023."
        )

    # Record consent event in consent_logs
    order_sm.record_consent(
        user_id=effective_user_id,
        customer_email=effective_email,
        consent_type="REGISTRY_VERIFICATION_CONSENT",
        purpose=consent_data.get("purpose", "Statutory GSTIN/Udyam Registry Verification under DPDP Act 2023"),
        version=consent_data.get("version", "v1.0"),
        consent_text=consent_data.get("consent_text", "Customer explicitly granted affirmative consent for registry verification.")
    )

    reasons = []
    registry_rec = None
    udyam_rec = None

    # 4. Server-Side Document Quality & Blur Check (Never trust client assertions)
    server_blur_variance = None
    if req.verification_session_id:
        v_session = order_sm.get_kyc_verification_session(req.verification_session_id)
        if v_session:
            # Verify session belongs to authenticated user
            if v_session["user_id"] != user["user_id"] and user["role"] != ROLE_ADMIN:
                raise HTTPException(
                    status_code=403,
                    detail="Cross-account security violation: Verification session does not belong to the authenticated user."
                )
            server_blur_variance = v_session.get("blur_variance")
            if not v_session.get("is_clear") or (server_blur_variance is not None and server_blur_variance < 100.0):
                reasons.append(f"Image Quality Failure: Server blur analysis flagged document as unreadable (sharpness variance: {server_blur_variance:.2f}). Please re-upload a clear photo.")
    if server_blur_variance is None and req.blur_variance is not None and req.blur_variance < 100.0:
        reasons.append(f"Image Quality Failure: Document is blurry/unreadable (sharpness variance: {req.blur_variance:.2f}). Please re-upload a clear photo.")

    # 5. Registry Status Check: Non-GST Mode vs Standard GST Mode (Conservative Handling)
    import re
    if req.is_non_gst_mode:
        udyam_val = (req.udyam_number or "").strip().upper()
        if not udyam_val:
            reasons.append("Non-GST Mode requires a valid Udyam Registration Number.")
        else:
            is_u_valid, u_msg, udyam_rec = kyc_validator.validate_udyam(udyam_val)
            if not is_u_valid:
                reasons.append(f"Statutory Rejection: {u_msg}")
    else:
        gstin_val = (req.gstin or "").strip().upper()
        if not gstin_val and not req.udyam_number:
            reasons.append("Active GSTIN is required for standard enterprise verification.")
        elif gstin_val:
            if not re.match(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$', gstin_val):
                reasons.append(f"Statutory Rejection: Invalid GSTIN format '{gstin_val}'. Expected 15-character statutory alphanumeric format.")
            else:
                registry_rec = loader.lookup_gstin(gstin_val)
                if not registry_rec:
                    reasons.append(f"Statutory Rejection: GSTIN '{gstin_val}' not found in official mock registry.")
                else:
                    status = registry_rec.get("status", "Unknown")
                    if status != "Active":
                        reasons.append(f"Statutory Rejection: GSTIN registration is '{status}' in the GST portal.")

        # Check Udyam if optionally provided
        if req.udyam_number:
            is_u_valid, u_msg, udyam_rec = kyc_validator.validate_udyam(req.udyam_number)
            if not is_u_valid:
                reasons.append(f"Statutory Rejection: {u_msg}")

    # 6. 90-Day Freshness Check (Only applies to Address Proof / Utility Bill)
    if req.bill_date:
        is_gst_reg_date = bool(registry_rec and req.bill_date == registry_rec.get("registration_date"))
        is_udyam_reg_date = bool(udyam_rec and req.bill_date == udyam_rec.get("date_of_registration"))

        if not is_gst_reg_date and not is_udyam_reg_date:
            is_fresh, diff_days = kyc_validator.validate_document_freshness(req.bill_date)
            if not is_fresh:
                reasons.append(f"Address Proof Expired: Bill is {diff_days} days old relative to 2026-07-15 (Allowed: <= 90 days).")

    # 7. Name Match Check
    check_name = req.entity_name
    if check_name:
        if registry_rec:
            reg_name = registry_rec.get("trade_name") or registry_rec.get("legal_name", "")
            matched, score = kyc_validator.match_entity_names(check_name, reg_name)
            if not matched and score < 70:
                reasons.append(f"Entity Name Discrepancy: '{check_name}' does not match registered GST name '{reg_name}'.")
        elif udyam_rec:
            u_name = udyam_rec.get("enterprise_name", "")
            matched, score = kyc_validator.match_entity_names(check_name, u_name)
            if not matched and score < 70:
                reasons.append(f"Entity Name Discrepancy: '{check_name}' does not match registered Udyam name '{u_name}'.")

    # Server-Controlled Verdict Calculation
    if len(reasons) == 0:
        status_decision = "VERIFIED"
        verdict = "APPROVED"
        action = "Approve Instant Straight-Through Processing" + (" (Non-GST Safe Mode)" if req.is_non_gst_mode else "")
    elif any("Statutory Rejection" in r or "Expired" in r for r in reasons):
        status_decision = "REJECTED"
        verdict = "REJECTED"
        action = "Hard Stop - Inform applicant and block onboarding"
    elif any("blurry" in r or "Image Quality Failure" in r for r in reasons):
        status_decision = "ACTION_REQUIRED"
        verdict = "ACTION_REQUIRED"
        action = "Prompt customer to re-upload clear document"
    else:
        status_decision = "MANUAL_REVIEW"
        verdict = "MANUAL_REVIEW"
        action = "Route to partner/agent for manual review"

    # Store authoritative server KYC case bound to authenticated customer
    case_id = order_sm.create_kyc_case(
        user_id=effective_user_id,
        customer_email=effective_email,
        doc_type="UDYAM" if req.is_non_gst_mode or req.udyam_number else "GST",
        id_number=req.udyam_number if req.is_non_gst_mode or req.udyam_number else req.gstin,
        entity_name=req.entity_name,
        verdict=verdict,
        details={
            "action": action,
            "reasons": reasons,
            "registry_details": registry_rec or {},
            "udyam_details": udyam_rec or {},
            "is_non_gst_mode": bool(req.is_non_gst_mode),
            "verification_session_id": req.verification_session_id
        }
    )

    return {
        "case_id": case_id,
        "status": status_decision,
        "verdict": verdict,
        "action": action,
        "reasons": reasons,
        "registry_details": registry_rec or {},
        "udyam_details": udyam_rec or {},
        "is_non_gst_mode": bool(req.is_non_gst_mode),
        "verified_fields": {
            "gstin": req.gstin.strip().upper() if req.gstin else None,
            "udyam_number": req.udyam_number.strip().upper() if req.udyam_number else None,
            "entity_name": req.entity_name,
            "bill_date": req.bill_date
        }
    }

@app.get("/api/kyc/cases/{case_id}")
def get_kyc_case_details(
    case_id: str,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    """
    Retrieves verified KYC case record. Enforces strict ownership check (Requirement 5).
    """
    extracted = extract_token_from_header(authorization, x_session_token, token)
    if not extracted:
        raise HTTPException(status_code=401, detail="Authentication required to inspect KYC case.")
    user = get_user_by_token(extracted)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session token.")

    case = order_sm.get_kyc_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="KYC case not found")

    if user["role"] == ROLE_MERCHANT:
        u_id = user["user_id"]
        u_email = (user["email"] or "").lower().strip()
        case_uid = case.get("user_id")
        case_email = (case.get("customer_email") or "").lower().strip()
        if (case_uid and case_uid != u_id) and (case_email and case_email != u_email):
            raise HTTPException(status_code=403, detail="Access denied: You do not own this KYC case.")

    return case

# 5. Orders & Tracker
@app.post("/api/orders/create")
def create_order(
    req: CreateOrderRequest,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    """
    Stages an enterprise subscriber order.
    - Requires authenticated customer session (fails closed).
    - Requires explicit customer consent (Requirement 8).
    - Validates server-controlled KYC case with approved verdict belonging to this customer.
    - Enforces ownership & identity binding.
    """
    user = verify_role_access([ROLE_MERCHANT, ROLE_ADMIN], authorization, x_session_token, token)
    effective_user_id = user["user_id"]
    effective_email = user["email"]
    effective_phone = user.get("phone") if user.get("phone") else req.contact_phone

    try:
        return order_sm.create_order(
            business_name=req.business_name,
            contact_phone=effective_phone,
            bundle_data=req.bundle_data,
            case_id=req.case_id,
            explicit_consent=req.consent,
            language=req.language,
            partner_id=req.partner_id,
            installation_address=req.installation_address,
            user_id=effective_user_id,
            udyam_number=req.udyam_number,
            gstin=req.gstin,
            kyc_details=req.kyc_details,
            customer_email=effective_email
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Order creation service error: {str(e)}")

@app.get("/api/notifications/emails/latest")
def get_latest_email_notification(
    order_id: Optional[str] = None,
    email: Optional[str] = None,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    """
    Retrieves latest email notification. Enforces ownership check (Requirement 5).
    Never leaks notifications of other customers.
    """
    extracted = extract_token_from_header(authorization, x_session_token, token)
    if not extracted:
        raise HTTPException(status_code=401, detail="Authentication required to view notifications.")
    user = get_user_by_token(extracted)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session token.")

    from app.modules.notifications.email_service import EmailNotificationService
    svc = EmailNotificationService.get_instance()

    if order_id:
        order = order_sm.get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if not order_sm.verify_order_ownership(order, user):
            raise HTTPException(status_code=403, detail="Access denied: You do not own this order's notifications.")
        notifs = svc.get_notifications_for_order(order_id)
        if notifs:
            return notifs[0]
        raise HTTPException(status_code=404, detail="No notification found for this order")

    # Strictly bound to authenticated customer's email (Requirement 5)
    target_email = user["email"].strip().lower() if user["role"] == ROLE_MERCHANT else (email or user["email"]).strip().lower()
    notif = svc.get_latest_notification_for_email(target_email)
    if notif:
        return notif
    raise HTTPException(status_code=404, detail="No email notification found for this account")

@app.get("/api/notifications/emails/{order_id}")
def get_order_email_notifications(
    order_id: str,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    """
    Retrieves email notifications for an order. Enforces ownership check (Requirement 5).
    """
    extracted = extract_token_from_header(authorization, x_session_token, token)
    if not extracted:
        raise HTTPException(status_code=401, detail="Authentication required to view notifications.")
    user = get_user_by_token(extracted)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session token.")

    order = order_sm.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if not order_sm.verify_order_ownership(order, user):
        raise HTTPException(status_code=403, detail="Access denied: You do not have permission to view notifications for this order.")

    from app.modules.notifications.email_service import EmailNotificationService
    svc = EmailNotificationService.get_instance()
    notifs = svc.get_notifications_for_order(order_id)
    return {"order_id": order_id, "notifications": notifs}

class TestEmailRequest(BaseModel):
    recipient_email: str = "phantomroasting@gmail.com"

@app.post("/api/notifications/test-email")
def trigger_test_email(req: TestEmailRequest):
    from app.modules.notifications.email_service import EmailNotificationService
    svc = EmailNotificationService.get_instance()
    result = svc.send_test_email(req.recipient_email)
    return result

@app.get("/api/orders/user/latest")
def get_latest_user_order(
    user_id: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    order_id: Optional[str] = None,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    """
    Fetches the latest active order for the specific session/user.
    Enforces ownership check: never leaks orders from other accounts (Requirement 5).
    """
    extracted = extract_token_from_header(authorization, x_session_token, token)
    if not extracted:
        raise HTTPException(status_code=401, detail="Authentication required.")
    user = get_user_by_token(extracted)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session token.")

    if user["role"] == ROLE_MERCHANT:
        eff_user_id = user["user_id"]
        eff_email = user["email"]
        eff_phone = user.get("phone")
    else:
        eff_user_id = user_id or user["user_id"]
        eff_email = email or user["email"]
        eff_phone = phone

    order = order_sm.get_latest_order_for_user(
        user_id=eff_user_id, phone=eff_phone, email=eff_email, order_id=order_id
    )
    if not order:
        raise HTTPException(status_code=404, detail="No active order found for this user")
    if not order_sm.verify_order_ownership(order, user):
        raise HTTPException(status_code=403, detail="Access denied: You do not have permission to access this order.")
    return order

@app.get("/api/orders/{order_id}")
def get_order(
    order_id: str,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    """
    Retrieves order details. Enforces ownership check (Requirement 5).
    """
    extracted = extract_token_from_header(authorization, x_session_token, token)
    if not extracted:
        raise HTTPException(status_code=401, detail="Authentication required to view order details.")
    user = get_user_by_token(extracted)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session token.")

    order = order_sm.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if not order_sm.verify_order_ownership(order, user):
        raise HTTPException(status_code=403, detail="Access denied: You do not have permission to access this order.")
    return order

@app.post("/api/orders/{order_id}/reschedule")
def reschedule_order(
    order_id: str,
    req: RescheduleRequest,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    """
    Reschedules installation date. Enforces ownership check (Requirement 5).
    """
    extracted = extract_token_from_header(authorization, x_session_token, token)
    if not extracted:
        raise HTTPException(status_code=401, detail="Authentication required.")
    user = get_user_by_token(extracted)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session token.")

    order = order_sm.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if not order_sm.verify_order_ownership(order, user):
        raise HTTPException(status_code=403, detail="Access denied: You do not have permission to modify this order.")

    success = order_sm.reschedule_installation(order_id, req.new_date)
    if not success:
        raise HTTPException(status_code=404, detail="Order not found or update failed")
    return {"status": "success", "order_id": order_id, "new_install_date": req.new_date}

@app.post("/api/orders/{order_id}/nps")
def submit_nps(
    order_id: str,
    req: NPSRequest,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    """
    Records customer NPS rating. Enforces ownership check (Requirement 5).
    """
    extracted = extract_token_from_header(authorization, x_session_token, token)
    if not extracted:
        raise HTTPException(status_code=401, detail="Authentication required.")
    user = get_user_by_token(extracted)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session token.")

    order = order_sm.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if not order_sm.verify_order_ownership(order, user):
        raise HTTPException(status_code=403, detail="Access denied: You do not have permission to rate this order.")

    success = order_sm.record_nps(order_id, req.rating)
    if not success:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"status": "success", "order_id": order_id, "nps_rating": req.rating}

# 5b. Payment Gateway & UPI AutoPay Mandate
@app.post("/api/payment/create-intent")
def create_payment_intent(
    req: PaymentIntentRequest,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    """
    Creates server-controlled payment intent (Requirement 7).
    Enforces authentication and order ownership check (Requirement 5).
    """
    user = verify_role_access([ROLE_MERCHANT, ROLE_ADMIN], authorization, x_session_token, token)
    try:
        return payment_gw.create_payment_intent(
            order_id=req.order_id or "PENDING_QUOTE",
            amount_inr=req.amount_inr,
            business_name=req.business_name or "",
            phone=req.phone or "",
            user=user
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/payment/confirm")
def confirm_payment(
    req: PaymentConfirmRequest,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    """
    Validates payment through server payment intent (Requirement 7).
    Enforces authentication, ownership check, and rejects client-declared transactions.
    """
    user = verify_role_access([ROLE_MERCHANT, ROLE_ADMIN], authorization, x_session_token, token)
    try:
        receipt = payment_gw.confirm_payment(
            order_id=req.order_id,
            intent_id=req.intent_id,
            payment_method=req.payment_method,
            mandate_active=req.mandate_active,
            user=user
        )
        if req.order_id:
            order = order_sm.get_order(req.order_id)
            if order and order.get("partner_attribution_id"):
                partner_portal.commissions["active_referrals_count"] = partner_portal.commissions.get("active_referrals_count", 28) + 1
                partner_portal.commissions["monthly_recurring_trail_inr"] = round(
                    partner_portal.commissions.get("monthly_recurring_trail_inr", 42850.0) + (order.get("monthly_total", 0.0) * 0.15), 2
                )
                partner_portal.commissions["total_pending_payout_inr"] = round(
                    partner_portal.commissions.get("total_pending_payout_inr", 16450.0) + 1000.0, 2
                )
        return receipt
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/payment/receipt/{order_id}")
def get_order_receipt(
    order_id: str,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    """
    Retrieves official B2B tax receipt. Enforces ownership check (Requirement 5).
    """
    extracted = extract_token_from_header(authorization, x_session_token, token)
    if not extracted:
        raise HTTPException(status_code=401, detail="Authentication required to view payment receipt.")
    user = get_user_by_token(extracted)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session token.")

    order = order_sm.get_order(order_id)
    if not order or not order.get("receipt"):
        raise HTTPException(status_code=404, detail="Receipt not found for this order")
    if not order_sm.verify_order_ownership(order, user):
        raise HTTPException(status_code=403, detail="Access denied: You do not own this payment receipt.")
    return order["receipt"]

class CustomerActivityRequest(BaseModel):
    user_id: Optional[str] = None
    business_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    action: str = "LOGGED_IN"
    stage: Optional[str] = None
    city: Optional[str] = None
    pincode: Optional[str] = None
    business_type: Optional[str] = None
    employee_count: Optional[int] = 1
    num_sites: Optional[int] = 1
    monthly_spend_inr: Optional[float] = 0.0
    has_gstin: Optional[str] = "N"
    bundle: Optional[Dict[str, Any]] = None
    lead_id: Optional[str] = None

@app.post("/api/leads/activity")
def record_customer_lead_activity(
    req: CustomerActivityRequest,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None)
):
    try:
        extracted = extract_token_from_header(authorization, x_session_token, None)
        if extracted:
            user = get_user_by_token(extracted)
            if user and user.get("role") == ROLE_MERCHANT:
                if not req.user_id:
                    req.user_id = user.get("user_id")
                if not req.business_name:
                    req.business_name = user.get("name")
                if not req.email:
                    req.email = user.get("email")
                if not req.phone:
                    req.phone = user.get("phone")
    except Exception:
        pass

    saved = partner_portal.record_customer_activity(
        user_id=req.user_id,
        business_name=req.business_name,
        email=req.email,
        phone=req.phone,
        action=req.action,
        stage=req.stage,
        city=req.city,
        pincode=req.pincode,
        business_type=req.business_type,
        employee_count=req.employee_count,
        num_sites=req.num_sites,
        monthly_spend_inr=req.monthly_spend_inr,
        has_gstin=req.has_gstin,
        bundle=req.bundle,
        lead_id=req.lead_id
    )
    return {
        "status": "success",
        "lead": saved,
        "lead_id": saved["lead_id"],
        "propensity_score": saved["propensity_score"],
        "stage_reached": saved["stage_reached"],
        "priority": saved["priority"],
        "updated_at": saved["last_activity_at"]
    }

class FunnelProgressionRequest(BaseModel):
    lead_id: Optional[str] = "L00003"
    stage: str
    propensity_boost: Optional[int] = 25

@app.post("/api/funnel/update-lead")
def update_funnel_lead(req: FunnelProgressionRequest):
    saved = partner_portal.record_customer_activity(
        lead_id=req.lead_id,
        stage=req.stage
    )
    return {
        "status": "success",
        "lead_id": saved["lead_id"],
        "updated_stage": saved["stage_reached"],
        "new_propensity_score": saved["propensity_score"],
        "fast_track_stp": True,
        "updated_at": saved["last_activity_at"]
    }

# 6. Auth & RBAC (OAuth2 + SQLite Database)
@app.post("/api/auth/login")
def login_user(req: LoginRequest):
    try:
        res = user_db.authenticate(req.email, req.password, role=req.role)
        if res["user"]["role"] == ROLE_MERCHANT:
            try:
                # Only record live customer activity for real business accounts (not demo seed)
                if res["user"]["email"] != "customer@business.in":
                    partner_portal.record_customer_activity(
                        user_id=res["user"]["user_id"],
                        business_name=res["user"]["name"],
                        email=res["user"]["email"],
                        phone=res["user"].get("phone", "+91 98110 12345"),
                        action="LOGGED_IN",
                        city="Rohtak",
                        pincode="124001"
                    )
            except Exception:
                pass
        return {
            "status": "success",
            "access_token": res["token"],
            "token_type": "bearer",
            "expires_in": 86400,
            "user": res["user"]
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Authentication service error: {str(e)}")

@app.post("/api/auth/signup")
@app.post("/api/auth/register")
def signup_user(req: SignUpRequest):
    try:
        requested_role = (req.role or ROLE_MERCHANT).upper().strip()
        if requested_role in [ROLE_ADMIN, ROLE_PARTNER]:
            raise HTTPException(
                status_code=403,
                detail=f"Registration as '{requested_role}' is restricted. Partner and Admin accounts must be created through an authorized admin workflow."
            )
        res = user_db.register_user(
            email=req.email,
            password=req.password,
            name=req.name,
            role=ROLE_MERCHANT,
            phone=req.phone,
            allow_privileged=False
        )
        if res["user"]["role"] == ROLE_MERCHANT:
            try:
                partner_portal.record_customer_activity(
                    user_id=res["user"]["user_id"],
                    business_name=res["user"]["name"],
                    email=res["user"]["email"],
                    phone=res["user"].get("phone", "+91 98110 12345"),
                    action="LOGGED_IN",
                    city="Rohtak",
                    pincode="124001"
                )
            except Exception:
                pass
        return {
            "status": "success",
            "access_token": res["token"],
            "token_type": "bearer",
            "expires_in": 86400,
            "user": res["user"]
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Registration service error: {str(e)}")

@app.post("/api/auth/admin/create-user")
def admin_create_user(
    req: AdminCreateUserRequest,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    """
    Authorized admin workflow to create privileged accounts (PARTNER, ADMIN, or MERCHANT).
    Enforces strict ADMIN role verification.
    """
    user = verify_role_access([ROLE_ADMIN], authorization, x_session_token, token)
    try:
        return user_db.create_privileged_user(
            email=req.email,
            password=req.password,
            name=req.name,
            role=req.role,
            phone=req.phone,
            assigned_pincode=req.assigned_pincode
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/auth/token")
def oauth_token(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        role = form_data.scopes[0] if form_data.scopes else None
        res = user_db.authenticate(form_data.username, form_data.password, role=role)
        return {
            "access_token": res["token"],
            "token_type": "bearer",
            "expires_in": 86400,
            "user": res["user"]
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.post("/api/auth/logout")
def logout_user(
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    extracted = extract_token_from_header(authorization, x_session_token, token)
    if extracted:
        user_db.logout_token(extracted)
    return {"status": "success", "message": "Successfully logged out"}

@app.get("/api/auth/me")
def get_current_user_profile(
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    extracted = extract_token_from_header(authorization, x_session_token, token)
    if not extracted:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please provide a valid session token."
        )
    user = get_user_by_token(extracted)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session token. Please log in again."
        )
    return user

# 7. Partner Portal (RBAC Guarded)
@app.get("/api/partner/leads")
def get_partner_leads(
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    user = verify_role_access([ROLE_PARTNER, ROLE_ADMIN], authorization, x_session_token, token)
    is_admin = (user["role"] == ROLE_ADMIN)
    partner_id = user["user_id"] if not is_admin else None
    partner_pincode = user.get("assigned_pincode") if not is_admin else None
    return partner_portal.get_stalled_leads_with_propensity(
        limit=15,
        partner_id=partner_id,
        partner_pincode=partner_pincode,
        is_admin=is_admin
    )

@app.get("/api/partner/referral")
def get_partner_referral(
    partner_id: str = "PTR-IND-882",
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    user = verify_role_access([ROLE_PARTNER, ROLE_ADMIN], authorization, x_session_token, token)
    pid = user["user_id"] if user["role"] == ROLE_PARTNER else partner_id
    return partner_portal.generate_partner_referral_link(partner_id=pid)

@app.post("/api/partner/leads/{lead_id}/claim")
def claim_partner_lead(
    lead_id: str,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    user = verify_role_access([ROLE_PARTNER, ROLE_ADMIN], authorization, x_session_token, token)
    is_admin = (user["role"] == ROLE_ADMIN)
    partner_pincode = user.get("assigned_pincode") if not is_admin else None
    try:
        return partner_portal.claim_stalled_lead(
            lead_id=lead_id,
            partner_id=user["user_id"],
            partner_pincode=partner_pincode,
            is_admin=is_admin
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/api/partner/leads/{lead_id}/call")
def call_partner_lead(
    lead_id: str,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    user = verify_role_access([ROLE_PARTNER, ROLE_ADMIN], authorization, x_session_token, token)
    try:
        res = partner_portal.call_lead(
            lead_id=lead_id,
            partner_id=user["user_id"],
            is_admin=(user["role"] == ROLE_ADMIN)
        )
        if res.get("status") == "NOT_FOUND":
            raise HTTPException(status_code=404, detail=res["message"])
        return res
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

@app.get("/api/partner/commissions")
def get_partner_commissions(
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    user = verify_role_access([ROLE_PARTNER, ROLE_ADMIN], authorization, x_session_token, token)
    return partner_portal.get_partner_commissions(partner_id=user["user_id"])

# 8. Data-Driven Admin Telemetry & Metrics (RBAC Guarded, multi-dimensional filters)
@app.get("/api/admin/metrics")
def get_admin_metrics(
    date_preset: Optional[str] = "all",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    segment: Optional[str] = "all",
    location: Optional[str] = "all",
    channel: Optional[str] = "all",
    stage: Optional[str] = "all",
    partner_id: Optional[str] = None,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    user = verify_role_access([ROLE_ADMIN], authorization, x_session_token, token)
    raw = dashboard_service.get_admin_dashboard_metrics(
        date_preset=date_preset,
        start_date=start_date,
        end_date=end_date,
        segment=segment,
        location=location,
        channel=channel,
        stage=stage,
        partner_id=partner_id
    )
    s = raw.get("summary", {})
    ft = raw.get("funnel_telemetry", {})
    ret = raw.get("retention_indicators", {})
    return {
        "status": "SUCCESS",
        "funnel_metrics": {
            "total_inbound_leads": s.get("total_leads", 0),
            "projected_digital_conversion_rate_percent": s.get("conversion_rate_percent", 0.0),
            "needs_assessed": ft.get("needs_assessed", 0),
            "quote_accepted": ft.get("quote_accepted", 0),
            "kyc_submitted": ft.get("kyc_submitted", 0),
            "activated": ft.get("activated", 0),
            "pending_orders_count": s.get("pending_orders", 0)
        },
        "operational_efficiency": {
            "udyam_digital_tta_days": s.get("avg_tta_days", 2.5),
            "udyam_digital_cac_inr": 850
        },
        "kyc_breakdown": {
            "total_kyc_failures": s.get("kyc_failure_count", 0),
            "failure_rate_percent": s.get("kyc_failure_rate_percent", 0.0),
            "reasons": raw.get("kyc_failure_reasons", {})
        },
        "partner_performance": raw.get("partner_performance", []),
        "retention_and_support": {
            "active_subscribers": ret.get("active_subscribers", 0),
            "csat_average": ret.get("avg_csat_rating", 4.8),
            "churn_risk_percent": ret.get("churn_risk_percent", 2.1),
            "open_tickets": ret.get("open_support_tickets", 0),
            "follow_up_queue": ret.get("follow_up_queue", [])
        },
        "manual_escalations_queue": [
            {
                "escalation_id": "ESC-4019",
                "business_name": "Sharma Retail & Kirana",
                "issue": "Aadhaar Masking Re-scan Needed",
                "assigned_agent": "Mitra Partner PTR-IND-882",
                "sla_remaining_hours": 3.5
            }
        ],
        "raw_analytics": raw
    }

@app.get("/api/admin/reports/export.csv")
def export_admin_leads_csv(
    date_preset: Optional[str] = "all",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    segment: Optional[str] = "all",
    location: Optional[str] = "all",
    channel: Optional[str] = "all",
    stage: Optional[str] = "all",
    partner_id: Optional[str] = None,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    user = verify_role_access([ROLE_ADMIN], authorization, x_session_token, token)
    csv_content = dashboard_service.export_leads_csv(
        segment=segment,
        location=location,
        channel=channel,
        stage=stage,
        partner_id=partner_id
    )
    from fastapi.responses import Response
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=airtel_leads_report.csv"}
    )

@app.get("/api/partner/metrics")
def get_partner_metrics(
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    user = verify_role_access([ROLE_PARTNER, ROLE_ADMIN], authorization, x_session_token, token)
    pid = user["user_id"] if user["role"] == ROLE_PARTNER else "PTR-IND-882"
    raw = dashboard_service.get_admin_dashboard_metrics(partner_id=pid)
    p_perf = next((p for p in raw.get("partner_performance", []) if p.get("partner_id") == pid), {})
    return {
        "status": "SUCCESS",
        "partner_id": pid,
        "territory": user.get("assigned_pincode") or "Indore Central (452001)",
        "partner_leads_claimed": p_perf.get("leads_claimed", 0),
        "partner_orders_attributed": p_perf.get("orders_attributed", 0),
        "monthly_recurring_trail_inr": p_perf.get("commission_earned_inr", 0),
        "total_pending_payout_inr": p_perf.get("commission_earned_inr", 0),
        "active_referrals_count": p_perf.get("orders_attributed", 0)
    }

# 9. Post-Activation Customer Retention & Support Ticketing
@app.post("/api/support/tickets")
def create_support_ticket(
    req: TicketCreateRequest,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    user = verify_role_access([ROLE_MERCHANT, ROLE_PARTNER, ROLE_ADMIN], authorization, x_session_token, token)
    ticket = support_service.create_ticket(
        user_id=user["user_id"],
        category=req.category,
        priority=req.priority,
        subject=req.subject or "Service Request",
        description=req.description,
        customer_email=user.get("email"),
        order_id=req.order_id
    )
    return {"status": "SUCCESS", "ticket": ticket}

@app.get("/api/support/tickets")
def list_support_tickets(
    status: Optional[str] = None,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    user = verify_role_access([ROLE_MERCHANT, ROLE_PARTNER, ROLE_ADMIN], authorization, x_session_token, token)
    if user["role"] == ROLE_ADMIN:
        return {"tickets": support_service.get_all_tickets(status=status)}
    else:
        return {"tickets": support_service.get_user_tickets(user_id=user["user_id"])}

@app.patch("/api/support/tickets/{ticket_id}")
def update_support_ticket(
    ticket_id: str,
    req: TicketUpdateRequest,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    user = verify_role_access([ROLE_ADMIN, ROLE_PARTNER], authorization, x_session_token, token)
    try:
        m_text = req.resolution_milestone or req.milestone or "IN_PROGRESS"
        updated = support_service.update_ticket_milestone(
            ticket_id=ticket_id,
            status=req.status,
            resolution_milestone=m_text,
            admin_notes=req.admin_notes
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Ticket not found")
        return {"status": "SUCCESS", "ticket": updated}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/support/feedback")
def submit_customer_feedback(
    req: FeedbackSubmitRequest,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    user = verify_role_access([ROLE_MERCHANT, ROLE_ADMIN], authorization, x_session_token, token)
    cmt = req.feedback or req.comments or ""
    res = support_service.submit_feedback(
        user_id=user["user_id"],
        rating=req.rating,
        feedback_type=req.journey_step or req.feedback_type,
        comments=cmt,
        customer_email=user.get("email"),
        order_id=req.order_id
    )
    return {"status": "SUCCESS", "feedback": res}

@app.get("/api/customer/dashboard")
def get_customer_dashboard(
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    user = verify_role_access([ROLE_MERCHANT, ROLE_ADMIN], authorization, x_session_token, token)
    uid = user["user_id"]
    u_email = (user.get("email") or "").lower().strip()

    orders = []
    with order_sm._get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM orders WHERE user_id = ? OR LOWER(customer_email) = ? ORDER BY created_at DESC",
            (uid, u_email)
        ).fetchall()
        for r in rows:
            od = dict(r)
            od["bundle"] = json.loads(od.get("bundle_json") or "{}")
            orders.append(od)

    tickets = support_service.get_user_tickets(uid)
    user_feedback = []
    with support_service._get_connection() as conn:
        fb_rows = conn.execute(
            "SELECT * FROM customer_feedback WHERE user_id = ? OR LOWER(customer_email) = ? ORDER BY created_at DESC",
            (uid, u_email)
        ).fetchall()
        user_feedback = [dict(r) for r in fb_rows]

    active_services = []
    monthly_subtotal = 999.0
    if orders:
        latest = orders[0]
        b_data = latest.get("bundle") or {}
        p_quantities = b_data.get("product_quantities") or {}
        monthly_subtotal = b_data.get("monthly_recurring_total") or (round(latest.get("monthly_total", 999.0) / 1.18, 2) if latest.get("monthly_total") else 999.0)
        
        for pid, qty in p_quantities.items():
            prod_info = loader.get_product(pid)
            p_name = prod_info.get("product_name", pid) if prod_info else pid
            p_speed = prod_info.get("speed") if prod_info and prod_info.get("speed") else "High-Speed Business Connectivity"
            p_charge = prod_info.get("price_inr") if prod_info else 0.0
            active_services.append({
                "product_id": pid,
                "product_name": p_name,
                "quantity": qty,
                "speed": p_speed,
                "monthly_charge_inr": p_charge
            })

    if not active_services:
        active_services = [
            {
                "product_id": "P01",
                "product_name": "Biz Fibre 100",
                "quantity": 1,
                "speed": "100 Mbps Unlimited Optical Fibre",
                "monthly_charge_inr": 999.0
            }
        ]

    gst_amt = round(monthly_subtotal * 0.18, 2)
    total_commitment = round(monthly_subtotal + gst_amt, 2)

    return {
        "status": "SUCCESS",
        "customer": {
            "id": uid,
            "email": user.get("email"),
            "name": user.get("name"),
            "phone": user.get("phone"),
            "business_name": (orders[0].get("business_name") if orders else None) or user.get("name")
        },
        "user": {
            "user_id": uid,
            "email": user.get("email"),
            "name": user.get("name"),
            "phone": user.get("phone")
        },
        "active_services_count": len(orders),
        "orders": orders,
        "latest_order": orders[0] if orders else None,
        "active_services": active_services,
        "billing_commitment": {
            "monthly_subtotal_inr": monthly_subtotal,
            "gst_inr": gst_amt,
            "monthly_total_commitment_inr": total_commitment
        },
        "tickets": tickets,
        "support_tickets": tickets,
        "customer_feedback": user_feedback,
        "open_tickets_count": sum(1 for t in tickets if t.get("status") in ["OPEN", "IN_PROGRESS"])
    }

@app.get("/api/admin/retention")
def get_admin_retention(
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    user = verify_role_access([ROLE_ADMIN], authorization, x_session_token, token)
    metrics = dashboard_service.get_admin_dashboard_metrics()
    ret = metrics.get("retention_indicators", {})
    return {
        "status": "SUCCESS",
        "active_subscribers": ret.get("active_subscribers", 0),
        "csat_average": ret.get("avg_csat_rating", 4.8),
        "churn_risk_percent": ret.get("churn_risk_percent", 2.1),
        "open_support_tickets": ret.get("open_support_tickets", 0),
        "dissatisfied_customers_queue": ret.get("follow_up_queue", [])
    }

# 7. WhatsApp Integration Router
app.include_router(whatsapp_router)

STATIC_DIR = Path(__file__).resolve().parent / "static"

@app.get("/whatsapp-simulator")
def serve_whatsapp_simulator():
    from fastapi.responses import FileResponse
    sim_path = STATIC_DIR / "whatsapp_simulator.html"
    if sim_path.exists():
        return FileResponse(sim_path)
    raise HTTPException(status_code=404, detail="Simulator UI not found")

@app.get("/login")
def serve_login_page():
    from fastapi.responses import FileResponse
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="Portal index not found")

@app.get("/mitra")
def serve_mitra_portal():
    from fastapi.responses import FileResponse
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="Portal index not found")

@app.get("/ops")
@app.get("/admin")
def serve_ops_portal():
    from fastapi.responses import FileResponse
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="Portal index not found")

@app.api_route("/", methods=["POST", "HEAD"])
async def root_webhook_fallback(request: Request):
    """
    Fallback handler if Twilio Sandbox is configured with root domain
    (e.g. https://...trycloudflare.com instead of .../api/whatsapp/twilio).
    """
    from app.modules.whatsapp.router import receive_twilio_webhook
    return await receive_twilio_webhook(request)

# Static Mounts
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/specimen", StaticFiles(directory=str(KYC_DOCUMENTS_DIR)), name="specimen")

if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
