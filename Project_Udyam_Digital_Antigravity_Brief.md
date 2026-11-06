# Airtel SYNC 2026 --- Project Udyam Digital

## Consolidated Product, Prototype and Engineering Direction for Antigravity

**Purpose:** This document consolidates the review of the current
*Project Udyam Digital: Master Implementation Blueprint* into an
actionable set of instructions for the coding agent working on the
project.

**Primary instruction:** Treat this as an implementation brief, not
permission to blindly rewrite the existing project. First inspect the
repository, current implementation, supplied case files and data
dictionary. Preserve working code and make the smallest coherent changes
needed to reach the priorities below.

------------------------------------------------------------------------

# 1. Executive direction

Build a reliable, end-to-end digital acquisition and onboarding journey
for an Indian MSME owner:

1.  Discover the business's needs.
2.  Recommend a valid bundle from the supplied product catalogue.
3.  Explain the recommendation in plain language.
4.  Let the owner modify the bundle and understand the complete price.
5.  Complete a consent-led, mock KYC process.
6.  Confirm the order and let the owner track its status.
7.  Hand unresolved leads to a field executive or local partner without
    making the digital channel compete with them.

**The complete journey is the product. The chatbot is only the entry
point.**

The existing concept is strategically strong, but the proposed scope is
too large for a hackathon prototype and a three-minute demonstration.
Prioritise correctness, continuity and demonstrability over feature
count.

## Definition of a successful prototype

A judge should be able to follow one believable customer from the first
interaction to an order confirmation without encountering: - invented
products, prices or eligibility rules; - contradictory totals; - broken
or dead-end screens; - KYC decisions that do not match the supplied mock
data; - claims that simulated actions are real integrations; - confusing
language or unexplained technical jargon.

The mandatory journey must work before stretch features are added.

------------------------------------------------------------------------

# 2. What is right in the current blueprint --- preserve it

These are good decisions. Retain them unless repository inspection
reveals a concrete reason not to.

## 2.1 LLM for understanding; deterministic code for decisions

Keep the separation:

-   **LLM:** Understand free-text or voice input, extract structured
    business requirements, identify intent, and phrase explanations
    naturally.
-   **Deterministic catalogue/rules engine:** Select eligible products,
    enforce dependencies, validate city tier and GST requirements, and
    calculate prices.
-   **UI:** Show the resulting recommendation and explain why it was
    selected.

The LLM must never invent SKUs, prices, discounts, contract terms,
eligibility or product dependencies. The backend must validate every
proposed product against the catalogue before it reaches the user.

Use a structured response schema for extraction, for example:

``` json
{
  "business_type": "clinic",
  "employee_count": 5,
  "num_sites": 1,
  "city": "Jaipur",
  "city_tier": 1,
  "has_gstin": true,
  "requirements": ["broadband", "two_sim_cards", "secure_email"],
  "budget_monthly_inr": 2500,
  "language": "hi"
}
```

The schema is illustrative. Adapt it to the actual fields in the
supplied data and catalogue.

## 2.2 Non-GST onboarding

Retain a clearly explained **Non-GST Safe Mode**. It is an important
response to the case's reported conversion gap between GST and non-GST
leads.

Do not interpret this as bypassing KYC. It should: - identify which
catalogue products require GSTIN; - allow only products that do not
require GSTIN; - offer the alternative Udyam/document route only where
supported by the case data and business rules; - explain which products
are unavailable and why; - route ambiguous cases to manual review rather
than falsely approving them.

## 2.3 Modular quote and down-selling

Retain: - live price recalculation when add-ons are toggled; - clear
recurring versus one-time charges; - GST itemisation; - contract
duration and setup fee visibility; - a lower-cost alternative when the
user says the bundle is too expensive.

The down-sell sequence should be a controlled decision flow, not an LLM
improvising discounts:

1.  Remove optional add-ons.
2.  Show the cheapest eligible configuration of the current base
    service.
3.  Offer an eligible lower-tier or alternative base product.
4.  Explain any limitations or trade-offs.

Never silently waive setup fees or invent a discount. Only apply a
waiver if it is explicitly configured as a proposed promotion and
labelled as such.

