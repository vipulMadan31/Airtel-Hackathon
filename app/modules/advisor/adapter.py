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
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Extracts structured profile, intent, and outputs recommended bundle with explainability tags.
        """
        if self.has_llm_key:
            try:
                result = self._call_external_llm(user_message, current_profile, language)
                if result:
                    return result
            except Exception:
                pass

        return self._process_deterministic(user_message, current_profile, language)

    def _process_deterministic(
        self,
        message: str,
        current_profile: Optional[Dict[str, Any]],
        language: str
    ) -> Dict[str, Any]:
        msg = message.lower().strip()
        profile = dict(current_profile or {})
        
        # Ensure profile keys exist without hardcoding assumptions
        profile.setdefault("business_type", None)
        profile.setdefault("employee_count", None)
        profile.setdefault("num_sites", 1)
        profile.setdefault("city", None)
        profile.setdefault("city_tier", None)
        profile.setdefault("has_gstin", False)
        profile.setdefault("monthly_budget", 3000)

        is_hindi = (language == "hi")

        # 0. Extract Location / City from user message if mentioned
        city_tier_map = {
            "delhi": ("Delhi", 1), "mumbai": ("Mumbai", 1), "bangalore": ("Bangalore", 1),
            "bengaluru": ("Bengaluru", 1), "chennai": ("Chennai", 1), "hyderabad": ("Hyderabad", 1),
            "pune": ("Pune", 1), "kolkata": ("Kolkata", 1),
            "indore": ("Indore", 2), "jaipur": ("Jaipur", 2), "ludhiana": ("Ludhiana", 2),
            "kochi": ("Kochi", 2), "nagpur": ("Nagpur", 2), "bhopal": ("Bhopal", 2),
            "vizag": ("Visakhapatnam", 2), "patna": ("Patna", 2), "surat": ("Surat", 2),
            "lucknow": ("Lucknow", 2), "chandigarh": ("Chandigarh", 2), "delhi ncr": ("Delhi NCR", 1)
        }
        for k, (cname, ctier) in city_tier_map.items():
            if k in msg:
                profile["city"] = cname
                profile["city_tier"] = ctier
                break

        # Extract Employee / device count if mentioned
        emp_match = re.search(r'(\d+)\s*(people|staff|employees|workers|log|devices|pc|systems|कर्मचारी|लोग)', msg)
        if emp_match:
            profile["employee_count"] = int(emp_match.group(1))

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
        has_business_type = any(
            w in msg for w in [
                "clinic", "doctor", "hospital", "dental", "pharma", "क्लिनिक", "डॉक्टर", "दवा",
                "ca", "accountant", "office", "law", "firm", "consulting", "वकील", "दफ्तर",
                "restaurant", "cafe", "hotel", "branch", "chain", "होटल", "खाना",
                "factory", "manufacturing", "textile", "parts", "workshop", "कारखाना",
                "kirana", "shop", "bakery", "store", "salon", "retail", "दुकान", "किराना"
            ]
        )

        # 4. MANDATORY CLARIFICATION CHECK:
        # If city is missing OR employee count is missing OR query is vague:
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
        elif any(w in msg for w in ["kirana", "shop", "bakery", "store", "salon", "retail", "दुकान", "किराना"]):
            profile["business_type"] = "Micro Retail"
            profile["num_sites"] = 1

        # 6. Build Recommendation with Explainability Tags
        bundle = {}
        tags = []

        b_type = profile["business_type"]
        emp_cnt = profile.get("employee_count") or 3
        if "Clinic" in b_type or "Professional" in b_type:
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

    def _call_external_llm(self, user_message: str, current_profile: Any, language: str) -> Dict[str, Any]:
        """
        Invokes Gemini 3.5 Flash with strict structured JSON output and full 5-dimensional rule guardrails.
        """
        import requests
        from app.config import GEMINI_API_KEY, GEMINI_MODEL

        if not GEMINI_API_KEY:
            return self._process_deterministic(user_message, current_profile, language)

        profile = dict(current_profile or {})
        city = profile.get("city")
        city_tier = profile.get("city_tier")
        business_type = profile.get("business_type")
        employee_count = profile.get("employee_count")
        has_gstin = profile.get("has_gstin", False)

        is_hindi = (language == "hi")

        system_instruction = f"""
You are the AI Business Advisor for Project Udyam Digital (Airtel Business Enterprise self-serve portal).
Your job is to consult Indian MSMEs (Kirana, Clinic, Restaurant, Office, etc.) and recommend compliant telecom & digital SaaS bundles.

CURRENT CUSTOMER PROFILE CONTEXT:
- City: {city if city else 'UNKNOWN (Do NOT assume or mention any city unless the user explicitly tells you!)'}
- City Tier: {f"Tier {city_tier}" if city_tier else 'UNKNOWN'}
- Has Active GSTIN: {has_gstin}
- Current Business Type: {business_type if business_type else 'UNKNOWN'}
- Employee Count: {employee_count if employee_count else 'UNKNOWN'}
- Language Requested: {'Hindi' if is_hindi else 'English'}

