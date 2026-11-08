# Privacy & security note

**AIRTEL SYNC · PROJECT UDYAM DIGITAL**  
What the design collects from an MSME owner, why, where it goes and how long it stays, against India's Digital Personal Data Protection Act 2023 (DPDP). The controls in section 2 are built and tested in the prototype; section 3 lists what production still needs.

---

| Ask only what activation needs | Consent before documents | Keep documents briefly | AI talks, never decides |
| :--- | :--- | :--- | :--- |
| About 5 questions, and no ID numbers in chat. | A plain notice in the owner's language (EN/HI/MR), one purpose at a time. | Processed in-memory, then deleted immediately once a decision is made. | Prices come from rules; the LLM never sees documents. |

---

### 01 Data map

| DATA | WHY | WHERE IT GOES | HOW LONG |
| :--- | :--- | :--- | :--- |
| **Chat and business profile**<br>*(type, city, staff, sites, needs, optional GSTIN)* | Recommend an eligible bundle | Operational store. Chat text goes to the LLM (Gemini) with personal identifiers removed first. | Session lifetime *(see production gaps)* |
| **KYC documents**<br>*(GST/Udyam certificate, signatory ID, address proof)* | Verify the business, as telecom rules require | Temporary secure staging. Never sent to the LLM or shown to sales and partners. | Deleted immediately when a verdict is reached (`unlink()`); max 7 days for manual review |
| **Verified details**<br>*(extracted fields, SHA-256 fingerprint, blur variance)* | Prove what was checked | Operational store; identifiers masked on every screen (`27ABC•••••••1Z5`) | Contract term plus statutory legal retention period |
| **Consent record**<br>*(purposes, notice version, language, timestamp)* | Evidence of consent and its withdrawal | Consent ledger (`consent_logs`) | As evidence, for as long as the relationship lasts |
| **UPI mandate and lead score**<br>*(booking token, masked UPI ID, partner attribution)* | Monthly billing; prioritise follow-up | UPI ID shown masked (`sh•••@okbank`); lead scores visible to staff only | Contract term |

---

### 02 Controls built into the design

* **Consent (DPDP §§ 5–6)**: Versioned notice in English, Hindi, or Marathi before any document: what, why, who sees it, how long, rights, grievance contact. Separate purposes: KYC is required; WhatsApp updates and marketing start unticked. Withdrawing consent before order confirmation deletes documents at once.
* **Data minimisation**: The advisor never asks for Aadhaar, PAN or bank details. If an owner pastes them, they are stripped before the text reaches the LLM. GSTIN is masked wherever it is shown (`27ABC•••••••1Z5`): screens, console free text, and tool outputs. Non-GST micro-stores use an exemption path.
* **Protection of documents**: Files processed in-memory and purged immediately after the decision (`dest_path.unlink()`); only extracted fields, sharpness metrics, and a fingerprint remain. Every KYC verdict lists its reasons; unclear cases go to manual review rather than failing silently.
* **Access and accountability**: Role-based console (RBAC): partners see only the leads routed to their assigned pincodes; only authorized staff decide KYC reviews. Atomic database locking prevents two partners from claiming the same lead. Audit log of consent given, uploads, verification, and orders.
* **Safe use of AI**: The LLM can only call server-side tools. A guard rejects any reply naming a price or product no tool returned, and the server re-prices every quote (`validate_and_price_order()`), so neither the model nor the browser can set a price. Owner messages are treated as data, not instructions.

---

### 03 Prototype shortcuts and what production needs

| IN THE PROTOTYPE | FOR PRODUCTION |
| :--- | :--- |
| **Console role set by bearer token / local login** | Single sign-on with multi-factor authentication; role-based access managed centrally via enterprise IAM |
| **SQLite file and local filesystem staging** | Managed database encrypted at rest and hosted in India; keys in a key management service (KMS/HSM) with rotation; backups |
| **Gemini on standard API key** | Paid or enterprise tier whose terms exclude training on prompts, under an enterprise data processing agreement (DPA) |
| **Registries, DigiLocker, e-Sign and UPI mocked** | Licensed production integrations (NIC GSTN, Ministry of MSME Udyam, DigiLocker, Aadhaar e-Sign, NPCI UPI Autopay) |
| **Chats kept for session duration; local CORS** | Delete unconverted chats (for example after 90 days); strict CORS origins, TLS 1.3, rate limits, and WAF |
| **In-app CSAT desk and consent log** | Data Protection Officer (DPO), statutory grievance desk, breach notice to the Data Protection Board and affected owners within 72 hours, regular security testing |

---

*Airtel Business · Project Udyam Digital. This note describes architectural choices, not legal advice.*
