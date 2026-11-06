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

## 🛡️ 3. Comprehensive Feasibility & Eligibility Framework

Feasibility is **multi-dimensional** and must be evaluated *before* recommending any bundle or answering technical questions. The AI Advisor evaluates feasibility across 5 critical dimensions:

### A. The 5 Dimensions of Feasibility & Eligibility

| Dimension | Rule & Constraint | Catalogue Truth (`product_catalogue.csv`) | AI Advisor Enforcement |
| :--- | :--- | :--- | :--- |
| **1. Statutory GSTIN Feasibility** | Regulated enterprise telecom & dedicated links require verified GSTIN | **Requires GSTIN (`requires_gstin = Y`)**: `P05` (ILL 20M), `P06` (ILL 100M), `P10` (SD-WAN), `P11` (Static IP), `P12` (SIP Trunk), `P15` (MPLS VPN), `P21` (Firewall) | If customer is **Non-GST**, strictly block these products. If requested, explain that Indian telecom regulations require an active GST registration for leased lines/static IPs, and recommend **Biz Fibre (`P01`/`P02`)** instead. |
| **2. Geographic City Tier Feasibility** | High-density optical infrastructure limits gigabit fibre & leased lines to certain tiers | **Tier-1 ONLY (`available_city_tiers = 1`)**: `P03` (Biz Fibre 1G).<br>**Tier 1 & 2 (`1;2`)**: `P01` (100M), `P02` (300M), `P04` (AirFiber 100M), `P05`/`P06` (ILL).<br>**Tier-3 / Rural**: Max speed is 100 Mbps (`P01`) or wireless 5G FWA (`P04`). | If a customer in a Tier-2 (Indore, Jaipur, Ludhiana) or Tier-3 city asks for **1 Gbps (`P03`)**, explain that 1 Gbps is currently metro-exclusive (Tier-1) and recommend the maximum feasible speed: **300 Mbps (`P02`)** or **100 Mbps (`P01`)**. |
| **3. Organizational Scale & Headcount** | Dedicated links & MPLS require minimum workforce scale | **`P05` (ILL 20M)**: Min $\ge 10$ employees.<br>**`P06` (ILL 100M)**: Min $\ge 25$ employees.<br>**`P15` (MPLS VPN)**: Min $\ge 10$ employees. | If a 3-person team asks for a Leased Line or MPLS, explain that dedicated 1:1 leased lines are built for large corporate infrastructure with $\ge 10$ staff, and recommend **Biz Fibre 300 (`P02`) with 4G Failover (`P09`)** as a faster, cost-effective fit. |
| **4. Topology & Multi-Site Feasibility** | Multi-branch routing products require multiple physical sites | **`P10` (Managed SD-WAN)**: Min $\ge 3$ branches/sites. | If a single-location retail shop asks for SD-WAN, explain that SD-WAN is designed to connect multiple distributed branches, and recommend **Secure Wi-Fi (`P22`)** for single-site security. |
| **5. Speed Floor & Catalogue Boundaries** | Broadband floor is strictly 100 Mbps; no sub-100 Mbps fibre exists | **Catalogue Floor**: `P01` (100 Mbps @ ₹999/mo).<br>**Sub-₹999 alternatives**: `P04` (5G AirFiber @ ₹899/mo) or `P07` (SIM @ ₹299/mo).<br>**Non-existent SKUs**: 50 Mbps, 30 Mbps, 20 Mbps fibre do **NOT** exist. | If customer asks for **50 Mbps or cheaper broadband**, NEVER hallucinate or agree that 50 Mbps exists! Explain that Airtel Business fibre starts at 100 Mbps to guarantee uninterrupted UPI & billing, and suggest the ₹799/₹899 wireless AirFiber option if price is the primary concern. |

---

## 💡 4. The Informational `inquiry` Intent (Zero Cart Pollution)

### The Problem
Previously, when a user asked a feasibility or technical question (e.g. *"Is there a 50 mbps option also?"* or *"Can I get 1 Gbps in Jaipur?"* or *"Can I get a leased line without GST?"*), the system assumed it was a new bundle purchase and tried to re-bundle, spitting out generic greetings and resetting the quote.

### The Solution: `intent: "inquiry"`
When the user asks an informational, technical, or feasibility question:
1. **Explain Clearly**: Answer the feasibility constraints honestly and politely in English or Hindi.
2. **Leave Cart Untouched**: Return `recommended_bundle: None` (or keep current bundle).
3. **Preserve User Profile**: Do not overwrite the user's business type or employee count.

#### Example Feasibility Inquiries:
- **Query**: *"Is there a 50 mbps option also?"*
  - **Intent**: `"inquiry"`
  - **Cart**: Untouched (`None`)
  - **AI Response**: *"Airtel Business fibre starts at 100 Mbps (Biz Fibre 100 @ ₹999/mo) as our enterprise standard to guarantee lag-free UPI payments and billing. We do not offer a 50 Mbps fibre tier. If you need a more economical option, our 5G AirFiber Wireless plan is available at ₹899/mo."*
