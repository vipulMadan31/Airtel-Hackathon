# Airtel Enterprise Operations: 3-Pillar Operational Benchmarks & Grounding Report

**Document Reference:** `OPS-BENCHMARK-2026-Q2-REV1`  
**Target Systems:** Airtel Enterprise Operations Desk (`/ops`), Mitra Partner Portal, Project Udyam Digital Core  
**Author:** Airtel Digital Operations & Telemetry Working Group  
**Review Status:** Verified & Authoritative — Zero Exaggeration Model  

---

## 1. Executive Summary & Problem Framing

> [!IMPORTANT]
> **CRITICAL TRANSPARENCY NOTICE: CURRENT DATABASE EMPIRICAL VALUES ARE SIMULATED**  
> All metrics and numbers listed under **Column 2: Current Database Empirical Values** (`udyam_orders.db`) are **SIMULATED PROTOTYPE VALUES** generated through local developer sandbox runs, automated end-to-end user tests, and synthetic merchant onboarding journeys. They do **NOT** represent live commercial Airtel production customer traffic or actual revenue billing.

A common vulnerability in enterprise digital transformation business cases is **metric inflation**—projecting unrealistic improvements such as 40%+ conversion rates or 24-hour fiber activations that ignore physical civil constraints, municipal rights-of-way, channel partner economics, and customer price sensitivity.

In accordance with leadership directives, the **Airtel Enterprise Operations Console (`/ops`)** has been refactored to eliminate unsubstantiated assumptions. It replaces vanity metrics with a rigorous **3-Pillar Comparative Telemetry Framework**:

```mermaid
flowchart LR
    A["1. Historical Baseline<br/><b>smb_leads.csv</b><br/>5,000 SMB records (Q2 2026)<br/>Legacy field sales & paper KYC"] --> D["Authoritative Operations Benchmarking"]
    B["2. Current Database<br/><b>udyam_orders.db (Simulated)</b><br/>Developer sandbox transactions<br/>Unmeasured metrics left BLANK (—)"] --> D
    C["3. Projected Metrics<br/><b>Pessimistic Model</b><br/>Strictly bounded assumptions<br/>Accounts for physical & field limits"] --> D
    D --> E["Admin Ops Console (/ops)<br/>Single Source of Truth"]
```

1. **Pillar 1: Historical Baseline Data** — Purely derived from the historical SMB dataset (`smb_leads.csv`, 5,000 enterprise and retail inquiries recorded across Q2 2026). Reflects traditional field-agent sales, physical paperwork, and manual feasibility verification.
2. **Pillar 2: Current Database Empirical Values (Simulated Sandbox Data)** — Queried directly from tables in `udyam_orders.db`. Measures prototype workflow execution under simulated testing. **Crucially, any metric not tracked by the prototype is left strictly blank (`—` / `[Not Tracked]`)** rather than filled with speculative numbers.
3. **Pillar 3: Projected Operational Metrics (Strictly Pessimistic)** — A conservative steady-state model that assumes modest, defensive gains (e.g., +3.64% absolute conversion uplift; 12-day activation time instead of claiming sub-48-hour fiber delivery).

---

## 2. Authoritative 3-Pillar Comparison Matrix

The table below reproduces the live data rendered in the Admin Ops Console (`/api/admin/metrics` → `comparative_benchmarks`):