## 2.4 Complete end-to-end flow

Keep the connection between advisor, quote, KYC, checkout and tracker.
This is more valuable than a sophisticated standalone chatbot.

## 2.5 Modular monolith for the prototype

Keep a modular monolith for the working prototype. It is easier to run,
debug and demonstrate than a distributed microservice deployment under
hackathon constraints.

The separate production architecture diagram may show a future
microservices deployment, but it must be labelled **target
architecture**, not represented as what the prototype already runs.

------------------------------------------------------------------------

# 3. What is wrong, risky or needs correction

## 3.1 Scope is over-engineered

The current plan attempts to implement too much at once: - eight
languages and voice; - extensive voice tooltips; - every catalogue
browsing interaction; - PDF quote export; - payment token and UPI
AutoPay simulation; - advanced OCR, deskewing, blur detection and fuzzy
matching; - elaborate DPDP consent and erasure scheduler; - engineer
assignment and rescheduling; - speed-test simulator and NPS; - partner
QR attribution; - propensity model and back-office Kanban.

This increases integration risk and makes the three-minute demo shallow.

**Action:** Do not build all of these before the core journey works.
Follow the priority matrix in Section 4.

## 3.2 DPDP claims are overstated or too broad

The current blueprint calls the system "Gazette-grade" and claims
comprehensive compliance. Do not make that claim.

Specific issues to correct: - A seven-year record-keeping obligation
associated with a registered Consent Manager should not be described as
a blanket retention requirement for the business. - Do not describe
DigiLocker as a generic "Consent Gateway" or assume an integration that
has not been established. - The Rule 8 erasure/notice provisions should
not be presented as applying identically to every abandoned application
and every data category. - A 30-day deletion period is a proposed
product retention policy, not a universal DPDP statutory period. -
Breach notification requirements should distinguish informing affected
individuals without delay from the Board's initial intimation and
subsequent detailed information within the prescribed period. - Do not
claim universal data localisation under Rule 13. - Do not claim full
compliance with provisions that are not yet in force.

**Implementation direction:** - Describe the design as **privacy by
design, aligned with the DPDP Act and applicable/notified
requirements**. - Make consent purpose-specific and unbundled. - Collect
only data needed for the stated purpose. - Record consent version,
purpose, timestamp and action. - Provide a clear withdrawal/request
route. - Define retention and deletion as an explicit product policy,
with legal-retention exceptions. - Mask sensitive identifiers in the UI
and logs. - Use synthetic data in the prototype. - Label every
compliance action that is simulated. - Do not fabricate a DPO email,
grievance URL, government integration or legal approval. Use clearly
marked demo placeholders if needed.

Before finalising legal language, verify the latest official Gazette
text and commencement notifications. This document is
product/engineering guidance, not a legal opinion.

## 3.3 Data analysis claims need more discipline

The blueprint includes claims such as field-sales leads having higher
churn and activation time correlating with NPS. These may be useful
observations, but do not state that they prove field agents oversell or
that activation speed causes NPS changes.

Use wording such as: - "is associated with"; - "the cohort exhibits"; -
"suggests an opportunity to investigate".

Do not imply causation from descriptive comparisons.

**Propensity model warning:** Do not use `stage_reached` to predict
activation if the score is intended to be calculated at initial lead
intake. That information is not available at that point and can cause
target leakage. Use only features available at scoring time. Split
train/test data and report validation results. If there is insufficient
data or time, use a transparent rule-based score instead of presenting
an unvalidated model as ML.

**NPS warning:** If the dataset field is a 0--10 respondent rating, its
average is not Net Promoter Score. NPS is the percentage of promoters
minus the percentage of detractors. Use the correct term for the actual
field.

## 3.4 Do not hard-code assumptions as facts

The following need evidence or explicit simulation labels: -
pincode-level fibre feasibility; - engineer names, contact details and
appointment slots; - live installation ETA; - refundable ₹499 booking
token; - UPI AutoPay/e-NACH integration; - annual savings claims; -
discounts or setup-fee waivers; - exact product dependency and
eligibility rules.

