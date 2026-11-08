"""
NLU and Intent / Entity Extraction Module for Project Udyam Digital.
Handles multilingual natural language extraction (English, Hindi, Hinglish)
for Indian MSME telecom & digital requirements.
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from app.modules.advisor.profile import CITY_BENCHMARK_PINCODES

HINDI_CITY_MAP: Dict[str, str] = {
    "इंदौर": "Indore",
    "इन्दौर": "Indore",
    "पुणे": "Pune",
    "जयपुर": "Jaipur",
    "भोपाल": "Bhopal",
    "रोहतक": "Rohtak",
    "नोएडा": "Noida",
    "मुंबई": "Mumbai",
    "बम्बई": "Mumbai",
    "दिल्ली": "Delhi",
    "नई दिल्ली": "New Delhi",
    "बेंगलुरु": "Bengaluru",
    "बैंगलोर": "Bengaluru",
    "चेन्नई": "Chennai",
    "हैदराबाद": "Hyderabad",
    "कोलकाता": "Kolkata",
    "अहमदाबाद": "Ahmedabad",
    "गुड़गांव": "Gurugram",
    "गुरुग्राम": "Gurugram",
    "फरीदाबाद": "Faridabad",
    "गाजियाबाद": "Ghaziabad",
    "लखनऊ": "Lucknow",
    "कानपुर": "Kanpur",
    "वाराणसी": "Varanasi",
    "पटना": "Patna",
    "सूरत": "Surat",
    "नागपुर": "Nagpur"
}

BUSINESS_TYPE_PATTERNS = [
    (r"\b(dental\s+clinic|dental|clinic|doctor|physician|dentist|hospital|healthcare|medical)\b", "clinic"),
    (r"\b(kirana|retail|store|grocery|general\s+store|shop|provision|bakery|dookan|dukan|दुकान|किराना)\b", "retail"),
    (r"\b(restaurant|cafe|dhaba|bistro|food\s+court|canteen|hotel|sweets|mithai)\b", "restaurant"),
    (r"\b(ca\s+firm|accounting|chartered\s+accountant|auditor|auditors|audit|legal|law\s+firm|advocate|consultancy|consulting|office)\b", "office"),
    (r"\b(tech\s+startup|software|it\s+firm|development\s+startup|startup|developer|agency|saas|fintech)\b", "startup"),
    (r"\b(factory|manufacturing|plant|workshop|warehouse|godown|karkhana|कारखाना)\b", "factory"),
    (r"\b(logistics|courier|transport|fleet|delivery)\b", "logistics"),
    (r"\b(school|coaching|institute|college|academy)\b", "education")
]

class NLUParser:
    """
    Extracts intents, business firmographics, and entities across English & Hindi.
    Does not invent default values; returns only explicitly detected entities.
    """

    def detect_intent(self, text: str, current_bundle: Optional[Dict[str, int]] = None) -> str:
        t = text.lower().strip()

        # 1. Downsell requests
        downsell_cues = [
            "sasta", "सस्ता", "सस्ते", "mehenga", "महंगा", "expensive", "cheaper",
            "too costly", "budget is low", "reduce price", "kam budget", "कम बजट",
            "kam daam", "low price", "affordable", "discount"
        ]
        if any(c in t for c in downsell_cues):
            return "downsell_request"

        # 2. Add-on removal
        remove_cues = ["remove ", "hata do", "hatao", "don't need ", "dont need ", "cancel ", "delete "]
        if any(c in t for c in remove_cues):
            return "remove_addon"

        # 3. Escalation / Human Agent requests
        escalation_cues = [
            "talk to agent", "talk to human", "speak to an executive", "executive callback",
            "call me", "customer care", "human support", "representative", "contact sales",
            "agent se baat", "executive se baat"
        ]
        if any(c in t for c in escalation_cues):
            return "escalation"

        # 4. Rural feasibility check
        rural_cues = ["village", "rural", "gaon", "gao", "देहात", "गाँव", "गांव", "gram panchayat", "dumra dehat"]
        taar_cues = ["taar nahi", "no wire", "no cable", "bina taar", "wireless"]
        if any(c in t for c in rural_cues) or any(c in t for c in taar_cues):
            return "rural_feasibility"

        # 5. Informational product / catalogue inquiries
        inquiry_cues = [
            "what plans do you have", "what are the other plans", "tell me about different plans",
            "show plans", "list plans", "what speeds", "speed options", "compare plans",
            "what is airfiber", "tell me about 1g", "what is ill", "pricing plans", "all plans"
        ]
        if any(c in t for c in inquiry_cues) and not any(k in t for k in ["recommend", "my clinic", "my shop", "for us"]):
            return "inquiry"

        # 6. General greetings
        if t in ["hi", "hello", "hey", "namaste", "नमस्ते", "pranam", "good morning", "good evening"]:
            return "greeting"

        # Default: could be clarification response or recommendation request
        return "recommendation"

    def extract_entities(self, text: str) -> Dict[str, Any]:
        entities: Dict[str, Any] = {}
        t_clean = text.strip()
        t_lower = t_clean.lower()

        # 1. 6-digit Pincode
        pin_match = re.search(r"\b([1-9][0-9]{5})\b", t_clean)
        if pin_match:
            entities["pincode"] = pin_match.group(1)

        # 2. City extraction (English & Hindi)
        # Check Hindi names first
        for h_city, eng_city in HINDI_CITY_MAP.items():
            if h_city in t_clean:
                entities["city"] = eng_city
                break
        # Check English benchmark names
        if "city" not in entities:
            for city_canonical in CITY_BENCHMARK_PINCODES.keys():
                pattern = rf"\b{re.escape(city_canonical.lower())}\b"
                if re.search(pattern, t_lower):
                    entities["city"] = city_canonical
                    break

        # 3. Business Type
        for pattern, b_type in BUSINESS_TYPE_PATTERNS:
            if re.search(pattern, t_lower):
                entities["business_type"] = b_type
                break

        # 4. Multi-site / Shop counts
        site_match = re.search(r"\b(\d+)\s*(shops|stores|branches|sites|locations|outlets|dukan|dookan|दुकानें|दुकान)\b", t_lower)
        if site_match:
            entities["num_sites"] = int(site_match.group(1))

        # Check distinct headcounts per site (e.g., "one has 10 employees and the other has 100")
        multi_headcounts = re.findall(r"(?:one|1st|first|shop\s*1)\s*(?:has|with)?\s*(\d+)\s*(?:employees|staff)?.*?(?:other|2nd|second|shop\s*2)\s*(?:has|with)?\s*(\d+)", t_lower)
        if multi_headcounts:
            hc1, hc2 = int(multi_headcounts[0][0]), int(multi_headcounts[0][1])
            entities["site_headcounts"] = [hc1, hc2]
            entities["employee_count"] = hc1 + hc2
            if "num_sites" not in entities:
                entities["num_sites"] = 2
        else:
            # 5. Single / Total Employee Count
            # English & Hindi patterns: "10 staff", "25 employees", "2 कर्मचारियों", "4 chairs"
            emp_match = re.search(r"\b(\d+)\s*(employees|employee|staff|workers|people|chairs|seats|auditors|log|kamgar|karmchari|karmchariyon|कर्मचारियों|कर्मचारी|स्टाफ)\b", t_lower)
            if emp_match:
                entities["employee_count"] = int(emp_match.group(1))
            else:
                # Check "with 1 helper"
                helper_match = re.search(r"\b(\d+)\s*helper\b", t_lower)
                if helper_match:
                    entities["employee_count"] = int(helper_match.group(1)) + 1

        # 6. GST Status
        gst_positive = [
            "yes we have gst", "have gst", "active gst", "with gst", "gstin hai",
            "gst registered", "registered gst", "gst number hai", "gst hai", "जीएसटी है"
        ]
        gst_negative = [
            "no gst", "without gst", "sole proprietorship", "non-gst", "non gst",
            "gst nahi", "gst nahi hai", "udyam only", "जीएसटी नहीं है"
        ]
        if any(k in t_lower for k in gst_positive):
            entities["has_gstin"] = True
        elif any(k in t_lower for k in gst_negative):
            entities["has_gstin"] = False

        # 7. Rural & Taar status
        rural_cues = ["village", "rural", "gaon", "gao", "देहात", "गाँव", "गांव", "gram panchayat", "dumra dehat"]
        if any(c in t_lower for c in rural_cues):
            entities["rural_location"] = True

        taar_negative = ["bina taar", "no wire", "taar nahi", "no cable", "wireless", "बिना तार"]
        taar_positive = ["taar hai", "wire hai", "cable is there", "fibre cable", "तार है"]
        if any(c in t_lower for c in taar_negative):
            entities["taar_present"] = False
        elif any(c in t_lower for c in taar_positive):
            entities["taar_present"] = True

        # 8. Add-on Removal Target (only if removal intent detected)
        remove_keywords = ["remove", "hata", "hatao", "delete", "hata do", "nahi chahiye", "cancel", "drop", "don't need", "dont need"]
        if any(w in t_lower for w in remove_keywords):
            if "soundbox" in t_lower or "pos" in t_lower or "upi" in t_lower:
                entities["remove_target"] = "P19"
            elif "backup" in t_lower:
                entities["remove_target"] = "P17"
            elif "cctv" in t_lower or "camera" in t_lower:
                entities["remove_target"] = "P23"
            elif "wifi" in t_lower or "guest" in t_lower:
                entities["remove_target"] = "P22"
            elif "email" in t_lower:
                entities["remove_target"] = "P16"
            elif "security" in t_lower or "antivirus" in t_lower or "endpoint" in t_lower:
                entities["remove_target"] = "P20"
            elif "p19" in t_lower:
                entities["remove_target"] = "P19"

        return entities
