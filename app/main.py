import os
import shutil
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from app.modules.advisor.adapter import AdvisorAdapter
from app.modules.catalog.engine import CatalogEngine
from app.modules.pricing.calculator import PricingCalculator
from app.modules.kyc.validator import KYCValidator
from app.modules.kyc.ocr_engine import OCREngine
from app.modules.orders.state_machine import OrderStateMachine
from app.modules.partner.portal import PartnerPortal
from app.data_loader import DataLoader
from app.config import KYC_DOCUMENTS_DIR

app = FastAPI(
    title="Project Udyam Digital",
    description="Digital Acquisition & Onboarding Engine for MSMEs (Airtel SYNC Hackathon 2026)",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
partner_portal = PartnerPortal()
loader = DataLoader.get_instance()

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Schemas
class ChatRequest(BaseModel):
    message: str
    current_profile: Optional[Dict[str, Any]] = None
    language: str = "en"

class BucketRequest(BaseModel):
    city_tier: int = 1
    employee_count: int = 3
    num_sites: int = 1
    has_gstin: bool = True
    current_base_id: Optional[str] = "P01"

class QuoteRequest(BaseModel):
    quantities: Dict[str, int]
    apply_digital_discount: bool = True
    waive_setup_fee: bool = True

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
    blur_variance: Optional[float] = 1000.0
    applicant_code: Optional[str] = "CUSTOM"
    is_non_gst_mode: Optional[bool] = False

class GstinLookupRequest(BaseModel):
    gstin: str

class UdyamLookupRequest(BaseModel):
    udyam_number: str

class CreateOrderRequest(BaseModel):
    business_name: str
    contact_phone: str
    bundle_data: Dict[str, Any]
    kyc_status: str = "VERIFIED"
    language: str = "en"

class RescheduleRequest(BaseModel):
    new_date: str

class NPSRequest(BaseModel):
    rating: int

# --- API ENDPOINTS ---

@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": "Project Udyam Digital", "version": "1.0.0"}

# 1. Advisor
@app.post("/api/advisor/chat")
def chat_with_advisor(req: ChatRequest):
    return advisor_adapter.process_user_message(req.message, req.current_profile, req.language)

# 2. Catalog & 3-Bucket Drawer
@app.get("/api/catalog/products")
def get_catalog_products():
    return loader.get_all_products()

@app.post("/api/catalog/buckets")
def get_catalog_buckets(req: BucketRequest):
    return catalog_engine.get_three_buckets(
        req.city_tier, req.employee_count, req.num_sites, req.has_gstin, req.current_base_id
    )

# 3. Pricing & Down-sell
@app.post("/api/pricing/quote")
def calculate_quote(req: QuoteRequest):
    return pricing_calculator.calculate_quote(
        req.quantities, req.apply_digital_discount, req.waive_setup_fee
    )

@app.post("/api/pricing/downsell")
def execute_downsell(req: DownsellRequest):
    return pricing_calculator.execute_downsell_step(req.quantities, req.step)

# 4. Smart KYC: Document Upload & Real OCR Pipeline
@app.post("/api/kyc/upload")
async def upload_kyc_document(file: UploadFile = File(...)):
    """
    Accepts real user file upload, runs OpenCV blur detection and Windows Native OCR.
    """
    dest_path = UPLOAD_DIR / file.filename
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    ocr_result = await ocr_engine.scan_document(str(dest_path))
    ocr_result["file_name"] = file.filename
    ocr_result["image_url"] = f"/uploads/{file.filename}"
    return ocr_result

@app.post("/api/kyc/specimen-scan")
async def scan_specimen_document(req: SpecimenScanRequest):
    """
    Runs real OCR and blur detection on the official hackathon specimen images.
    Supports GST Certificate, Address Proof, and Udyam Certificate.
    """
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
    ocr_result["file_name"] = filename
    ocr_result["image_url"] = f"/specimen/{filename}"
    return ocr_result

@app.post("/api/verify/gstin")
def verify_gstin_lookup(req: GstinLookupRequest):
    """
    Mock GSTIN Lookup API querying official mock_gstin_registry.csv.
    """
    gstin_val = req.gstin.strip().upper()
    record = loader.lookup_gstin(gstin_val)
    if not record:
        raise HTTPException(status_code=404, detail=f"GSTIN '{gstin_val}' not found in official mock registry.")
    return {
        "found": True,
        "gstin": gstin_val,
        "legal_name": record.get("legal_name"),
        "trade_name": record.get("trade_name"),
        "status": record.get("status"),
        "is_active": record.get("status") == "Active",
        "principal_place_of_business": record.get("principal_place_of_business"),
        "registration_date": record.get("registration_date")
    }

@app.post("/api/verify/udyam")
def verify_udyam_lookup(req: UdyamLookupRequest):
    """
    Mock Udyam Lookup API querying official mock_udyam_registry.csv.
    """
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
def verify_extracted_data(req: VerifyExtractedRequest):
    """
    Validates reviewed extracted fields against mock registries (GSTIN & Udyam),
    90-day date rule, and blur threshold.
    """
    reasons = []
    registry_rec = None
    udyam_rec = None

    # 1. Blur Check
    if req.blur_variance is not None and req.blur_variance < 100.0:
        reasons.append(f"Image Quality Failure: Document is blurry/unreadable (sharpness variance: {req.blur_variance:.2f}). Please re-upload a clear photo.")

    # 2. Registry Status Check: Non-GST Mode vs Standard GST Mode
    if req.is_non_gst_mode:
        udyam_val = (req.udyam_number or "").strip().upper()
        if not udyam_val:
            reasons.append("Non-GST Mode requires a valid Udyam Registration Number.")
        else:
            is_u_valid, u_msg, udyam_rec = kyc_validator.validate_udyam(udyam_val)
            if not is_u_valid:
                reasons.append(u_msg)
    else:
        gstin_val = (req.gstin or "").strip().upper()
        if not gstin_val and not req.udyam_number:
            reasons.append("Active GSTIN is required for standard enterprise verification.")
        elif gstin_val:
            registry_rec = loader.lookup_gstin(gstin_val)
            if not registry_rec:
                reasons.append(f"GSTIN '{gstin_val}' not found in official mock registry.")
            else:
                status = registry_rec.get("status", "Unknown")
                if status != "Active":
                    reasons.append(f"Statutory Rejection: GSTIN registration is '{status}' in the GST portal.")

        # Check Udyam if optionally provided
        if req.udyam_number:
            is_u_valid, u_msg, udyam_rec = kyc_validator.validate_udyam(req.udyam_number)
            if not is_u_valid:
                reasons.append(u_msg)

    # 3. 90-Day Freshness Check (Only applies to Address Proof / Electricity Bill)
    if req.bill_date:
        is_gst_reg_date = bool(registry_rec and req.bill_date == registry_rec.get("registration_date"))
        is_udyam_reg_date = bool(udyam_rec and req.bill_date == udyam_rec.get("date_of_registration"))

        if not is_gst_reg_date and not is_udyam_reg_date:
            is_fresh, diff_days = kyc_validator.validate_document_freshness(req.bill_date)
            if not is_fresh:
                reasons.append(f"Address Proof Expired: Bill is {diff_days} days old relative to 2026-07-15 (Allowed: <= 90 days).")

    # 4. Name Match Check
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

    # Decision Logic
    if len(reasons) == 0:
        status_decision = "VERIFIED"
        action = "Approve Instant Straight-Through Processing" + (" (Non-GST Safe Mode)" if req.is_non_gst_mode else "")
    elif any("Statutory Rejection" in r or "Expired" in r for r in reasons):
        status_decision = "REJECTED"
        action = "Hard Stop - Inform applicant and block onboarding"
    elif any("blurry" in r for r in reasons):
        status_decision = "ACTION_REQUIRED"
        action = "Prompt customer to re-upload clear document"
    else:
        status_decision = "MANUAL_REVIEW"
        action = "Route to partner/agent for manual review"

    return {
        "status": status_decision,
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

# 5. Orders & Tracker
@app.post("/api/orders/create")
def create_order(req: CreateOrderRequest):
    return order_sm.create_order(
        req.business_name, req.contact_phone, req.bundle_data, req.kyc_status, req.language
    )

@app.get("/api/orders/{order_id}")
def get_order(order_id: str):
    order = order_sm.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.post("/api/orders/{order_id}/reschedule")
def reschedule_order(order_id: str, req: RescheduleRequest):
    success = order_sm.reschedule_installation(order_id, req.new_date)
    if not success:
        raise HTTPException(status_code=404, detail="Order not found or update failed")
    return {"status": "success", "order_id": order_id, "new_install_date": req.new_date}

@app.post("/api/orders/{order_id}/nps")
def submit_nps(order_id: str, req: NPSRequest):
    success = order_sm.record_nps(order_id, req.rating)
    if not success:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"status": "success", "order_id": order_id, "nps_rating": req.rating}

# 6. Partner Portal
@app.get("/api/partner/leads")
def get_partner_leads():
    return partner_portal.get_stalled_leads_with_propensity(limit=15)

@app.get("/api/partner/referral")
def get_partner_referral():
    return partner_portal.generate_partner_referral_link()

# Static Mounts
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/specimen", StaticFiles(directory=str(KYC_DOCUMENTS_DIR)), name="specimen")

STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