Use the supplied catalogue and README as the source of truth. If the
supplied files do not contain a field or rule, do not invent it. Either
omit the feature or add a clearly labelled demo assumption.

## 3.5 Verify all catalogue and KYC rules from the actual data

Before implementing product IDs such as P01--P25 or KYC cases
K01/K02/K04/K11/K12: - inspect the actual CSVs and README; - validate
the column names and value formats; - check all product dependencies and
eligibility conditions; - check registry statuses and document
contents; - confirm the expected result for each planted KYC case from
the student-provided pack; - never access, request or use the
judges-only pack.

The blueprint's trap table is a useful test-plan hypothesis, but the
actual supplied student data and README must take precedence if there is
a discrepancy.

------------------------------------------------------------------------

# 4. Prioritised feature scope

## P0 --- Must work end-to-end

  -----------------------------------------------------------------------------
  Module                  Required behaviour        Acceptance condition
  ----------------------- ------------------------- ---------------------------
  Advisor                 Collect business type,    A user can complete
                          size, location, number of discovery with a short
                          sites, needs, budget and  guided conversation
                          GST status                

  Structured extraction   Convert user answers into Missing/uncertain values
                          validated fields          trigger a clarification,
                                                    not a guess

  Catalogue engine        Apply actual product      No ineligible SKU can enter
                          eligibility, dependency   the quote
                          and city-tier rules       

  Recommendation          Recommend a base bundle   Every recommendation has a
                          plus optional add-ons     plain-language reason

  Quote                   Show recurring price,     All totals reconcile with
                          one-time charge, GST and  catalogue data
                          contract terms            

  Down-sell               Offer cheaper valid       No fabricated discounts or
                          alternatives              invalid downgrade

  Consent                 Show data items, purposes No document/registry action
                          and affirmative choice    before consent
                          before KYC processing     

  Mock KYC                Upload/extract/validate   Correct
                          documents and query mock  pass/reject/manual-review
                          registries                state for test cases

  Checkout                Confirm a simulated order Clearly labelled
                                                    simulation; no real payment
                                                    claim

  Tracker                 Show persistent order ID  Refreshing the page does
                          and status milestones     not lose the order
  -----------------------------------------------------------------------------

## P1 --- Build after P0 is stable

-   Hindi and English UI, with Hinglish where practical.
-   One additional regional language only if translations can be tested
    properly.
-   Non-GST Safe Mode.
-   Document quality pre-check for blur/unreadable images.
-   OCR extraction and manual correction.
-   Basic partner handoff for unresolved leads.
-   Basic partner dashboard showing lead status and reason for handoff.

## P2 --- Stretch only

-   Voice input.
-   WhatsApp front end.
-   All eight languages.
-   PDF/WhatsApp quote export.
-   QR partner attribution.
-   Propensity scoring.
-   Advanced Kanban and analytics.
-   Engineer assignment, rescheduling and speed-test simulator.
-   Elaborate retention countdown UI.

Do not start P1/P2 work while a P0 acceptance condition is failing.

------------------------------------------------------------------------

# 5. Preferred technology stack

Prefer a small, dependable stack with minimal operational complexity.

  -----------------------------------------------------------------------
  Layer                   Preferred choice        Guidance
  ----------------------- ----------------------- -----------------------
  Frontend                React + TypeScript +    Componentised UI, typed
                          Vite                    API contracts

  Styling                 Tailwind CSS            Consistent responsive
                                                  design; avoid excessive
                                                  animation

  Backend                 Python + FastAPI        Modular monolith,
                                                  Pydantic validation

  Persistence             SQLite for local demo;  Persist orders, consent
                          PostgreSQL if already   events and application
                          configured              state

  Catalogue               CSV loaded and          Single source of truth;
                          validated at startup    do not duplicate
                                                  catalogue values in
                                                  frontend

  LLM                     Existing available LLM  Use structured
                          API/provider            extraction; keep
                                                  provider behind an
                                                  adapter

  OCR                     Existing reliable OCR   OCR is assistive; user
                          library/service;        correction and manual
                          evaluate Tesseract or   fallback required
                          PaddleOCR based on      
                          environment             

  Image quality           OpenCV                  Basic blur/quality
                                                  pre-check; do not
                                                  overclaim document
                                                  authenticity

  Registry                FastAPI mock endpoints  Never call real
                          over supplied CSVs      government systems in
                                                  the demo

  Testing                 Pytest + frontend test  Unit tests for rules,
                          tooling already in repo pricing, KYC and state
                                                  transitions

  API documentation       FastAPI OpenAPI         Keep request/response
                                                  schemas explicit

  Deployment              Local run or one simple Avoid multi-service
                          hosting setup           infrastructure unless
                                                  already working
  -----------------------------------------------------------------------

