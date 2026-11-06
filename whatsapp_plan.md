# Project Udyam Digital — WhatsApp AI Business Advisor & KYC Plan
*Unified Conversational Commerce, Zero-Touch KYC Ingestion & Proactive Lead Recovery via WhatsApp*

---

## 1. Executive Summary & Strategic Rationale

In Indian MSME markets (Tier-2/3 cities like Indore, Jaipur, Ludhiana, Kochi), business owners rarely complete desktop web forms. They operate primarily on WhatsApp.

Analysis of the official hackathon specimen leads (`audit_data.py` / 1,000 lost leads) revealed:
- **107 leads dropped out because they *"Decided to wait"* to consult partners or family.**
- **164 leads dropped out because *"Owner had no time for a physical visit"*.**
- **193 leads stalled on *"Installation delayed beyond 21 days"* with zero status visibility.**

Bringing the **AI Business Advisor and Straight-Through KYC onto WhatsApp** directly targets these root causes:
1. **Zero-Friction Discovery**: Owner asks questions in Hindi or English using voice or text without downloading an app or visiting a website.
2. **Instant Shareable PDF Quote**: 1-tap forward to partners/co-owners directly inside WhatsApp.
3. **Camera-to-KYC**: Snapping a photo of a GST certificate or electricity bill inside WhatsApp automatically triggers OCR + Rule 3 statutory validation.
4. **Proactive Order Milestones**: Replaces status-chase phone calls with automated WhatsApp milestone updates (e.g., *"Engineer Manoj is scheduled to install tomorrow at 11 AM"*).

---

## 2. High-Level Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                   WhatsApp User (MSME Business Owner)                  │
│                     [Voice Notes, Texts, Photos]                       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ (Encrypted HTTPS)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│             Meta WhatsApp Cloud API / Webhook Gateway                  │
│              POST /api/whatsapp/webhook  &  GET /api/whatsapp/webhook  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│             WhatsApp Session & State Manager (SQLite / In-Memory)      │
│  - Phone Keyed: 9198XXXXXXXX                                          │
│  - Session Stages: CLARIFY -> QUOTE -> DOC_UPLOAD -> CONFIRMED -> TRACK │
└─────────────┬────────────────────────────────────────────┬─────────────┘
              │ (Text / Query)                             │ (Image / PDF)
              ▼                                            ▼
┌─────────────────────────────────┐      ┌────────────────────────────────┐
│   AI Business Advisor Adapter   │      │     KYC & OCR Pipeline         │
│  - Google Gemini 3.5 Flash      │      │  - Media Download from Meta    │
│  - Progressive Clarification    │      │  - OpenCV Laplacian Sharpness  │
│  - Policy Catalog Guardrails    │      │  - Tesseract OCR & Date Check  │
│  - 18% GST Quotation Engine     │      │  - Rule 3 Statutory Traps      │
└─────────────┬───────────────────┘      └────────────────┬───────────────┘
              │                                           │
              └─────────────────────┬─────────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│             WhatsApp Response Dispatcher (Outbound Graph API)          │
│  - Interactive Quick-Reply Buttons (e.g., [Sasta Plan], [Confirm])     │
│  - Rich Text Cards (*Bold*, Emoji, Linebreaks)                         │
│  - Dynamic 1-Page PDF / Image Quotation Attachment                     │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Conversational Journey & Experience Design

### Step 1: Progressive Clarification (Handling Vague Queries)
When a user sends a vague message like *"Mujhe wifi chahiye"* or *"I need internet for office"*:
- **Advisor Action**: Does not add default SKUs blindly.
- **WhatsApp Message**:
  > *नमस्ते! एयरटेल बिजनेस में आपका स्वागत है। 🙏*
  > 
  > आपके व्यवसाय के लिए सबसे सही प्लान चुनने के लिए कृपया 3 बातें बताएं:
  > 1️⃣ आपका किस प्रकार का काम/दुकान है? (उदा. किराना, क्लिनिक, ऑफिस)
  > 2️⃣ कितने कर्मचारी या डिवाइसेस इंटरनेट से जुड़ेंगे?
  > 3️⃣ क्या आपको सीसीटीवी कैमरा, यूपीआई साउंडबॉक्स या बैकअप डोंगल की भी जरूरत है?
- **Interactive Quick-Reply Buttons**:
  - `[🛒 किराना / रिटेल]`
  - `[🏥 क्लिनिक / फार्मेसी]`
  - `[🏢 ऑफिस / सीए फर्म]`

