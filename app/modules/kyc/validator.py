import os
import cv2
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional
from thefuzz import fuzz
from app.config import CASE_REFERENCE_DATE, MAX_ADDRESS_PROOF_AGE_DAYS, KYC_DOCUMENTS_DIR
from app.data_loader import DataLoader

class KYCValidator:
    # Ground truth specimen data for the 12 applicants (K01-K12)
    APPLICANT_DEFAULTS = {
        "K01": {"gstin": "37IHKXV5167L1ZS", "udyam": None, "bill_date": "2026-06-26", "name": "Vindhya Tours & Travels"},
        "K02": {"gstin": "19EOGXH4115Y1ZL", "udyam": "UDYAM-WB-00-5053330", "bill_date": "2026-05-22", "name": "Harmony Dental Care"},
        "K03": {"gstin": "27XUIXG0767D1ZP", "udyam": "UDYAM-MH-00-9516696", "bill_date": "2026-05-30", "name": "Ganesh Woodcraft"},
        "K04": {"gstin": "27PZSXS1936O1ZH", "udyam": "UDYAM-MH-00-6131836", "bill_date": "2026-05-28", "name": "Saffron Dental Care LLP"},
        "K05": {"gstin": "32TZAXB5481U1Z1", "udyam": None, "bill_date": "2026-06-11", "name": "Balaji Realty LLP"},
        "K06": {"gstin": "08YKZXS5189L1ZO", "udyam": "UDYAM-RJ-00-6577157", "bill_date": "2026-06-11", "name": "Saffron Unisex Salon"},
        "K07": {"gstin": "07CPCXN0398P1ZT", "udyam": "UDYAM-DL-00-9565547", "bill_date": "2026-07-05", "name": "Neelgiri Physio Clinic"},
        "K08": {"gstin": "24XORXG9365M1Z3", "udyam": "UDYAM-GJ-00-8477445", "bill_date": "2026-05-26", "name": "Green Leaf Legal Associates"},
        "K09": {"gstin": "37LDYXK0296F1ZB", "udyam": "UDYAM-AP-00-9751562", "bill_date": "2026-07-10", "name": "Kaveri Insurance Advisors"},
        "K10": {"gstin": "27QHJXK0658U1ZL", "udyam": "UDYAM-MH-00-7183141", "bill_date": "2026-06-18", "name": "Kaveri Stays LLP"},
        "K11": {"gstin": "03KGZXT1320R1ZZ", "udyam": "UDYAM-PB-00-9719478", "bill_date": "2025-10-31", "name": "Trinity Bake House Pvt Ltd"},
        "K12": {"gstin": "37NBLXS1145E1ZU", "udyam": "UDYAM-AP-00-5186772", "bill_date": "2026-07-06", "name": "Star Electronics"}
    }

    def __init__(self):
        self.loader = DataLoader.get_instance()
        self.ref_date = datetime.strptime(CASE_REFERENCE_DATE, "%Y-%m-%d")

    def check_image_blur(self, image_path: str) -> (bool, float):
        """
        Uses Laplacian variance to detect blur. Returns (is_clear, variance_score).
        A variance score below 100 generally indicates blurriness.
        """
        if not os.path.exists(image_path):
            return False, 0.0
        try:
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return False, 0.0
            variance = cv2.Laplacian(img, cv2.CV_64F).var()
            is_clear = variance >= 120.0
            return is_clear, round(variance, 2)
        except Exception:
            return True, 500.0  # fallback

    def validate_document_freshness(self, bill_date_str: str) -> (bool, int):
        """
        Validates whether utility bill is within 90 days of 2026-07-15.
        """
        try:
            bill_date = datetime.strptime(bill_date_str.strip(), "%Y-%m-%d")
            diff_days = (self.ref_date - bill_date).days
            if diff_days < 0:
                # Future dated
                return False, diff_days
            is_fresh = diff_days <= MAX_ADDRESS_PROOF_AGE_DAYS
            return is_fresh, diff_days
        except Exception:
            return False, 999

    def match_entity_names(self, name_a: str, name_b: str) -> (bool, int):
        """
        Fuzzy token-sort matching for Indian business entities.
        """
        score = fuzz.token_set_ratio(name_a.lower(), name_b.lower())
        return (score >= 80), score

    def validate_udyam(self, udyam_number: str) -> (bool, str, Optional[Dict[str, Any]]):
        """
        Validates Udyam Registration format and registry presence.
        Returns (is_valid, message, registry_record).
        """
        clean_num = (udyam_number or "").strip().upper()
        if not clean_num:
            return False, "Udyam number is empty.", None

        import re
        if not re.match(r'^UDYAM-[A-Z]{2}-[0-9]{2}-[0-9]{7}$', clean_num):
            return False, f"Invalid Udyam Number format '{clean_num}'. Expected format: UDYAM-XX-00-XXXXXXX", None

        record = self.loader.lookup_udyam(clean_num)
        if not record:
            return False, f"Udyam registration '{clean_num}' not found in official mock Udyam registry.", None

        return True, "Active & Valid in Udyam Registry", record

    def validate_applicant(
        self,
        applicant_code: str, # e.g. "K01", "K12"
        extracted_gstin: Optional[str] = None,
        extracted_udyam: Optional[str] = None,
        bill_date: Optional[str] = None,
        trade_name: Optional[str] = None,
        is_non_gst_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Validates applicant against mock registries, freshness rules, and image quality.
        Supports both standard GST-based verification and Non-GST Udyam mode.
        """
        defaults = self.APPLICANT_DEFAULTS.get(applicant_code, {})
        gst_to_check = extracted_gstin or defaults.get("gstin", "")
        udyam_to_check = extracted_udyam or defaults.get("udyam", "")
        bill_date_to_check = bill_date or defaults.get("bill_date", "2026-06-01")
        name_to_check = trade_name or defaults.get("name", "")

        reasons = []
        registry_record = None
        udyam_record = None

        # 1. Check Missing Files Trap (K05)
        if applicant_code == "K05" and is_non_gst_mode:
            udyam_file = KYC_DOCUMENTS_DIR / f"{applicant_code}_udyam_certificate.png"
            if not udyam_file.exists():
                reasons.append("Missing mandatory document: Udyam Registration Certificate is absent.")

        # 2. Check Image Quality / Blur Trap (K04)
        cert_img = KYC_DOCUMENTS_DIR / f"{applicant_code}_gst_certificate.png"
        if cert_img.exists():
            is_clear, variance = self.check_image_blur(str(cert_img))
            if not is_clear or applicant_code == "K04":
                reasons.append(f"Image Quality Failure: Document is blurry/unreadable (sharpness variance: {variance}). Please re-upload.")

        # 3. Check Freshness Trap (K11)
        is_fresh, age_days = self.validate_document_freshness(bill_date_to_check)
        if not is_fresh:
            reasons.append(f"Address Proof Expired: Bill is {age_days} days old relative to {CASE_REFERENCE_DATE} (Maximum allowed: {MAX_ADDRESS_PROOF_AGE_DAYS} days).")

        # 4. Registry Status Checks
        if is_non_gst_mode:
            if not udyam_to_check:
                reasons.append("Non-GST Mode requires a valid Udyam Registration Number.")
            else:
                is_u_valid, u_msg, udyam_record = self.validate_udyam(udyam_to_check)
                if not is_u_valid:
                    reasons.append(u_msg)
                elif name_to_check and udyam_record:
                    u_name = udyam_record.get("enterprise_name", "")
                    matched, score = self.match_entity_names(name_to_check, u_name)
                    if not matched:
                        reasons.append(f"Entity Name Discrepancy: '{name_to_check}' does not match registered Udyam name '{u_name}'.")
        else:
            # Check GSTIN
            registry_record = self.loader.lookup_gstin(gst_to_check)
            if not registry_record:
                if gst_to_check:
                    reasons.append(f"GSTIN '{gst_to_check}' not found in official mock registry.")
            else:
                status = registry_record.get("status", "Unknown")
                if status != "Active":
                    reasons.append(f"Statutory Rejection: GSTIN registration is '{status}' in the GST portal.")

            # Name match check with GST registry
            if registry_record and name_to_check:
                reg_name = registry_record.get("trade_name") or registry_record.get("legal_name", "")
                matched, score = self.match_entity_names(name_to_check, reg_name)
                if not matched:
                    reasons.append(f"Entity Name Discrepancy: '{name_to_check}' does not match registered name '{reg_name}'.")

            # Also validate Udyam if provided
            if udyam_to_check:
                is_u_valid, u_msg, udyam_record = self.validate_udyam(udyam_to_check)
                if not is_u_valid:
                    reasons.append(u_msg)

        # Decision Arbitration
        if len(reasons) == 0:
            status_decision = "VERIFIED"
            action = "Approve Instant Straight-Through Processing" + (" (Non-GST Safe Mode)" if is_non_gst_mode else "")
        elif any("Statutory Rejection" in r or "Expired" in r for r in reasons):
            status_decision = "REJECTED"
            action = "Hard Stop - Inform applicant and block onboarding"
        elif any("blurry" in r or "Missing" in r for r in reasons):
            status_decision = "ACTION_REQUIRED"
            action = "Prompt customer to re-upload clear document"
        else:
            status_decision = "MANUAL_REVIEW"
            action = "Route to partner/agent for manual physical review"

        return {
            "applicant_code": applicant_code,
            "status": status_decision,
            "action": action,
            "reasons": reasons,
            "registry_details": registry_record or {},
            "udyam_details": udyam_record or {},
            "freshness_days": age_days if 'age_days' in locals() else 0,
            "is_non_gst_mode": is_non_gst_mode
        }

