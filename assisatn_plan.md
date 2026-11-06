# Project Udyam Digital — AI Business Advisor Integration Plan
> **AI Architecture, Progressive Clarification Flow & Policy Guardrail Blueprint**

---

## 📌 Executive Summary

This document outlines the end-to-end integration plan for powering the **AI Business Advisor** in Project Udyam Digital with a production-grade Large Language Model (LLM). 

The integration is built on two core principles:
1. **100% Free for Demo & Evaluation**: Utilizes Google Gemini 1.5/2.0 Flash via Google AI Studio's free tier (1,500 requests/day, no credit card required).
2. **Deterministic Policy Guardrails & Progressive Clarification**: Prevents blind guessing when queries are vague (e.g. *"I need wifi"*), ensures multi-turn discovery, and guarantees zero hallucination against the 25 official products in `product_catalogue.csv`.

---

## 🏛️ End-to-End System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        USER INPUT (English / Hindi)                    │
│                 e.g. "I need wifi" OR "Dental clinic with 5 staff"     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│             CONTEXT INJECTOR & POLICY PROMPT ENGINE                    │
│  - Active 25-Product Catalogue & Rules (requires_gstin, city_tier)     │
│  - Current User Profile State (business_type, employees, has_gstin)    │
│  - Down-sell Trigger Keywords ("sasta", "expensive", "budget")         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               FREE LLM INFERENCE (Google Gemini 1.5 Flash)              │
│  - Free Tier: 15 RPM / 1,500 RPD (Google AI Studio, ₹0 cost)          │
│  - Native Multilingual: English, Hindi, Hinglish                       │
│  - Structured JSON Output Mode (`response_mime_type="application/json"`)│
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
        [ Intent: "clarification" ]      [ Intent: "recommendation" ]
                    │                               │
                    ▼                               ▼
       ┌────────────────────────┐      ┌────────────────────────┐
       │ Multi-Turn Inquiry     │      │ Deterministic Catalog  │
       │ - Asks business type   │      │ Rule-Engine Guardrail  │
       │ - Asks team size       │      │ - Validates GST status │
       │ - Asks payment/CCTV    │      │ - Checks dependencies  │
       │ (Cart untouched)       │      │ - Prevents invalid SKUs│
       └────────────────────────┘      └────────────┬───────────┘
                                                    │
                                                    ▼
                                       ┌────────────────────────┐
                                       │ Live Cart Reconciler   │
                                       │ - Itemized 18% GST     │
                                       │ - ₹2,500 Setup Waived  │
                                       │ - ₹499 Booking Token   │
                                       └────────────────────────┘
```

---

## 💬 1. Progressive Clarification Flow (No Blind Guessing)

### The Problem
When a small business owner enters a vague query like:
> *"I need wifi"* or *"Mujhe net chahiye"*

A naive bot will either recommend an arbitrary expensive plan or dump the whole catalogue on the screen, causing drop-offs.

### The Solution: 2-Stage Multi-Turn Discovery

If the user query does not contain sufficient firmographic signals (**Business Type**, **Team Size**, or **Specific Operational Needs**), the AI assistant **must enter a `clarification` state**:

#### English Clarification Flow:
* **User**: *"I need wifi"*
* **AI Advisor**:
  > *"To help me find the best plan for you, could you tell me a little more about your business?*
  > 
  > 1. **What kind of business do you run?** *(e.g., retail shop, clinic, restaurant, CA office)*
  > 2. **How many staff members or devices will connect to the internet?**
  > 3. **Do you also need digital billing, UPI QR soundbox, CCTV, or backup connectivity?**"

#### Vernacular Hindi Clarification Flow:
* **User**: *"मुझे इंटरनेट चाहिए"*
* **AI Advisor**:
  > *"आपके व्यवसाय के लिए सबसे सही और किफायती प्लान चुनने के लिए, क्या आप थोड़ी और जानकारी दे सकते हैं?*
  > 
  > 1. **आपका किस प्रकार का व्यवसाय है?** *(जैसे किराना दुकान, क्लिनिक, रेस्टोरेंट, ऑफिस)*
  > 2. **दुकान या दफ्तर में कितने लोग या कंप्यूटर इंटरनेट से जुड़ेंगे?**
  > 3. **क्या आपको यूपीआई क्यूआर, डिजिटल बिलिंग, सीसीटीवी या 4G/5G बैकअप की भी आवश्यकता है?*"

#### Intent State Logic:
1. **`intent: "clarification"`**:
   * The assistant asks focused questions.
   * `recommended_bundle` remains empty or retains the base entry plan.
   * The quote cart does not jump or overwhelm the customer.
2. **`intent: "recommendation"`**:
   * Triggered once the user provides context (e.g., *"I have a medical clinic in Pune with 6 staff"*).
   * Generates a tailored bundle with **Explainability Tags** (*"Why we picked this for your business"*).
3. **`intent: "downsell_request"`**:
   * Triggered when the user objects to price (*"Yeh thoda mehenga hai"*, *"sasta plan dikhao"*).
   * Executes the 4-step controlled down-sell sequence (stripping non-essential SaaS add-ons first while safeguarding basic broadband).

---

## 🆓 2. Zero-Cost LLM Selection (For Demo & Hackathon)

For a live prototype demo with zero billing risk:

### Recommended: Google Gemini 1.5 / 2.0 Flash
* **Provider**: Google AI Studio ([aistudio.google.com](https://aistudio.google.com/))
* **Free Tier Quota**:
  * **15 Requests Per Minute (RPM)**
  * **1,500 Requests Per Day (RPD)**
  * **1 Million Tokens Per Minute (TPM)**
* **Cost**: **$0.00 / ₹0.00 Forever** on the free tier.
* **Credit Card Required**: **No**. Any standard Google account can generate an API key in 60 seconds.
* **Key Advantages**:
  * Native understanding of **Hindi, Hinglish, and regional Indian terminology** (Kirana, Dukan, Dawa Khana, Galla, Parchi).
  * Strict JSON Schema enforcement via `response_mime_type="application/json"`.
  * Low latency (< 1.2s response time).

---

## 🛡️ 3. Accel Business Policy & Catalog Constraints

The LLM is strictly bound by Accel Business catalog rules to prevent hallucination:

| Policy Rule | Rule Code | Enforcement in Advisor |
| :--- | :--- | :--- |
| **Whitelisted SKUs Only** | `CAT-01` | LLM may only output product IDs from `P01` to `P25`. |
| **Non-GST Safe Mode** | `CAT-02` | If `has_gstin == false`, plans **`P05`** (Static IP), **`P15`** (Corporate MPLS), and **`P21`** (Dedicated Cloud Connect) **must never be recommended**. |
| **Connectivity Dependency** | `CAT-03` | Add-ons like `P19` (Cloud POS), `P20` (Endpoint Security), and `P23` (Cloud CCTV) require at least one base connectivity plan (`P01`–`P04` or `P07`–`P08`). |
| **Minimum Employees** | `CAT-04` | `P15` (MPLS VPN) requires $\ge 10$ employees. |
| **Down-Sell Hierarchy** | `DOWN-01` | When down-selling, remove optional add-ons (`P19`/`P20`/`P23`) before degrading connectivity bandwidth. |

---

## 📋 4. Structured JSON Output Schema

To integrate cleanly with the existing FastAPI backend, the LLM must respond exclusively in structured JSON:

```json
{
  "intent": "clarification | recommendation | downsell_request",
  "language_detected": "en | hi",
  "message": "Conversational reply in the user's language asking clarifying questions or presenting the bundle.",
  "profile": {
    "business_type": "Clinic / Healthcare | Micro Retail | Professional Office | Restaurant",
    "employee_count": 5,
    "num_sites": 1,
    "city_tier": 2,
    "has_gstin": true
  },
  "recommended_bundle": {
    "P02": 1,
    "P09": 1,
    "P16": 5,
    "P20": 2
  },
  "explainability_tags": [
    {
      "product_id": "P02",
      "name": "Biz Fibre 300",
      "tag": "High-speed broadband for patient records & cloud clinical software"
    },
    {
      "product_id": "P09",
      "name": "Backup 4G/5G Failover",
      "tag": "Automatic cellular backup so clinic appointments never halt if fibre cuts"
    }
  ]
}
```

---

## 🔒 5. Two-Tier Guardrail Pipeline (Zero Hallucination)

```
[User Message] 
       │
       ▼