### Step 2: Policy-Guarded Quote Generation
When user replies: *"Kirana store in Indore, 2 staff, UPI payments needed"*:
- **Advisor Action**:
  - Automatically identifies profile: Micro Retail, Tier-2 city, Non-GST.
  - Applies non-GST safe mode (no ILL `P05` or SIP Trunk `P21`).
  - Bundles: `P01` (Biz Fibre 100), `P07` (Soundbox), `P19` (Cloud POS).
- **WhatsApp Message**:
  > *📋 आपके व्यवसाय के लिए तैयार किया गया डिजिटल प्लान:*
  > 
  > 🔹 *Biz Fibre 100 (P01)* — ₹999/माह  
  > 🔹 *Airtel Payments Soundbox (P07)* — ₹199/माह  
  > 🔹 *Cloud POS & Billing (P19)* — ₹499/माह  
  > 
  > ━━━━━━━━━━━━━━━━━━━  
  > 💵 *मासिक किराया:* ₹1,697  
  > 🏛️ *18% GST:* ₹305.46  
  > 🏷️ *कुल मासिक बिल:* *₹2,002.46* (कंसोलिडेटेड बिल)  
  > 🎁 *सेटअप शुल्क:* ₹0 (डिजिटल ऑनबोर्डिंग पर 100% माफ)  
  > ━━━━━━━━━━━━━━━━━━━  
  > 💡 *यह प्लान क्यों चुना?*  
  > • साउंडबॉक्स हर यूपीआई भुगतान की तुरंत बोलकर पुष्टि करेगा।  
  > • 100 Mbps फाइबर से पीक आवर्स में बिलिंग कभी नहीं रुकेगी।
- **Interactive Buttons**:
  - `[📄 PDF कोटेशन डाउनलोड करें]`
  - `[💸 सस्ता प्लान दिखाओ]`
  - `[⚡ आगे बढ़ें (तुरंत KYC)]`

### Step 3: Camera-to-KYC Document Verification on WhatsApp
When the user taps `[⚡ आगे बढ़ें (तुरंत KYC)]`:
- **WhatsApp Message**:
  > *कृपया अपनी दुकान/ऑफिस के बिजली बिल या जीएसटी सर्टिफिकेट की एक साफ फोटो यहां भेजें।* 📸
- **User Action**: Snaps a photo of their bill or GST doc using the WhatsApp camera.
- **Backend Flow**:
  1. Webhook receives message with `type: "image"` and `image.id`.
  2. Downloads media payload from Meta Graph API.
  3. Runs `OcrEngine.extract_and_validate()`:
     - Laplacian variance check: If $< 100$ (e.g. hackathon specimen `K04`), rejects instantly:
       > *⚠️ फोटो बहुत धुंधली है (Sharpness Score: 42.1)। कृपया रोशनी में बिना कैमरे हिलाए दोबारा फोटो भेजें।*
     - Date check: If bill $> 90$ days old (e.g. `K11`), flags freshness:
       > *⚠️ यह बिजली बिल 90 दिनों से अधिक पुराना है। कृपया नवीनतम बिल भेजें।*
     - Active GSTIN Match: If valid (e.g. `K12`), instantly parses name and address.
- **WhatsApp Success Message**:
  > *✅ केवाईसी तुरंत सत्यापित हो गई!*  
  > 🏢 *व्यवसाय का नाम:* Trinity Bake House Pvt Ltd  
  > 📍 *पता:* Shop 188, Ludhiana  
  > 🛡️ *स्थिति:* जीएसटी पोर्टल में सत्यापित और सक्रिय  
  > 
  > केवल *₹100* का टोकन शुल्क देकर अपनी स्थापना (Installation) बुक करें।  
  > (यह टोकन पहले महीने के बिल में 100% एडजस्ट हो जाएगा)
- **Interactive Button**: `[💳 ₹100 टोकन भुगतान करें]`

### Step 4: Proactive Milestone Notifications (Status Chase Reduction)
Once booked:
- **T+2 hours**: *"नमस्ते! आपका ऑर्डर #ORD-8829 दर्ज कर लिया गया है। इंजीनियर मनोज कुमार (📞 98765-XXXXX) को आपकी साइट के लिए नियुक्त किया गया है।"*
- **T+24 hours**: *"अपडेट: कल सुबह 11:00 AM पर फाइबर केबलिंग और वाईफाई राउटर इंस्टॉलेशन निर्धारित है। यदि आप समय बदलना चाहते हैं, तो 'RESCHEDULE' लिखें।"*
- **T+48 hours (Post Handover)**: *"स्थापना पूर्ण हुई! कृपया हमारे तकनीशियन के कार्य को 1 से 5 स्टार रेटिंग दें।"* `[⭐️ 5]` `[⭐️ 4]` `[⭐️ 3]`

---

## 4. Implementation Strategy (Dual-Track Approach)

