from typing import Dict, Any, List, Optional

class WhatsAppFormatter:
    """
    Formats messages, quotes, KYC decisions, and interactive buttons
    specifically for the WhatsApp Business messaging experience.
    """

    @staticmethod
    def format_quote_card(quote: Dict[str, Any], language: str = "en") -> str:
        is_hi = (language == "hi")
        items = quote.get("items", [])
        subtotal = quote.get("monthly_subtotal_inr", 0.0)
        gst = quote.get("gst_18_inr", 0.0)
        total = quote.get("total_monthly_inr", 0.0)
        savings = quote.get("digital_exclusive_savings_monthly", 0.0)

        lines = []
        if is_hi:
            lines.append("📋 *एयरटेल बिजनेस — आपका डिजिटल कोटेशन*")
            lines.append("────────────────────────")
            for it in items:
                lines.append(f"• *{it['product_name']}* ({it['product_id']}) × {it['quantity']}")
                lines.append(f"  ₹{it['line_monthly_inr']:.2f}/माह  _{it['category']}_")
            lines.append("────────────────────────")
            lines.append(f"💵 *मासिक किराया:* ₹{subtotal:.2f}")
            lines.append(f"🏛️ *18% जीएसटी:* ₹{gst:.2f}")
            lines.append(f"🏷️ *कुल मासिक बिल:* *₹{total:.2f}* (कंसोलिडेटेड)")
            lines.append("🎁 *सेटअप शुल्क:* ~₹2,500.00~ *₹0.00 (100% माफ)*")
            if savings > 0:
                lines.append(f"⚡ *डिजिटल डिस्काउंट बचत:* ₹{savings:.2f}/माह")
        else:
            lines.append("📋 *AIRTEL BUSINESS — DIGITAL QUOTATION*")
            lines.append("────────────────────────")
            for it in items:
                lines.append(f"• *{it['product_name']}* ({it['product_id']}) × {it['quantity']}")
                lines.append(f"  ₹{it['line_monthly_inr']:.2f}/mo  _{it['category']}_")
            lines.append("────────────────────────")
            lines.append(f"💵 *Monthly Subtotal:* ₹{subtotal:.2f}")
            lines.append(f"🏛️ *18% GST:* ₹{gst:.2f}")
            lines.append(f"🏷️ *Total Monthly Commitment:* *₹{total:.2f}* (Consolidated)")
            lines.append("🎁 *One-time Setup Fee:* ~₹2,500.00~ *₹0.00 (Waived)*")
            if savings > 0:
                lines.append(f"⚡ *Self-Serve Discount Savings:* ₹{savings:.2f}/mo")

        return "\n".join(lines)

    @staticmethod
    def format_kyc_approved(data: Dict[str, Any], language: str = "en") -> str:
        is_hi = (language == "hi")
        reg = data.get("registry_details") or {}
        udyam = data.get("udyam_details") or {}
        name = reg.get("legal_name") or udyam.get("enterprise_name") or "Verified Applicant"
        addr = reg.get("principal_place_of_business") or (f"{udyam.get('city')}, {udyam.get('state')}" if udyam.get('city') else "Verified on Record")
        gstin = data.get("verified_fields", {}).get("gstin")

        if is_hi:
            lines = [
                "✅ *केवाईसी सत्यापित (Straight-Through Processing Approved)!*",
                "",
                f"🏢 *कानूनी नाम:* {name}",
                f"📍 *पंजीकृत पता:* {addr}"
            ]
            if gstin:
                lines.append(f"🛡️ *जीएसटी स्थिति:* सक्रिय ({gstin})")
            if udyam.get("udyam_number"):
                lines.append(f"📜 *उद्यम पंजीकरण:* {udyam.get('udyam_number')} ({udyam.get('enterprise_type', 'Micro')})")
            lines.extend([
                "",
                "⚡ *अगला कदम:* अपना स्लॉट सुरक्षित करने के लिए मात्र *₹100* का टोकन शुल्क दें।",
                "_(यह ₹100 आपके पहले महीने के बिल में 100% क्रेडिट हो जाएगा)_"
            ])
        else:
            lines = [
                "✅ *KYC VERIFIED (Straight-Through Processing Approved)!*",
                "",
                f"🏢 *Legal Entity:* {name}",
                f"📍 *Principal Address:* {addr}"
            ]
            if gstin:
                lines.append(f"🛡️ *GSTIN Status:* Active & Valid ({gstin})")
            if udyam.get("udyam_number"):
                lines.append(f"📜 *Udyam Registration:* {udyam.get('udyam_number')} ({udyam.get('enterprise_type', 'Micro')})")
            lines.extend([
                "",
                "⚡ *Next Step:* Pay a fully adjustable *₹100* booking token to lock in priority 48-hour installation.",
                "_(The ₹100 is credited 100% on your first monthly invoice)_"
            ])

        return "\n".join(lines)

    @staticmethod
    def format_kyc_rejected(reasons: List[str], language: str = "en") -> str:
        is_hi = (language == "hi")
        if is_hi:
            lines = [
                "❌ *केवाईसी अस्वीकृत (Statutory Trap Detected)*",
                "",
                "आपके दस्तावेज़ में निम्नलिखित नियम उल्लंघन पाया गया:"
            ]
            for r in reasons:
                lines.append(f"• {r}")
            lines.append("")
            lines.append("कृपया एक वैध और हालिया दस्तावेज़ की स्पष्ट फोटो पुनः भेजें।")
        else:
            lines = [
                "❌ *KYC REJECTED (Statutory Trap Detected)*",
                "",
                "The following policy compliance issue was flagged:"
            ]
            for r in reasons:
                lines.append(f"• {r}")
            lines.append("")
            lines.append("Please upload a clear, valid, and recent document to proceed.")

        return "\n".join(lines)

    @staticmethod
    def format_order_confirmed(order_id: str, install_date: str, language: str = "en") -> str:
        is_hi = (language == "hi")
        if is_hi:
            return (
                f"🎉 *बधाई हो! आपका ऑर्डर कन्फर्म हो गया है!*\n\n"
                f"📦 *ऑर्डर आईडी:* `{order_id}`\n"
                f"📅 *स्थापना तिथि:* {install_date}\n"
                f"👷 *फील्ड इंजीनियर:* मनोज कुमार (📞 98765-XXXXX)\n"
                f"💳 *टोकन भुगतान:* ₹100 सफल (पहले बिल में क्रेडिट होगा)\n\n"
                f"स्थापना की लाइव ट्रैकिंग के लिए किसी भी समय *STATUS* लिखकर भेजें।"
            )
        else:
            return (
                f"🎉 *Congratulations! Your Airtel Business Order is Confirmed!*\n\n"
                f"📦 *Order ID:* `{order_id}`\n"
                f"📅 *Scheduled Installation:* {install_date}\n"
                f"👷 *Field Lead:* Manoj Kumar (📞 98765-XXXXX)\n"
                f"💳 *Token Payment:* ₹100 Received (100% credited to first invoice)\n\n"
                f"Reply *STATUS* anytime to track live installation milestones."
            )