### Architecture principles

1.  Keep business logic in backend modules, not React components.
2.  Keep LLM provider calls behind an adapter so the provider can be
    changed.
3.  Use deterministic backend validation before accepting a
    recommendation or quote.
4.  Use a single pricing function shared by recommendation, cart and
    checkout.
5.  Persist application/order state.
6.  Use mock adapters for external systems.
7.  Make all external dependencies optional where possible, with a
    deterministic fallback.
8.  Avoid adding Redis, RabbitMQ, Kong, Kubernetes or Docker Compose
    solely to make the architecture look enterprise-grade. Add
    infrastructure only when there is a working need.

------------------------------------------------------------------------

# 6. Suggested component and module design

Adapt naming to the existing repository. Do not create duplicate modules
if equivalents already exist.

## 6.1 Frontend components

``` text
frontend/src/
  app/
    App.tsx
    routes.tsx
  components/
    LanguageSwitcher.tsx
    ChatMessage.tsx
    QuickReplyChips.tsx
    AdvisorInput.tsx
    BusinessProfileSummary.tsx
    RecommendationCard.tsx
    ExplainabilityTags.tsx
    PlanComparisonDrawer.tsx
    AddOnToggle.tsx
    QuoteBreakdown.tsx
    ConsentNotice.tsx
    DocumentUploader.tsx
    OCRFieldReview.tsx
    KYCStatusCard.tsx
    CheckoutConfirmation.tsx
    OrderTimeline.tsx
    PartnerHandoffCard.tsx
  pages/
    OnboardingPage.tsx
    QuotePage.tsx
    KYCPage.tsx
    OrderTrackerPage.tsx
    PartnerDashboardPage.tsx
  services/
    api.ts
  types/
    api.ts
    domain.ts
  locales/
    en.json
    hi.json
```

Avoid one giant `App.tsx`. Keep state transitions explicit and
components focused.

## 6.2 Backend modules

``` text
backend/
  app/
    main.py
    config.py
    api/
      routes/
        advisor.py
        catalogue.py
        quote.py
        consent.py
        kyc.py
        checkout.py
        tracker.py
        partner.py
    modules/
      advisor/
        schemas.py
        extraction.py
        prompts.py
        service.py
      catalogue/
        loader.py
        schemas.py
        eligibility.py
        dependencies.py
        recommender.py
      pricing/
        calculator.py
        schemas.py
      consent/
        models.py
        service.py
        audit.py
      kyc/
        registry.py
        ocr.py
        image_quality.py
        validation.py
        service.py
      orders/
        models.py
        state_machine.py
        service.py
      partners/
        service.py
    repositories/
    data/
      product_catalogue.csv
      smb_leads.csv
      mock_gstin_registry.csv
      mock_udyam_registry.csv
    tests/
```

Keep the provided data files in their original form where possible. Do
not modify source datasets just to make a demo pass. If normalisation is
required, do it in a loader or preprocessing step and document it.

------------------------------------------------------------------------

# 7. Detailed implementation guidance

## 7.1 First inspect the repository and data

Before coding, Antigravity must:

1.  List the existing repository structure.
2.  Identify what is already implemented and what works.
3.  Read the case brief and dataset README.
4.  Inspect the schema, null values, unique values and sample rows of
    each supplied CSV.
5.  Inspect the product catalogue and its eligibility/dependency fields.
6.  Inspect the KYC specimen folder and map each applicant to its
    expected validation path using the student-provided materials.