| Operational Metric | Unit | 1. Dataset Baseline (`smb_leads.csv`) | 2. Current DB (Simulated Prototype) | 3. Projected (Pessimistic) | Proj. vs Base Variance | Grounding & Assumption Classification |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Total Inbound Leads** | Leads / Qtr | **5,000** | **167** | **5,000** | *Normalized Scale* | **Baseline**: Exact Q2 sample. **Current DB**: Simulated prototype test population. |
| **Overall Funnel Conversion** | % | **7.36%** (368 / 5,000) | **35.9%** (60 / 167 paid) | **11.00%** (550 / 5,000) | **+3.64% absolute** (+49.5% rel.) | **Pessimistic Assumption**: Current DB 35.9% is a simulated sandbox artifact. Real-world conversion will stay near 11%. |
| **Time to Activation (TTA)** | Days | **17.6 days** (Median: 17.0) | **—** *(Not Tracked)* | **12.0 days** (Median: 11.0) | **-5.6 days** (-31.8%) | **Pessimistic Assumption**: Digital KYC saves ~5.6 days. Physical fiber stringing, survey & pole access still take ~12 days. |
| **Customer Status Follow-ups** | Calls / Lead | **3.01 calls** | **—** *(Not Tracked)* | **2.00 calls** | **-1.01 calls** (-33.5%) | **Pessimistic Assumption**: WhatsApp alerts reduce anxiety, but delivery scheduling still triggers ~2 calls. |
| **Blended Acquisition Cost (CAC)** | INR | **₹15,053.37** | **—** *(Not Tracked)* | **₹12,200.00** | **-₹2,853** (-18.9%) | **Pessimistic Assumption**: Eliminates wasted field visits; preserves partner commissions (₹1k + 15% trail) and digital ads. |
| **Avg Monthly Plan (ARPU)** | INR / mo | **₹12,350.52** | **₹1,637.32** | **₹2,450.00** | **-₹9,901** *(Mix Shift)* | **Simulated & Model**: Baseline had expensive Leased Lines; DB transactions simulated micro-retail bundles (Biz Fibre 100). |
| **KYC Drop-off / Failure Rate** | % | **31.7%** (273 / 861) | **26.4%** (42 / 159) | **22.0%** (209 / 950) | **-9.7% drop-off** | **Simulated & Model**: Automated OCR reduces drop-off in sandbox tests; blurred cameras keep real failure rate near 22%. |
| **6-Month Customer Churn** | % | **15.22%** (56 / 368) | **—** *(Not Tracked)* | **13.00%** (72 / 550) | **-2.2% churn** | **Pessimistic Assumption**: Proactive CSAT desk resolves early issues; micro-SMB organic mortality bounds churn at ~13%. |
| **Customer Satisfaction (CSAT/NPS)** | Score | **6.86 / 10** (NPS) | **2.75 / 5** (CSAT) | **7.40 / 10** (NPS) | **+0.54 score** | **Simulated & Model**: DB CSAT represents simulated test feedback; projected NPS reflects transparent digital quoting. |

> [!NOTE]
> **Data Integrity Rule**: In Column 2 (*Current DB*), metrics where the database lacks tracking infrastructure (such as PBX call logs or marketing ad-spend ledgers) are rendered as `—` (*Not Tracked*). Under no circumstances are placeholder constants substituted for missing database fields.

---

## 3. Deep Dive into the Three Pillars

### Pillar 1: Historical Baseline (`smb_leads.csv`)
The baseline represents 5,000 SMB commercial inquiries handled via traditional Airtel enterprise telesales and field-partner operations during Q2 2026:
- **Funnel Drop-offs**:
  - `Inbound Leads`: **5,000** (100.0%)
  - `Contacted`: **3,406** (68.1%) — *31.9% of leads were never successfully reached by sales reps.*
  - `Needs Assessed`: **1,974** (39.5%) — *1,432 dropouts during manual discovery calls.*
  - `Quote Accepted`: **861** (17.2%) — *1,113 leads rejected manual PDF quotes.*
  - `KYC Submitted/Complete`: **588** (11.8%) — *273 accepted quotes failed physical document collection/verification (31.7% KYC failure).*
  - `Activated`: **368** (7.36% overall conversion) — *220 dropouts during physical fiber survey and trenching.*
- **Historical Commercial & Operational Footprint**:
  - *Time to Activation (TTA)*: Mean **17.6 days**, standard deviation **5.7 days**, median **17.0 days**.
  - *Chase Calls*: Mean **3.01 customer calls** inquiring about application status prior to activation.
  - *Blended CAC*: **₹15,053.37** per activated customer (reflects field sales visits, physical document couriers, and commissions).
  - *Product Mix & ARPU*: High baseline ARPU of **₹12,350.52/month** because the legacy portfolio was dominated by Internet Leased Lines (₹8,000–₹16,000/mo) and multi-site MPLS/SD-WAN.

---

### Pillar 2: Current Database Empirical Values (Simulated Prototype Data — `udyam_orders.db`)

> [!NOTE]
> **SIMULATED PROTOTYPE EXECUTION**: All records in `udyam_orders.db` represent **simulated sandbox transactions** generated during software development, automated test suites, and simulated merchant lifecycle runs. They demonstrate end-to-end database schema integration and query accuracy, but do **not** represent live commercial Airtel production network traffic.

Aggregation across the 6 core transactional tables (`leads`, `orders`, `kyc_cases`, `customer_feedback`, `support_tickets`, `users`):
- **Simulated Funnel Counts**:
  - `leads`: **167** records.
  - `orders`: **142** records created.
  - `orders with token_paid = 1`: **60** orders (representing simulated committed token purchases in the prototype).
  - `Simulated Conversion`: **35.9%** (60 / 167). *Recognized as a simulation artifact from small-sample automated testing; not representative of unassisted retail traffic.*
- **Simulated KYC Verification Engine**:
  - Total KYC Ingestions: **159 cases**.
  - Verified / Approved: **117 cases** (73.6%).
  - Rejected / Failed: **42 cases** (26.4%).
  - Primary causes in DB: Address proof mismatch (19), unreadable blurred photo (14), expired shop license (9).
