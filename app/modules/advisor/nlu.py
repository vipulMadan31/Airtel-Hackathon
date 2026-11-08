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
    "नागपुर": "Nagpur",
    "नागपूर": "Nagpur",
    "नाशिक": "Nashik",
    "औरंगाबाद": "Aurangabad",
    "छत्रपती संभाजीनगर": "Aurangabad",
    "कोल्हापूर": "Kolhapur",
    "ठाणे": "Thane",
    "ठाण्यात": "Thane",
    "पुणे": "Pune",
    "पुण्यात": "Pune",
    "पुण्यामध्ये": "Pune",
    "मुंबई": "Mumbai",
    "मुंबईत": "Mumbai",
    "इंदूर": "Indore"
}

BUSINESS_TYPE_PATTERNS = [
    (r"\b(dental\s+clinic|dental|clinic|doctor|physician|dentist|hospital|healthcare|medical|दवाखाना|क्लिनिक)\b", "clinic"),
    (r"\b(kirana|retail|store|grocery|general\s+store|shop|provision|bakery|dookan|dukan|दुकान|किराना|किराणा|स्टोअर)\b", "retail"),
    (r"\b(salon|beauty\s+parlour|parlor|spa|सैलून|सलून|पार्लर)\b", "salon"),
    (r"\b(pharmacy|chemist|medical\s+store|druggist|फार्मसी|औषध)\b", "pharmacy"),
    (r"\b(restaurant|cafe|dhaba|bistro|food\s+court|canteen|hotel|sweets|mithai|हॉटेल|कॅफे|धाबा)\b", "restaurant"),
    (r"\b(ca\s+firm|accounting|chartered\s+accountant|auditor|auditors|audit|legal|law\s+firm|advocate|consultancy|consulting|office|कार्यालय)\b", "office"),
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
            "kam daam", "low price", "affordable", "discount", "स्वस्त", "कमी करा", "कमी", "जास्त किंमत"
        ]
        if any(c in t for c in downsell_cues):
            return "downsell_request"

        # 2. Add-on removal
        remove_cues = ["remove ", "hata do", "hatao", "don't need ", "dont need ", "cancel ", "delete ", "काढा", "काढून टाका", "नको", "हटवा", "काढून घ्या"]
        has_remove_cue = any(c in t for c in remove_cues)
        if has_remove_cue:
            # If the user is currently completing mandatory discovery inputs (e.g., stating employee count, GST, city, business type)
            # or if no active bundle has been generated yet, this is discovery preference (e.g. "dont need cctv"), NOT an active cart modification.
            has_active_bundle = bool(current_bundle and any(current_bundle.values()))
            has_discovery_content = bool(
                re.search(r"\b(\d+)\s*(employees|employee|staff|workers|people|chairs|seats|shops|stores)\b", t) or
                re.search(r"\b(have\s*(a\s+)?gst|with\s*(a\s+)?gst|active\s*gst|gstin|non-?gst|sole\s*proprietorship)\b", t) or
                re.search(r"\b(shop|clinic|office|store|firm|hospital|restaurant)\b", t)
            )
            if has_active_bundle and not has_discovery_content:
                return "remove_addon"
            elif not has_active_bundle and not has_discovery_content:
                return "remove_addon"

        # 3. Escalation / Human Agent requests
        escalation_cues = [
            "talk to agent", "talk to human", "speak to an executive", "executive callback",
            "call me", "customer care", "human support", "representative", "contact sales",
            "agent se baat", "executive se baat", "एजंटशी बोला", "कॉल करा", "मदत हवी"
        ]
        if any(c in t for c in escalation_cues):
            return "escalation"

        # 4. Rural feasibility check
        rural_cues = ["village", "rural", "gaon", "gao", "देहात", "गाँव", "गांव", "gram panchayat", "dumra dehat", "गाव", "खेडेगाव"]
        taar_cues = ["taar nahi", "no wire", "no cable", "bina taar", "wireless", "वायर नाही", "केबल नाही"]
        if any(c in t for c in rural_cues) or any(c in t for c in taar_cues):
            return "rural_feasibility"

        # 5. Informational product / catalogue inquiries
        inquiry_cues = [
            "what plans do you have", "what are the other plans", "tell me about different plans",
            "show plans", "list plans", "what speeds", "speed options", "compare plans",
            "what is airfiber", "tell me about 1g", "what is ill", "pricing plans", "all plans",
            "प्लॅन दाखवा", "कोणते प्लॅन आहेत"
        ]
        if any(c in t for c in inquiry_cues) and not any(k in t for k in ["recommend", "my clinic", "my shop", "for us"]):
            return "inquiry"

        # 6. General greetings
        if t in ["hi", "hello", "hey", "namaste", "नमस्ते", "नमस्कार", "pranam", "good morning", "good evening", "शुभ प्रभात", "शुभ सकाळ"]:
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
            emp_match = re.search(r"(?:^|[^\w\u0900-\u097F])(\d+)\s*(?:employees|employee|staff|workers|people|chairs|seats|auditors|log|kamgar|karmchari|karmchariyon|कर्मचारियों|कर्मचारी|स्टाफ|कामगार)(?:$|[^\w\u0900-\u097F])", t_lower)
            if emp_match:
                entities["employee_count"] = int(emp_match.group(1))
            else:
                # Check "with 1 helper"
                helper_match = re.search(r"\b(\d+)\s*helper\b", t_lower)
                if helper_match:
                    entities["employee_count"] = int(helper_match.group(1)) + 1

        # 6. GST Status
        gst_negative_patterns = [
            r"\b(dont|don't|do not|no)\s+(have\s+)?(a\s+)?gst\b",
            r"\b(without|non-?gst|udyam only)\b",
            r"\bsole\s*proprietorship\b",
            r"gst\s*nahi",
            r"जीएसटी\s*नहीं"
        ]
        gst_positive_patterns = [
            r"\b(yes\s*(we\s*)?have\s*(a\s+)?gst|have\s*(a\s+)?gst|with\s*(a\s+)?gst|active\s*gst|gstin\s*hai|gst\s*registered|registered\s*gst|gst\s*number\s*(hai)?|gst\s*hai|yes\s*gst|got\s*(a\s+)?gst|gst\s*available|gst\s*is\s*there)\b",
            r"जीएसटी\s*है"
        ]

        if any(re.search(p, t_lower) for p in gst_negative_patterns):
            entities["has_gstin"] = False
        elif any(re.search(p, t_lower) for p in gst_positive_patterns):
            entities["has_gstin"] = True

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
            target_pid = None
            if any(k in t_lower for k in ["security", "antivirus", "endpoint", "p20"]):
                target_pid = "P20"
            elif any(k in t_lower for k in ["soundbox", "pos", "upi", "qr", "p19"]):
                target_pid = "P19"
            elif any(k in t_lower for k in ["backup", "tally", "p17"]):
                target_pid = "P17"
            elif any(k in t_lower for k in ["cctv", "camera", "p23"]):
                target_pid = "P23"
            elif any(k in t_lower for k in ["guest wifi", "guest network", "p22"]):
                target_pid = "P22"
            elif any(k in t_lower for k in ["email", "workspace", "m365", "mail", "p16"]):
                target_pid = "P16"
            elif any(k in t_lower for k in ["static ip", "public ip", "ip", "p11"]):
                target_pid = "P11"
            elif any(k in t_lower for k in ["firewall", "p21"]):
                target_pid = "P21"
            elif any(k in t_lower for k in ["sd-wan", "sdwan", "p10"]):
                target_pid = "P10"
            elif any(k in t_lower for k in ["toll", "1800", "p13"]):
                target_pid = "P13"
            elif any(k in t_lower for k in ["sms", "p14"]):
                target_pid = "P14"
            elif any(k in t_lower for k in ["whatsapp", "p15"]):
                target_pid = "P15"

            if target_pid:
                entities["remove_target"] = target_pid
                entities["removed_addons"] = [target_pid]

        return entities
