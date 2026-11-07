"""
================================================================================
ROBUST KYC VERIFICATION SUITE — 47 SPECIMEN DOCUMENTS ACROSS 12 APPLICANTS (K01-K12)
================================================================================
Tests all 47 synthetic KYC files against DoT/TRAI statutory regulations:
  1. Image Sharpness & Blur Gate (OpenCV Laplacian Variance threshold >= 120.0)
  2. Document Freshness Gate (Address Proof <= 90 days relative to 2026-07-15)
  3. Statutory GSTIN Registry Integrity (Active vs. Cancelled/Suspended in mock registry)
  4. Udyam Registration Format & Existence (UDYAM-XX-00-XXXXXXX in mock registry)
  5. Mandatory Document Completeness (Detection of missing files e.g. K05 Udyam)
  6. Non-GST Udyam Safe Mode validation for micro-enterprises
================================================================================
"""

import sys
import os
import json
import asyncio
from pathlib import Path
from datetime import datetime
import cv2
from PIL import Image
import winocr
import pandas as pd
from thefuzz import process, fuzz
from app.main import verify_extracted_data, VerifyExtractedRequest
from app.data_loader import DataLoader
from app.modules.kyc.validator import KYCValidator
from app.modules.kyc.ocr_engine import OCREngine
from app.config import CASE_REFERENCE_DATE, MAX_ADDRESS_PROOF_AGE_DAYS, KYC_DOCUMENTS_DIR

loader = DataLoader.get_instance()
validator = KYCValidator()
ocr_engine = OCREngine()

REF_DATE = datetime.strptime(CASE_REFERENCE_DATE, "%Y-%m-%d")

# Ground Truth Definition for the 12 Applicants
GROUND_TRUTH = {
    "K01": {
        "name": "Vindhya Tours & Travels",
        "expected_gst_status": "REJECTED",
        "reason_pattern": "Cancelled",
        "description": "Statutory Trap: GSTIN 37IHKXV5167L1ZS is Cancelled in GST Registry"
    },
    "K02": {
        "name": "Harmony Dental Care",
        "expected_gst_status": "VERIFIED",
        "description": "Golden Path: Active GSTIN 19E0GXH4115Y1ZL, Fresh Address Proof (54d)"
    },
    "K03": {
        "name": "Ganesh Woodcraft",
        "expected_gst_status": "VERIFIED",
        "expected_nongst_status": "VERIFIED",
        "description": "Dual-Path: Active GSTIN 27XUIXG0767D1ZP & Valid Udyam MH-00-9516696"
    },
    "K04": {
        "name": "Saffron Dental Care LLP",
        "expected_gst_status": "ACTION_REQUIRED",
        "reason_pattern": "blurry",
        "description": "Image Quality Trap: K04_gst_certificate.png is heavily blurred (var: 1.03)"
    },
    "K05": {
        "name": "Balaji Realty LLP",
        "expected_gst_status": "VERIFIED",
        "expected_nongst_status": "ACTION_REQUIRED",
        "reason_pattern": "Missing mandatory document",
        "description": "File Completeness Trap: K05_udyam_certificate.png is absent from pack"
    },
    "K06": {
        "name": "Saffron Unisex Salon",
        "expected_gst_status": "VERIFIED",
        "description": "Clean Micro Enterprise: Active GSTIN 08YKZXS5189L1ZO, Fresh Bill (34d)"
    },
    "K07": {
        "name": "Neelgiri Physio Clinic",
        "expected_gst_status": "VERIFIED",
        "description": "Clean Clinic Enterprise: Active GSTIN 07CPCXN0398P1ZT, Fresh Bill (10d)"
    },
    "K08": {
        "name": "Green Leaf Legal Associates",
        "expected_gst_status": "VERIFIED",
        "description": "Clean Legal Practice: Active GSTIN 24XORXG9365M1Z3, Fresh Bill (50d)"
    },
    "K09": {
        "name": "Kaveri Insurance Advisors",
        "expected_gst_status": "VERIFIED",
        "description": "Clean Financial Services: Active GSTIN 37LDYXK0296F1ZB, Fresh Bill (5d)"
    },
    "K10": {
        "name": "Kaveri Stays LLP",
        "expected_gst_status": "VERIFIED",
        "description": "Clean Hospitality Enterprise: Active GSTIN 27QHJXK0658U1ZL, Fresh Bill (27d)"
    },
    "K11": {
        "name": "Trinity Bake House Pvt Ltd",
        "expected_gst_status": "REJECTED",
        "reason_pattern": "Expired",
        "description": "Freshness Trap: Address Proof bill date 2025-10-31 is 257 days old (>90d)"
    },
    "K12": {
        "name": "Star Electronics",
        "expected_gst_status": "VERIFIED",
        "expected_nongst_status": "VERIFIED",
        "description": "Golden Path: Active GSTIN 37NBLXS1145E1ZU & Valid Udyam AP-00-5186772"
    }
}