To ensure this can be demonstrated immediately during the hackathon judging without relying on external Meta business verification, we implement a **Dual-Track Architecture**:

```
                       ┌─────────────────────────┐
                       │   WhatsApp Engine Core  │
                       └────────────┬────────────┘
                                    │
           ┌────────────────────────┴────────────────────────┐
           ▼                                                 ▼
┌─────────────────────────────┐           ┌────────────────────────────────┐
│   Track A: Live Meta API    │           │  Track B: Interactive Web      │
│   (Production / Staging)    │           │      WhatsApp Simulator        │
├─────────────────────────────┤           ├────────────────────────────────┤
│ • /api/whatsapp/webhook     │           │ • /whatsapp-simulator UI       │
│ • Validates Meta token      │           │ • Realistic phone frame with   │
│ • Downloads media via Graph │           │   green WhatsApp chat layout   │
│ • Works with ngrok / domain │           │ • Camera photo upload button   │
│                             │           │ • Instant interactive demo for │
│                             │           │   hackathon presentation       │
└─────────────────────────────┘           └────────────────────────────────┘
```

### Track A: Real WhatsApp Cloud API Endpoints
1. `GET /api/whatsapp/webhook`:
   - Validates `hub.mode == "subscribe"` and `hub.verify_token == WHATSAPP_VERIFY_TOKEN`.
   - Returns `hub.challenge` with HTTP 200.
2. `POST /api/whatsapp/webhook`:
   - Parses Meta webhook payload (`entry[0].changes[0].value.messages[0]`).
   - Routes text, buttons, and media to the `WhatsAppSessionManager`.
   - Sends outbound replies via `https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages`.

### Track B: Built-in Visual WhatsApp Phone Simulator
- An embedded, ultra-clean mobile mockup accessible directly at `/whatsapp-simulator` or via a button in the main navbar (*"📱 Open WhatsApp Mode"*).
- Allows live testing of:
  - Text prompts (*"I need wifi"*, *"यह प्लान बहुत महंगा है"*).
  - Document image uploads (drag-and-drop or file selector mimicking the phone camera).
  - Interactive quick-reply buttons and quote rendering.
- **Zero setup needed for judges**: Operates 100% locally on `http://127.0.0.1:8000`.

---

## 5. WhatsApp Session Manager & Data Schema

Each incoming phone number is assigned a lightweight persistent session in `udyam_orders.db`:

```sql
CREATE TABLE IF NOT EXISTS whatsapp_sessions (
    phone_number TEXT PRIMARY KEY,
    current_stage TEXT NOT NULL DEFAULT 'DISCOVERY', -- DISCOVERY, QUOTED, KYC_UPLOAD, CONFIRMED
    language TEXT NOT NULL DEFAULT 'en',            -- 'en' or 'hi'
    current_profile TEXT,                           -- JSON: business_type, employee_count, city, etc.
    active_bundle TEXT,                            -- JSON: {"P01": 1, "P07": 2, ...}
    last_ocr_data TEXT,                            -- JSON: extracted GSTIN, name, address, blur score
    order_id TEXT,                                 -- Linked Udyam Order ID
    last_interaction DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 6. Implementation Checklist & Deliverables

| Phase | Milestone | Files Involved | Status |
| :--- | :--- | :--- | :--- |
| **Phase 1** | Configuration & Meta Cloud API Contract | `app/config.py`, `.env` | Ready to build |
| **Phase 2** | WhatsApp Session Engine & State Machine | `app/modules/whatsapp/session.py` | Ready to build |
| **Phase 3** | Formatter & Gemini Adapter for WhatsApp | `app/modules/whatsapp/formatter.py` | Ready to build |
| **Phase 4** | Webhook Handlers (GET / POST) & Media Download | `app/modules/whatsapp/router.py`, `app/main.py` | Ready to build |
| **Phase 5** | Interactive WhatsApp Mobile Phone Simulator | `app/static/whatsapp_simulator.html`, `app/static/whatsapp.js` | Ready to build |
| **Phase 6** | End-to-end Test Suite | `test_whatsapp_flow.py` | Ready to test |

---

## 7. Safety, Cost & Privacy Controls

1. **Free-Tier Protection**: Uses existing Google Gemini free-tier keys via the shared `AdvisorAdapter` failover mechanism.
2. **DPDP Act Compliance**: Documents received via WhatsApp are stored locally in the secure `uploads/` folder with temporary 48-hour retention tags; no PII is echoed back in unredacted form.
3. **Strict Policy Compliance**: All quotes generated over WhatsApp pass through the same deterministic `CatalogEngine` and `Rule3PolicyValidator` guardrails as the web portal.
4. **Git Constraint**: All changes remain local until explicit user testing and sign-off.

