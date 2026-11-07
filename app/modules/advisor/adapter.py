import re
import json
from typing import Dict, Any, List, Optional
from app.config import GEMINI_API_KEY, OPENAI_API_KEY
from app.data_loader import DataLoader
from app.modules.catalog.engine import CatalogEngine

CITY_BENCHMARK_PINCODES: Dict[str, str] = {
    "Delhi": "110001",
    "Delhi NCR": "110001",
    "New Delhi": "110001",
    "Mumbai": "400001",
    "Bangalore": "560001",
    "Bengaluru": "560001",
    "Chennai": "600001",
    "Hyderabad": "500001",
    "Pune": "411001",
    "Kolkata": "700001",
    "Ahmedabad": "380001",
    "Noida": "201301",
    "Gurgaon": "122001",
    "Gurugram": "122001",
    "Indore": "452001",
    "Bhopal": "462001",
    "Jaipur": "302001",
    "Ludhiana": "141001",
    "Kochi": "682001",
    "Nagpur": "440001",
    "Visakhapatnam": "530001",
    "Patna": "800001",
    "Surat": "395001",
    "Lucknow": "226001",
    "Chandigarh": "160001",
    "Rohtak": "124001",
    "Faridabad": "121001",
    "Ghaziabad": "201001",
    "Kanpur": "208001",
    "Varanasi": "221001",
    "Agra": "282001",
    "Amritsar": "143001",
    "Dehradun": "248001",
    "Mysore": "570001",
    "Coimbatore": "641001",
    "Vadodara": "390001",
    "Rajkot": "360001",
    "Meerut": "250001",
    "Jalandhar": "144001",
    "Raipur": "492001",
    "Jabalpur": "482001",
    "Gwalior": "474001",
    "Nashik": "422001",
    "Aurangabad": "431001",
    "Madurai": "625001",
    "Mangalore": "575001",
    "Thiruvananthapuram": "695001",
    "Kozhikode": "673001"
}

PINCODE_PREFIX_MAP: Dict[str, tuple] = {
    "110": ("Delhi", 1),
    "121": ("Faridabad", 2),
    "122": ("Gurgaon", 1),
    "124": ("Rohtak", 3),
    "141": ("Ludhiana", 2),
    "143": ("Amritsar", 2),
    "144": ("Jalandhar", 2),
    "160": ("Chandigarh", 2),
    "2010": ("Ghaziabad", 2),
    "2013": ("Noida", 1),
    "208": ("Kanpur", 2),
    "221": ("Varanasi", 2),
    "226": ("Lucknow", 2),
    "248": ("Dehradun", 2),
    "250": ("Meerut", 2),
    "282": ("Agra", 2),
    "302": ("Jaipur", 2),
    "380": ("Ahmedabad", 1),
    "390": ("Vadodara", 2),
    "395": ("Surat", 2),
    "400": ("Mumbai", 1),
    "411": ("Pune", 1),
    "422": ("Nashik", 2),
    "431": ("Aurangabad", 2),
    "440": ("Nagpur", 2),
    "452": ("Indore", 2),
    "462": ("Bhopal", 2),
    "474": ("Gwalior", 2),
    "482": ("Jabalpur", 2),
    "492": ("Raipur", 2),
    "500": ("Hyderabad", 1),
    "530": ("Visakhapatnam", 2),
    "560": ("Bengaluru", 1),
    "570": ("Mysore", 2),
    "575": ("Mangalore", 2),
    "600": ("Chennai", 1),
    "625": ("Madurai", 2),
    "641": ("Coimbatore", 2),
    "673": ("Kozhikode", 2),
    "682": ("Kochi", 2),
    "695": ("Thiruvananthapuram", 2),
    "700": ("Kolkata", 1),
    "800": ("Patna", 2),
}

