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

# Official Case Study Reference Date for Date-based validation (README line 65)
CASE_REFERENCE_DATE = "2026-07-15"
MAX_ADDRESS_PROOF_AGE_DAYS = 90

# Optional LLM Key - can be passed via environment or .env
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