def run_pass_1_individual_document_audit():
    print("\n" + "=" * 75)
    print("RUN 1: INDIVIDUAL AUDIT OF ALL 47 SPECIMEN KYC FILES")
    print("=" * 75)
    
    files = sorted(list(KYC_DOCUMENTS_DIR.glob("*.png")))
    assert len(files) == 47, f"Expected exactly 47 KYC documents, found {len(files)}"
    print(f"✔ File Count Verification: Exactly 47 files located in {KYC_DOCUMENTS_DIR.name}/")

    doc_type_counts = {"GST_CERTIFICATE": 0, "UDYAM_CERTIFICATE": 0, "ADDRESS_PROOF": 0, "SIGNATORY_ID": 0}
    blur_failures = []
    
    for idx, f in enumerate(files, 1):
        # 1. Existence and size
        size_bytes = f.stat().st_size
        assert size_bytes > 10000, f"File {f.name} is abnormally small ({size_bytes} bytes)"

        # 2. Laplacian Blur Check
        img = cv2.imread(str(f), cv2.IMREAD_GRAYSCALE)
        assert img is not None, f"Failed to load image {f.name}"
        var = float(cv2.Laplacian(img, cv2.CV_64F).var())
        is_clear = var >= 120.0

        if not is_clear:
            blur_failures.append((f.name, var))

        # 3. Classify document type from filename
        if "gst_certificate" in f.name:
            doc_type_counts["GST_CERTIFICATE"] += 1
        elif "udyam_certificate" in f.name:
            doc_type_counts["UDYAM_CERTIFICATE"] += 1
        elif "address_proof" in f.name:
            doc_type_counts["ADDRESS_PROOF"] += 1
        elif "signatory_id" in f.name:
            doc_type_counts["SIGNATORY_ID"] += 1

    print("\nDocument Category Breakdown:")
    for doc_type, count in doc_type_counts.items():
        print(f"  • {doc_type:20}: {count} files")
    
    assert doc_type_counts["GST_CERTIFICATE"] == 12
    assert doc_type_counts["ADDRESS_PROOF"] == 12
    assert doc_type_counts["SIGNATORY_ID"] == 12
    assert doc_type_counts["UDYAM_CERTIFICATE"] == 11 # K05 is intentionally missing
    print("✔ Category Breakdown: Exactly 12 GST, 12 Address Proofs, 12 Signatory IDs, 11 Udyam Certs")

    print(f"\nLaplacian Image Clarity Audit (Threshold: >= 120.0):")
    print(f"  • Clear Documents: {47 - len(blur_failures)} / 47")
    print(f"  • Blur Failures: {len(blur_failures)} -> {blur_failures}")
    assert len(blur_failures) == 1
    assert blur_failures[0][0] == "K04_gst_certificate.png"
    assert blur_failures[0][1] < 5.0
    print(f"✔ Blur Detection Gate: K04_gst_certificate.png correctly flagged (Variance: {blur_failures[0][1]})")