7.  Identify existing run commands, environment variables and API
    integrations.
8.  Report conflicts between the current code, blueprint and supplied
    data.

Do not assume that the written blueprint's example values or filenames
exactly match the actual repository.

## 7.2 Catalogue engine

Implement a deterministic pipeline:

1.  Load and validate catalogue records.
2.  Parse product IDs, prices, contract lengths and setup fees.
3.  Parse GST requirement, city-tier availability, minimum employee
    count and dependency rules.
4.  Evaluate each product against the customer's profile.
5.  Return eligible products and ineligible products with human-readable
    reasons.
6.  Validate the final selected bundle again before quote generation.

Important: - Dependencies must be enforced in the backend. - Add-ons
cannot be purchased without their required base product. - GST-required
products must remain unavailable when GST eligibility is absent. -
City-tier and minimum-employee rules must be checked. - Do not rely on
frontend disabled states as security/business validation.

## 7.3 Advisor and LLM guardrails

Use the LLM for: - intent understanding; - extracting structured profile
fields; - asking concise follow-up questions; - explaining a
recommendation using supplied product facts; - understanding cost
objections and mapping them to a deterministic down-sell action.

Do not use the LLM for: - calculating totals; - creating products or
discounts; - deciding legal KYC acceptance; - overriding eligibility; -
inventing coverage or installation dates.

If LLM output is invalid or the API fails: - fall back to a guided
questionnaire; - keep the same deterministic catalogue and pricing
pipeline; - show a graceful message; - never block the user from
completing the demo journey.

Store the extracted profile and conversation state so a page refresh or
next step does not restart the journey.

## 7.4 Pricing and quote

Use one backend pricing function. It must be the only authority for
totals.

Quote should show: - selected base product; - selected add-ons; -
monthly recurring subtotal; - GST and whether catalogue prices are
inclusive/exclusive of GST; - one-time setup charges; - any explicitly
configured discount/waiver; - contract duration; - final amount due now,
if applicable; - future recurring amount.

Do not assume every catalogue price is GST-exclusive. Read the
README/catalogue semantics first.

The frontend should request a recalculation whenever the selection
changes. Add unit tests for: - base product alone; - base plus valid
add-on; - invalid dependency; - GST-required product without GSTIN; -
tier-ineligible product; - discount/waiver, if implemented; - rounding
and GST calculation.

The annual savings slider is optional. If included, show the user's
entered comparison bill and clearly state that it is an estimate. Do not
hard-code a savings claim.

## 7.5 Smart KYC flow

Recommended sequence:

1.  Show the consent notice before document upload or registry lookup.
2.  Capture affirmative consent and log the version, purpose, timestamp
    and action.
3.  Ask for the minimum required identifier/document.
4.  Query the supplied mock registry through a backend endpoint.
5.  Run OCR and extract fields.
6.  Show extracted values to the user for correction.
7.  Validate document status, dates, name/address match and required
    fields using deterministic logic.
8.  Return one of:
    -   **Verified**
    -   **Action required**
    -   **Manual review**
    -   **Rejected**, with a specific reason
9.  Continue only according to the verification result and business
    rules.

### KYC implementation cautions

-   Blur detection is a quality check, not proof of document
    authenticity.
-   Deskewing improves OCR but does not establish validity.
-   Fuzzy matching must not auto-approve a high-risk mismatch merely
    because a score exceeds 85%.
-   Use separate thresholds and manual review for ambiguous matches.
-   Treat cancelled/suspended registry records according to the actual
    registry status and rules.
-   Treat expired address proof according to the specified reference
    date and case requirements.
-   Preserve the ability to manually correct OCR fields.
-   Do not expose full identifiers in logs, UI screenshots or demo
    recordings.
-   Use synthetic case data only.

For the demo, include at least: - one clear successful KYC path; - one
rejection path; - one document-quality or manual-review path; - one
Non-GST path if supported by the actual rules.

Do not build an elaborate OCR pipeline before the registry and
deterministic validation paths work.

## 7.6 Consent and privacy implementation

