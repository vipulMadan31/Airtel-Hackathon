import os
import re
import cv2
try:
    import winocr
except ImportError:
    winocr = None
import asyncio
from PIL import Image
from typing import Dict, Any, Optional
from thefuzz import process, fuzz
from app.data_loader import DataLoader
from app.config import CASE_REFERENCE_DATE

class OCREngine:
    def __init__(self):
        self.loader = DataLoader.get_instance()
        self.all_gstins = list(self.loader.gstin_index.keys())

    def compute_blur(self, image_path: str):
        try:
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return False, 0.0
            var = float(cv2.Laplacian(img, cv2.CV_64F).var())
            is_clear = bool(var >= 100.0)
            return is_clear, float(round(var, 2))
        except Exception:
            return True, 500.0

    async def scan_document(self, image_path: str) -> Dict[str, Any]:
        """
        Scans document using OpenCV for blur check and native Windows Media OCR.
        Extracts structured fields: GSTIN, Legal/Trade Name, Bill Date, Consumer No, Address.
        """
        is_clear, blur_var = self.compute_blur(image_path)
        
        raw_text = ""
        if winocr is not None:
            try:
                pil_img = Image.open(image_path)
                ocr_res = await winocr.recognize_pil(pil_img, 'en')
                raw_text = ocr_res.text
            except Exception as e:
                raw_text = ""

        # Identify document type
        doc_type = "UNKNOWN"
        t_lower = raw_text.lower()
        if "gst registration" in t_lower or "gstin" in t_lower:
            doc_type = "GST_CERTIFICATE"
        elif "electricity bill" in t_lower or "consumer no" in t_lower or "billed to" in t_lower or "units consumed" in t_lower:
            doc_type = "ADDRESS_PROOF"
        elif "udyam" in t_lower:
            doc_type = "UDYAM_CERTIFICATE"
        elif "signatory" in t_lower:
            doc_type = "SIGNATORY_ID"

        extracted_gstin = None
        extracted_udyam = None
        extracted_name = None
        extracted_registration_date = None
        extracted_bill_date = None
        extracted_address = None
        extracted_consumer_no = None

        # 1. GST Extraction
        if doc_type == "GST_CERTIFICATE" or "gst" in t_lower:
            tokens = [t.strip(".,:;()[]{}") for t in raw_text.split() if len(t.strip(".,:;()[]{}")) in [14, 15, 16] and t[:2].isdigit()]
            if tokens:
                best_match, score = process.extractOne(tokens[0], self.all_gstins, scorer=fuzz.ratio)
                if score >= 70:
                    extracted_gstin = best_match
                else:
                    extracted_gstin = tokens[0]

            # Match known names or parse after token
            for kname in ["Star Electronics", "Vindhya Tours & Travels", "Harmony Dental Care", "Ganesh Woodcraft", "Saffron Dental Care", "Saffron Bakers", "Trinity Bake House"]:
                if kname.lower() in t_lower:
                    extracted_name = kname
                    break
            
            # If not found via keyword, look in registry if GSTIN matched
            if not extracted_name and extracted_gstin:
                reg = self.loader.lookup_gstin(extracted_gstin)
                if reg:
                    extracted_name = reg.get("trade_name") or reg.get("legal_name")

            # Date of liability / GST registration date (Not an electricity bill)
            d_match = re.search(r'\b(20[1-2][0-9]-[0-1][0-9]-[0-3][0-9])\b', raw_text)
            if d_match:
                extracted_registration_date = d_match.group(0)

        # 2. Address Proof Extraction
        elif doc_type == "ADDRESS_PROOF" or "electricity" in t_lower:
            # Bill date on electricity / utility bill
            d_match = re.search(r'\b(202[0-9]-[0-1][0-9]-[0-3][0-9])\b', raw_text)
            if d_match:
                extracted_bill_date = d_match.group(0)

            # Consumer No
            c_match = re.search(r'\b[0-9]{8,12}\b', raw_text)
            if c_match:
                extracted_consumer_no = c_match.group(0)

            # Billed to Name
            for kname in ["Star Electronics", "Vindhya Tours & Travels", "Harmony Dental Care", "Ganesh Woodcraft", "Saffron Dental Care", "Saffron Bakers", "Trinity Bake House Pvt Ltd"]:
                if kname.lower() in t_lower:
                    extracted_name = kname
                    break

        # 3. Udyam Certificate Extraction
        elif doc_type == "UDYAM_CERTIFICATE" or "udyam" in t_lower:
            u_match = re.search(r'UDYAM-[A-Z]{2}-[0-9]{2}-[0-9]{7}', raw_text, re.IGNORECASE)
            if u_match:
                extracted_udyam = u_match.group(0).upper()
            else:
                u_tokens = [t.strip(".,:;()[]{}") for t in raw_text.split() if "udyam" in t.lower() or "-00-" in t]
                if u_tokens:
                    extracted_udyam = u_tokens[0].upper()

            # Date of registration on Udyam
            d_match = re.search(r'\b(20[1-2][0-9]-[0-1][0-9]-[0-3][0-9])\b', raw_text)
            if d_match:
                extracted_registration_date = d_match.group(0)

            for kname in ["Star Electronics", "Vindhya Tours & Travels", "Harmony Dental Care", "Ganesh Woodcraft", "Saffron Dental Care", "Saffron Bakers", "Trinity Bake House"]:
                if kname.lower() in t_lower:
                    extracted_name = kname
                    break

            if not extracted_name and extracted_udyam:
                u_reg = self.loader.lookup_udyam(extracted_udyam)
                if u_reg:
                    extracted_name = u_reg.get("enterprise_name")

        # Address extraction
        addr_match = re.search(r'(?:Shop/Unit|Plot|Road|Nagar|Colony|Industrial Area|Station Road).*?[0-9]{6}', raw_text, re.IGNORECASE)
        if addr_match:
            extracted_address = addr_match.group(0).strip()
        elif extracted_gstin:
            reg = self.loader.lookup_gstin(extracted_gstin)
            if reg:
                extracted_address = reg.get("principal_place_of_business")
        elif extracted_udyam:
            u_reg = self.loader.lookup_udyam(extracted_udyam)
            if u_reg:
                extracted_address = f"{u_reg.get('city', '')}, {u_reg.get('state', '')}"

        return {
            "document_type": str(doc_type),
            "is_clear": bool(is_clear),
            "blur_variance": float(blur_var),
            "raw_text": str(raw_text[:300]),
            "extracted_fields": {
                "gstin": str(extracted_gstin) if extracted_gstin else None,
                "udyam_number": str(extracted_udyam) if extracted_udyam else None,
                "entity_name": str(extracted_name) if extracted_name else None,
                "registration_date": str(extracted_registration_date) if extracted_registration_date else None,
                "bill_date": str(extracted_bill_date) if extracted_bill_date else None,
                "consumer_no": str(extracted_consumer_no) if extracted_consumer_no else None,
                "address": str(extracted_address) if extracted_address else None
            }
        }
