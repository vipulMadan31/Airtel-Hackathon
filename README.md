# Project Udyam Digital — Airtel Business Onboarding Prototype
> **Airtel SYNC Hackathon 2026 — Enterprise Track A: MSME Digital Self-Serve Acquisition & Onboarding**

---

## 🚀 Overview

Project Udyam Digital is an instant, digital-first, self-serve acquisition and onboarding platform designed for Indian Micro, Small, and Medium Enterprises (MSMEs). 

It solves the four critical operational bottlenecks of legacy telco enterprise onboarding:
1. **Time-to-Activate (TTA)**: Reduced from **17.6 days to < 48 hours**.
2. **Customer Acquisition Cost (CAC)**: Slashed from **₹15,000 to < ₹2,500** via zero-touch digital discovery.
3. **Funnel Drop-Off**: Conversions boosted from **7.36% to > 25%** with a 4-step progressive down-sell sequence and transparent pricing.
4. **Channel Harmony**: Local field agents and sales partners earn **15% recurring commissions** on digital referrals, eliminating channel conflict.

---

## 🏛️ The 4 Architectural Pillars

```
┌────────────────────────────────────────────────────────────────────────┐
│                        PROJECT UDYAM DIGITAL                           │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
    ┌────────────────┬───────────────┴───────────────┬─────────────────┐
    ▼                ▼                               ▼                 ▼
[ Pillar 1 ]     [ Pillar 2 ]                  [ Pillar 3 ]      [ Pillar 4 ]
Bilingual AI    Transparent 3-Bucket          Smart KYC & Real   Self-Serve Tracker
Advisor & Chat  Pricing Reconciler            OCR Pipeline       & Handover
- English/Hindi - Itemized 18% GST            - Native Win OCR   - Milestone timeline
- Persona chips - Setup Fee Waived (₹2,500)   - OpenCV Blur var  - Reschedule date
- Why-we-picked - ₹499 Booking Token          - 90-day validity  - Post-install NPS
                - 4-Step Down-Sell Sequence   - DPDP 2025 Notice - Partner Portal
```

### 1. Bilingual Conversational Advisor (English & हिंदी)
* Single-tap vernacular toggle translates all UI copy, chip labels, card tags, notices, and chat responses.
* Conversational intent classifier handles sector-specific bundles (Kirana, Clinic, CA, Restaurant) with explainability tags (*"Why we picked this for your business"* / *"हमने आपके व्यवसाय के लिए इसे क्यों चुना"*).
* Pluggable LLM architecture ready for Gemini / OpenAI API keys while operating deterministically out of the box.

### 2. Transparent 3-Bucket Catalog & Pricing Reconciler
* Solves MSME product overload across all 25 catalogue products:
  * **Bucket A**: Alternative Base Connectivity Plans
  * **Bucket B**: Modular Value Add-Ons (CCTV, Cloud POS, Secure Email)
  * **Bucket C**: Ineligible / Locked Plans (with explicit rationale to protect non-GST buyers)
* **Reconciled Pricing**: Automatically itemizes 18% GST, waives the one-time ₹2,500 setup fee, and introduces the **₹499 Refundable Booking Token** model via UPI AutoPay.
* **4-Step Controlled Down-Sell**: Automatically strips non-essential add-ons when a customer requests a cheaper option (*"Sasta plan dikhao"*).

### 3. Smart KYC with Real OCR & Statutory Trap Prevention
* Real drag-and-drop document upload for **GST Registration Certificates** and **Electricity Bills (Address Proof)**.
* Native Windows Media OCR (`winocr`) + OpenCV Laplacian variance blur filter (threshold: 100.0).
* **Editable Extracted Fields Review Card**: Allows applicants to review and correct OCR-extracted GSTIN, business name, and address before statutory submission.
* **Registry Rule Checks**:
  * Clean passes: **K12 (Star Electronics)** $\rightarrow$ Instant Straight-Through Processing approval.
  * Blurry upload trap: **K04 (Ganesh Woodcraft)** $\rightarrow$ Action Required prompt.
  * Cancelled GST trap: **K01 (Vindhya Tours)** $\rightarrow$ Hard statutory rejection.
  * Expired utility bill trap: **K11 (Trinity Bake House)** $\rightarrow$ Hard rejection (>90 days old relative to benchmark `2026-07-15`).