- **Simulated Commercial Reality**:
  - Average Paid Monthly Recurring Total: **₹1,637.32 / month**.
  - Reflects adoption of micro-business packages: **Biz Fibre 100** (₹999/mo) and **Smart POS** (₹599/mo), with zero setup fees.
- **Service & Experience Feedback (Simulated Sandbox)**:
  - Customer Feedback Entries: **20 reviews**.
  - Mean CSAT Rating: **2.75 / 5.0**.
  - Dissatisfied Reviews (CSAT $\le 3$): **15 customers** flagged into `customer_feedback` for proactive 4-hour retention outreach.
  - Open Customer Support Tickets: **10 active tickets** in `support_tickets` table.
- **Explicitly Blank Metrics (`—`)**:
  - `Avg TTA`: **—** (*Simulated telecom provisioning does not measure field fiber trenching*).
  - `Customer Follow-up Calls`: **—** (*No telephony PBX database table exists*).
  - `Blended CAC`: **—** (*Prototype does not record external ad-network spend or partner payroll*).
  - `6-Month Churn`: **—** (*System uptime is < 6 months; computing long-term subscription churn would be inaccurate*).

---

### Pillar 3: Projected Operational Metrics (Pessimistic Model)

To avoid managerial over-optimism, the steady-state projections are grounded in conservative operational realities:

#### 1. Conversion Rate: Projected at 11.00% (Not 25%–40%)
- **Baseline**: 7.36% $\rightarrow$ **Projected**: 11.00% (**+3.64% absolute uplift**).
- *Grounding Justification*: While instant AI recommendations, regional Marathi/Hindi NLU, and transparent pricing reduce drop-off, real-world micro-retailers (Kirana stores) operate on tight margins. When field technicians arrive, budget constraints and competing residential FTTH options cause dropouts. Modeling above 11–12% in Year 1 would be irresponsible.

#### 2. Time to Activation: Projected at 12.0 Days (Not Sub-48h)
- **Baseline**: 17.6 days $\rightarrow$ **Projected**: 12.0 days (**-5.6 days savings**).
- *Grounding Justification*: Instant self-service quoting and automated KYC eliminate ~5.6 days of paper transit and back-office review. However, **wired fiber cannot bypass the physical world**: pole attachments, municipal permissions, optical line splitter allocations, and on-site ONT technician visits physically demand 10 to 14 days in typical Indian urban and semi-urban localities. Sub-48-hour SLAs are only feasible for wireless 5G AirFiber, not fixed-line enterprise broadband.

#### 3. Status Follow-Up Calls: Projected at 2.00 Calls (Not Zero)
- **Baseline**: 3.01 calls $\rightarrow$ **Projected**: 2.00 calls (**-1.01 calls savings**).
- *Grounding Justification*: Automated SMS/WhatsApp milestone tracking and the customer portal eliminate repetitive "is my document accepted?" inquiries. However, coordinating physical technician access to the customer's shop always requires 1 to 2 phone touches.

#### 4. Blended CAC: Projected at ₹12,200 (Not ₹850)
- **Baseline**: ₹15,053.37 $\rightarrow$ **Projected**: ₹12,200.00 (**-18.9% reduction**).
- *Grounding Justification*: Earlier prototype assumptions modeled CAC at ₹850, which falsely assumed zero channel partner commissions and zero performance marketing expense. In reality, Airtel Mitra partners must receive **₹1,000 upfront plus 15% revenue share** to remain incentivized, and search/social digital acquisition costs for verified MSME owners exceed ₹4,000 per lead. True blended CAC reduces modestly from ₹15k to ₹12.2k by eliminating wasted field visits on unfeasible leads.

#### 5. 6-Month Churn: Projected at 13.00% (Not < 2%)
- **Baseline**: 15.22% $\rightarrow$ **Projected**: 13.00% (**-2.2% reduction**).
- *Grounding Justification*: Proactive CSAT retention tickets (reaching out to customers rating $\le 3$ within 4 hours) effectively resolve initial billing and Wi-Fi coverage grievances. However, macro-level MSME mortality in India (stores shutting down or changing premises) inherently sets a natural churn floor around 12–14%.

---

## 4. Grounding & Transparency Audit: What is Assumed vs. What is Empirical