[Gemini LLM Inference] ──> Returns raw JSON bundle
       │
       ▼
[CatalogEngine Validation]
  ├── 1. Check Product ID Existence (P01-P25 whitelist)
  ├── 2. Check GST Eligibility (Drop P05/P15/P21 if has_gstin == false)
  ├── 3. Check Dependencies (Ensure base internet exists for SaaS add-ons)
  └── 4. Reconcile with Authoritative Pricing Engine (18% GST + Waiver)
       │
       ▼
[Live UI Update] ──> Auto-updates Cart, Totals, and Chat Bubble
```

### Fail-Safe Guarantee:
If the API key is absent, rate-limited, or throws an exception, the system **automatically falls back to the deterministic rule engine** inside [`app/modules/advisor/adapter.py`](file:///c:/Users/HP/Desktop/Airtel/app/modules/advisor/adapter.py). The user or hackathon judge will never see a broken screen or error prompt.

---

## 🚀 6. Implementation Roadmap

### Phase 1: Environment & Dependency Setup
* Add `google-genai` to `requirements.txt`.
* Configure `GEMINI_API_KEY` in `app/config.py` with an environment variable fallback.

### Phase 2: Prompt Engineering & Intent Routing
* Construct the system instruction prompt in [`adapter.py`](file:///c:/Users/HP/Desktop/Airtel/app/modules/advisor/adapter.py).
* Implement the **Progressive Clarification** pattern for vague inputs (`"I need wifi"`).
* Define the structured Pydantic schema for Gemini JSON output mode.

### Phase 3: Post-Generation Deterministic Guardrail
* Pass LLM recommendations through `catalog_engine.validate_bundle_dependencies()`.
* Strip any illegal add-ons or non-GST violations automatically before returning to the frontend.

### Phase 4: Verification & Automated Testing
* Test 4 core scenarios:
  1. **Vague query**: *"I need wifi"* $\rightarrow$ AI asks for business type and staff count.
  2. **Detailed query**: *"CA office with 8 staff in Jaipur"* $\rightarrow$ AI suggests `P02` (Biz Fibre 300) + `P16` (Email) + `P20` (Security).
  3. **Hindi query**: *"किराना दुकान के लिए नेट चाहिए"* $\rightarrow$ AI replies in Hindi with soundbox/QR tags.
  4. **Down-sell query**: *"Yeh thoda mehenga hai"* $\rightarrow$ AI strips add-ons and applies floor discount.

---

## 🔑 How to Obtain a Free Gemini API Key (60 Seconds)

1. Open **[https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)** in your browser.
2. Sign in with any standard Google account.
3. Click **"Create API Key"** $\rightarrow$ select any default project.
4. Copy the key and add it to your project:
   * In a `.env` file:
     ```env
     GEMINI_API_KEY="AIzaSyYourGeneratedFreeKeyHere..."
     ```
   * Or in PowerShell:
     ```powershell
     $env:GEMINI_API_KEY="AIzaSyYourGeneratedFreeKeyHere..."
     ```
