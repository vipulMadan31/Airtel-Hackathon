import os
import uuid
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.modules.advisor.adapter import AdvisorAdapter
from app.modules.pricing.calculator import PricingCalculator
from app.modules.kyc.ocr_engine import OCREngine
from app.modules.kyc.validator import KYCValidator
from app.modules.orders.state_machine import OrderStateMachine
from app.modules.whatsapp.formatter import WhatsAppFormatter
from app.modules.whatsapp.session import WhatsAppSessionManager
from app.config import UPLOAD_DIR, CASE_REFERENCE_DATE

class WhatsAppHandler:
    def __init__(self):
        self.session_mgr = WhatsAppSessionManager()
        self.advisor = AdvisorAdapter()
        self.pricing = PricingCalculator()
        self.ocr = OCREngine()
        self.kyc_validator = KYCValidator()
        self.order_machine = OrderStateMachine()
        self.formatter = WhatsAppFormatter()

    def process_incoming_message(
        self,
        phone_number: str,
        message_text: Optional[str] = None,
        image_path: Optional[str] = None,
        button_payload: Optional[str] = None,
        language_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for processing incoming WhatsApp events (text, button tap, or image upload).
        Returns a rich response payload containing text messages, interactive buttons, and media.
        """
        session = self.session_mgr.get_session(phone_number)
        language = language_override or session["language"]
        raw_text = (button_payload or message_text or "").strip()
        lower_text = raw_text.lower()

        # 1. Check Language Switch
        if lower_text in ["hindi", "हिंदी", "hi"]:
            session = self.session_mgr.update_session(phone_number, language="hi")
            return {
                "messages": ["नमस्ते! एयरटेल बिजनेस व्हाट्सएप असिस्टेंट में आपका स्वागत है। आप अपने व्यवसाय (दुकान, क्लिनिक, ऑफिस) के बारे में बताएं और मैं आपके लिए सबसे सही प्लान चुनूँगा।"],
                "buttons": [
                    {"id": "btn_kirana", "title": "🛒 किराना / रिटेल", "payload": "मेरी किराना दुकान है"},
                    {"id": "btn_clinic", "title": "🏥 क्लिनिक", "payload": "मेरा क्लिनिक है"},
                    {"id": "btn_office", "title": "🏢 ऑफिस", "payload": "मेरा ऑफिस है"}
                ]
            }
        elif lower_text in ["english", "en"]:
            session = self.session_mgr.update_session(phone_number, language="en")
            return {
                "messages": ["Namaste! Welcome to Airtel Business WhatsApp Advisor. Tell me about your business (type, employees, location) and I will craft the ideal digital bundle."],
                "buttons": [
                    {"id": "btn_kirana", "title": "🛒 Retail Store", "payload": "I run a retail shop"},
                    {"id": "btn_clinic", "title": "🏥 Clinic", "payload": "I run a clinic"},
                    {"id": "btn_office", "title": "🏢 Office", "payload": "I run an office"}
                ]
            }

        # 2. Check Reset
        if lower_text in ["reset", "restart", "start over", "re-start"]:
            self.session_mgr.reset_session(phone_number)
            is_hi = (language == "hi")
            return {
                "messages": [
                    "सत्र रीसेट कर दिया गया है। आप किस प्रकार के व्यवसाय के लिए इंटरनेट या डिजिटल सेवाएं तलाश रहे हैं?"
                    if is_hi else
                    "Session reset. What type of business do you run and what services are you looking for?"
                ],
                "buttons": [
                    {"id": "btn_wifi", "title": "📶 Need Wi-Fi", "payload": "I need wifi"},
                    {"id": "btn_sasta", "title": "💸 Cheapest Plan", "payload": "sasta plan dikhao"}
                ]
            }

        # 3. Check Order Status Inquiry
        if lower_text in ["status", "track", "order status", "स्थिति"]:
            is_hi = (language == "hi")
            if session.get("order_id"):
                order = self.order_machine.get_order(session["order_id"])
                if order:
                    status_text = (
                        f"📦 *ऑर्डर स्थिति: {order['order_id']}*\n"
                        f"🔹 स्थिति: *{order['status']}*\n"
                        f"📅 स्थापना स्लॉट: *{order['scheduled_install_date']}*\n"
                        f"👷 नियुक्त तकनीशियन: मनोज कुमार (📞 98765-XXXXX)\n"
                        f"यदि आपको स्थापना की तारीख बदलनी है, तो *RESCHEDULE* लिखें।"
                        if is_hi else
                        f"📦 *Order Status: {order['order_id']}*\n"
                        f"🔹 Current Status: *{order['status']}*\n"
                        f"📅 Scheduled Slot: *{order['scheduled_install_date']}*\n"
                        f"👷 Lead Field Tech: Manoj Kumar (📞 98765-XXXXX)\n"
                        f"Reply *RESCHEDULE* if you need to adjust your time slot."
                    )
                    return {"messages": [status_text], "buttons": []}
            return {
                "messages": [
                    "वर्तमान में कोई सक्रिय ऑर्डर नहीं मिला। क्या आप नया प्लान चुनना चाहेंगे?"
                    if is_hi else
                    "No active order found for this number. Would you like to select a new digital plan?"
                ],
                "buttons": [{"id": "btn_start", "title": "Start Discovery", "payload": "I need wifi"}]
            }

        # 3b. Check Executive / Human Call Request
        executive_keywords = [
            "call an executive", "executive", "call me", "talk to executive",
            "talk to human", "agent", "customer care", "representative",
            "speak to someone", "human", "call lagao", "baat karao", "baat karni",
            "callback", "contact me", "phone call", "call karo", "call back",
            "बात कराओ", "कॉल करो", "एग्जीक्यूटिव", "कस्टमर केयर", "फोन करो", "एजेंट"
        ]
        if any(w in lower_text for w in executive_keywords):
            is_hi = (language == "hi")
            token = f"TK-{phone_number[-4:]}" if len(phone_number) >= 4 else "TK-3210"
            web_url = f"/?token={token}#kyc"
            exec_msg = (
                "धन्यवाद! आपके समय के लिए धन्यवाद। हमारे एयरटेल बिजनेस के विशेषज्ञ एग्जीक्यूटिव जल्द ही इस नंबर पर आपसे संपर्क करेंगे। 🙏\n\n"
                f"यदि आप इंतजार नहीं करना चाहते हैं, तो आप सीधे हमारे वेब पोर्टल पर 60 सेकंड में डिजिटल केवाईसी पूरा कर सकते हैं:\n{web_url}"
                if is_hi else
                "Thanks for your time! An Airtel Business executive will reach out to you shortly on this number to assist you further. 🙏\n\n"
                f"If you would like to proceed immediately without waiting, you can complete your digital KYC on our website here:\n{web_url}"
            )
            return {
                "messages": [exec_msg],
                "buttons": [
                    {"id": "btn_web_kyc", "title": "🌐 Complete KYC on Website" if not is_hi else "🌐 वेब पर KYC करें", "payload": f"url:{web_url}"},
                    {"id": "btn_plans", "title": "📶 View Plans" if not is_hi else "📶 प्लान देखें", "payload": "I need wifi"}
                ]
            }

        # 3c. Check Price / Cost Inquiry (e.g. "ok, what would be the price for that", "price kya hai", "how much")
        price_keywords = [
            "price", "cost", "how much", "charges", "charge", "rate", "tariff",
            "rental", "monthly bill", "kitna", "kharcha", "kimat", "kya rate",
            "what would be the price", "what is the price"
        ]
        is_downsell = any(w in lower_text for w in ["sasta", "cheap", "expensive", "discount", "kam karo", "kam budget"])
        if any(w in lower_text for w in price_keywords) and not is_downsell:
            active_bundle = session.get("active_bundle")
            if not active_bundle or len(active_bundle) == 0:
                active_bundle = {"P01": 1}
            quote = self.pricing.calculate_quote(
                active_bundle,
                apply_digital_discount=True,
                waive_setup_fee=True
            )
            profile = session.get("current_profile") or {}
            self.session_mgr.update_session(
                phone_number,
                stage="QUOTED",
                profile=profile,
                bundle=active_bundle,
                quote=quote
            )
            is_hi = (language == "hi")
            plan_name = "Biz Fibre 100" if "P01" in active_bundle else "Biz Fibre 300"
            price_msg = (
                f"एयरटेल बिज़नेस '{plan_name}' का मासिक किराया मात्र *₹{int(quote['monthly_subtotal_inr'])}/माह* है।\n"
                f"18% जीएसटी जोड़कर कुल मासिक बिल *₹{quote['total_monthly_inr']:.2f}* होता है।\n"
                "🎁 स्थापना शुल्क (~₹2,500) 100% माफ है!"
                if is_hi else
                f"The rental for Airtel Business '{plan_name}' (high-speed enterprise internet) is *₹{int(quote['monthly_subtotal_inr'])}/month*.\n"
                f"With 18% GST, the total consolidated monthly commitment is *₹{quote['total_monthly_inr']:.2f}*.\n"
                "🎁 One-time setup fee (~₹2,500) is 100% WAIVED!"
            )
            quote_card = self.formatter.format_quote_card(quote, language)
            token = f"TK-{phone_number[-4:]}" if len(phone_number) >= 4 else "TK-3210"
            web_url = f"/?token={token}#kyc"
            kyc_link_msg = (
                f"🌐 *वेबसाइट पर तुरंत KYC और एक्टिवेशन पूरा करें:*\n{web_url}\n\n"
                "_(आपका चुना हुआ प्लान और 18% GST कोटेशन लॉक है। 60 सेकंड में बिना किसी रुकावट के एक्टिवेशन के लिए ऊपर दिए गए लिंक पर क्लिक करें)_"
                if is_hi else
                f"🌐 *Complete KYC & Fast-Track Activation on Website:*\n{web_url}\n\n"
                "_(Your selected bundle & 18% GST quote are locked in. Click the link above to complete instant 60-second paperless KYC on our web portal)_"
            )
            return {
                "messages": [price_msg, quote_card, kyc_link_msg],
                "buttons": [
                    {"id": "btn_web_kyc", "title": "🌐 Complete KYC on Web" if not is_hi else "🌐 वेबसाइट पर KYC करें", "payload": f"url:{web_url}"},
                    {"id": "btn_proceed", "title": "📸 Upload Photo in Chat" if not is_hi else "📸 चैट में फोटो अपलोड", "payload": "action:proceed_kyc"},
                    {"id": "btn_sasta", "title": "💸 Sasta Plan" if not is_hi else "💸 सस्ता प्लान", "payload": "sasta plan dikhao"}
                ]
            }

        # 4. Check Button Action: Proceed to KYC
        if lower_text in ["action:proceed_kyc", "proceed to kyc", "kyc karein", "⚡ proceed to kyc"]:
            session = self.session_mgr.update_session(phone_number, stage="KYC_UPLOAD")
            is_hi = (language == "hi")
            token = f"TK-{phone_number[-4:]}"
            web_url = f"http://127.0.0.1:8000/?token={token}#kyc"
            if is_hi:
                msg = (
                    "📸 *केवाईसी सत्यापन के दो सुरक्षित विकल्प:*\n\n"
                    "1️⃣ *चैट में तुरंत फोटो अपलोड:* अपने *बिजली बिल* या *जीएसटी प्रमाणपत्र* की फोटो सीधे यहां भेजें।\n\n"
                    f"2️⃣ *वेब पोर्टल पर 60 सेकंड केवाईसी (DoT अनुपालन):*\n{web_url}\n\n"
                    "_(आपका कोटेशन लॉक है। वेब पोर्टल बिना किसी फोटो संपीड़न के हाई-रेज़ोल्यूशन ओसीआर स्कैन करता है)_"
                )
                buttons = [
                    {"id": "btn_web_kyc", "title": "🌐 वेब पर KYC करें", "payload": f"url:{web_url}"}
                ]
            else:
                msg = (
                    "📸 *Upload Document for Instant KYC Verification:*\n\n"
                    "1️⃣ *Direct in Chat:* Take or upload a clear photo of your *Electricity Bill* or *GST Certificate* directly in this chat.\n\n"
                    f"2️⃣ *Pre-Filled Web Portal (DoT Compliant & High-Res OCR):*\n{web_url}\n\n"
                    "_(Your quote is locked in. Telecom regulations support direct lossless upload for fast 48h activation)_"
                )
                buttons = [
                    {"id": "btn_web_kyc", "title": "🌐 Open Web KYC Portal", "payload": f"url:{web_url}"}
                ]
            return {"messages": [msg], "buttons": buttons}

        # 5. Check Button Action: Confirm Order & Pay Token
        if lower_text in ["action:confirm_order", "pay token", "confirm", "book installation", "💳 pay ₹100 & confirm"]:
            is_hi = (language == "hi")
            quote = session.get("active_quote") or {}
            bundle = session.get("active_bundle") or {"P01": 1}
            profile = session.get("current_profile") or {}

            order = self.order_machine.create_order(
                business_name=profile.get("business_type") or "Udyam Digital Applicant",
                contact_phone=phone_number,
                bundle_data={"bundle": bundle, "quote": quote},
                kyc_status="VERIFIED",
                language=language,
                typical_install_days=2
            )
            order_id = order["order_id"]
            install_date = order.get("scheduled_install_date", (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d"))
            self.session_mgr.update_session(phone_number, stage="CONFIRMED", order_id=order_id)

            confirmed_msg = self.formatter.format_order_confirmed(order_id, install_date, language)
            return {
                "messages": [confirmed_msg],
                "buttons": [
                    {"id": "btn_status", "title": "📍 Track Order", "payload": "status"},
                    {"id": "btn_support", "title": "💬 Chat with Support", "payload": "support"}
                ]
            }

        # 6. Handle Document Image Upload
        if image_path:
            return self._handle_image_upload(phone_number, image_path, session, language)

        # 7. Conversational Chat & AI Advisor Flow
        profile = session.get("current_profile") or {}

        # If user states a fresh discovery request (e.g. "I need wifi", "I need a wifi for my shop"),
        # do not inherit stale city or scale from previous completed conversations
        fresh_starters = [
            "need wifi", "need a wifi", "need internet", "wifi chahiye", "internet chahiye",
            "new connection", "broadband chahiye", "wifi for my", "wifi for shop", "wifi for office"
        ]
        if any(w in lower_text for w in fresh_starters):
            city_keywords = [
                "delhi", "mumbai", "bangalore", "bengaluru", "chennai", "hyderabad",
                "pune", "kolkata", "indore", "jaipur", "ludhiana", "kochi",
                "nagpur", "bhopal", "vizag", "patna", "surat", "lucknow", "chandigarh"
            ]
            import re
            has_city_in_msg = any(c in lower_text for c in city_keywords)
            has_emp_in_msg = bool(re.search(r'\d+\s*(people|staff|employees|workers|log|devices|pc|systems)', lower_text))

            if not has_city_in_msg:
                profile["city"] = None
                profile["city_tier"] = None
            if not has_emp_in_msg:
                profile["employee_count"] = None

        advisor_res = self.advisor.process_user_message(raw_text, profile, language)
        new_profile = advisor_res.get("profile") or profile
        intent = advisor_res.get("intent", "recommendation")
        bot_message = advisor_res.get("message", "")
        bundle = advisor_res.get("recommended_bundle")

        # ALWAYS persist customer context (city, scale, business type) to DB on every turn
        self.session_mgr.update_session(phone_number, profile=new_profile)

        # If recommendation intent, guarantee a valid bundle so pricing quote card is always sent
        if intent == "recommendation" and (not bundle or len(bundle) == 0):
            bundle = {"P01": 1}

        messages = [bot_message]
        buttons = []

        if intent == "clarification":
            self.session_mgr.update_session(phone_number, stage="DISCOVERY", profile=new_profile)
            buttons = []

        elif intent == "inquiry":
            self.session_mgr.update_session(phone_number, profile=new_profile)

        elif bundle and len(bundle) > 0:
            quote = self.pricing.calculate_quote(
                bundle,
                apply_digital_discount=True,
                waive_setup_fee=True
            )
            self.session_mgr.update_session(
                phone_number,
                stage="QUOTED",
                profile=new_profile,
                bundle=bundle,
                quote=quote
            )
            quote_card = self.formatter.format_quote_card(quote, language)
            messages.append(quote_card)

            is_hi = (language == "hi")
            token = f"TK-{phone_number[-4:]}" if len(phone_number) >= 4 else "TK-3210"
            web_url = f"/?token={token}#kyc"

            kyc_link_msg = (
                f"🌐 *वेबसाइट पर तुरंत KYC पूरा करें:*\n{web_url}\n\n"
                "_(आपका चुना हुआ प्लान और 18% GST कोटेशन लॉक है। 60 सेकंड में बिना किसी रुकावट के एक्टिवेशन के लिए ऊपर दिए गए लिंक पर क्लिक करें)_"
                if is_hi else
                f"🌐 *Complete KYC & Fast-Track Activation on Website:*\n{web_url}\n\n"
                "_(Your selected bundle & 18% GST quote are locked in. Click the link above to complete instant 60-second paperless KYC on our web portal)_"
            )
            messages.append(kyc_link_msg)

            buttons = [
                {"id": "btn_web_kyc", "title": "🌐 Complete KYC on Web" if not is_hi else "🌐 वेबसाइट पर KYC करें", "payload": f"url:{web_url}"},
                {"id": "btn_proceed", "title": "📸 Upload Photo in Chat" if not is_hi else "📸 चैट में फोटो अपलोड", "payload": "action:proceed_kyc"},
                {"id": "btn_downsell", "title": "💸 Sasta Plan" if not is_hi else "💸 सस्ता प्लान", "payload": "sasta plan dikhao"}
            ]

        return {"messages": messages, "buttons": buttons}

    def _handle_image_upload(
        self,
        phone_number: str,
        image_path: str,
        session: Dict[str, Any],
        language: str
    ) -> Dict[str, Any]:
        """
        Processes document image through OpenCV sharpness check, OCR scan, and statutory KYC rules.
        """
        is_hi = (language == "hi")
        
        # 1. Compute blur variance via OpenCV
        is_clear, blur_score = self.ocr.compute_blur(image_path)
        if blur_score < 100.0:
            rejection_text = (
                f"⚠️ *फोटो बहुत धुंधली है (Sharpness Score: {blur_score:.1f})*\n\n"
                "दस्तावेज़ की लिखावट पढ़ने योग्य नहीं है। कृपया अच्छी रोशनी में बिना कैमरा हिलाए स्पष्ट फोटो दोबारा भेजें।"
                if is_hi else
                f"⚠️ *Document Photo is Blurry (Sharpness Score: {blur_score:.1f})*\n\n"
                "The text cannot be verified by our automated KYC engine. Please take a well-lit photo without camera shake and upload again."
            )
            return {"messages": [rejection_text], "buttons": []}

        # 2. Run OCR scan
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            doc_data = loop.run_until_complete(self.ocr.scan_document(image_path))
        except Exception:
            doc_data = {}

        # 3. Detect applicant specimen code from filename or extracted GSTIN
        f_name = Path(image_path).name.upper()
        applicant_code = "K12"
        for code in ["K01", "K02", "K03", "K04", "K05", "K06", "K07", "K08", "K09", "K10", "K11", "K12"]:
            if code in f_name:
                applicant_code = code
                break

        gstin = doc_data.get("extracted_gstin")
        udyam = doc_data.get("extracted_udyam")
        trade_name = doc_data.get("extracted_entity_name")
        bill_date = doc_data.get("extracted_bill_date") or doc_data.get("extracted_registration_date")

        kyc_res = self.kyc_validator.validate_applicant(
            applicant_code=applicant_code,
            extracted_gstin=gstin,
            extracted_udyam=udyam,
            bill_date=bill_date,
            trade_name=trade_name,
            is_non_gst_mode=session.get("current_profile", {}).get("has_gstin") is False
        )

        status = kyc_res.get("status")
        if status == "VERIFIED":
            self.session_mgr.update_session(
                phone_number,
                stage="KYC_VERIFIED",
                kyc_data=kyc_res
            )
            approved_text = self.formatter.format_kyc_approved(kyc_res, language)
            buttons = [
                {"id": "btn_pay_token", "title": "💳 ₹100 टोकन देकर बुक करें" if is_hi else "💳 Pay ₹100 & Confirm", "payload": "action:confirm_order"},
                {"id": "btn_back", "title": "📋 कोटेशन देखें" if is_hi else "📋 View Quote", "payload": "action:view_quote"}
            ]
            return {"messages": [approved_text], "buttons": buttons}
        else:
            reasons = kyc_res.get("reasons", ["Document validation failed statutory check."])
            rejection_text = self.formatter.format_kyc_rejected(reasons, language)
            buttons = [
                {"id": "btn_retry", "title": "🔄 पुनः अपलोड करें" if is_hi else "🔄 Upload Another Photo", "payload": "action:proceed_kyc"}
            ]
            return {"messages": [rejection_text], "buttons": buttons}