Create a compact, honest consent experience: - data items collected; -
purpose for each category; - whether a field/document is required or
optional; - who processes it in the prototype; - retention/deletion
policy as a proposed product policy; - how to withdraw consent or raise
a request; - explicit accept and decline actions.

Technical safeguards: - mask identifiers in the UI and application
logs; - do not commit secrets or API keys; - keep synthetic data in the
repository; - avoid storing uploaded documents longer than needed for
the demo; - delete temporary files when the session/application is
cleared, where feasible; - keep consent events separate from raw
document contents; - document any limitations of the mock
implementation.

Do not claim encryption, deletion, access control or government
integration unless it is actually implemented and tested.

## 7.7 Checkout and order tracking

Checkout should be explicitly simulated: - generate a unique
application/order ID; - save the chosen quote and KYC state; - show a
confirmation screen; - create a tracker record; - progress through a
small number of meaningful milestones.

Suggested milestones: 1. Application submitted 2. Business verification
3. Order confirmed 4. Installation scheduled 5. Installation completed
6. Service activated

Only show dates/ETAs if they are sourced from data or labelled as
illustrative demo estimates.

If a ₹499 token is retained, present it as a **proposed simulated
booking flow**, not a real payment. Do not collect real UPI credentials
or claim that AutoPay is active.

## 7.8 Partner handoff

Keep this simple: - show the lead/application ID; - show why the advisor
could not close it (e.g. coverage unknown, KYC mismatch, customer
requested assistance); - allow a simulated "Request partner callback"
action; - show the lead in a basic partner dashboard.

QR attribution and propensity scoring are optional. A clear handoff is
more important than a sophisticated partner portal.

------------------------------------------------------------------------

# 8. Analytics and business case requirements

Use the supplied `smb_leads.csv` to establish a baseline. Recompute
every reported number from the actual file and document the calculation.

Recommended analyses: - funnel conversion by stage; - drop reasons; -
activation by GST status; - activation time distribution; - churn by
bundle and acquisition channel; - NPS distribution by activation-time
bucket and channel; - segment-level opportunity, where supported by
available fields.

For each statistic: - state numerator and denominator; - state the
cohort/filter used; - distinguish mean, median and percentage; -
identify missing data; - avoid causal language unless the analysis
supports it.

## Proposed pilot metrics

Use these as **targets to test**, not promised outcomes:

  ------------------------------------------------------------------------
  Metric                    Baseline reported in     Proposed pilot target
                               current blueprint 
  -------------------- ------------------------- -------------------------
  Lead-to-activation                       7.36%              At least 10%
  conversion                                     

  Average activation                   17.6 days              Under 7 days
  time                                           

  Status-chasing calls                       3.0                 At most 1

  CAC                                    ₹15,000           At most ₹10,500
  ------------------------------------------------------------------------

Revalidate all baseline figures from the actual dataset before putting
them in the deck. Add six-month churn as a guardrail metric; do not
improve conversion by selling unsuitable bundles that later churn.

The business case must explain the mechanism behind each target: -
self-serve discovery reduces sales effort; - better bundle fit reduces
quote rejection and churn; - digital KYC reduces document
back-and-forth; - tracker visibility reduces status calls; - partner
handoff preserves human support for complex cases.

Do not claim that the prototype has achieved these improvements. Label
them as projected pilot outcomes.

------------------------------------------------------------------------

# 9. Customer segment strategy

The case asks which MSME segments should be prioritised and which bundle
fits each. Make this a clear business decision, not just a list of
possible customer types.

Suggested hypotheses to validate against the dataset and catalogue:

  -----------------------------------------------------------------------
  Segment                 Likely need             Product strategy
  ----------------------- ----------------------- -----------------------
  Professional offices:   Reliable broadband,     Higher-value base
  clinics, CA firms,      business communication, connectivity plus
  coaching centres        secure digital tools    relevant add-ons

  Micro retail and        Affordable              Low-cost base plan,
  services: kiranas,      connectivity, POS/UPI   optional
  salons, pharmacies      continuity, simple      failover/POS-related
                          onboarding              services

  Multi-site businesses:  Consistency across      Multi-site bundle where
  restaurants and small   locations,              catalogue eligibility
  chains                  CCTV/connectivity,      supports it
                          central visibility      
  -----------------------------------------------------------------------

