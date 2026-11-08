# AI Advisor Modularization & Architecture Report

## Executive Summary
The AI Business Advisor (`app/modules/advisor`) has been re-architected from a 1,460-line monolithic adapter into a clean, modular, tool-based architecture. Under this architecture:
- **Gemini handles natural language conversations, empathy, and consultative dialogue.**
- **The backend deterministically controls all pricing, statutory eligibility, technical network feasibility, and bundle compositions.**

All business logic, catalogue information, and pricing strictly interface with `CatalogEngine`, `DataLoader`, and `PricingCalculator`.

---

## 1. Modular Architecture Overview

The oversized `adapter.py` has been split into 9 dedicated, single-responsibility modules:

```
app/modules/advisor/
├── __init__.py           # Package exports & public API
├── adapter.py            # Backward-compatible facade delegating to AdvisorService
├── service.py            # Main orchestration layer (NLU -> profile -> tools/LLM -> guard)
├── profile.py            # Non-destructive profile merging & location sync (City ↔ PIN ↔ Tier)
├── nlu.py                # Multilingual intent detection & entity extraction (English, Hindi, Hinglish)
├── tools.py              # Pure deterministic backend business operations & pricing
├── prompts.py            # Concise Gemini system instructions & function declarations (tools)
├── llm_client.py         # Gemini API client with function-calling & graceful fallback
├── scripted.py           # Deterministic rule-based fallback using identical tools
├── response_guard.py     # 5-dimensional statutory & pricing validation guardrails
└── session.py            # Persistent thread-safe conversation state & ownership verification
```

---

## 2. Key Improvements & Defect Removals

| Problem in Previous System | Solution in New Architecture |
| :--- | :--- |
| **Monolithic Adapter** (~1,460 lines combining regexes, prompts, pricing, and storage) | Split into 9 specialized modules with clear boundaries. |
| **Duplicated Rural Logic** (duplicated blocks for village/dehat in `adapter.py`) | Consolidated in `tools.py` and `scripted.py` with clean feasibility evaluation. |
| **Unvalidated Bundle Repair** (guessing keywords like "backup" in text to inject P17) | Strict tool-generated bundles; all items validated through `CatalogEngine.evaluate_product_eligibility` and dependency checks. |
| **Hardcoded Prices** (₹999, ₹1,499, ₹3,999 in prompt text) | All quotations computed dynamically through `PricingCalculator.calculate_quote` using `product_catalogue.csv`. |
| **Premature Assumptions** (assuming GST, employee scale, or location) | Consultative multi-turn clarification triggered whenever scale or GST is unstated. |
| **Cart Mutation on Inquiries** | Informational queries ("what plans do you have") strictly set `recommended_bundle = None` without modifying cart. |

---

## 3. Tool-Based AI Orchestration

Gemini is configured with 7 explicit backend tools matching pure server-side functions:

1. `update_profile`: Updates customer firmographics non-destructively.
2. `check_network_feasibility`: Checks FTTH Optical Fibre vs 5G AirFiber for any PIN/city.
3. `get_catalogue`: Retrieves official product items from database/CSV.
4. `check_product_eligibility`: Enforces 5-dimensional rules (Tier, Headcount, Sites, GST).
5. `generate_bundle`: Deterministically creates tailored bundles with explainability tags.
6. `progressive_downsell`: 4-step controlled down-sell sequence.
7. `remove_addon`: Removes optional add-on while preserving core connectivity.
8. `request_human_assistance`: Schedules partner/executive callbacks.

---

## 4. Evaluation & Test Results

A comprehensive scenario test suite (`tests/test_advisor_scenarios.py`) was introduced alongside existing live tests:

| Scenario / Test Suite | Test Objective | Status |
| :--- | :--- | :---: |
| **Scenario 1: Retail Shop** | Kirana store in Indore (PIN 452001, Tier 2), 2 staff $\to$ `P01` + `P19` + `P20` | **100% PASS** |
| **Scenario 2: Dental Clinic** | Clinic in Pune (Tier 1), 6 staff $\to$ `P02` (300M) + `P22` (Guest Wi-Fi) + `P17` (Cloud Backup) | **100% PASS** |
| **Scenario 3: Multi-Site Outlets** | 2 shops in Rohtak (PIN 124001, 10 & 100 staff) $\to$ `P02` x 2 + `P19` + `P20` | **100% PASS** |
| **Scenario 4: Tech Startup** | Software firm in Noida (PIN 201301, Tier 1, 25 staff) $\to$ `P03` (1G) + `P16` (Email x25) + `P11` (Static IP) | **100% PASS** |
| **Scenario 5: Rural vs Fiber** | Dumra Dehat village $\to$ clarifies wireline vs wireless $\to$ selects `P04` (5G AirFiber 100) + `P19` | **100% PASS** |
| **Scenario 6: Non-GST Safe Mode** | Sole proprietorship without GST $\to$ filters out GST-restricted products (ILL, SD-WAN, Firewall) | **100% PASS** |
| **Scenario 7: Progressive Downsell** | "Too expensive" / "सस्ता प्लान" $\to$ unbundles add-ons, sets floor connectivity (`P01`/`P02`), waives setup fee | **100% PASS** |
| **Scenario 8: Informational Inquiries** | "What plans do you have" $\to$ clear overview with zero cart mutation (`bundle=None`) | **100% PASS** |
| **Scenario 9: WhatsApp Continuity** | Multilingual session persistence, PIN/City synchronization across turns | **100% PASS** |
| **`test_gst_employee_clarification.py`** | 2-turn consultative flow (Rohtak shops & Pune clinic) | **100% PASS** |
| **`test_phase2_pincode_sync.py`** | Conversational PIN $\leftrightarrow$ City sync (Indore, Noida, Pune, Jaipur, Bhopal, Rohtak, Bengaluru, Mumbai) | **100% PASS** |
| **`test_core_flow.py`** | Full end-to-end backend pipeline (Catalogue, Pricing, KYC, Orders, Advisor) | **100% PASS** |
| **`test_advisor_live.py`** | Live Gemini Progressive Clarification, Policy Recommendation, and Hindi Downsell | **100% PASS** |
| **`test_multisite_chat_flow.py`** | Full browser headless multi-site UI chat with drawer breakdown & remove add-on | **100% PASS** |
| **`test_clinic_chat_flow.py`** | Full browser headless clinic UI chat with drawer breakdown & explainability tags | **100% PASS** |