def run_pass_2_applicant_verification_engine():
    print("\n" + "=" * 75)
    print("RUN 2: APPLICANT-LEVEL STATUTORY VERIFICATION (K01 TO K12)")
    print("=" * 75)

    results_table = []
    
    for app_code in [f"K{i:02d}" for i in range(1, 13)]:
        truth = GROUND_TRUTH[app_code]
        expected_status = truth["expected_gst_status"]

        # Run Standard GST Validation
        gst_decision = validator.validate_applicant(app_code, is_non_gst_mode=False)
        actual_status = gst_decision["status"]

        # Assert correct decision
        assert actual_status == expected_status, (
            f"Applicant {app_code} mismatch! Expected {expected_status}, got {actual_status}. "
            f"Reasons: {gst_decision.get('reasons')}"
        )

        # Check reason pattern if specified
        if "reason_pattern" in truth and actual_status != "VERIFIED":
            reasons_str = " ".join(gst_decision.get("reasons", []))
            assert truth["reason_pattern"].lower() in reasons_str.lower(), (
                f"Applicant {app_code} reason missing pattern '{truth['reason_pattern']}': {reasons_str}"
            )

        # If dual-path / non-gst testable:
        nongst_status = None
        if "expected_nongst_status" in truth:
            nongst_expected = truth["expected_nongst_status"]
            nongst_dec = validator.validate_applicant(app_code, is_non_gst_mode=True)
            nongst_status = nongst_dec["status"]
            assert nongst_status == nongst_expected, (
                f"Applicant {app_code} Non-GST mismatch! Expected {nongst_expected}, got {nongst_status}."
            )
            if "reason_pattern" in truth and nongst_status != "VERIFIED":
                ng_reasons = " ".join(nongst_dec.get("reasons", []))
                assert truth["reason_pattern"].lower() in ng_reasons.lower(), (
                    f"Applicant {app_code} Non-GST missing pattern: {ng_reasons}"
                )

        results_table.append({
            "applicant": app_code,
            "business_name": truth["name"],
            "gst_decision": actual_status,
            "nongst_decision": nongst_status or "N/A",
            "action": gst_decision["action"],
            "description": truth["description"]
        })
        print(f"  ✔ [{app_code}] {truth['name']:30} -> {actual_status:16} | {truth['description']}")

    # Check via FastAPI route handler (Testing the live API route)
    print("\n[Route Handler Validation via verify_extracted_data()]")
    defaults = validator.APPLICANT_DEFAULTS
    for app_code in ["K01", "K04", "K11", "K12"]:
        truth = GROUND_TRUTH[app_code]
        def_data = defaults.get(app_code, {})
        req = VerifyExtractedRequest(
            applicant_code=app_code,
            gstin=def_data.get("gstin"),
            udyam_number=def_data.get("udyam"),
            entity_name=def_data.get("name"),
            bill_date=def_data.get("bill_date"),
            blur_variance=1.03 if app_code == "K04" else 1000.0,
            is_non_gst_mode=False
        )
        res = verify_extracted_data(req)
        assert res["status"] == truth["expected_gst_status"], f"Route handler mismatch for {app_code}: {res}"
        print(f"  ✔ API verify_extracted_data [{app_code}]: {res['status']} matches ground truth")


def main():
    print("=" * 75)
    print("STARTING COMPREHENSIVE 47-DOCUMENT KYC VALIDATION SUITE")
    print("=" * 75)
    
    # Check 1: Individual file and image audit
    run_pass_1_individual_document_audit()

    # Check 2: Applicant business logic and statutory traps verification
    run_pass_2_applicant_verification_engine()

    print("\n" + "=" * 75)
    print("ALL 47 KYC DOCUMENTS & 12 APPLICANTS VERIFIED TWICE (100% GREEN)")
    print("=" * 75)

if __name__ == "__main__":
    main()