Use the supplied data to justify the priority order. Do not present the
suggested order as a proven finding until the data supports it. All
prices and contract lengths must come from the actual catalogue or be
explicitly labelled as proposed pricing.

------------------------------------------------------------------------

# 10. Testing and acceptance checklist

Antigravity should not declare the prototype complete until these checks
pass.

## Core journey

-   [ ] New user can start onboarding.
-   [ ] User can select language.
-   [ ] Advisor collects required fields.
-   [ ] Missing fields trigger a clarification.
-   [ ] Recommendation uses real catalogue records.
-   [ ] Recommendation explains why each product fits.
-   [ ] User can remove an add-on and see a correct recalculated quote.
-   [ ] User can request a cheaper eligible option.
-   [ ] Invalid product combinations are blocked server-side.
-   [ ] Quote totals reconcile with catalogue rules.
-   [ ] Consent is required before KYC processing.
-   [ ] Mock GSTIN/Udyam lookup works from supplied data.
-   [ ] OCR output can be reviewed and corrected.
-   [ ] KYC returns verified/action-required/manual-review/rejected
    states correctly.
-   [ ] Checkout creates a persistent order ID.
-   [ ] Tracker shows the saved order and status after refresh.
-   [ ] Partner handoff works for at least one unresolved scenario.

## Reliability

-   [ ] LLM API failure falls back to guided input.
-   [ ] Registry lookup failure has a clear retry/manual route.
-   [ ] OCR failure has a manual-entry route.
-   [ ] Empty/malformed CSV values do not crash the application.
-   [ ] Invalid API payloads return understandable errors.
-   [ ] No secret/API key is committed.
-   [ ] No real payment or government integration is falsely claimed.

## Data and rules

-   [ ] All 25 catalogue entries are loaded correctly, if the full
    catalogue is displayed.
-   [ ] Product dependencies are tested.
-   [ ] GST eligibility is tested.
-   [ ] City-tier eligibility is tested.
-   [ ] Minimum employee requirements are tested.
-   [ ] KYC planted cases from the student pack are tested against
    expected outcomes.
-   [ ] Every business-case statistic is reproducible from the source
    data.

------------------------------------------------------------------------

# 11. Three-minute demo plan

Do not try to demonstrate every feature. Tell one coherent story using
one customer profile.

  -----------------------------------------------------------------------
  Time                    What to show            Message
  ----------------------- ----------------------- -----------------------
  0:00--0:15              Introduce a small       Why the journey needs
                          business owner and the  to change
                          onboarding problem      

  0:15--0:50              Advisor in              Understands the
                          Hindi/English, profile  business rather than
                          extraction,             selling a fixed package
                          recommendation          

  0:50--1:15              Toggle add-on, show     Transparent and
                          price, ask for a        deterministic pricing
                          cheaper option          

  1:15--2:00              Consent, document       Fast but responsible
                          upload, registry result onboarding
                          and KYC decision        

  2:00--2:25              Checkout confirmation   One continuous
                          and tracker             self-serve journey

  2:25--2:45              Partner                 Digital complements the
                          handoff/dashboard       field force

  2:45--3:00              Show proposed pilot     Business impact
                          metrics and close       
  -----------------------------------------------------------------------

Record a clean, rehearsed path. Prepare test data and reset scripts so
the recording does not depend on unpredictable LLM output or network
conditions. Use captions or visible text for important results.

------------------------------------------------------------------------

# 12. Submission deliverables

The case asks for four deliverables. Keep them consistent with one
another.

## Deliverable 1 --- Working prototype

-   Three-minute maximum demo video.
-   Code repository with setup instructions.
-   `.env.example`, but no secrets.
-   Clear list of mock/simulated integrations.
-   Seed/demo data instructions.

## Deliverable 2 --- Solution architecture

Show: - customer channels; - API/backend boundary; - advisor/LLM
adapter; - deterministic catalogue and pricing; - KYC and mock
registry; - consent/audit handling; - order/tracker state; - partner
handoff; - data stores and security boundaries.