* **DPDP Act 2023 & Rules 2025 Compliance**: Explicit purpose specification, itemized consent notices, and tamper-evident SQLite consent logging.

### 4. Self-Serve Order Tracker & Channel Partner Portal
* Real-time 4-step milestone timeline with assigned field lead engineer details.
* **Single-Tap Installation Date Rescheduling**: Lets the business owner change the installation date if unavailable.
* **Digital Handover & NPS Rating**: In-app 0–10 score recording post-activation.
* **Partner & Channel Portal**:
  * Unique referral links (`?ref=PTR-IND-882`) and QR codes for offline sales executives earning a 15% commission.
  * **Stalled Leads Recovery Queue**: Real leads from `smb_leads.csv` scored using a calibrated firmographic propensity algorithm (0–100) to prioritize high-value reactivation calls.

---

## 🛠️ Tech Stack

* **Backend**: Python 3.11+, FastAPI, Uvicorn, SQLite3
* **Computer Vision & OCR**: OpenCV (Laplacian Sharpness Filter), Native Windows Media OCR (`winocr`), TheFuzz (Levenshtein Fuzzy Matching)
* **Frontend**: Zero-dependency Vanilla JS SPA, Tailwind CSS (CDN), bilingual i18n dictionary
* **Testing**: Comprehensive end-to-end Python test suite and Chrome DevTools Protocol automation

---

## ⚡ Quickstart

### 1. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 2. Run the Application
```powershell
python run.py
```
Open your browser at: **`http://127.0.0.1:8000`**

### 3. Run Automated Tests
```powershell
python test_complete_prototype.py
python test_browser_clicks_proper.py
```

---

## 📁 Repository Structure

```text
├── app/
│   ├── config.py                  # Case reference dates (2026-07-15) & paths
│   ├── data_loader.py             # Singleton indexer for GSTIN, Udyam, & Leads
│   ├── main.py                    # FastAPI application & REST routing
│   ├── modules/
│   │   ├── advisor/               # Bilingual intent extractor & explainability
│   │   ├── catalog/               # 3-Bucket Drawer engine & dependency validator
│   │   ├── kyc/                   # OpenCV blur check, WinOCR, registry validator
│   │   ├── orders/                # SQLite state machine, rescheduling & NPS
│   │   └── partner/               # Referral engine & propensity lead recovery
│   └── static/
│       ├── app.js                 # State manager, OCR upload handler, tracker
│       ├── index.html             # Single-page UI with Tailwind & DPDP notices
│       ├── locales.js             # English & Hindi i18n dictionaries
│       └── styles.css             # Chat bubble formatting & custom scrollbars
├── YTL_TrackA_Udyam_Digital_Data/ # Official Hackathon Dataset (Registries & Specimen KYC)
├── audit_data.py                  # Dataset schema audit utility
├── PROJECT_EXECUTION_BLUEPRINT.md # Exhaustive architecture specification
├── requirements.txt               # Python package dependencies
├── run.py                         # Single-command launcher
├── test_browser_clicks_proper.py  # Chrome CDP browser click verification
└── test_complete_prototype.py     # 8-suite automated end-to-end test suite
```

---

## 🏆 Hackathon Evaluation Readiness

| Criteria | Implementation Evidence |
| :--- | :--- |
| **Pillar 1: Discovery** | Bilingual AI Advisor with persona chips and explainability tags |
| **Pillar 2: Transparent Pricing** | Itemized 18% GST, setup fee waiver, and 4-step progressive down-sell |
| **Pillar 3: Smart KYC** | Real file upload, OpenCV blur scoring, native Windows OCR, and mock registry verification |
| **Pillar 4: Tracker & Handover** | Real-time milestone tracker, date rescheduling, and NPS handover capture |
| **Channel Harmony** | Dedicated partner portal with referral links and calibrated propensity scores |
| **DPDP Compliance** | Rule 3 itemized notices, specified purpose limitation, and consent audit logs |