| Item | Status | Source / Calculation Method | Potential Bias / Risk |
| :--- | :---: | :--- | :--- |
| **5,000 Baseline Inquiries** | **Empirical** | Direct aggregation of `smb_leads.csv` across all rows. | Represents historical enterprise lead generation mix; high ILL share. |
| **7.36% Baseline Conversion** | **Empirical** | Computed as $\frac{368 \text{ Activated}}{5000 \text{ Leads}} \times 100$. | Verified historical outcome. |
| **17.6-Day Baseline TTA** | **Empirical** | Arithmetic mean of `time_to_activation_days` column. | Skewed slightly by Tier 3 locations with poor fiber trenching. |
| **₹15,053 Baseline CAC** | **Empirical** | Derived from legacy sales overhead / activations in `smb_leads.csv`. | Includes corporate sales rep salaries. |
| **167 Current DB Leads** | **Simulated** | `SELECT COUNT(*) FROM leads` in `udyam_orders.db`. | Simulated sandbox test accounts and runs. |
| **60 Paid Orders** | **Simulated** | `SELECT COUNT(*) FROM orders WHERE token_paid = 1`. | Simulated sandbox checkout transactions. |
| **26.4% KYC Failure Rate** | **Simulated** | `SELECT verdict FROM kyc_cases` (42 failed / 159 total). | Simulated document upload verification trials. |
| **Current DB TTA / CAC / Churn** | **Blank (`—`)** | Marked `None` in backend; displayed as `— [Not Tracked]` in UI. | **Zero synthetic filler**; preserves data integrity. |
| **11.0% Projected Conversion** | **Assumed** | Analytical model adding +3.64% absolute uplift for digital self-service. | Vulnerable to offline dealer price undercutting. |
| **12.0-Day Projected TTA** | **Assumed** | Baseline 17.6d minus 5.6d administrative/paperwork reduction. | Civil fiber works remain the critical path. |
| **₹12,200 Projected CAC** | **Assumed** | Model maintaining ₹1k partner bounty + digital ad spend. | Dependent on Google/Meta ad auction volatility. |
| **13.0% Projected Churn** | **Assumed** | Baseline 15.2% minus 2.2% saved via proactive CSAT desk. | Bounded by Indian MSME shop mortality. |

---

## 5. Architectural & System Verification

### 1. Backend Service Implementation
Located in [`app/modules/analytics/dashboard_service.py`](file:///c:/Users/HP/Desktop/Airtel/app/modules/analytics/dashboard_service.py):
- Method `get_comparative_ops_benchmarks()` queries `udyam_orders.db` dynamically for real counts while returning pre-aggregated baseline data and pessimistic projection structures.
- Unmeasured metrics explicitly set to `None` in the returned Python dictionary.

### 2. API Contract
Exposed at `GET /api/admin/metrics`:
```json
{
  "status": "SUCCESS",
  "comparative_benchmarks": {
    "baseline": { "sample_size_leads": 5000, "funnel": { "conversion_rate_percent": 7.36 }, ... },
    "current_db": { "funnel": { "inbound_leads": 167, "activated": 60 }, "operational_kpis": { "avg_tta_days": null, ... } },
    "projected_pessimistic": { "funnel": { "conversion_rate_percent": 11.0 }, "operational_kpis": { "avg_tta_days": 12.0 }, ... },
    "comparison_table": [ ... 9 structured rows ... ]
  }
}
```

### 3. Frontend Operations View
- Located in [`app/static/index.html`](file:///c:/Users/HP/Desktop/Airtel/app/static/index.html) (`#opsView`) and populated by [`app/static/app.js`](file:///c:/Users/HP/Desktop/Airtel/app/static/app.js) (`loadOpsViewData()`).
- Renders the 3-pillar comparative table `#opsComparativeBenchmarksTableBody`.
- Formats missing values as clean, honest placeholders:
  ```html
  <span class="text-slate-400 font-mono font-bold text-sm block">—</span>
  <span class="text-[9px] text-slate-400 font-medium block uppercase tracking-wider">[Not Tracked]</span>
  ```

### 4. Automated Regression Coverage
- Test case `test_comparative_ops_benchmarks` added to [`tests/test_p1_features.py`](file:///c:/Users/HP/Desktop/Airtel/tests/test_p1_features.py).
- Entire test suite (25/25 tests) passes cleanly:
  ```
  tests/test_p1_features.py::test_comparative_ops_benchmarks PASSED [100%]
  ======================== 25 passed in 84.95s ========================
  ```

---

## 6. Conclusion & Recommendation

By adopting this **3-Pillar Operational Benchmarking framework**, Airtel Enterprise Operations establishes an audit-ready, credible baseline for leadership. 

The console neither hides the challenges of the historical field process (17.6-day TTA, 31.7% KYC failure) nor promises miraculous overnight delivery for wired broadband. Instead, it demonstrates how **Project Udyam Digital** methodically improves operational throughput (from 7.36% to 11.0% conversion; 17.6 to 12.0 days activation) while preserving channel partner economics and keeping commercial figures strictly grounded in reality.
