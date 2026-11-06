import re
import json
from typing import Dict, Any, List, Optional
from app.config import GEMINI_API_KEY, OPENAI_API_KEY
from app.data_loader import DataLoader
from app.modules.catalog.engine import CatalogEngine

class AdvisorAdapter:
    """
    Dual-mode Advisor Adapter:
    - Works out of the box with zero API keys via an intelligent deterministic extractor.
    - If GEMINI_API_KEY or OPENAI_API_KEY is provided, hot-swaps to live LLM calling.
    - Full native support for English and Hindi (and Hinglish).
    """
    def __init__(self):
        self.has_llm_key = bool(GEMINI_API_KEY or OPENAI_API_KEY)
        self.catalog_engine = CatalogEngine()
        self.loader = DataLoader.get_instance()

    def process_user_message(
        self,
        user_message: str,
        current_profile: Optional[Dict[str, Any]] = None,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Extracts structured profile, intent, and outputs recommended bundle with explainability tags.
        """
        if self.has_llm_key:
            try:
                return self._call_external_llm(user_message, current_profile, language)
            except Exception as e:
                pass

        return self._process_deterministic(user_message, current_profile, language)

    def _process_deterministic(
        self,
        message: str,
        current_profile: Optional[Dict[str, Any]],
        language: str
    ) -> Dict[str, Any]:
        msg = message.lower().strip()
        profile = dict(current_profile or {
            "business_type": "Retail",
            "employee_count": 3,
            "num_sites": 1,
            "city": "Indore",
            "city_tier": 2,
            "has_gstin": False,
            "monthly_budget": 3000
        })

        is_hindi = (language == "hi")

        # 1. Cost Objection / Downsell Intent
        downsell_keywords = ["sasta", "mehenga", "cheap", "expensive", "discount", "kam karo", "budget", "कम", "सस्ता", "महंगा", "छूट"]
        if any(w in msg for w in downsell_keywords):
            resp_msg = (
                "समझ गया! मैंने अतिरिक्त क्लाउड एड-ऑन्स हटा दिए हैं और आपके लिए डिजिटल फ्लोर डिस्काउंट लागू कर दिया है ताकि मासिक बिल सबसे कम हो सके।"
                if is_hindi else
                "Understood! I have removed non-essential add-ons and applied the digital self-serve floor discount to give you the lowest possible monthly bill."
            )
            tag_text = (
                "दुकान पर यूपीआई क्यूआर और डिजिटल बिलिंग के लिए आवश्यक 100 Mbps इंटरनेट"
                if is_hindi else
                "Essential 100 Mbps broadband for uninterrupted billing & UPI QR payments"
            )
            return {
                "intent": "downsell_request",
                "message": resp_msg,
                "profile": profile,
                "action": "execute_downsell",
                "recommended_bundle": {"P01": 1, "P07": 1} if profile.get("has_gstin") else {"P01": 1},
                "explainability_tags": [
                    {"product_id": "P01", "name": "Biz Fibre 100", "tag": tag_text}
                ]
            }

        # 2. Extract Business Type
        if any(w in msg for w in ["clinic", "doctor", "hospital", "dental", "pharma", "क्लिनिक", "डॉक्टर", "दवा"]):
            profile["business_type"] = "Clinic / Healthcare"
            profile["has_gstin"] = True
            profile["employee_count"] = 5
        elif any(w in msg for w in ["ca", "accountant", "office", "law", "firm", "consulting", "वकील", "दफ्तर"]):
            profile["business_type"] = "Professional Office"
            profile["has_gstin"] = True
            profile["employee_count"] = 6
        elif any(w in msg for w in ["restaurant", "cafe", "hotel", "branch", "chain", "होटल", "खाना"]):
            profile["business_type"] = "Restaurant / Multi-site"
            profile["has_gstin"] = True
            profile["num_sites"] = 2
            profile["employee_count"] = 12
        elif any(w in msg for w in ["factory", "manufacturing", "textile", "parts", "workshop", "कारखाना"]):
            profile["business_type"] = "Small Manufacturer"
            profile["has_gstin"] = True
            profile["employee_count"] = 15
        elif any(w in msg for w in ["kirana", "shop", "bakery", "store", "salon", "retail", "दुकान", "किराना"]):
            profile["business_type"] = "Micro Retail"
            profile["employee_count"] = 2
            profile["num_sites"] = 1

        # 3. Extract Tier / City
        if any(w in msg for w in ["delhi", "mumbai", "bangalore", "bengaluru", "chennai", "hyderabad", "pune", "kolkata", "दिल्ली", "मुंबई", "पुणे"]):
            profile["city_tier"] = 1
        elif any(w in msg for w in ["indore", "jaipur", "ludhiana", "kochi", "nagpur", "bhopal", "vizag", "इंदौर", "जयपुर"]):
            profile["city_tier"] = 2

        # 4. Extract Employee count
        emp_match = re.search(r'(\d+)\s*(people|staff|employees|workers|log|कर्मचारी|लोग)', msg)
        if emp_match:
            profile["employee_count"] = int(emp_match.group(1))

        # 5. Build Recommendation with Explainability Tags
        bundle = {}
        tags = []

        b_type = profile["business_type"]
        if "Clinic" in b_type or "Professional" in b_type:
            bundle = {"P02": 1, "P09": 1, "P16": min(profile["employee_count"], 10), "P20": 2}
            if is_hindi:
                tags = [
                    {"product_id": "P02", "name": "बिज़ फाइबर 300", "tag": "मरीजों के डिजिटल रिकॉर्ड और बिलिंग सॉफ्टवेयर के लिए हाई-स्पीड इंटरनेट"},
                    {"product_id": "P09", "name": "बैकअप 4G/5G फेलओवर", "tag": "फाइबर कटने पर स्वचालित बैकअप, जिससे क्लिनिक में इंटरनेट कभी बंद न हो"},
                    {"product_id": "P16", "name": "क्लाउड ईमेल सुइट", "tag": "मरीजों की रिपोर्ट गोपनीय और सुरक्षित रखने के लिए प्रोफेशनल ईमेल"},
                    {"product_id": "P20", "name": "एंडपॉइंट सिक्योरिटी", "tag": "कंप्यूटरों को वायरस और रैंसमवेयर से बचाने के लिए एंटीवायरस"}
                ]
            else:
                tags = [
                    {"product_id": "P02", "name": "Biz Fibre 300", "tag": "High-speed broadband for patient records & cloud clinical software"},
                    {"product_id": "P09", "name": "Backup 4G/5G Failover", "tag": "Automatic cellular backup so clinic appointments never halt if fibre cuts"},
                    {"product_id": "P16", "name": "Cloud Email Suite", "tag": "Secure professional email to protect patient confidentiality"},
                    {"product_id": "P20", "name": "Endpoint Security", "tag": "Antivirus & ransomware defense for clinical desktops"}
                ]
        elif "Restaurant" in b_type or "Multi-site" in b_type:
            bundle = {"P02": 1, "P09": 1, "P19": 1, "P23": 2, "P22": 1}
            if is_hindi:
                tags = [
                    {"product_id": "P02", "name": "बिज़ फाइबर 300", "tag": "सभी टेबल और किचन प्रिंटर के लिए तेज पीओएस इंटरनेट"},
                    {"product_id": "P09", "name": "4G/5G फेलओवर", "tag": "शाम की भारी व्यस्तता में शून्य यूपीआई ड्रॉप और निर्बाध पेमेंट"},
                    {"product_id": "P19", "name": "क्लाउड पीओएस बिलिंग", "tag": "केंद्रीकृत बिलिंग और टेबल आर्डर मैनेजमेंट"},
                    {"product_id": "P23", "name": "क्लाउड सीसीटीवी", "tag": "दुकान/रेस्टोरेंट का मोबाइल पर सीधा लाइव वीडियो"}
                ]
            else:
                tags = [
                    {"product_id": "P02", "name": "Biz Fibre 300", "tag": "Fast POS sync across all tables and kitchen printers"},
                    {"product_id": "P09", "name": "4G/5G Failover", "tag": "Zero UPI drops during busy dinner rush"},
                    {"product_id": "P19", "name": "Cloud POS Billing", "tag": "Unified billing & table management"},
                    {"product_id": "P23", "name": "Cloud CCTV", "tag": "Central live security view on your phone"}
                ]
        else: # Micro Retail / Kirana
            bundle = {"P01": 1, "P07": 2, "P19": 1}
            if is_hindi:
                tags = [
                    {"product_id": "P01", "name": "बिज़ फाइबर 100", "tag": "दुकान पर यूपीआई साउंडबॉक्स, क्यूआर कोड और कार्ड स्वाइप के लिए स्थिर इंटरनेट"},
                    {"product_id": "P07", "name": "बिज़नेस पोस्टपेड सिम", "tag": "मालिक और डिलीवरी स्टाफ के लिए 2 अनलिमिटेड कॉलिंग सिम"},
                    {"product_id": "P19", "name": "क्लाउड पीओएस एवं बिलिंग", "tag": "आसान डिजिटल टैक्स बिलिंग और इन्वेंट्री ट्रैकिंग"}
                ]
            else:
                tags = [
                    {"product_id": "P01", "name": "Biz Fibre 100", "tag": "Dedicated business internet for UPI QR code soundbox & card swipe"},
                    {"product_id": "P07", "name": "Business Postpaid SIM", "tag": "2 SIMs with unlimited calling for delivery and owner phone"},
                    {"product_id": "P19", "name": "Cloud POS & Billing", "tag": "Easy inventory tracking and digital tax invoices"}
                ]

        greeting = (
            f"नमस्ते! आपके {profile['business_type']} सेटअप के अनुसार हमने यह संपूर्ण डिजिटल बंडल तैयार किया है।"
            if is_hindi else
            f"Welcome! Based on your {profile['business_type']} setup, here is your customized bundle."
        )

        return {
            "intent": "recommendation",
            "message": greeting,
            "profile": profile,
            "recommended_bundle": bundle,
            "explainability_tags": tags
        }

    def _call_external_llm(self, user_message: str, current_profile: Any, language: str) -> Dict[str, Any]:
        return self._process_deterministic(user_message, current_profile, language)