- **Query**: *"Can we get 1 Gbps for our office in Indore?"*
  - **Intent**: `"inquiry"`
  - **Cart**: Untouched (`None`)
  - **AI Response**: *"In Indore (Tier-2 city), our optical fibre network currently supports speeds up to 300 Mbps (Biz Fibre 300 @ ₹1,499/mo). Our 1 Gbps ultra-high-speed plan is currently available in Tier-1 metropolitan cities. Would you like to proceed with the 300 Mbps plan?"*
- **Query**: *"We don't have GST, can we still take a Leased Line?"*
  - **Intent**: `"inquiry"`
  - **Cart**: Untouched (`None`)
  - **AI Response**: *"Under Indian telecom regulations, dedicated Internet Leased Lines (1:1 contention) require active GST registration. However, you can easily get our high-speed Biz Fibre broadband (100 Mbps or 300 Mbps) with PAN and address proof without requiring a GSTIN."*

---

## 📋 5. Structured JSON Output Schema

To integrate cleanly with the existing FastAPI backend, the LLM must respond exclusively in structured JSON:

```json
{
  "intent": "clarification | recommendation | downsell_request | inquiry",
  "language_detected": "en | hi",
  "message": "Conversational reply in the user's language answering feasibility questions, asking clarifying questions, or presenting the bundle.",
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

## 🔒 6. Multi-Tier Feasibility Guardrail Pipeline (Zero Hallucination)

```
[User Message] 
       │
       ▼
[Gemini LLM Inference] ──> Returns raw JSON bundle or Inquiry Answer
       │
       ▼
[CatalogEngine Authoritative Validation]
  ├── 1. Intent Check: If "inquiry" or "clarification", bypass bundle mutation (Cart Untouched)
  ├── 2. Whitelist Check (P01-P25 catalogue boundary)
  ├── 3. Full 5-Dimensional Feasibility (evaluate_product_eligibility):
  │     ├── City Tier: Block P03 (1G) in Tier-2/3
  │     ├── GSTIN Prerequisite: Block P05, P06, P10, P11, P12, P15, P21 if non-GST
  │     ├── Min Employees: Block P05/P15 if < 10 staff; P06 if < 25 staff
  │     └── Min Sites: Block P10 if < 3 branches
  ├── 4. Dependency Check (Ensure base internet exists for SaaS add-ons)
  └── 5. Reconcile with Authoritative Pricing Engine (18% GST + ₹2,500 Setup Waiver)
       │
       ▼
[Live UI Update] ──> Auto-updates Cart, Totals, and Chat Bubble
```

### Fail-Safe Guarantee:
If the API key is absent, rate-limited, or throws an exception, the system **automatically falls back to the deterministic rule engine** inside [`app/modules/advisor/adapter.py`](file:///c:/Users/HP/Desktop/Airtel/app/modules/advisor/adapter.py). The user or hackathon judge will never see a broken screen or error prompt.

---

## 🚀 7. Implementation Roadmap

### Phase 1: Environment & Dependency Setup
* Add `google-genai` to `requirements.txt`.
* Configure `GEMINI_API_KEY` in `app/config.py` with an environment variable fallback.

### Phase 2: Prompt Engineering & Intent Routing
* Construct the system instruction prompt in [`adapter.py`](file:///c:/Users/HP/Desktop/Airtel/app/modules/advisor/adapter.py).
* Implement **Progressive Clarification** pattern for vague inputs (`"I need wifi"`).
* Implement **Informational Feasibility Inquiries** (`intent: "inquiry"`) for speed & capability questions without cart pollution.
* Define the structured Pydantic schema for Gemini JSON output mode.

### Phase 3: Post-Generation Deterministic Guardrail
* Wire `catalog_engine.evaluate_product_eligibility()` into the advisor adapter.
* Pass LLM recommendations through `catalog_engine.validate_bundle_dependencies()`.
* Automatically strip or downgrade any illegal add-ons, tier mismatches, or non-GST violations before returning to the frontend.

### Phase 4: Verification & Automated Testing
* Test 6 core conversation scenarios:
  1. **Vague query**: *"I need wifi"* $\rightarrow$ AI asks for business type and staff count (Cart untouched).
  2. **Technical Feasibility Query**: *"Is there a 50 mbps option also?"* $\rightarrow$ AI explains 100 Mbps floor, mentions 5G AirFiber, leaves cart untouched.
  3. **Tier Feasibility Query**: *"Can we get 1 Gbps for our office in Indore?"* $\rightarrow$ AI explains 1 Gbps is Tier-1 only, suggests 300 Mbps floor.
  4. **GST Feasibility Query**: *"Can I get a Leased Line without GST?"* $\rightarrow$ AI explains statutory requirement, offers Biz Fibre broadband.
  5. **Detailed Recommendation**: *"CA office with 8 staff in Jaipur"* $\rightarrow$ AI suggests `P02` (Biz Fibre 300) + `P16` (Email) + `P20` (Security).
  6. **Down-sell Query**: *"Yeh thoda mehenga hai"* $\rightarrow$ AI strips add-ons and applies floor discount.

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