class AdvisorAdapter:
    """
    Dual-mode Advisor Adapter:
    - Works out of the box with zero API keys via an intelligent deterministic extractor.
    - If GEMINI_API_KEY or OPENAI_API_KEY is provided, hot-swaps to live LLM calling.
    - Full native support for English, Hindi, and Hinglish.
    - Strict Progressive Clarification (Zero Assumption of City or Employee Scale).
    - Strict 5-Dimensional Feasibility & Boundary Guardrails (GST, City Tier, Headcount, Sites, Speeds).
    """
    def __init__(self):
        self.catalog_engine = CatalogEngine()
        self.loader = DataLoader.get_instance()

    @property
    def has_llm_key(self) -> bool:
        from app.config import GEMINI_API_KEY, OPENAI_API_KEY
        return bool(GEMINI_API_KEY or OPENAI_API_KEY)

    def process_user_message(
        self,
        user_message: str,
        current_profile: Optional[Dict[str, Any]] = None,
        language: str = "en",
        history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Extracts structured profile, intent, and outputs recommended bundle with explainability tags.
        """
        if self.has_llm_key:
            try:
                result = self._call_external_llm(user_message, current_profile, language, history=history)
                if result:
                    return result
            except Exception:
                pass

        return self._process_deterministic(user_message, current_profile, language, history=history)

    def _process_deterministic(
        self,
        message: str,
        current_profile: Optional[Dict[str, Any]],
        language: str,
        history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        msg = message.lower().strip()
        profile = dict(current_profile or {})
        
        # Ensure profile keys exist without hardcoding assumptions
        profile.setdefault("business_type", None)
        profile.setdefault("employee_count", None)
        profile.setdefault("num_sites", 1)
        profile.setdefault("city", None)
        profile.setdefault("city_tier", None)
        profile.setdefault("pincode", None)
        profile.setdefault("has_gstin", None)
        profile.setdefault("monthly_budget", 3000)

        is_hindi = (language == "hi")

        # 0a. Check explicit 6-digit postal pincode in user message
        pin_match = re.search(r'\b([1-9][0-9]{5})\b', msg)
        if pin_match:
            explicit_pin = pin_match.group(1)
            profile["pincode"] = explicit_pin
            # Infer city and tier from pincode prefix if not already known
            if not profile.get("city"):
                for pfx, (cname, ctier) in PINCODE_PREFIX_MAP.items():
                    if explicit_pin.startswith(pfx):
                        profile["city"] = cname
                        profile["city_tier"] = ctier
                        break

        # 0b. Extract Location / City from user message if mentioned
        city_tier_map = {
            "delhi": ("Delhi", 1), "mumbai": ("Mumbai", 1), "bangalore": ("Bangalore", 1),
            "bengaluru": ("Bengaluru", 1), "chennai": ("Chennai", 1), "hyderabad": ("Hyderabad", 1),
            "pune": ("Pune", 1), "kolkata": ("Kolkata", 1),
            "indore": ("Indore", 2), "jaipur": ("Jaipur", 2), "ludhiana": ("Ludhiana", 2),
            "kochi": ("Kochi", 2), "nagpur": ("Nagpur", 2), "bhopal": ("Bhopal", 2),
            "vizag": ("Visakhapatnam", 2), "patna": ("Patna", 2), "surat": ("Surat", 2),
            "lucknow": ("Lucknow", 2), "chandigarh": ("Chandigarh", 2), "delhi ncr": ("Delhi NCR", 1),
            "rohtak": ("Rohtak", 3), "gurgaon": ("Gurgaon", 1), "gurugram": ("Gurugram", 1),
            "noida": ("Noida", 1), "faridabad": ("Faridabad", 2), "ghaziabad": ("Ghaziabad", 2),
            "ahmedabad": ("Ahmedabad", 1), "kanpur": ("Kanpur", 2), "varanasi": ("Varanasi", 2),
            "agra": ("Agra", 2), "amritsar": ("Amritsar", 2), "dehradun": ("Dehradun", 2),
            "mysore": ("Mysore", 2), "coimbatore": ("Coimbatore", 2), "vadodara": ("Vadodara", 2),
            "rajkot": ("Rajkot", 2), "meerut": ("Meerut", 2), "jalandhar": ("Jalandhar", 2),
            "raipur": ("Raipur", 2), "jabalpur": ("Jabalpur", 2), "gwalior": ("Gwalior", 2),
            "nashik": ("Nashik", 2), "aurangabad": ("Aurangabad", 2), "madurai": ("Madurai", 2),
            "mangalore": ("Mangalore", 2), "trivandrum": ("Thiruvananthapuram", 2), "calicut": ("Kozhikode", 2),
            # Devanagari Hindi mappings
            "इंदौर": ("Indore", 2), "रोहतक": ("Rohtak", 3), "पुणे": ("Pune", 1),
            "जयपुर": ("Jaipur", 2), "भोपाल": ("Bhopal", 2), "दिल्ली": ("Delhi", 1),
            "मुंबई": ("Mumbai", 1), "नोएडा": ("Noida", 1), "बेंगलुरु": ("Bengaluru", 1),
            "बैंगलोर": ("Bengaluru", 1), "चेन्नई": ("Chennai", 1), "कोलकाता": ("Kolkata", 1),
            "हैदराबाद": ("Hyderabad", 1), "अहमदाबाद": ("Ahmedabad", 1), "लखनऊ": ("Lucknow", 2),
            "कानपुर": ("Kanpur", 2), "लुधियाना": ("Ludhiana", 2), "कोच्चि": ("Kochi", 2),
            "चंडीगढ़": ("Chandigarh", 2), "गुड़गांव": ("Gurgaon", 1), "गुरुग्राम": ("Gurugram", 1),
            "नागपुर": ("Nagpur", 2), "पटना": ("Patna", 2), "सूरत": ("Surat", 2),
            "वाराणसी": ("Varanasi", 2), "आगरा": ("Agra", 2), "अमृतसर": ("Amritsar", 2),
            "देहरादून": ("Dehradun", 2), "गाजियाबाद": ("Ghaziabad", 2), "फरीदाबाद": ("Faridabad", 2)
        }
        for k, (cname, ctier) in city_tier_map.items():
            if k in msg:
                profile["city"] = cname
                profile["city_tier"] = ctier
                # If explicit pincode was not entered, sync with benchmark city pincode
                if not profile.get("pincode") and cname in CITY_BENCHMARK_PINCODES:
                    profile["pincode"] = CITY_BENCHMARK_PINCODES[cname]
                break

        # Fallback sync: if city is known but pincode is still missing
        if profile.get("city") and not profile.get("pincode"):
            profile["pincode"] = CITY_BENCHMARK_PINCODES.get(profile["city"], "452001")

        # Extract Employee / device / scale count if mentioned
        emp_match = re.search(r'(\d+)\s*(people|staff|employees|workers|log|devices|pc|systems|chairs|beds|doctors|seats|users|counters|कर्मचारी|लोग)', msg)
        if emp_match:
            profile["employee_count"] = int(emp_match.group(1))

        # 0b. Village / Rural / Outskirts Infrastructure Feasibility Check (Biz Fibre vs Biz 5G AirFiber)
        rural_keywords = ["गांव", "देहात", "गाँव", "gram", "village", "rural", "kasba", "dehat", "panchayat", "basti", "outskirts", "dumra dehat", "dumra"]
        no_wire_keywords = [
            "no fiber", "no cable", "no wire", "wire nahi", "cable nahi", "taar nahi", "tar nahi", 
            "bina taar", "bina wire", "khamba nahi", "pole nahi", "airfiber", "wireless", "bina tar", "bina wire wala",
            "तार नहीं", "बिना तार", "केबल नहीं", "खंभा नहीं", "एयरफाइबर", "वायरलेस", "तार नहीं आई", "तार नहीं है", "केबल नहीं है",
            "5g airfiber", "air fiber", "पहला", "1st", "option 1"
        ]
        has_wire_keywords = [
            "fiber hai", "wire hai", "cable hai", "taar hai", "tar hai", "line aayi", "cable aayi",
            "तार है", "केबल है", "फाइबर है", "तार आई", "लाइन है", "दूसरा", "2nd", "option 2",
            "केबल आई", "तार पहुंची", "केबल पहुंची", "फाइबर वाला", "केबल वाला", "तार वाला", "फाइबर लगा", "केबल लगा"
        ]

        is_rural_mention = any(w in msg for w in rural_keywords) or profile.get("is_rural")
        if is_rural_mention:
            profile["is_rural"] = True
            if any(w in msg for w in no_wire_keywords):
                profile["prefers_airfiber"] = True
                resp_msg = (
                    "चूंकि आपके गांव में ऑप्टिकल फाइबर केबल नहीं है, आपके लिए सबसे उत्तम समाधान 'Biz 5G AirFiber 100' (₹899/माह) है। यह 100 Mbps का हाई-स्पीड वायरलेस वाई-फाई है जिसमें तार खींचने या खंभे की कोई जरूरत नहीं है—बस प्लग इन करें और तुरंत चालू! साथ ही दुकान पर डिजिटल पेमेंट्स व आवाज अलर्ट के लिए 'Cloud POS & UPI Soundbox' (₹599/माह) शामिल है। ₹2,500 का इंस्टॉलेशन शुल्क पूरी तरह माफ है।"
                    if is_hindi else
                    "Since physical optical fibre cables have not reached your village, the ideal solution is 'Biz 5G AirFiber 100' (@ ₹899/mo). It provides 100 Mbps high-speed wireless plug-and-play Wi-Fi with zero civil drilling or wire-pulling. We have included Cloud POS & UPI Soundbox (@ ₹599/mo) for instant payment voice alerts. The ₹2,500 setup fee is 100% waived."
                )
                tag_text = (
                    "ग्रामीण व देहात क्षेत्र के लिए बिना तार वाला 100 Mbps वायरलेस 5G AirFiber"
                    if is_hindi else
                    "Zero-wire 100 Mbps plug-and-play 5G AirFiber for rural and village locations"
                )
                return {
                    "intent": "recommendation",
                    "message": resp_msg,
                    "profile": profile,
                    "recommended_bundle": {"P04": 1, "P19": 1},
                    "explainability_tags": [
                        {"product_id": "P04", "name": "Biz 5G AirFiber 100", "tag": tag_text},
                        {"product_id": "P19", "name": "Cloud POS & UPI Soundbox", "tag": "दुकान पर यूपीआई पेमेंट साउंडबॉक्स व बिलिंग" if is_hindi else "UPI QR voice alert soundbox for shop"}
                    ]
                }
            elif any(w in msg for w in has_wire_keywords) or profile.get("fiber_confirmed"):
                profile["fiber_confirmed"] = True
                resp_msg = (
                    "बहुत बढ़िया! चूंकि आपकी बाजार/दुकान तक एयरटेल फाइबर की केबल उपलब्ध है, आपकी दुकान के लिए 'Biz Fibre 100' (₹999/माह) सबसे उपयुक्त है। यह 100 Mbps का अल्ट्रा-फास्ट ऑप्टिकल फाइबर ब्रॉडबैंड है जो फोन, वाई-फाई और निर्बाध बिलिंग सुनिश्चित करेगा। साथ ही दुकान पर तुरंत ऑडियो पेमेंट अलर्ट के लिए 'Cloud POS & UPI Soundbox' (₹599/माह) शामिल है। ₹2,500 का इंस्टॉलेशन शुल्क पूरी तरह माफ है।"
                    if is_hindi else
                    "Great! Since optical fiber cable is available at your market, the best solution for your shop is 'Biz Fibre 100' (@ ₹999/mo). This 100 Mbps optical fibre connection guarantees uninterrupted Wi-Fi, billing, and UPI transactions across your devices. We have included Cloud POS & UPI Soundbox (@ ₹599/mo) for instant payment voice alerts. The ₹2,500 setup fee is 100% waived."
                )
                tag_text = (
                    "दुकान पर वाई-फाई और यूपीआई बिलिंग के लिए 100 Mbps ऑप्टिकल फाइबर ब्रॉडबैंड"
                    if is_hindi else
                    "100 Mbps optical fibre for shop Wi-Fi and UPI billing"
                )
                return {
                    "intent": "recommendation",
                    "message": resp_msg,
                    "profile": profile,
                    "recommended_bundle": {"P01": 1, "P19": 1},
                    "explainability_tags": [
                        {"product_id": "P01", "name": "Biz Fibre 100", "tag": tag_text},
                        {"product_id": "P19", "name": "Cloud POS & UPI Soundbox", "tag": "दुकान पर यूपीआई पेमेंट साउंडबॉक्स व बिलिंग" if is_hindi else "UPI QR voice alert soundbox for shop"}
                    ]
                }
            elif not any(w in msg for w in has_wire_keywords) and not profile.get("fiber_confirmed"):
                resp_msg = (
                    "नमस्ते! गांव/देहात क्षेत्र में आपकी दुकान के लिए Airtel Business में दो बेहतरीन विकल्प हैं:\n\n"
                    "1️⃣ **Biz 5G AirFiber 100 (₹899/माह):** बिना किसी तार (केबल) वाला प्लग-एंड-प्ले वायरलेस 5G वाई-फाई (तुरंत चालू, बिना तार खींचे)।\n"
                    "2️⃣ **Biz Fibre 100 (₹999/माह):** अगर आपके बाजार/गली तक एयरटेल की ऑप्टिकल फाइबर केबल की तार आई हुई है।\n\n"
                    "क्या आपकी दुकान तक एयरटेल फाइबर की तार/केबल पहुंची हुई है, या आप बिना तार वाला 5G AirFiber लगवाना चाहेंगे?"
                    if is_hindi else
                    "Welcome! For shops in village and rural locations, Airtel Business offers two great solutions:\n\n"
                    "1️⃣ **Biz 5G AirFiber 100 (₹899/mo):** Wireless plug-and-play 100 Mbps Wi-Fi (zero wire-pulling or poles, instant setup).\n"
                    "2️⃣ **Biz Fibre 100 (₹999/mo):** Optical wireline broadband, if physical fiber cables are available in your market.\n\n"
                    "Does your market have physical Airtel optical fiber cable installed, or would you prefer the wireless plug-and-play 5G AirFiber?"
                )
                return {
                    "intent": "clarification",
                    "message": resp_msg,
                    "profile": profile,
                    "recommended_bundle": None,
                    "explainability_tags": []
                }

        # 0b. Village / Rural / Outskirts Infrastructure Feasibility Check (Biz Fibre vs Biz 5G AirFiber)
        rural_keywords = ["गांव", "देहात", "गाँव", "gram", "village", "rural", "kasba", "dehat", "panchayat", "basti", "outskirts", "dumra dehat", "dumra"]
        no_wire_keywords = [
            "no fiber", "no cable", "no wire", "wire nahi", "cable nahi", "taar nahi", "tar nahi", 
            "bina taar", "bina wire", "khamba nahi", "pole nahi", "airfiber", "wireless", "bina tar", "bina wire wala",
            "तार नहीं", "बिना तार", "केबल नहीं", "खंभा नहीं", "एयरफाइबर", "वायरलेस", "तार नहीं आई", "तार नहीं है", "केबल नहीं है",
            "5g airfiber", "air fiber", "पहला", "1st", "option 1"
        ]
        has_wire_keywords = [
            "fiber hai", "wire hai", "cable hai", "taar hai", "tar hai", "line aayi", "cable aayi",
            "तार है", "केबल है", "फाइबर है", "तार आई", "लाइन है", "दूसरा", "2nd", "option 2",
            "केबल आई", "तार पहुंची", "केबल पहुंची", "फाइबर वाला", "केबल वाला", "तार वाला", "फाइबर लगा", "केबल लगा"
        ]

        is_rural_mention = any(w in msg for w in rural_keywords) or profile.get("is_rural")
        if is_rural_mention:
            profile["is_rural"] = True
            if any(w in msg for w in no_wire_keywords):
                profile["prefers_airfiber"] = True
                resp_msg = (
                    "चूंकि आपके गांव में ऑप्टिकल फाइबर केबल नहीं है, आपके लिए सबसे उत्तम समाधान 'Biz 5G AirFiber 100' (₹899/माह) है। यह 100 Mbps का हाई-स्पीड वायरलेस वाई-फाई है जिसमें तार खींचने या खंभे की कोई जरूरत नहीं है—बस प्लग इन करें और तुरंत चालू! साथ ही दुकान पर डिजिटल पेमेंट्स व आवाज अलर्ट के लिए 'Cloud POS & UPI Soundbox' (₹599/माह) शामिल है। ₹2,500 का इंस्टॉलेशन शुल्क पूरी तरह माफ है।"
                    if is_hindi else
                    "Since physical optical fibre cables have not reached your village, the ideal solution is 'Biz 5G AirFiber 100' (@ ₹899/mo). It provides 100 Mbps high-speed wireless plug-and-play Wi-Fi with zero civil drilling or wire-pulling. We have included Cloud POS & UPI Soundbox (@ ₹599/mo) for instant payment voice alerts. The ₹2,500 setup fee is 100% waived."
                )
                tag_text = (
                    "ग्रामीण व देहात क्षेत्र के लिए बिना तार वाला 100 Mbps वायरलेस 5G AirFiber"
                    if is_hindi else
                    "Zero-wire 100 Mbps plug-and-play 5G AirFiber for rural and village locations"
                )
                return {
                    "intent": "recommendation",
                    "message": resp_msg,
                    "profile": profile,
                    "recommended_bundle": {"P04": 1, "P19": 1},
                    "explainability_tags": [
                        {"product_id": "P04", "name": "Biz 5G AirFiber 100", "tag": tag_text},
                        {"product_id": "P19", "name": "Cloud POS & UPI Soundbox", "tag": "दुकान पर यूपीआई पेमेंट साउंडबॉक्स व बिलिंग" if is_hindi else "UPI QR voice alert soundbox for shop"}
                    ]
                }
            elif any(w in msg for w in has_wire_keywords) or profile.get("fiber_confirmed"):
                profile["fiber_confirmed"] = True
                resp_msg = (
                    "बहुत बढ़िया! चूंकि आपकी बाजार/दुकान तक एयरटेल फाइबर की केबल उपलब्ध है, आपकी दुकान के लिए 'Biz Fibre 100' (₹999/माह) सबसे उपयुक्त है। यह 100 Mbps का अल्ट्रा-फास्ट ऑप्टिकल फाइबर ब्रॉडबैंड है जो फोन, वाई-फाई और निर्बाध बिलिंग सुनिश्चित करेगा। साथ ही दुकान पर तुरंत ऑडियो पेमेंट अलर्ट के लिए 'Cloud POS & UPI Soundbox' (₹599/माह) शामिल है। ₹2,500 का इंस्टॉलेशन शुल्क पूरी तरह माफ है।"
                    if is_hindi else
                    "Great! Since optical fiber cable is available at your market, the best solution for your shop is 'Biz Fibre 100' (@ ₹999/mo). This 100 Mbps optical fibre connection guarantees uninterrupted Wi-Fi, billing, and UPI transactions across your devices. We have included Cloud POS & UPI Soundbox (@ ₹599/mo) for instant payment voice alerts. The ₹2,500 setup fee is 100% waived."
                )
                tag_text = (
                    "दुकान पर वाई-फाई और यूपीआई बिलिंग के लिए 100 Mbps ऑप्टिकल फाइबर ब्रॉडबैंड"
                    if is_hindi else
                    "100 Mbps optical fibre for shop Wi-Fi and UPI billing"
                )
                return {
                    "intent": "recommendation",
                    "message": resp_msg,
                    "profile": profile,
                    "recommended_bundle": {"P01": 1, "P19": 1},
                    "explainability_tags": [
                        {"product_id": "P01", "name": "Biz Fibre 100", "tag": tag_text},
                        {"product_id": "P19", "name": "Cloud POS & UPI Soundbox", "tag": "दुकान पर यूपीआई पेमेंट साउंडबॉक्स व बिलिंग" if is_hindi else "UPI QR voice alert soundbox for shop"}
                    ]
                }
            elif not any(w in msg for w in has_wire_keywords) and not profile.get("fiber_confirmed"):
                resp_msg = (
                    "नमस्ते! गांव/देहात क्षेत्र में आपकी दुकान के लिए Airtel Business में दो बेहतरीन विकल्प हैं:\n\n"
                    "1️⃣ **Biz 5G AirFiber 100 (₹899/माह):** बिना किसी तार (केबल) वाला प्लग-एंड-प्ले वायरलेस 5G वाई-फाई (तुरंत चालू, बिना तार खींचे)।\n"
                    "2️⃣ **Biz Fibre 100 (₹999/माह):** अगर आपके बाजार/गली तक एयरटेल की ऑप्टिकल फाइबर केबल की तार आई हुई है।\n\n"
                    "क्या आपकी दुकान तक एयरटेल फाइबर की तार/केबल पहुंची हुई है, या आप बिना तार वाला 5G AirFiber लगवाना चाहेंगे?"
                    if is_hindi else
                    "Welcome! For shops in village and rural locations, Airtel Business offers two great solutions:\n\n"
                    "1️⃣ **Biz 5G AirFiber 100 (₹899/mo):** Wireless plug-and-play 100 Mbps Wi-Fi (zero wire-pulling or poles, instant setup).\n"
                    "2️⃣ **Biz Fibre 100 (₹999/mo):** Optical wireline broadband, if physical fiber cables are available in your market.\n\n"
                    "Does your market have physical Airtel optical fiber cable installed, or would you prefer the wireless plug-and-play 5G AirFiber?"
                )
                return {
                    "intent": "clarification",
                    "message": resp_msg,
                    "profile": profile,
                    "recommended_bundle": None,
                    "explainability_tags": []
                }

        # 1. Feasibility & Boundary Inquiries (50 Mbps, 1G in Tier 2, Leased Line without GST, Faster Wifi)
        # 1a. 50 Mbps / Sub-100 Mbps speed inquiry
        if any(w in msg for w in ["50 mbps", "50mbps", "50 mb", "50mb", "30 mbps", "20 mbps", "slower plan", "kam speed"]):
            inquiry_msg = (
                "एयरटेल बिजनेस में ऑप्टिकल फाइबर ब्रॉडबैंड 100 Mbps (Biz Fibre 100 @ ₹999/माह) से शुरू होता है, ताकि यूपीआई पेमेंट्स, बिलिंग और सीसीटीवी बिना किसी रुकावट के चल सकें। हमारे पास 50 Mbps का फाइबर प्लान नहीं है।\n\nयदि आप कम बजट में विकल्प चाहते हैं, तो हमारा '5G AirFiber Wireless' प्लान ₹899/माह पर उपलब्ध है।"
                if is_hindi else
                "In Airtel Business, optical fibre starts at 100 Mbps (Biz Fibre 100 @ ₹999/mo) as our enterprise standard to guarantee uninterrupted UPI payments, Cloud POS, and billing. We do not have a 50 Mbps fibre tier.\n\nIf you need a more economical option, our plug-and-play 'Biz 5G AirFiber' wireless plan is available at ₹899/mo."
            )
            return {
                "intent": "inquiry",
                "message": inquiry_msg,
                "profile": profile,
                "recommended_bundle": None,
                "explainability_tags": []
            }

        # 1b. Faster Wifi inquiry
        if any(w in msg for w in ["faster wifi", "faster internet", "more speed", "higher speed", "speed badhao", "fast wifi", "tez net"]):
            curr_city = profile.get("city")
            curr_tier = profile.get("city_tier")
            if curr_city and curr_tier:
                if curr_tier == 1:
                    resp = (
                        f"{curr_city} (टियर-1 शहर) में हमारे पास 300 Mbps (₹1,499/माह), 500 Mbps (₹2,499/माह) और 1 Gbps (₹3,999/माह) तक के अल्ट्रा-फास्ट फाइबर प्लान उपलब्ध हैं। आपकी दुकान या ऑफिस में कितने लोग इंटरनेट का उपयोग करेंगे?"
                        if is_hindi else
                        f"In {curr_city} (Tier-1 metro), we offer high-speed plans including 300 Mbps (Biz Fibre 300 @ ₹1,499/mo) and 1 Gbps (Biz Fibre 1G @ ₹3,999/mo). Approximately how many devices or users will be connecting?"
                    )
                else:
                    resp = (
                        f"{curr_city} (टियर-2 शहर) में हमारी फाइबर स्पीड अधिकतम 300 Mbps (Biz Fibre 300 @ ₹1,499/माह) तक उपलब्ध है। (1 Gbps प्लान वर्तमान में टियर-1 महानगरों में सीमित है)। क्या आप 300 Mbps प्लान जोड़ना चाहेंगे?"
                        if is_hindi else
                        f"In {curr_city} (Tier-2 city), our fibre network supports up to 300 Mbps (Biz Fibre 300 @ ₹1,499/mo). 1 Gbps plans are currently limited to Tier-1 metros. Would you like to upgrade your setup to 300 Mbps?"
                    )
            else:
                resp = (
                    "हमारे पास 300 Mbps (Biz Fibre 300) और टियर-1 शहरों में 1 Gbps तक के हाई-स्पीड फाइबर प्लान उपलब्ध हैं।\n\nआपके क्षेत्र में उपलब्ध अधिकतम स्पीड की जांच के लिए, कृपया बताएं कि आपकी दुकान/ऑफिस किस शहर में स्थित है और कितने डिवाइसेस जुड़ेंगे?"
                    if is_hindi else
                    "We offer high-speed fibre options up to 300 Mbps (Biz Fibre 300 @ ₹1,499/mo), and up to 1 Gbps in Tier-1 metros.\n\nTo confirm the maximum speed available for your address, could you please share which city you are located in and how many devices will connect?"
                )
            return {
                "intent": "inquiry",
                "message": resp,
                "profile": profile,
                "recommended_bundle": None,
                "explainability_tags": []
            }

        # 1c. Tier Feasibility: 1 Gbps query
        if "1 gbps" in msg or "1gbps" in msg or "1000 mbps" in msg or "gigabit" in msg:
            curr_city = profile.get("city")
            curr_tier = profile.get("city_tier")
            if curr_tier and curr_tier > 1:
                city_name = curr_city or "आपके शहर"
                inquiry_msg = (
                    f"{city_name} (टियर-{curr_tier} शहर) में हमारी वर्तमान ऑप्टिकल फाइबर क्षमता अधिकतम 300 Mbps (Biz Fibre 300 @ ₹1,499/माह) तक उपलब्ध है। 1 Gbps प्लान वर्तमान में टियर-1 मेट्रो शहरों (दिल्ली, मुंबई, बेंगलुरु आदि) में उपलब्ध है। क्या आप 300 Mbps प्लान के साथ आगे बढ़ना चाहेंगे?"
                    if is_hindi else
                    f"In {city_name} (Tier-{curr_tier}), the maximum optical fibre broadband currently supported is 300 Mbps (Biz Fibre 300 @ ₹1,499/mo). The 1 Gbps plan is currently exclusive to Tier-1 metropolitan areas. Would you like to explore our 300 Mbps plan?"
                )
            else:
                inquiry_msg = (
                    "हमारा 1 Gbps (Biz Fibre 1G @ ₹3,999/माह) प्लान टियर-1 महानगरों में उपलब्ध है। आपके पते पर इसकी उपलब्धता जांचने के लिए कृपया अपना शहर बताएं।"
                    if is_hindi else
                    "Our 1 Gbps ultra-fast plan (Biz Fibre 1G @ ₹3,999/mo) is available in Tier-1 metropolitan cities. To verify availability for your business, could you let us know which city you are located in?"
                )
            return {
                "intent": "inquiry",
                "message": inquiry_msg,
                "profile": profile,
                "recommended_bundle": None,
                "explainability_tags": []
            }

        # 1d. GST Feasibility: Leased Line or Static IP without GST
        if any(w in msg for w in ["leased line", "ill", "static ip", "mpls"]) and any(w in msg for w in ["without gst", "no gst", "bina gst", "gst nahi"]):
            inquiry_msg = (
                "भारतीय दूरसंचार नियमों के अनुसार, डेडिकेटेड इंटरनेट लीज्ड लाइन (1:1 SLA) और स्टैटिक आईपी के लिए सक्रिय जीएसटी (GSTIN) पंजीकरण अनिवार्य है।\n\nहालाँकि, बिना जीएसटी के भी आप पैन कार्ड और दुकान के पते के प्रमाण पर 100 Mbps या 300 Mbps का 'Biz Fibre' ब्रॉडबैंड तुरंत ले सकते हैं।"
                if is_hindi else
                "Under Indian telecom regulations, dedicated Internet Leased Lines (1:1 bandwidth) and Static IPs strictly mandate an active GSTIN registration.\n\nHowever, without a GST certificate, you can readily onboard onto our high-speed Biz Fibre broadband (100 Mbps or 300 Mbps) using your PAN and address proof."
            )
            return {
                "intent": "inquiry",
                "message": inquiry_msg,
                "profile": profile,
                "recommended_bundle": None,
                "explainability_tags": []
            }

        # 1e. Executive / Human Call Request
        exec_keywords = [
            "call an executive", "executive", "call me", "talk to executive",
            "talk to human", "agent", "customer care", "representative",
            "speak to someone", "human", "call lagao", "baat karao", "baat karni",
            "callback", "contact me", "phone call", "call karo", "call back",
            "बात कराओ", "कॉल करो", "एग्जीक्यूटिव", "कस्टमर केयर", "फोन करो"
        ]
        if any(w in msg for w in exec_keywords):
            resp_msg = (
                "धन्यवाद! आपके समय के लिए धन्यवाद। हमारे एयरटेल बिजनेस के विशेषज्ञ एग्जीक्यूटिव जल्द ही इस नंबर पर आपसे संपर्क करेंगे। 🙏"
                if is_hindi else
                "Thanks for your time! An Airtel Business executive will reach out to you shortly on this number to assist you further. 🙏"
            )
            return {
                "intent": "inquiry",
                "message": resp_msg,
                "profile": profile,
                "recommended_bundle": None,
                "explainability_tags": []
            }

        # 1f. General Plan Inquiry / Catalogue Overview
        plan_inquiry_keywords = [
            "other plans", "other plan", "different plans", "different plan", "all plans",
            "what plans", "types of plan", "plan options", "available plans", "list plans",
            "plans list", "plans available", "show plans", "plans kya hai", "konsa plan",
            "aur plan", "dusre plan", "tell me about plans", "what are your plans", "show me different plans"
        ]
        if any(w in msg for w in plan_inquiry_keywords):
            inquiry_msg = (
                "📶 *एयरटेल बिज़नेस एंटरप्राइज प्लान्स व स्पीड्स:*\n\n"
                "1️⃣ *Biz 5G AirFiber 100:* ₹899/माह (100 Mbps वायरलेस 5G FWA, प्लग-एंड-प्ले, बिना तार)\n"
                "2️⃣ *Biz Fibre 100:* ₹999/माह (100 Mbps ऑप्टिकल फाइबर ब्रॉडबैंड, दुकानों, बिलिंग व यूपीआई के लिए)\n"
                "3️⃣ *Biz Fibre 300:* ₹1,499/माह (300 Mbps हाई-स्पीड फाइबर, क्लिनिक, ऑफिस व 5-20 कर्मचारियों के लिए)\n"
                "4️⃣ *Biz Fibre 1G:* ₹3,999/माह (1 Gbps अल्ट्रा-फास्ट गीगाबिट फाइबर, टियर-1 महानगरों व भारी डेटा उपयोग के लिए)\n"
                "5️⃣ *इंटरनेट लीज्ड लाइन (ILL 20M):* ₹8,000/माह (डेडिकेटेड 1:1 सिमेट्रिक बैंडविड्थ, 99.9% SLA)\n\n"
                "💼 *डिजिटल प्रोडक्टिविटी एड-ऑन्स:*\n"
                "• क्लाउड ईमेल (Google Workspace / M365): ₹125/यूज़र/माह\n"
                "• क्लाउड बैकअप 1 TB (टैली बैकअप): ₹499/माह\n"
                "• यूपीआई साउंडबॉक्स व बिलिंग पीओएस: ₹599/माह\n"
                "• क्लाउड सीसीटीवी AI कैमरा: ₹199/कैमरा/माह\n"
                "• स्टेटिक पब्लिक आईपी: ₹200/माह\n\n"
                "आपके व्यवसाय के लिए सबसे सटीक प्लान चुनने के लिए, कृपया अपना शहर, व्यवसाय का प्रकार व कर्मचारियों की संख्या बताएं!"
                if is_hindi else
                "📶 *Airtel Business Enterprise Plans & Speeds:*\n\n"
                "1️⃣ *Biz 5G AirFiber 100:* ₹899/mo (100 Mbps wireless plug-and-play FWA, zero wiring, instant setup)\n"
                "2️⃣ *Biz Fibre 100:* ₹999/mo (100 Mbps optical fibre broadband, ideal for retail shops, billing & UPI)\n"
                "3️⃣ *Biz Fibre 300:* ₹1,499/mo (300 Mbps high-speed fibre, ideal for clinics, offices, 5-20 staff)\n"
                "4️⃣ *Biz Fibre 1G:* ₹3,999/mo (1 Gbps gigabit fibre, Tier-1 metros for tech startups & heavy usage)\n"
                "5️⃣ *Internet Leased Line (ILL 20M):* ₹8,000/mo (Dedicated 1:1 symmetric CIR bandwidth with 99.9% uptime SLA)\n\n"
                "💼 *Digital Productivity & Security Add-ons:*\n"
                "• Cloud Email & Office Suite (Google Workspace / M365): ₹125/user/mo\n"
                "• Cloud Backup 1 TB (Encrypted Tally & DB backup): ₹499/mo\n"
                "• Cloud POS & UPI Soundbox: ₹599/mo\n"
                "• Smart AI Cloud CCTV: ₹199/camera/mo\n"
                "• Static Commercial IP: ₹200/mo\n\n"
                "To recommend the ideal plan for your needs, could you please tell me which city your business is in, what type of business you run, and how many employees or devices will connect?"
            )
            return {
                "intent": "inquiry",
                "message": inquiry_msg,
                "profile": profile,
                "recommended_bundle": None,
                "explainability_tags": []
            }

        # 2. Cost Objection / Downsell Intent
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

        # 3. Check for Business Type
        has_business_type = bool(profile.get("business_type")) or any(
            w in msg for w in [
                "clinic", "doctor", "hospital", "dental", "pharma", "क्लिनिक", "डॉक्टर", "दवा",
                "ca", "accountant", "office", "law", "firm", "consulting", "वकील", "दफ्तर",
                "restaurant", "cafe", "hotel", "branch", "chain", "होटल", "खाना",
                "factory", "manufacturing", "textile", "parts", "workshop", "कारखाना",
                "kirana", "shop", "bakery", "store", "salon", "retail", "दुकान", "किराना",
                "startup", "tech", "software", "agency", "it", "स्टार्टअप"
            ]
        )

        # 4. MANDATORY CLARIFICATION CHECK:
        # If city is missing OR employee count is missing OR business type is missing:
        is_profile_incomplete = (
            profile.get("city") is None or
            profile.get("employee_count") is None or
            not has_business_type
        )

        if is_profile_incomplete:
            detected_b = "business"
            if any(w in msg for w in ["shop", "store", "kirana", "retail", "दुकान"]):
                detected_b = "shop"
                profile["business_type"] = "Micro Retail"
            elif any(w in msg for w in ["clinic", "doctor", "dental", "pharma", "क्लिनिक"]):
                detected_b = "clinic"
                profile["business_type"] = "Clinic / Healthcare"
            elif any(w in msg for w in ["ca", "accountant", "office", "law", "दफ्तर"]):
                detected_b = "office"
                profile["business_type"] = "Professional Office"
            elif any(w in msg for w in ["restaurant", "cafe", "hotel", "होटल"]):
                detected_b = "restaurant"
                profile["business_type"] = "Restaurant / Multi-site"
            elif any(w in msg for w in ["startup", "tech", "software", "agency", "it", "स्टार्टअप"]):
                detected_b = "startup"
                profile["business_type"] = "Tech Startup"

            if is_hindi:
                clarify_msg = (
                    f"नमस्ते! आपके {detected_b} के लिए सबसे सही और किफायती प्लान चुनने के लिए, क्या आप ये 3 विवरण साझा कर सकते हैं?\n\n"
                    "1. आपकी दुकान/व्यवसाय किस शहर या इलाके में स्थित है?\n"
                    "2. दुकान में कितने कर्मचारी या उपकरण (फोन, बिलिंग कंप्यूटर, कार्ड मशीन) इंटरनेट से जुड़ेंगे?\n"
                    "3. क्या आपको डिजिटल पेमेंट साउंडबॉक्स (UPI आवाज अलर्ट), सीसीटीवी या बिलिंग सॉफ्टवेयर की भी आवश्यकता है?"
                )
            else:
                clarify_msg = (
                    f"Welcome! We'd love to help set up business wifi for your {detected_b}. To help me recommend the ideal plan and verify network feasibility at your address, could you please share:\n\n"
                    "1. Which city or locality is your business located in?\n"
                    "2. Approximately how many staff members or devices (phones, billing computers, swipe machines) will connect to the internet?\n"
                    "3. Do you also need add-ons like a UPI QR Soundbox for payment voice alerts, CCTV cameras, or cloud billing POS?"
                )
            return {
                "intent": "clarification",
                "message": clarify_msg,
                "profile": profile,
                "recommended_bundle": None,
                "explainability_tags": []
            }

        # 5. Extract Business Type Details (only if city and staff are both known)
        if any(w in msg for w in ["clinic", "doctor", "hospital", "dental", "pharma", "क्लिनिक", "डॉक्टर", "दवा"]):
            profile["business_type"] = "Clinic / Healthcare"
            profile["has_gstin"] = True
        elif any(w in msg for w in ["ca", "accountant", "office", "law", "firm", "consulting", "वकील", "दफ्तर"]):
            profile["business_type"] = "Professional Office"
            profile["has_gstin"] = True
        elif any(w in msg for w in ["restaurant", "cafe", "hotel", "branch", "chain", "होटल", "खाना"]):
            profile["business_type"] = "Restaurant / Multi-site"
            profile["has_gstin"] = True
            profile["num_sites"] = 2
        elif any(w in msg for w in ["factory", "manufacturing", "textile", "parts", "workshop", "कारखाना"]):
            profile["business_type"] = "Small Manufacturer"
            profile["has_gstin"] = True
        elif any(w in msg for w in ["startup", "tech", "software", "agency", "it", "स्टार्टअप"]):
            profile["business_type"] = "Tech Startup"
            profile["num_sites"] = 1
        elif any(w in msg for w in ["kirana", "shop", "bakery", "store", "salon", "retail", "दुकान", "किराना"]):
            profile["business_type"] = "Micro Retail"
            profile["num_sites"] = 1

        # 6. Build Recommendation with Explainability Tags
        bundle = {}
        tags = []

        b_type = profile["business_type"]
        emp_cnt = profile.get("employee_count") or 3
        if "Tech Startup" in b_type:
            tier = profile.get("city_tier") or 1
            if emp_cnt >= 20 and tier == 1:
                bundle = {"P02": 1, "P11": 1, "P16": min(emp_cnt, 25), "P20": 5}
                speed_name = "Biz Fibre 300 (300 Mbps)"
            else:
                bundle = {"P02": 1, "P16": min(emp_cnt, 10), "P20": 2}
                speed_name = "Biz Fibre 300 (300 Mbps)"
            if is_hindi:
                tags = [
                    {"product_id": "P02", "name": "बिज़ फाइबर 300", "tag": f"{emp_cnt} कर्मचारियों के स्टार्टअप के लिए हाई-स्पीड 300 Mbps इंटरनेट"},
                    {"product_id": "P16", "name": "क्लाउड ईमेल सुइट", "tag": "टीम के लिए Google Workspace / Microsoft 365 प्रोफेशनल ईमेल"},
                    {"product_id": "P20", "name": "एंडपॉइंट सिक्योरिटी", "tag": "वर्कस्टेशन व लैपटॉप के लिए क्लाउड एंटीवायरस व सुरक्षा"},
                    {"product_id": "P11", "name": "स्टैटिक आईपी", "tag": "डेवलपमेंट सर्वर और रिमोट एक्सेस के लिए फिक्स्ड आईपी"}
                ]
            else:
                tags = [
                    {"product_id": "P02", "name": "Biz Fibre 300", "tag": f"300 Mbps high-speed symmetric connectivity for {emp_cnt}-member startup team workloads"},
                    {"product_id": "P16", "name": "Cloud Email Suite", "tag": f"Professional business email (Google Workspace/M365) for your team"},
                    {"product_id": "P20", "name": "Endpoint Security", "tag": "Antivirus & ransomware defense for business workstations"},
                    {"product_id": "P11", "name": "Static IP", "tag": "Fixed commercial IP for remote dev access, servers & VPN"}
                ]
            rec_msg = (
                f"आपके {profile.get('city', '')} स्थित {emp_cnt} कर्मचारियों के स्टार्टअप के लिए, मैंने *{speed_name}* के साथ प्रोफेशनल क्लाउड ईमेल और सुरक्षा सुइट का बंडल तैयार किया है। यह तेज़ गति और विश्वसनीय इंटरनेट प्रदान करता है ताकि आपकी पूरी टीम बिना किसी रुकावट के काम कर सके।\n\n"
                f"मासिक किराया: ₹1,499/माह (+ 18% GST = ₹1,768.82/माह कुल), स्थापना शुल्क (~₹2,500) 100% माफ है!"
                if is_hindi else
                f"For your {emp_cnt}-member startup in {profile.get('city', '')}, I recommend our *{speed_name}* plan bundled with Professional Cloud Email and Endpoint Security. It provides high-speed, low-latency connectivity to keep development, video calls, and cloud workflows running smoothly at ₹1,499/month (+ 18% GST = ₹1,768.82/month total with zero setup fee!)."
            )
            return {
                "intent": "recommendation",
                "message": rec_msg,
                "profile": profile,
                "recommended_bundle": bundle,
                "explainability_tags": tags
            }
        elif "Clinic" in b_type or "Professional" in b_type:
            bundle = {"P02": 1, "P09": 1, "P16": min(emp_cnt, 10), "P20": 2}
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

        city_str = f" in {profile['city']}" if profile.get("city") else ""
        greeting = (
            f"नमस्ते! आपके {profile['business_type']}{city_str} सेटअप के अनुसार हमने यह संपूर्ण डिजिटल बंडल तैयार किया है।"
            if is_hindi else
            f"Welcome! Based on your {profile['business_type']}{city_str} setup, here is your customized bundle."
        )

        return {
            "intent": "recommendation",
            "message": greeting,
            "profile": profile,
            "recommended_bundle": bundle,
            "explainability_tags": tags
        }

    def _call_external_llm(
        self,
        user_message: str,
        current_profile: Any,
        language: str,
        history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Invokes Gemini with multi-turn conversation awareness, structured JSON output,
        full 25-item Airtel Business product catalog, and 5-dimensional feasibility rules.
        """
        import requests
        from app.config import GEMINI_API_KEY, GEMINI_MODEL

        if not GEMINI_API_KEY:
            return self._process_deterministic(user_message, current_profile, language, history=history)

        profile = dict(current_profile or {})
        city = profile.get("city")
        city_tier = profile.get("city_tier")
        business_type = profile.get("business_type")
        employee_count = profile.get("employee_count")
        has_gstin = profile.get("has_gstin", None)

        is_hindi = (language == "hi")

        system_instruction = f"""
You are the AI Business Advisor for Project Udyam Digital (Airtel Business Enterprise self-serve portal).
Your job is to consult Indian MSMEs and businesses (Kirana, Clinic, Restaurant, Office, Tech Startup, etc.) and recommend compliant telecom & digital SaaS bundles.

CURRENT CUSTOMER PROFILE CONTEXT:
- City: {city if city else 'UNKNOWN (Do NOT assume or mention any city unless the user explicitly told you in this conversation!)'}
- City Tier: {f"Tier {city_tier}" if city_tier else 'UNKNOWN'}
- Has Active GSTIN: {has_gstin if has_gstin is not None else 'UNKNOWN'}
- Current Business Type: {business_type if business_type else 'UNKNOWN'}
- Employee Count: {employee_count if employee_count else 'UNKNOWN'}
- Language Requested: {'Hindi' if is_hindi else 'English'}

AIRTEL BUSINESS COMPLETE 25-PRODUCT PORTFOLIO & FEASIBILITY RULES:

1. BROADBAND FIBRE & WIRELESS CONNECTIVITY:
   - P01: Biz Fibre 100 (₹999/mo, Tier 1 & 2) — 100 Mbps symmetric optical fibre broadband. Unlimited data, 99.9% uptime. Best for retail shops, UPI QR soundbox, basic billing.
   - P02: Biz Fibre 300 (₹1,499/mo, Tier 1 & 2) — 300 Mbps high-speed optical fibre. Ideal for clinics, professional offices (CA, Legal), and growing startups (5-20+ staff) running cloud tools and video calls.
   - P03: Biz Fibre 1G (₹3,999/mo, TIER-1 METROS ONLY: Delhi NCR, Mumbai, Bengaluru, Chennai, Pune, Hyderabad, Kolkata) — 1 Gbps (1,000 Mbps) gigabit fibre. Ideal for tech startups, software teams, media studios with 20-50+ heavy users.
   - P04: Biz 5G AirFiber 100 (₹899/mo, Tier 1 & 2) — 100 Mbps plug-and-play wireless 5G fixed wireless access (FWA). Zero civil drilling or optical wire pulling needed. Ideal for quick setup, kiosks, budget options.
   - P05: Internet Leased Line 20 Mbps (₹8,000/mo, requires GSTIN, >=10 staff) — Dedicated 1:1 symmetric uncompressed leased line with 99.9% uptime SLA.
   - P06: Internet Leased Line 100 Mbps (₹25,000/mo, requires GSTIN, >=25 staff) — High-throughput 1:1 enterprise leased line.

2. CORPORATE MOBILE & FAILOVER:
   - P07: Business Postpaid 299 (₹299/SIM/mo) — Corporate CUG postpaid SIM with unlimited calls and 30GB data.
   - P08: Business Postpaid 599 (₹599/SIM/mo) — Corporate postpaid SIM with unlimited calls and 100GB rollover data.
   - P09: Backup 4G/5G Failover (₹499/mo) — Automatic wireless router backup keeping POS and billing online during fibre cuts.

3. NETWORK SECURITY & MANAGED INFRASTRUCTURE:
   - P10: Managed SD-WAN (₹2,500/mo, requires GSTIN, >=3 sites) — Multi-branch network optimization.
   - P11: Static IP (₹200/mo) — Fixed commercial IPv4 address for CCTV remote streaming, tally/ERP servers, VPN.
   - P20: Endpoint Security (₹99/device/mo) — Cloud antivirus and anti-ransomware protection for business PCs.
   - P21: Managed Firewall (₹1,999/mo, requires GSTIN) — Unified Threat Management (UTM) firewall.
   - P22: Secure Wi-Fi with Guest Network (₹399/mo) — Dual SSID router with captive portal separating private billing from customer Wi-Fi.

4. CLOUD, SAAS & DIGITAL PRODUCTIVITY:
   - P16: Cloud Email & Office Suite (₹125/user/mo) — Professional Google Workspace / Microsoft 365 @yourbusiness.com email.
   - P17: Cloud Backup 1 TB (₹499/mo) — Encrypted automated offsite cloud backup for Tally and databases.
   - P18: Website + Domain Starter (₹299/mo) — Domain name (.in/.com), hosting, and SSL certificate.
   - P19: Cloud POS & Billing (₹599/mo) — Cloud billing software and Airtel UPI Soundbox for instant audio alerts.

5. BUSINESS COMMUNICATIONS & OMNICHANNEL:
   - P12: Cloud Telephony / SIP Trunk (₹1,000/mo, requires GSTIN) — Virtual IVR and smart call routing.
   - P13: Toll-free 1800 Number (₹1,500/mo, requires GSTIN) — 1800 brand helpline.
   - P14: Business SMS 10k (₹1,500/mo, requires GSTIN) — Transactional OTP and marketing SMS.
   - P15: WhatsApp Business API Starter (₹999/mo, requires GSTIN) — Official green-tick verified WhatsApp business messaging.

6. IOT & SMART SURVEILLANCE:
   - P23: Cloud CCTV (₹199/camera/mo) — Smart AI night-vision security camera with cloud recording.
   - P24: Machine Monitoring IoT (₹149/sensor/mo, requires GSTIN) — Factory equipment vibration/temperature sensors.
   - P25: Fleet Tracker (₹199/vehicle/mo) — GPS vehicle tracking for logistics & delivery.

FEASIBILITY & STATUTORY RULES:
- Broadband fibre starts at 100 Mbps (P01 @ ₹999/mo). Sub-100 Mbps fibre (50M, 30M, 20M) DOES NOT EXIST in Airtel Business!
- P03 (Biz Fibre 1G) is TIER-1 ONLY. In Tier-2/3, maximum broadband speed is 300 Mbps (P02 @ ₹1,499).
- Broadband fibre (P01, P02, P04) is accessible WITHOUT GSTIN.
- STRICT GUARDRAIL: NEVER tell the customer "Since you do not have a GSTIN" or assume their GST status! Do NOT preach about GST unprompted!
- VILLAGE / RURAL / REMOTE INFRASTRUCTURE FEASIBILITY (CRITICAL):
  - In villages, rural areas, dehat, kasba, gram panchayats, or small towns (e.g. 'गांव', 'देहात', 'गाँव', 'village', 'rural', 'dumra dehat'):
    Physical optical wireline fibre (FTTH) may NOT be available or laid yet!
  - If the customer mentions a village or rural location and has NOT explicitly confirmed whether physical fiber cable is present:
    DO NOT ASSUME BIZ FIBRE 100!
    Instead, set intent="clarification", recommended_bundle=null, and ask:
    "गांव/देहात क्षेत्र में आपकी दुकान के लिए Airtel Business में दो विकल्प उपलब्ध हैं:
    1) Biz 5G AirFiber 100 (₹899/माह): बिना तार वाला प्लग-एंड-प्ले वायरलेस वाई-फाई (तुरंत चालू, बिना तार खींचे)।
    2) Biz Fibre 100 (₹999/माह): अगर आपके बाजार/दुकान तक एयरटेल की ऑप्टिकल फाइबर केबल की तार पहुंची हुई है।
    क्या आपकी दुकान तक एयरटेल फाइबर की तार/केबल पहुंची हुई है, या आप बिना तार वाला 5G AirFiber लगवाना चाहेंगे?"
    (or in English if chatting in English).
  - If the customer mentions that there is NO wire / cable ("bina taar", "no wire", "no cable", "taar nahi hai") or asks for wireless or confirms AirFiber:
    Set intent="recommendation". Recommend Biz 5G AirFiber 100 (P04 @ ₹899) + Cloud POS & UPI Soundbox (P19 @ ₹599).
    Set recommended_bundle={"P04": 1, "P19": 1}.
    Explain that Biz 5G AirFiber needs zero civil drilling or wire-pulling, works over 5G mobile towers, and is ideal for village shops!

CRITICAL INSTRUCTIONS FOR INTENT ROUTING:

A. MULTI-TURN CONVERSATION MEMORY (NEVER FORGET PREVIOUS FACTS):
   - Review the conversation turns!
   - If the user previously mentioned their city (e.g. 'Noida'), business type (e.g. 'startup'), or headcount (e.g. '25'), YOU MUST RETAIN THEM IN "profile"!
   - NEVER ask for information that was ALREADY stated in earlier turns or in CURRENT CUSTOMER PROFILE CONTEXT!
   - When City, Business Type, and Headcount/Scale are ALL KNOWN:
     YOU HAVE COMPLETE INFORMATION! DO NOT ASK ANY MORE QUESTIONS!
     Immediately set intent="recommendation"!

B. PLAN INQUIRIES & CATALOGUE OVERVIEW (intent: "inquiry"):
   - If user asks "what plans do you have?", "tell me about different plans", "what are the other plans", "what speeds do you have", "show plans":
     Set intent="inquiry", recommended_bundle=null.
     Provide a clear, helpful overview of the main plan tiers:
     1. Biz 5G AirFiber 100 (₹899/mo - Wireless plug-and-play, zero wiring)
     2. Biz Fibre 100 (₹999/mo - 100 Mbps optical fibre, best for retail & billing)
     3. Biz Fibre 300 (₹1,499/mo - 300 Mbps high-speed fibre for clinics, offices, 5-20+ staff)
     4. Biz Fibre 1G (₹3,999/mo - 1 Gbps gigabit fibre in Tier-1 metros for heavy tech usage)
     5. Internet Leased Line (ILL 20M @ ₹8,000/mo - 1:1 dedicated symmetric SLA)
     Mention add-ons (Cloud Email @ ₹125/user, Cloud Backup @ ₹499, CCTV @ ₹199, UPI Soundbox @ ₹599, Static IP @ ₹200).

C. TAILORED RECOMMENDATIONS (intent: "recommendation"):
   - When recommending for Tech Startups / Software / Agencies (e.g., 25 employees in Noida):
     Recommend Biz Fibre 300 (P02 @ ₹1,499/mo) or Biz Fibre 1G (P03 @ ₹3,999/mo) + Cloud Email (P16) + Endpoint Security (P20) + Static IP (P11). Set recommended_bundle={{"P02": 1, "P16": 25, "P20": 5, "P11": 1}}.
   - For Retail / Kirana shops: Biz Fibre 100 (P01 @ ₹999) + UPI Soundbox / POS (P19 @ ₹599).
   - For Clinics / Healthcare: Biz Fibre 300 (P02 @ ₹1,499) + Cloud Backup 1TB (P17 @ ₹499) + Guest Wi-Fi (P22 @ ₹399).
   - For Professional Offices (CA, Legal): Biz Fibre 300 (P02) + Cloud Email (P16) + Cloud Backup (P17).
   - State the monthly commitment and mention that the ₹2,500 setup fee is 100% waived!

D. PRICE INQUIRIES & PRICING QUESTIONS:
   - If user asks for price or cost of their recommended plan:
     State the exact rental with 18% GST and waived setup fee clearly.

E. EXECUTIVE / CALL REQUESTS (intent: "inquiry"):
   - If user asks to speak to an executive, agent, human, or request a call/callback:
     Set intent="inquiry", recommended_bundle=null.
     Reply politely: "Thanks for your time! An Airtel Business executive will reach out to you shortly on this number to assist you further. 🙏" (or in Hindi if chatting in Hindi).

JSON FORMAT:
Return ONLY a valid JSON object matching this schema:
{{
  "intent": "clarification" | "inquiry" | "recommendation" | "downsell_request",
  "language": "en" | "hi",
  "message": "Conversational reply in the user's language.",
  "profile": {{
    "business_type": string | null,
    "employee_count": number | null,
    "num_sites": number,
    "city": string | null,
    "city_tier": 1 | 2 | 3 | null,
    "has_gstin": boolean | null
  }},
  "recommended_bundle": {{ "<product_id>": <quantity> }} | null,
  "explainability_tags": [
    {{ "product_id": "P02", "name": "Biz Fibre 300", "tag": "Explanation why chosen" }}
  ]
}}
"""

        candidate_models = [GEMINI_MODEL, "gemini-3.1-flash-lite", "gemini-3-flash-preview"]

        # Build multi-turn contents from conversation history if available
        contents = []
        if history:
            for turn in history[-12:]:
                r = "user" if turn.get("role") == "user" else "model"
                txt = turn.get("text", "")
                if txt:
                    contents.append({"role": r, "parts": [{"text": txt}]})
        if not contents or contents[-1]["role"] != "user" or contents[-1]["parts"][0]["text"] != user_message:
            contents.append({"role": "user", "parts": [{"text": user_message}]})

        payload = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2
            }
        }

        for model_name in candidate_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
            try:
                r = requests.post(url, json=payload, timeout=8)
                if r.status_code == 200:
                    raw_json = r.json()['candidates'][0]['content']['parts'][0]['text']
                    data = json.loads(raw_json)

                    # Extract and validate intent
                    intent = data.get("intent", "recommendation")
                    resp_message = data.get("message", "")
                    # Merge with existing profile so previously known facts are NEVER erased
                    llm_profile_raw = data.get("profile") or {}
                    merged_profile = dict(profile)
                    for pk, pv in llm_profile_raw.items():
                        if pv is not None and pv != "":
                            merged_profile[pk] = pv
                    if merged_profile.get("city") and not merged_profile.get("city_tier"):
                        city_tier_map = {
                            "delhi": 1, "mumbai": 1, "bangalore": 1, "bengaluru": 1, "chennai": 1,
                            "hyderabad": 1, "pune": 1, "kolkata": 1, "noida": 1, "gurgaon": 1,
                            "gurugram": 1, "delhi ncr": 1, "ahmedabad": 1,
                            "indore": 2, "jaipur": 2, "ludhiana": 2, "kochi": 2, "nagpur": 2,
                            "bhopal": 2, "vizag": 2, "patna": 2, "surat": 2, "lucknow": 2,
                            "chandigarh": 2, "faridabad": 2, "ghaziabad": 2, "kanpur": 2,
                            "rohtak": 3
                        }
                        c_lower = str(merged_profile["city"]).lower().strip()
                        merged_profile["city_tier"] = city_tier_map.get(c_lower, 2)
                    if merged_profile.get("city") and not merged_profile.get("pincode"):
                        merged_profile["pincode"] = CITY_BENCHMARK_PINCODES.get(merged_profile["city"], "452001")
                    llm_profile = merged_profile

                    raw_bundle = data.get("recommended_bundle") or {}
                    raw_tags = data.get("explainability_tags", [])

                    # If recommendation intent but bundle was omitted by LLM, auto-populate from recommendation text
                    if intent == "recommendation" and not raw_bundle:
                        if "1g" in resp_message.lower() or "1 gbps" in resp_message.lower() or "p03" in resp_message.lower():
                            raw_bundle = {"P03": 1}
                        elif "300" in resp_message.lower() or "p02" in resp_message.lower():
                            raw_bundle = {"P02": 1}
                        elif "airfiber" in resp_message.lower() or "p04" in resp_message.lower():
                            raw_bundle = {"P04": 1}
                        else:
                            raw_bundle = {"P01": 1}

                    # If clarification or inquiry, return clean without cart changes
                    if intent in ["clarification", "inquiry"]:
                        return {
                            "intent": intent,
                            "message": resp_message,
                            "profile": llm_profile,
                            "recommended_bundle": None,
                            "explainability_tags": [],
                            "ai_engine": f"Gemini ({model_name})"
                        }

                    # FULL 5-DIMENSIONAL RULE-ENGINE GUARDRAIL ON LLM OUTPUT
                    validated_bundle = {}
                    city_tier = int(llm_profile.get("city_tier") or profile.get("city_tier") or 2)
                    emp_count = int(llm_profile.get("employee_count") or profile.get("employee_count") or 3)
                    num_sites = int(llm_profile.get("num_sites") or profile.get("num_sites") or 1)
                    has_gstin = bool(llm_profile.get("has_gstin") or profile.get("has_gstin") or False)

                    for pid, qty in raw_bundle.items():
                        prod = self.loader.get_product(pid)
                        if not prod:
                            continue

                        # Pass through authoritative CatalogEngine feasibility evaluator
                        eligible, reason = self.catalog_engine.evaluate_product_eligibility(
                            prod, city_tier, emp_count, num_sites, has_gstin
                        )
                        if not eligible:
                            if pid == "P03" and city_tier > 1:
                                validated_bundle["P02"] = 1
                            continue

                        validated_bundle[pid] = max(1, int(qty))

                    # Check if bundle has base connectivity
                    base_pids = ["P01", "P02", "P03", "P04", "P07", "P08"]
                    has_base = any(pid in validated_bundle for pid in base_pids)
                    if not has_base and validated_bundle:
                        if "1g" in resp_message.lower() or "1 gbps" in resp_message.lower() or "p03" in resp_message.lower():
                            validated_bundle["P03" if city_tier == 1 else "P02"] = 1
                        elif "300" in resp_message.lower() or "p02" in resp_message.lower():
                            validated_bundle["P02"] = 1
                        elif "airfiber" in resp_message.lower() or "p04" in resp_message.lower():
                            validated_bundle["P04"] = 1
                        else:
                            validated_bundle["P01"] = 1

                    # Clean tags to only validated products
                    validated_tags = [
                        t for t in raw_tags if t.get("product_id") in validated_bundle
                    ]

                    return {
                        "intent": intent,
                        "message": resp_message,
                        "profile": llm_profile,
                        "recommended_bundle": validated_bundle,
                        "explainability_tags": validated_tags,
                        "ai_engine": f"Gemini ({model_name})"
                    }
            except Exception:
                continue

        return self._process_deterministic(user_message, current_profile, language)