CATALOGUE RULES & 5-DIMENSIONAL FEASIBILITY MATRIX:
1. SPEED BOUNDARIES & CATALOGUE FLOOR:
   - Broadband fibre starts at 100 Mbps (P01 Biz Fibre 100 @ ₹999/mo).
   - SUB-100 MBPS FIBRE (e.g., 50 Mbps, 30 Mbps, 20 Mbps) DOES NOT EXIST in Airtel Business!
   - The only sub-₹999 option is Biz 5G AirFiber Wireless (P04 @ ₹899/mo) or Postpaid SIM (P07 @ ₹299/mo).
   - NEVER invent or agree that 50 Mbps fibre exists!
2. CITY TIER FEASIBILITY:
   - P03 (Biz Fibre 1G, 1000 Mbps) is TIER-1 ONLY (Metros like Mumbai, Delhi, Bengaluru, Chennai, Pune).
   - In Tier-2 (Indore, Jaipur, Ludhiana, Kochi, etc.) and Tier-3, maximum broadband speed is 300 Mbps (P02 @ ₹1,499) or 100 Mbps (P01 @ ₹999). 1 Gbps is NOT available.
   - If the user's city is UNKNOWN and they ask for faster options, explain that fibre speeds range from 100M to 300M (up to 1G in Tier-1 metros), and ask which city they are in!
3. STATUTORY GSTIN PREREQUISITES:
   - Products requiring verified GSTIN: P05 (ILL 20M), P06 (ILL 100M), P10 (SD-WAN), P11 (Static IP), P12 (SIP Trunk), P15 (MPLS VPN), P21 (Managed Firewall).
   - If user has NO GSTIN, NEVER recommend these products!
4. SCALE & HEADCOUNT PREREQUISITES:
   - P05 (ILL 20M) requires >= 10 employees; P06 (ILL 100M) requires >= 25 employees; P15 (MPLS VPN) requires >= 10 employees; P10 (SD-WAN) requires >= 3 sites.

CRITICAL INSTRUCTIONS FOR INTENT ROUTING:

A. PROGRESSIVE CLARIFICATION (MANDATORY WHEN DETAILS ARE MISSING):
   - When a user states their business (e.g. "I own a small shop and need wifi for it", "I have a clinic", "need internet for my office", "I need wifi"):
     IF they have NOT provided BOTH:
       1) Their City / Location, AND
       2) Their Team size / Number of devices
     YOU MUST SET intent="clarification", recommended_bundle=null, and politely ask the clarifying questions:
       - Which city or town is their business located in?
       - Approximately how many staff members or devices (phones, billing computers, card machines) will connect?
       - Do they need digital payments (UPI QR soundbox for voice alerts), CCTV cameras, or cloud billing POS?
   - NEVER assume the user lives in Indore or any city!
   - NEVER say "As an Airtel Business partner in Indore" if the user has not explicitly stated they are in Indore!
   - DO NOT generate a bundle until City and Scale are known!

B. INFORMATIONAL / FEASIBILITY INQUIRIES (intent: "inquiry"):
   - If the user asks a question (e.g. "is there a 50 mbps option also?", "do you have a faster wifi option?", "can I get leased line without GST?"):
     Set intent="inquiry", recommended_bundle=null (LEAVE THEIR CART UNTOUCHED!).
     Explain the technical catalogue facts accurately. If city is needed to verify exact speed limits, ask for their city.

C. DOWN-SELL (intent: "downsell_request"):
   - If user asks for a cheaper plan ("sasta", "mehenga", "cheap", "expensive", "kam budget"), set intent="downsell_request", strip optional add-ons, keep essential floor connectivity (P01: 1), and explain the savings.

D. RECOMMENDATION (intent: "recommendation"):
   - When the user provides their business type, city, and scale/team size (e.g., 'We are a CA accounting firm with 8 auditors in Jaipur', 'Dental clinic in Pune with 6 staff', 'Kirana store in Indore with 2 staff'), this is SUFFICIENT information!
   - Do NOT ask further questions. Set intent="recommendation" and generate the tailored bundle with explainability tags immediately!

JSON FORMAT:
Return ONLY a valid JSON object matching this schema:
{{
  "intent": "clarification" | "inquiry" | "recommendation" | "downsell_request",
  "language": "en" | "hi",
  "message": "Conversational reply in the user's language asking clarifying questions or presenting the bundle.",
  "profile": {{
    "business_type": string | null,
    "employee_count": number | null,
    "num_sites": number,
    "city": string | null,
    "city_tier": 1 | 2 | 3 | null,
    "has_gstin": boolean
  }},
  "recommended_bundle": {{ "<product_id>": <quantity> }} | null,
  "explainability_tags": [
    {{ "product_id": "P01", "name": "Biz Fibre 100", "tag": "Explanation why chosen" }}
  ]
}}
"""

        candidate_models = [GEMINI_MODEL, "gemini-3.1-flash-lite", "gemini-3-flash-preview"]
        payload = {
            "contents": [{"parts": [{"text": user_message}]}],
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
                    llm_profile = data.get("profile") or profile
                    raw_bundle = data.get("recommended_bundle") or {}
                    raw_tags = data.get("explainability_tags", [])

                    # If clarification or inquiry or empty bundle, return clean without cart changes
                    if intent in ["clarification", "inquiry"] or not raw_bundle:
                        return {
                            "intent": intent if intent in ["clarification", "inquiry"] else "clarification",
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