Show the **prototype modular monolith** separately from the **future
target architecture**. Do not imply that queues, gateways or
microservices exist in the running prototype if they do not.

## Deliverable 3 --- Business case deck (10 slides maximum)

Suggested structure: 1. Problem and opportunity 2. Dataset-backed
baseline and funnel leakage 3. Target MSME segments and prioritisation
4. Product concept and end-to-end journey 5. Advisor and deterministic
recommendation 6. Quote, pricing and down-sell 7. KYC, privacy and
partner model 8. Architecture and rollout 9. Unit economics and proposed
success metrics 10. Risks, mitigations and ask/next steps

## Deliverable 4 --- One-page privacy and security note

Cover: - data collected and purpose; - consent capture and withdrawal; -
data minimisation; - masking and secure handling; - retention/deletion
policy; - mock integrations and limitations; - incident/grievance
handling design; - what is implemented versus proposed.

------------------------------------------------------------------------

# 13. Implementation sequence for Antigravity

Work in this order. Do not start all modules in parallel.

### Step 0 --- Repository and data audit

Produce a short report: - current repo structure; - implemented
features; - broken/incomplete features; - actual dataset schemas; -
catalogue rule summary; - discrepancies between source data and
blueprint; - recommended next tasks.

Do not make destructive changes in this step.

### Step 1 --- Build the vertical slice

Implement one happy-path customer journey: - guided advisor; -
deterministic recommendation; - quote; - consent; - mock KYC; -
checkout; - tracker.

Use simple UI and mock data initially, but use the real catalogue and
registry files wherever supplied.

### Step 2 --- Make rules correct

Add catalogue, dependency, pricing, consent-ordering and KYC tests. Fix
edge cases before adding more UI.

### Step 3 --- Improve UX

Add language switching, explainability, down-sell, Non-GST Safe Mode and
clear error states.

### Step 4 --- Add partner handoff

Implement a simple unresolved-lead flow and dashboard.

### Step 5 --- Add stretch features only if time remains

Voice, PDF export, QR attribution and propensity scoring are optional.
Choose at most one or two that can be completed and tested properly.

### Step 6 --- Submission hardening

-   run the full test suite;
-   test from a clean environment;
-   verify README instructions;
-   prepare stable demo data;
-   record the three-minute video;
-   ensure the architecture, deck and privacy note describe the same
    implementation.

------------------------------------------------------------------------

# 14. Instructions for Antigravity's working style

1.  **Inspect before editing.** Do not assume the repository is empty or
    replace working code.
2.  **Work incrementally.** Make one coherent change at a time and run
    the relevant tests.
3.  **Do not overbuild.** P0 acceptance criteria take precedence over
    stretch features.
4.  **Use source data as truth.** Do not invent catalogue fields,
    prices, KYC outcomes or statistics.
5.  **Separate facts from assumptions.** Mark proposed commercial
    choices and simulated integrations clearly.
6.  **Keep the UI demo-ready.** Responsive, readable, consistent and
    free of dead ends.
7.  **Keep the backend authoritative.** Frontend state must not bypass
    eligibility, pricing or KYC validation.
8.  **Use graceful fallbacks.** The journey should survive LLM, OCR or
    mock API failures.
9.  **Do not claim unimplemented security or compliance.** Document what
    is real, mocked and proposed.
10. **Preserve working behaviour.** Avoid broad refactors unless
    necessary.
11. **At the end of each phase, report:** files changed, features
    completed, tests run and passed, known limitations, and next
    recommended task.
12. **Do not stop at a visually convincing frontend.** The key flows
    must be connected to working backend logic and persistent state.

## First task to execute

Start with **Step 0 --- Repository and data audit**. Return the audit
findings and a prioritised implementation plan before making major
architectural changes. Then implement the P0 vertical slice in small,
testable increments.

------------------------------------------------------------------------

# Final product principle

**Make it easy for an MSME owner to buy the right service, not merely
easy to chat with an AI.**

A smaller prototype with accurate catalogue logic, transparent pricing,
responsible KYC and a working tracker is stronger than a broad prototype
with many simulated features that do not connect reliably.
