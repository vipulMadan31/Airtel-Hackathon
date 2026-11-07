import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "YTL_TrackA_Udyam_Digital_Data"

PRODUCT_CATALOGUE_PATH = DATA_DIR / "product_catalogue.csv"
MOCK_GSTIN_REGISTRY_PATH = DATA_DIR / "mock_gstin_registry.csv"
MOCK_UDYAM_REGISTRY_PATH = DATA_DIR / "mock_udyam_registry.csv"
SMB_LEADS_PATH = DATA_DIR / "smb_leads.csv"
KYC_DOCUMENTS_DIR = DATA_DIR / "kyc_documents"

DB_PATH = BASE_DIR / "udyam_orders.db"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Official Case Study Reference Date for Date-based validation (README line 65)
CASE_REFERENCE_DATE = "2026-07-15"
MAX_ADDRESS_PROOF_AGE_DAYS = 90

# Load .env if present
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    try:
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip("'\""))
    except Exception:
        pass

# LLM Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

# OCR Engine Configuration
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "")
OCR_MIN_BLUR_VARIANCE = float(os.getenv("OCR_MIN_BLUR_VARIANCE", "100.0"))
OCR_ENABLE_DESKEW = os.getenv("OCR_ENABLE_DESKEW", "true").lower() in ["true", "1", "yes"]

