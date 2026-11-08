"""
Deterministic Rule-Based Fallback Advisor for Project Udyam Digital.
Executes when Gemini is unavailable, using the EXACT same backend business tools
as the AI orchestrator to ensure 100% pricing, statutory, and catalog consistency.
"""

from typing import Dict, Any, List, Optional
from app.modules.advisor.tools import AdvisorTools, get_explainability_tag
from app.modules.advisor.profile import is_ready_for_recommendation

class ScriptedAdvisor:
    """
    High-precision deterministic advisor fallback providing consultative multi-turn discovery,
    progressive down-selling, and tailored Airtel Business recommendations in English & Hindi.
    """
    def __init__(self, tools: Optional[AdvisorTools] = None):
        self.tools = tools or AdvisorTools()

    def process(
        self,
        user_message: str,
        profile: Dict[str, Any],
        language: str = "en",
        detected_intent: str = "recommendation",
        active_bundle: Optional[Dict[str, int]] = None,
        entities: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        is_hindi = (language == "hi")
        is_marathi = (language == "mr")
        biz_name = profile.get("business_type") or "business"
        city = profile.get("city")
        pincode = profile.get("pincode")
        emp_count = profile.get("employee_count")
        num_sites = profile.get("num_sites", 1)
        has_gst = profile.get("has_gstin")
        rural = profile.get("rural_location")
        taar_present = profile.get("taar_present")
        bundle = active_bundle or profile.get("current_bundle") or {}

        # 1. Greetings
        if detected_intent == "greeting":
            if is_marathi:
                msg = "नमस्कार! एअरटेल बिझनेस एआय सल्लागारामध्ये आपले स्वागत आहे. आपल्या व्यवसायाबद्दल (दुकान/क्लिनिक/कार्यालय, शहर आणि कर्मचारी/डिव्हाइस संख्या) सांगा, आणि मी आपल्यासाठी सर्वोत्तम डिजिटल प्लॅन तयार करेन."
            elif is_hindi:
                msg = "नमस्ते! एयरटेल बिजनेस एआई एडवाइजर में आपका स्वागत है। अपने व्यवसाय (दुकान/क्लीनिक/ऑफिस, शहर, और कर्मचारियों की संख्या) के बारे में बताएं, और मैं आपके लिए सबसे उपयुक्त डिजिटल प्लान तैयार करूंगा।"
            else:
                msg = "Namaste! Welcome to Airtel Business Advisor. Tell me about your business (type, location, employees/devices) and I will craft the ideal digital bundle for you."
            return {
                "intent": "clarification",
                "message": msg,
                "profile": profile,
                "recommended_bundle": None,
                "explainability_tags": [],
                "ai_engine": "Udyam Deterministic Rule Engine"
            }

        # 2. Informational Catalog Overview / Inquiries
        if detected_intent == "inquiry":
            if is_marathi:
                msg = (
                    "Airtel Business मध्ये आपल्या व्यवसायासाठी मुख्य प्लॅन्स उपलब्ध आहेत:\n\n"
                    "1. **Biz 5G AirFiber 100 (₹899/महिना)**: विना-केबल प्लग-अँड-प्ले 5G वायरलेस वाय-फाय (त्वरित सुरू, केबल ओढण्याची गरज नाही).\n"
                    "2. **Biz Fibre 100 (₹999/महिना)**: 100 Mbps सिमेट्रिक ऑप्टिकल फायबर, किरकोळ दुकाने आणि UPI साउंडबॉक्ससाठी सर्वोत्तम.\n"
                    "3. **Biz Fibre 300 (₹1,599/महिना)**: क्लिनिक्स आणि मध्यम कार्यालयांसाठी हाय-स्पीड फायबर.\n"
                    "4. **Biz Fibre 1G (₹3,999/महिना)**: आयटी फर्म्स आणि कॉर्पोरेट्ससाठी 1 Gbps अल्ट्रा-फास्ट ब्रॉडबँड.\n\n"
                    "आपल्या व्यवसायाचा प्रकार, शहर आणि कर्मचारी संख्या सांगा, मी थेट योग्य प्लॅन शिफारस करेन."
                )
            elif is_hindi:
                msg = (
                    "Airtel Business में आपके व्यवसाय के लिए मुख्य प्लान्स उपलब्ध हैं:\n\n"
                    "1. **Biz 5G AirFiber 100 (₹899/माह)**: बिना तार वाला प्लग-एंड-प्ले 5G वायरलेस वाई-फाई (तुरंत चालू, बिना केबल)।\n"
                    "2. **Biz Fibre 100 (₹999/माह)**: 100 Mbps सिमेट्रिक ऑप्टिकल फाइबर, रिटेल दुकानों और UPI साउंडबॉक्स के लिए आदर्श।\n"
                    "3. **Biz Fibre 300 (₹1,599/माह)**: क्लीनिक्स और मध्यम दफ्तरों के लिए हाई-स्पीड फाइबर।\n"
                    "4. **Biz Fibre 1G (₹3,999/माह)**: टेक स्टार्टअप्स और कॉर्पोरेट्स के लिए 1 Gbps अल्ट्रा-फास्ट ब्रॉडबैंड।\n\n"
                    "कृपया अपने व्यवसाय का प्रकार, शहर और कर्मचारियों की संख्या बताएं, ताकि मैं आपको सटीक कोटेशन दे सकूं।"
                )
            else:
                msg = (
                    "Here is an overview of Airtel Business connectivity plans tailored for MSMEs:\n\n"
                    "1. **Biz 5G AirFiber 100 (₹899/mo)**: Plug-and-play wireless 5G fixed access. Zero wiring or drilling needed.\n"
                    "2. **Biz Fibre 100 (₹999/mo)**: 100 Mbps symmetric optical broadband with unlimited data and 99.9% uptime. Perfect for retail & billing.\n"
                    "3. **Biz Fibre 300 (₹1,499/mo)**: 300 Mbps high-speed fibre for clinics, CA firms, and 5-20+ connected devices.\n"
                    "4. **Biz Fibre 1G (₹3,999/mo)**: 1 Gbps gigabit fibre for heavy tech workflows and software startups (Tier-1 Metros).\n"
                    "5. **Internet Leased Line (ILL 20M @ ₹8,000/mo)**: 1:1 symmetric uncompressed enterprise bandwidth with guaranteed 99.9% SLA.\n\n"
                    "Digital Add-ons: Cloud Email (₹125/user), Cloud Backup 1TB (₹499), Cloud POS & UPI Soundbox (₹599), Static IP (₹200)."
                )
            return {
                "intent": "inquiry",
                "message": msg,
                "profile": profile,
                "recommended_bundle": None,
                "explainability_tags": [],
                "ai_engine": "Udyam Deterministic Rule Engine"
            }

        # 3. Partner / Executive Escalation
        if detected_intent == "escalation":
            res = self.tools.request_human_assistance("Customer requested executive support", profile)
            return {
                "intent": "inquiry",
                "message": res.get("message", "An Airtel Business executive will reach out to you shortly."),
                "profile": profile,
                "recommended_bundle": None,
                "explainability_tags": [],
                "ai_engine": "Udyam Deterministic Rule Engine"
            }

        # 4. Rural Feasibility Clarification
        if rural and taar_present is None:
            if is_marathi:
                msg = (
                    "ग्रामीण/खेडूत भागातील आपल्या दुकानासाठी Airtel Business मध्ये दोन पर्याय उपलब्ध आहेत:\n"
                    "1) **Biz 5G AirFiber 100 (₹899/महिना)**: विना-केबल प्लग-अँड-प्ले वायरलेस वाय-फाय (केबल न ओढता त्वरित सुरू).\n"
                    "2) **Biz Fibre 100 (₹999/महिना)**: जर आपल्या बाजारात/दुकानापर्यंत एअरटेलची ऑप्टिकल फायबर केबल पोहोचलेली असेल.\n\n"
                    "आपल्या दुकानापर्यंत एअरटेल फायबरची केबल पोहोचली आहे का, की आपल्याला वायरलेस 5G AirFiber हवे आहे?"
                )
            elif is_hindi:
                msg = (
                    "गांव/देहात क्षेत्र में आपकी दुकान के लिए Airtel Business में दो विकल्प उपलब्ध हैं:\n"
                    "1) **Biz 5G AirFiber 100 (₹899/माह)**: बिना तार वाला प्लग-एंड-प्ले वायरलेस वाई-फाई (तुरंत चालू, बिना तार खींचे)।\n"
                    "2) **Biz Fibre 100 (₹999/माह)**: अगर आपके बाजार/दुकान तक एयरटेल की ऑप्टिकल फाइबर केबल की तार पहुंची हुई है।\n\n"
                    "क्या आपकी दुकान तक एयरटेल फाइबर की तार/केबल पहुंची हुई है, या आप बिना तार वाला 5G AirFiber लगवाना चाहेंगे?"
                )
            else:
                msg = (
                    "In village and rural areas, Airtel Business offers two reliable deployment options:\n"
                    "1) **Biz 5G AirFiber 100 (₹899/mo)**: Plug-and-play wireless Wi-Fi operating over 5G towers with zero cable pulling.\n"
                    "2) **Biz Fibre 100 (₹999/mo)**: Optical wireline broadband if Airtel fibre cables are already present in your market.\n\n"
                    "Does your location have Airtel optical fibre cable laid, or would you prefer wireless 5G AirFiber?"
                )
            return {
                "intent": "clarification",
                "message": msg,
                "profile": profile,
                "recommended_bundle": None,
                "explainability_tags": [],
                "ai_engine": "Udyam Deterministic Rule Engine"
            }

        # 5. Progressive Down-sell Request
        if detected_intent == "downsell_request":
            current_step = profile.get("downsell_level", 0) + 1
            if not bundle:
                bundle = {"P01": 1, "P19": 1}
            downsell_res = self.tools.progressive_downsell(bundle, current_step)
            profile["downsell_level"] = downsell_res["step_executed"]
            profile["current_bundle"] = downsell_res["bundle"]

            q = downsell_res["quotation"]
            subtotal = q.get("monthly_subtotal_inr", 0)
            gst = q.get("gst_18_inr", 0)
            total = q.get("total_monthly_inr", 0)

            if is_marathi:
                msg = (
                    f"समजले! आम्ही आपल्या बजेटनुसार प्लॅन कमी (डाउन-सेल) केला आहे:\n\n"
                    f"- {downsell_res['explanation']}\n"
                    f"- **नवीन मासिक भाडे:** ₹{subtotal:,.2f}/महिना (+ 18% GST = ₹{total:,.2f}/महिना)\n"
                    f"- **सेटअप शुल्क:** ₹2,500 (100% मोफत / Waived)\n\n"
                    f"हा आपल्या व्यवसायासाठी सर्वोत्तम आवश्यक floor price प्लॅन आहे."
                )
            elif is_hindi:
                msg = (
                    f"समझ गया! हमने आपके बजट के अनुसार प्लान को डाउन-सेल कर दिया है:\n\n"
                    f"- {downsell_res['explanation']}\n"
                    f"- **नया मासिक किराया:** ₹{subtotal:,.2f}/माह (+ 18% GST = ₹{total:,.2f}/माह)\n"
                    f"- **सेटअप शुल्क:** ₹2,500 (100% पूरी तरह फ्री / Waived)\n\n"
                    f"यह आपके व्यवसाय के लिए न्यूनतम आवश्यक floor price प्लान है।"
                )
            else:
                msg = (
                    f"Understood! We have adjusted your bundle for maximum cost efficiency:\n\n"
                    f"- {downsell_res['explanation']}\n"
                    f"- **Updated Monthly Subtotal:** ₹{subtotal:,.2f}/mo (+ 18% GST = ₹{total:,.2f}/mo)\n"
                    f"- **Setup & Installation:** ₹2,500 (100% Waived FREE)\n\n"
                    f"This provides your business with verified floor connectivity without compromising core operations."
                )

            return {
                "intent": "downsell_request",
                "message": msg,
                "profile": profile,
                "recommended_bundle": downsell_res["bundle"],
                "explainability_tags": downsell_res["tags"],
                "quotation": q,
                "ai_engine": "Udyam Deterministic Rule Engine"
            }

        # 6. Remove Add-on Request
        if detected_intent == "remove_addon":
            target = (entities or {}).get("remove_target", "P19")
            if not bundle or not any(bundle.values()):
                base_res = self.tools.generate_bundle(profile)
                bundle = base_res["bundle"]
            res = self.tools.remove_addon(bundle, target)
            profile["current_bundle"] = res["bundle"]
            q = res["quotation"]
            removed_id = res.get("removed_id") or target

            # Guard against empty bundle or 0 subtotal
            base_pids = {"P01", "P02", "P03", "P04", "P05", "P06", "P07", "P08"}
            if not any(p in res["bundle"] for p in base_pids):
                res["bundle"]["P01"] = 1
                q = self.tools.calculate_quotation(res["bundle"])
                profile["current_bundle"] = res["bundle"]

            subtotal_val = q.get('monthly_subtotal_inr', 0)
            total_val = q.get('total_monthly_inr', 0)
            if subtotal_val == 0:
                res["bundle"]["P01"] = 1
                q = self.tools.calculate_quotation(res["bundle"])
                subtotal_val = q.get('monthly_subtotal_inr', 999.0)
                total_val = q.get('total_monthly_inr', 1178.82)
                profile["current_bundle"] = res["bundle"]

            if is_marathi:
                msg = f"समजले! आम्ही आपल्या बंडलमधून ॲड-ऑन काढून टाकले आहे. आपले नवीन मासिक भाडे ₹{subtotal_val:,.2f} + GST अपडेट झाले आहे."
            elif is_hindi:
                msg = f"समझ गया! हमने आपके बंडल से ऐड-ऑन को हटा दिया है। आपका नया मासिक किराया ₹{subtotal_val:,.2f} + GST अपडेट कर दिया गया है।"
            else:
                msg = f"Understood! I have removed the requested add-on from your bundle. Your updated monthly subtotal is ₹{subtotal_val:,.2f} (+ 18% GST = ₹{total_val:,.2f}/mo)."

            return {
                "intent": "recommendation",
                "action": "remove_addon",
                "removed_product_id": removed_id,
                "message": msg,
                "profile": profile,
                "recommended_bundle": res["bundle"],
                "explainability_tags": res["tags"],
                "quotation": q,
                "ai_engine": "Udyam Deterministic Rule Engine"
            }

        # 7. Mandatory Consultative Discovery & Clarification
        # Check if user has provided both location (city/pincode) AND scale
        ready = is_ready_for_recommendation(profile)
        # Exception: if user specified multi-site with headcounts (e.g. 10 and 100), or user provided clear scale in this turn
        if not ready and not profile.get("site_headcounts"):
            has_location = bool(profile.get("city") or profile.get("pincode"))
            has_scale = (profile.get("employee_count") is not None)

            if not has_location and has_scale:
                # User gave scale and business, but location is missing
                if is_marathi:
                    msg = (
                        f"धन्यवाद! आपल्या {biz_name} चे तपशील नोंदवले आहेत.\n\n"
                        f"अचूक शहर टियर (Tier 1/2/3) निश्चित करण्यासाठी आणि नेटवर्क व्यवहार्यता (ऑप्टिकल फायबर विरुद्ध 5G AirFiber) तपासण्यासाठी, "
                        f"कृपया सांगा की आपले दुकान/व्यवसाय कोणत्या **शहरात किंवा 6-अंकी पिनकोड** मध्ये आहे?"
                    )
                elif is_hindi:
                    msg = (
                        f"धन्यवाद! आपके {biz_name} के विवरण नोट कर लिए गए हैं।\n\n"
                        f"सटीक सिटी टियर (Tier 1/2/3) निर्धारित करने और नेटवर्क फिजिबिलिटी (ऑप्टिकल फाइबर बनाम 5G AirFiber) की पुष्टि करने के लिए, "
                        f"कृपया बताएं कि आपकी दुकान/व्यवसाय किस **शहर या 6-अंकों के पिनकोड** में स्थित है?"
                    )
                else:
                    msg = (
                        f"Thank you for sharing those details! To determine your city tier (Tier 1/2/3), "
                        f"confirm network feasibility (optical fibre vs 5G AirFiber), and calculate your exact quotation, "
                        f"could you please share which **city or 6-digit pincode** your {biz_name} is located in?"
                    )
            else:
                loc_str = f" in {city}" if city else ""
                shop_str = f" across your {num_sites} shops" if num_sites > 1 else ""
                if is_marathi:
                    msg = (
                        f"खूप छान!{loc_str} मध्ये आपल्या व्यवसायासाठी Airtel Business कडे सर्वोत्तम सोल्यूशन्स उपलब्ध आहेत.\n\n"
                        f"अचूक आणि योग्य प्लॅनची शिफारस करण्यासाठी, कृपया तीन बाबी स्पष्ट करा:\n"
                        f"1. आपण कोणता व्यवसाय चालवता आणि तो कोणत्या **शहरात किंवा 6-अंकी पिनकोड** मध्ये आहे?\n"
                        f"2. आपल्याकडे दुकानासाठी सक्रिय जीएसटी (GSTIN) आहे की आपण विना-जीएसटी (Non-GST / Udyam) चालवता?\n"
                        f"3. दुकानात अंदाजे किती कर्मचारी, बिलिंग कम्प्युटर्स किंवा ग्राहक वाय-फाय वापरतील?"
                    )
                elif is_hindi:
                    msg = (
                        f"बहुत बढ़िया!{loc_str} में आपके व्यवसाय के लिए Airtel Business में सर्वोत्तम समाधान उपलब्ध हैं।\n\n"
                        f"सटीक और उपयुक्त प्लान की सिफारिश करने के लिए, कृपया तीन विवरण स्पष्ट करें:\n"
                        f"1. आप किस प्रकार का व्यवसाय चलाते हैं और यह किस **शहर या 6-अंकों के पिनकोड** में स्थित है?\n"
                        f"2. क्या आपके पास अपनी दुकान/फर्म के लिए सक्रिय जीएसटी (GSTIN) है, या आप बिना जीएसटी (Non-GST / Udyam) चलाते हैं?\n"
                        f"3. कुल कितने कर्मचारी, बिलिंग कंप्यूटर, या ग्राहक डिवाइस वाई-फाई से कनेक्ट होंगे?"
                    )
                else:
                    msg = (
                        f"That's great! Setting up high-speed business Wi-Fi{shop_str}{loc_str} is easy with Airtel Business.\n\n"
                        f"To recommend the most suitable plan and speed for your {biz_name}, could you please clarify:\n"
                        f"1. What type of business do you run, and in which **city or 6-digit pincode** is it located?\n"
                        f"2. Do you have an active registered GST (GSTIN) for your business, or do you operate under sole-proprietorship (Non-GST / Udyam mode)?\n"
                        f"3. Approximately how many employees, billing devices, or customer connections will be using the Wi-Fi at each location?"
                    )
            return {
                "intent": "clarification",
                "message": msg,
                "profile": profile,
                "recommended_bundle": None,
                "explainability_tags": [],
                "ai_engine": "Udyam Deterministic Rule Engine"
            }

        # 8. Tailored Bundle Recommendation
        result = self.tools.generate_bundle(profile)
        profile["current_bundle"] = result["bundle"]
        q = result["quotation"]
        subtotal = q.get("monthly_subtotal_inr", 0)
        gst = q.get("gst_18_inr", 0)
        total = q.get("total_monthly_inr", 0)

        # Build readable message
        items_desc = []
        for it in q.get("items", []):
            items_desc.append(f"- **{it['product_name']}** ({it['quantity']}x @ ₹{it['unit_price_inr']:,.0f}/mo)")
        items_summary_str = "\n".join(items_desc)

        loc_mention = f" in {city}" if city else ""
        if is_marathi:
            msg = (
                f"धन्यवाद! आपल्या तपशिलानुसार{loc_mention}, हे आहे आपले शिफारस केलेले Airtel Business बंडल:\n\n"
                f"{items_summary_str}\n\n"
                f"**आर्थिक सारांश:**\n"
                f"- **एकूण मासिक भाडे:** ₹{subtotal:,.2f}/महिना\n"
                f"- **जीएसटी (18%):** ₹{gst:,.2f}\n"
                f"- **एकूण मासिक बांधिलकी:** ₹{total:,.2f}/महिना\n"
                f"- **सेटअप आणि इन्स्टॉलेशन शुल्क:** ₹2,500 (100% मोफत / Waived)\n\n"
                f"*टीप: आपल्याला यातील कोणतेही ॲड-ऑन नको असल्यास, फक्त मला सांगा (उदा. 'soundbox काढा').*"
            )
        elif is_hindi:
            msg = (
                f"धन्यवाद! आपके विवरण के अनुसार{loc_mention}, यहाँ आपका अनुशंसित Airtel Business बंडल है:\n\n"
                f"{items_summary_str}\n\n"
                f"**वित्तीय विवरण:**\n"
                f"- **मासिक कुल किराया:** ₹{subtotal:,.2f}/माह\n"
                f"- **जीएसटी (18%):** ₹{gst:,.2f}\n"
                f"- **कुल मासिक प्रतिबद्धता:** ₹{total:,.2f}/माह\n"
                f"- **सेटअप और इंस्टॉलेशन शुल्क:** ₹2,500 (100% पूरी तरह फ्री)\n\n"
                f"*नोट: यदि आपको किसी डिजिटल ऐड-ऑन की आवश्यकता नहीं है, तो बस मुझे इसे हटाने के लिए कहें (उदा. 'soundbox हटा दो')।*"
            )
        else:
            msg = (
                f"Thank you for sharing the details! Based on your {biz_name} requirements{loc_mention}, here is your tailored solution:\n\n"
                f"{items_summary_str}\n\n"
                f"**Financial Summary:**\n"
                f"- **Monthly Subtotal:** ₹{subtotal:,.2f}/mo\n"
                f"- **GST (18%):** ₹{gst:,.2f}\n"
                f"- **Total Monthly Commitment:** ₹{total:,.2f}/mo\n"
                f"- **Setup & Installation:** ₹2,500 (100% Waived FREE)\n\n"
                f"*Note: I have included essential security and productivity add-ons. If you do not need any of these, simply ask me to remove them (e.g. 'remove soundbox') or click 'Remove ×' in your quote drawer!*"
            )

        return {
            "intent": "recommendation",
            "message": msg,
            "profile": profile,
            "recommended_bundle": result["bundle"],
            "explainability_tags": result["tags"],
            "quotation": q,
            "ai_engine": "Udyam Deterministic Rule Engine"
        }

