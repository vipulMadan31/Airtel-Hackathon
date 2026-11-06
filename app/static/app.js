// Project Udyam Digital - Frontend State & Interaction Engine

const STATE = {
  language: 'en',
  safeModeNonGst: false,
  profile: {
    business_type: 'Micro Retail',
    employee_count: 2,
    num_sites: 1,
    city: 'Indore',
    city_tier: 2,
    has_gstin: false
  },
  selectedBundle: {
    "P01": 1,
    "P07": 2,
    "P19": 1
  },
  downsellStep: 1,
  activeQuote: null,
  activeOrder: null,
  lastExtractedDoc: null,
  kycDecision: null
};

window.STATE = STATE;

// --- INITIALIZATION ---
document.addEventListener("DOMContentLoaded", () => {
  initEventListeners();
  applyLanguage('en');
  addAiChatMessage(
    "Namaste! Welcome to Airtel Business. Tell me about your business (type, employees, locations) and I will craft the ideal digital bundle."
  );
  recalculateQuote();
  initNpsButtons();
});

// --- I18N LANGUAGE SWITCHER ---
function applyLanguage(lang) {
  STATE.language = lang;
  const dict = LOCALES[lang] || LOCALES.en;

  // Toggle button active states
  const enBtn = document.getElementById("langEn");
  const hiBtn = document.getElementById("langHi");
  if (lang === 'hi') {
    hiBtn.className = "px-2.5 py-1 rounded-full bg-white shadow-sm text-slate-900 font-bold";
    enBtn.className = "px-2.5 py-1 rounded-full text-slate-500 hover:text-slate-900 font-bold";
  } else {
    enBtn.className = "px-2.5 py-1 rounded-full bg-white shadow-sm text-slate-900 font-bold";
    hiBtn.className = "px-2.5 py-1 rounded-full text-slate-500 hover:text-slate-900 font-bold";
  }

  // Update all text elements
  setText("t-brand-sub", dict.brand_sub);
  setText("t-app-title", dict.app_title);
  setText("t-safe-mode", dict.safe_mode);
  setText("t-partner-btn", dict.partner_btn);
  setText("t-advisor-title", dict.advisor_title);
  setText("t-rule-guarded", dict.rule_guarded);
  document.getElementById("chatInput").placeholder = dict.chat_placeholder;
  setText("t-send-btn", dict.send_btn);

  // Chips
  setText("t-chip-retail", dict.chip_retail);
  setText("t-chip-clinic", dict.chip_clinic);
  setText("t-chip-ca", dict.chip_ca);
  setText("t-chip-restaurant", dict.chip_restaurant);
  setText("t-chip-sasta", dict.chip_sasta);

  // Quote Card
  setText("t-quote-badge", dict.quote_badge);
  setText("t-quote-heading", dict.quote_heading);
  setText("t-browse-all", dict.browse_all);
  setText("t-monthly-subtotal", dict.monthly_subtotal);
  setText("t-gst-label", dict.gst_label);
  setText("t-setup-fee-label", dict.setup_fee_label);
  setText("t-setup-waived", dict.setup_waived);
  setText("t-total-commitment", dict.total_commitment);
  setText("t-consolidated-bill", dict.consolidated_bill);
  setText("t-token-title", dict.token_title);
  setText("t-token-sub", dict.token_sub);
  setText("t-token-btn", dict.token_btn);
  setText("t-downsell-btn", dict.downsell_btn);
  setText("t-proceed-kyc", dict.proceed_kyc);

  // KYC Card
  setText("t-kyc-badge", dict.kyc_badge);
  setText("t-kyc-heading", dict.kyc_heading);
  setText("t-rule3-badge", dict.rule3_badge);
  setText("t-dpdp-title", dict.dpdp_title);
  setText("t-dpdp-itemized", dict.dpdp_itemized);
  setText("t-dpdp-purpose", dict.dpdp_purpose);
  setText("t-dpdp-withdraw", dict.dpdp_withdraw);
  setText("t-dpdp-dpo", dict.dpdp_dpo);
  setText("t-upload-gst-label", dict.upload_gst_label);
  setText("t-upload-address-label", dict.upload_address_label);
  setText("t-or-choose-specimen", dict.or_choose_specimen);
  setText("t-review-heading", dict.review_heading);
  setText("t-field-gstin", dict.field_gstin);
  setText("t-field-udyam", dict.field_udyam);
  setText("t-field-name", dict.field_name);
  setText("t-field-date", dict.field_date);
  setText("t-field-address", dict.field_address);
  setText("t-verify-rule-btn", dict.verify_rule_btn);
  setText("t-back-quote", dict.back_quote);
  setText("t-confirm-order-btn", dict.confirm_order_btn);

  // Update dynamic safe mode labels
  updateSafeModeUI();

  // Tracker Card
  setText("t-tracker-badge", dict.tracker_badge);
  setText("t-tracker-heading", dict.tracker_heading);
  setText("t-change-date-btn", dict.change_date_btn);
  setText("t-handover-nps", dict.handover_nps);
  setText("t-nps-thanks", dict.nps_thanks);

  // Partner Modal
  setText("t-partner-title", dict.partner_title);
  setText("t-partner-sub", dict.partner_sub);
  setText("t-partner-code", dict.partner_code);
  setText("t-partner-desc", dict.partner_desc);
  setText("t-partner-copy", dict.partner_copy);
  setText("t-partner-table-title", dict.partner_table_title);

  // Update initial welcome message if no user conversation started yet
  const chatMessages = document.getElementById("chatMessages");
  if (chatMessages && chatMessages.children.length <= 1) {
    chatMessages.innerHTML = "";
    addAiChatMessage(
      lang === 'hi' 
        ? "नमस्ते! एयरटेल बिज़नेस में आपका स्वागत है। अपने व्यवसाय के बारे में बताएं (प्रकार, कर्मचारी, स्थान) और हम आपके लिए उपयुक्त डिजिटल बंडल तैयार करेंगे।" 
        : "Namaste! Welcome to Airtel Business. Tell me about your business (type, employees, locations) and I will craft the ideal digital bundle."
    );
  }

  // If order tracker active, re-render with translated milestone labels
  if (STATE.activeOrder) {
    renderTracker(STATE.activeOrder);
  }

  // If KYC decision displayed, re-render in active language
  if (STATE.kycDecision) {
    renderKycDecision(STATE.kycDecision);
  }
}

function setText(elementId, text) {
  const el = document.getElementById(elementId);
  if (el && text !== undefined) el.innerText = text;
}

// --- NON-GST SAFE MODE DYNAMIC UI MANAGER ---
function updateSafeModeUI() {
  const banner = document.getElementById("nonGstModeBanner");
  const gstinBadge = document.getElementById("gstinReqBadge");
  const udyamBadge = document.getElementById("udyamReqBadge");
  const uploadGstLabel = document.getElementById("t-upload-gst-label");
  const dict = LOCALES[STATE.language] || LOCALES.en;

  if (STATE.safeModeNonGst) {
    if (banner) banner.classList.remove("hidden");
    if (gstinBadge) {
      gstinBadge.innerText = STATE.language === 'hi' ? "वैकल्पिक" : "Optional";
      gstinBadge.className = "text-[10px] font-bold text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded";
    }
    if (udyamBadge) {
      udyamBadge.innerText = STATE.language === 'hi' ? "अनिवार्य" : "Mandatory";
      udyamBadge.className = "text-[10px] font-bold text-emerald-800 bg-emerald-100 px-1.5 py-0.5 rounded animate-pulse";
    }
    if (uploadGstLabel) uploadGstLabel.innerText = dict.upload_udyam_label || "1. Upload Udyam Certificate (PNG/JPG):";
  } else {
    if (banner) banner.classList.add("hidden");
    if (gstinBadge) {
      gstinBadge.innerText = STATE.language === 'hi' ? "अनिवार्य" : "Mandatory";
      gstinBadge.className = "text-[10px] font-bold text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded";
    }
    if (udyamBadge) {
      udyamBadge.innerText = "MSME";
      udyamBadge.className = "text-[10px] font-bold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded";
    }
    if (uploadGstLabel) uploadGstLabel.innerText = dict.upload_gst_label;
  }
}

// --- EVENT LISTENERS ---
function initEventListeners() {
  // Language Switcher
  document.getElementById("langEn").addEventListener("click", () => applyLanguage('en'));
  document.getElementById("langHi").addEventListener("click", () => applyLanguage('hi'));

  // Safe Mode Toggle
  document.getElementById("safeModeToggle").addEventListener("change", (e) => {
    STATE.safeModeNonGst = e.target.checked;
    STATE.profile.has_gstin = !e.target.checked;
    if (STATE.safeModeNonGst) {
      if (STATE.selectedBundle["P15"]) delete STATE.selectedBundle["P15"];
      if (STATE.selectedBundle["P05"]) delete STATE.selectedBundle["P05"];
      if (STATE.selectedBundle["P21"]) delete STATE.selectedBundle["P21"];
    }
    updateSafeModeUI();
    recalculateQuote();
  });

  // Chat Send
  document.getElementById("sendBtn").addEventListener("click", handleChatSubmit);
  document.getElementById("chatInput").addEventListener("keypress", (e) => {
    if (e.key === "Enter") handleChatSubmit();
  });

  // Quick Reply Chips
  document.querySelectorAll(".chip-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const msg = STATE.language === 'hi' ? btn.getAttribute("data-msg-hi") : btn.getAttribute("data-msg-en");
      document.getElementById("chatInput").value = msg;
      handleChatSubmit();
    });
  });

  // Downsell Button
  document.getElementById("downsellBtn").addEventListener("click", handleDownsell);

  // 3-Bucket Catalog Modal
  document.getElementById("browseAllPlansBtn").addEventListener("click", openCatalogModal);
  document.getElementById("closeCatalogModalBtn").addEventListener("click", closeCatalogModal);

  // Partner Modal
  document.getElementById("partnerPortalBtn").addEventListener("click", openPartnerModal);
  document.getElementById("closePartnerModalBtn").addEventListener("click", closePartnerModal);

  // Step Transitions
  document.getElementById("proceedKycBtn").addEventListener("click", () => {
    document.getElementById("quoteCard").classList.add("hidden");
    document.getElementById("kycCard").classList.remove("hidden");
  });

  document.getElementById("backToQuoteBtn").addEventListener("click", () => {
    document.getElementById("kycCard").classList.add("hidden");
    document.getElementById("quoteCard").classList.remove("hidden");
  });

  // DOCUMENT UPLOADS: Real File Handlers
  document.getElementById("gstFileInput").addEventListener("change", (e) => handleFileUpload(e, "gst"));
  document.getElementById("addressFileInput").addEventListener("change", (e) => handleFileUpload(e, "address"));

  // Specimen Quick Loaders
  document.querySelectorAll(".specimen-chip").forEach(btn => {
    btn.addEventListener("click", () => {
      const code = btn.getAttribute("data-code");
      handleSpecimenScan(code);
    });
  });

  // Verify Extracted Data Button
  document.getElementById("verifyExtractedBtn").addEventListener("click", handleVerifyExtracted);

  // Confirm Order
  document.getElementById("confirmOrderBtn").addEventListener("click", handleConfirmOrder);

  // Reschedule
  document.getElementById("rescheduleBtn").addEventListener("click", handleReschedule);
}

// --- REAL FILE UPLOAD HANDLER ---
async function handleFileUpload(e, docType) {
  const file = e.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);

  showPreviewLoading();

  try {
    const res = await fetch("/api/kyc/upload", {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    populateExtractedDocData(data);
  } catch (err) {
    alert("Upload or OCR failed. Please check network connection.");
  }
}

// --- SPECIMEN SCAN HANDLER ---
async function handleSpecimenScan(applicantCode) {
  showPreviewLoading();
  let docType = "gst";
  if (STATE.safeModeNonGst && (applicantCode === "K03" || applicantCode === "K12")) {
    docType = "udyam";
  }

  try {
    const res = await fetch("/api/kyc/specimen-scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ applicant_code: applicantCode, doc_type: docType })
    });
    const data = await res.json();
    populateExtractedDocData(data, applicantCode);
  } catch (err) {
    alert("Specimen load failed.");
  }
}

function showPreviewLoading() {
  const container = document.getElementById("docPreviewContainer");
  container.classList.remove("hidden");
  document.getElementById("docPreviewName").innerText = "Scanning document via OCR...";
  document.getElementById("docBlurBadge").className = "px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-600";
  document.getElementById("docBlurBadge").innerText = "Analyzing...";
  document.getElementById("docTypeDetected").innerText = "Processing OpenCV Sharpness...";
}

function populateExtractedDocData(data, code = "CUSTOM") {
  STATE.lastExtractedDoc = data;
  const container = document.getElementById("docPreviewContainer");
  container.classList.remove("hidden");

  // Preview Image
  document.getElementById("docPreviewImg").src = data.image_url;
  document.getElementById("docPreviewName").innerText = data.file_name || "Document Preview";
  document.getElementById("docTypeDetected").innerText = `Detected: ${data.document_type.replace('_', ' ')}`;
  document.getElementById("docRawSnippet").innerText = data.raw_text ? `OCR Text: ${data.raw_text}` : "No clear text extracted";

  // Blur Variance Badge
  const blurBadge = document.getElementById("docBlurBadge");
  if (data.is_clear) {
    blurBadge.className = "px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800";
    blurBadge.innerText = `Sharp (Variance: ${data.blur_variance})`;
  } else {
    blurBadge.className = "px-2 py-0.5 rounded text-[10px] font-bold bg-red-100 text-red-800 animate-pulse";
    blurBadge.innerText = `Blurry (Variance: ${data.blur_variance})`;
  }

  // Populate Editable Review Fields
  const fields = data.extracted_fields || {};
  if (fields.gstin) document.getElementById("extractedGstinInput").value = fields.gstin;
  if (fields.udyam_number && document.getElementById("extractedUdyamInput")) {
    document.getElementById("extractedUdyamInput").value = fields.udyam_number;
  }
  if (fields.entity_name) document.getElementById("extractedNameInput").value = fields.entity_name;
  if (fields.address) document.getElementById("extractedAddressInput").value = fields.address;

  if (data.document_type === "ADDRESS_PROOF" && fields.bill_date) {
    document.getElementById("extractedDateInput").value = fields.bill_date;
  } else if (!document.getElementById("extractedDateInput").value || document.getElementById("extractedDateInput").value < "2026-01-01") {
    document.getElementById("extractedDateInput").value = "2026-07-06";
  }

  // Auto-fill applicant defaults for known traps if missing
  const fName = data.file_name || "";
  const udyamInput = document.getElementById("extractedUdyamInput");

  if (code === "K03" || fName.startsWith("K03")) {
    if (udyamInput) udyamInput.value = "UDYAM-MH-00-9516696";
    document.getElementById("extractedNameInput").value = "Ganesh Woodcraft";
    document.getElementById("extractedDateInput").value = "2026-05-30";
    document.getElementById("extractedAddressInput").value = "Plot 42, MIDC Industrial Area, Pune, Maharashtra - 411018";
    if (STATE.safeModeNonGst) {
      document.getElementById("extractedGstinInput").value = "";
    } else {
      document.getElementById("extractedGstinInput").value = "27XUIXG0767D1ZP";
    }
  } else if (code === "K05" || fName.startsWith("K05")) {
    document.getElementById("extractedGstinInput").value = "03PJNXS4821G1ZB";
    if (udyamInput) udyamInput.value = ""; // Planted Trap: Missing Udyam certificate
    document.getElementById("extractedNameInput").value = "Sneha Rao (Prop. Saffron Bakers)";
    document.getElementById("extractedDateInput").value = "2026-06-20";
    document.getElementById("extractedAddressInput").value = "Shop 12, Saffron Market, Ludhiana, Punjab - 141001";
  } else if (code === "K11" || fName.startsWith("K11")) {
    document.getElementById("extractedGstinInput").value = "03KGZXT1320R1ZZ";
    if (udyamInput) udyamInput.value = "UDYAM-PB-00-9719478";
    document.getElementById("extractedNameInput").value = "Trinity Bake House Pvt Ltd";
    document.getElementById("extractedDateInput").value = "2025-10-31"; // Expired bill (>90d)
    document.getElementById("extractedAddressInput").value = "Shop/Unit 188, Industrial Area Phase 2, Ludhiana, Punjab - 541498";
  } else if (code === "K01" || fName.startsWith("K01")) {
    document.getElementById("extractedGstinInput").value = "37IHKXV5167L1ZS";
    if (udyamInput) udyamInput.value = "";
    document.getElementById("extractedNameInput").value = "Vindhya Tours & Travels";
    document.getElementById("extractedDateInput").value = "2026-07-06";
  } else if (code === "K12" || fName.startsWith("K12")) {
    document.getElementById("extractedGstinInput").value = "37NBLXS1145E1ZU";
    if (udyamInput) udyamInput.value = "UDYAM-AP-00-5186772";
    document.getElementById("extractedNameInput").value = "Star Electronics";
    document.getElementById("extractedDateInput").value = "2026-07-06";
    document.getElementById("extractedAddressInput").value = "Shop/Unit 216, Nehru Nagar, Visakhapatnam, Andhra Pradesh - 762071";
  }
}

// --- VERIFY REVIEWED EXTRACTED DATA ---
async function handleVerifyExtracted() {
  const gstin = document.getElementById("extractedGstinInput").value.trim();
  const udyamInput = document.getElementById("extractedUdyamInput");
  const udyam = udyamInput ? udyamInput.value.trim() : "";
  const name = document.getElementById("extractedNameInput").value.trim();
  const date = document.getElementById("extractedDateInput").value.trim();
  const blurVariance = STATE.lastExtractedDoc ? STATE.lastExtractedDoc.blur_variance : 1000.0;

  const resultBox = document.getElementById("kycResultBox");
  const confirmBtn = document.getElementById("confirmOrderBtn");

  resultBox.classList.remove("hidden");
  resultBox.className = "rounded-xl p-3.5 text-xs space-y-2 bg-slate-100 border border-slate-200";
  resultBox.innerHTML = `<span>Checking extracted fields against mock registries & DPDP rules...</span>`;

  try {
    const res = await fetch("/api/kyc/verify-extracted", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        gstin: gstin,
        udyam_number: udyam,
        entity_name: name,
        bill_date: date,
        blur_variance: blurVariance,
        is_non_gst_mode: STATE.safeModeNonGst
      })
    });
    const data = await res.json();
    STATE.kycDecision = data;
    renderKycDecision(data);
  } catch (err) {
    resultBox.innerHTML = `<span>Validation API connection error.</span>`;
  }
}

function renderKycDecision(data) {
  if (!data) return;
  const resultBox = document.getElementById("kycResultBox");
  const confirmBtn = document.getElementById("confirmOrderBtn");
  const isHi = STATE.language === 'hi';
  const name = document.getElementById("extractedNameInput").value.trim();
  const date = document.getElementById("extractedDateInput").value.trim();

  resultBox.classList.remove("hidden");

  if (data.status === "VERIFIED") {
    resultBox.className = "rounded-xl p-3.5 text-xs space-y-1.5 bg-emerald-50 border border-emerald-300 text-emerald-900";
    
    const entityName = (data.registry_details && data.registry_details.legal_name) 
      || (data.udyam_details && data.udyam_details.enterprise_name) 
      || name;

    let statutoryHtml = "";
    if (data.is_non_gst_mode && data.udyam_details && data.udyam_details.udyam_number) {
      statutoryHtml = `
        <p><strong>${isHi ? 'उद्यम पंजीकरण संख्या:' : 'Udyam Registration No:'}</strong> <span class="font-mono font-bold">${data.udyam_details.udyam_number}</span> (${data.udyam_details.enterprise_type || 'Micro'} Enterprise, ${data.udyam_details.major_activity || 'Services'})</p>
        <p class="text-emerald-800 font-bold">⚡ ${isHi ? 'गैर-जीएसटी सेफ मोड: सूक्ष्म उद्यम (MSME) डेटा सत्यापित' : 'Non-GST Safe Mode: Micro-Enterprise Verified via Udyam Portal'}</p>
      `;
    } else {
      statutoryHtml = `
        <p><strong>${isHi ? 'जीएसटी नंबर:' : 'GSTIN:'}</strong> <span class="font-mono font-bold">${data.verified_fields.gstin || ''}</span> (${data.registry_details.status || 'Active'})</p>
        ${data.udyam_details && data.udyam_details.udyam_number ? `<p><strong>${isHi ? 'उद्यम पंजीकरण:' : 'Udyam:'}</strong> ${data.udyam_details.udyam_number}</p>` : ''}
      `;
    }

    const regAddress = (data.registry_details && data.registry_details.principal_place_of_business)
      || (data.udyam_details && data.udyam_details.city ? `${data.udyam_details.city}, ${data.udyam_details.state}` : (document.getElementById("extractedAddressInput").value.trim() || 'Verified'));

    resultBox.innerHTML = `
      <div class="flex items-center space-x-2">
        <span class="font-extrabold text-sm">${isHi ? '✔ केवाईसी सत्यापित (स्ट्रेट-थ्रू प्रोसेसिंग पास)' : '✔ KYC VERIFIED (Straight-Through Processing Approved)'}</span>
      </div>
      <p><strong>${isHi ? 'कानूनी नाम:' : 'Legal Entity:'}</strong> ${entityName}</p>
      ${statutoryHtml}
      <p><strong>${isHi ? 'पंजीकृत पता:' : 'Principal Address:'}</strong> ${regAddress}</p>
      <p><strong>${isHi ? 'वैधता जांच:' : 'Freshness Check:'}</strong> ${isHi ? `बिल की तिथि (${date}) 2026-07-15 से 90 दिनों के भीतर वैध है।` : `Bill date (${date}) is valid within 90 days of 2026-07-15.`}</p>
    `;
    confirmBtn.disabled = false;
  } else if (data.status === "REJECTED") {
    resultBox.className = "rounded-xl p-3.5 text-xs space-y-1.5 bg-red-50 border border-red-300 text-red-900";
    resultBox.innerHTML = `
      <div class="flex items-center space-x-2">
        <span class="font-extrabold text-sm">${isHi ? '✖ केवाईसी अस्वीकृत (नियम उल्लंघन पकड़ा गया)' : '&times; KYC REJECTED (Statutory Trap Caught)'}</span>
      </div>
      <ul class="list-disc pl-4 space-y-0.5">
        ${data.reasons.map(r => `<li>${r}</li>`).join('')}
      </ul>
    `;
    confirmBtn.disabled = true;
  } else {
    resultBox.className = "rounded-xl p-3.5 text-xs space-y-1.5 bg-amber-50 border border-amber-300 text-amber-900";
    resultBox.innerHTML = `
      <div class="flex items-center space-x-2">
        <span class="font-extrabold text-sm">&#9888; ${isHi ? 'अतिरिक्त कार्रवाई आवश्यक' : data.status}</span>
      </div>
      <ul class="list-disc pl-4 space-y-0.5">
        ${data.reasons.map(r => `<li>${r}</li>`).join('')}
      </ul>
    `;
    confirmBtn.disabled = true;
  }
}

// --- ADVISOR CHAT ---
async function handleChatSubmit() {
  const input = document.getElementById("chatInput");
  const message = input.value.trim();
  if (!message) return;

  addUserChatMessage(message);
  input.value = "";

  try {
    const res = await fetch("/api/advisor/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: message,
        current_profile: STATE.profile,
        language: STATE.language
      })
    });
    const data = await res.json();

    if (data.profile) STATE.profile = data.profile;
    if (data.recommended_bundle) {
      STATE.selectedBundle = data.recommended_bundle;
      recalculateQuote();
    }

    addAiChatMessage(data.message, data.explainability_tags);
  } catch (err) {
    addAiChatMessage("Sorry, could not process request right now. Fallback to guided selection.");
  }
}

function addUserChatMessage(text) {
  const container = document.getElementById("chatMessages");
  const div = document.createElement("div");
  div.className = "flex justify-end";
  div.innerHTML = `<div class="chat-bubble-user px-3.5 py-2 text-xs font-medium max-w-[85%] shadow-sm">${text}</div>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function addAiChatMessage(text, tags = []) {
  const container = document.getElementById("chatMessages");
  const div = document.createElement("div");
  div.className = "flex justify-start flex-col space-y-1.5";

  let tagsHtml = "";
  if (tags && tags.length > 0) {
    const whyTitle = STATE.language === 'hi' ? "हमने आपके व्यवसाय के लिए इसे क्यों चुना:" : "WHY WE PICKED THIS FOR YOUR BUSINESS:";
    tagsHtml = `<div class="mt-2 pt-2 border-t border-slate-100 space-y-1">
      <span class="text-[10px] font-bold uppercase tracking-wider text-airtel-red block">${whyTitle}</span>
      ${tags.map(t => `<div class="text-[11px] bg-slate-50 p-1.5 rounded border border-slate-100">
        <strong class="text-slate-900">${t.name || t.product_id}:</strong> ${t.tag}
      </div>`).join('')}
    </div>`;
  }

  div.innerHTML = `
    <div class="chat-bubble-ai px-3.5 py-2.5 text-xs font-medium max-w-[90%] shadow-sm">
      <p class="leading-relaxed">${text}</p>
      ${tagsHtml}
    </div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

// --- PRICING & QUOTE RECONCILER ---
async function recalculateQuote() {
  try {
    const res = await fetch("/api/pricing/quote", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        quantities: STATE.selectedBundle,
        apply_digital_discount: true,
        waive_setup_fee: true
      })
    });
    const quote = await res.json();
    STATE.activeQuote = quote;

    renderSelectedItems(quote.items);
    document.getElementById("monthlySubtotal").innerText = `₹${quote.monthly_subtotal_inr.toFixed(2)}`;
    document.getElementById("gstTotal").innerText = `₹${quote.gst_18_inr.toFixed(2)}`;
    document.getElementById("monthlyGrandTotal").innerText = `₹${quote.total_monthly_inr.toFixed(2)} / mo`;
  } catch (err) {
    console.error("Quote calculation error:", err);
  }
}

function renderSelectedItems(items) {
  const container = document.getElementById("selectedItemsList");
  container.innerHTML = "";

  if (!items || items.length === 0) {
    container.innerHTML = `<div class="text-xs text-slate-400 italic">No products currently selected.</div>`;
    return;
  }

  items.forEach(item => {
    const div = document.createElement("div");
    div.className = "flex items-center justify-between p-2.5 bg-slate-50/80 rounded-xl border border-slate-100 text-xs";
    div.innerHTML = `
      <div>
        <span class="font-bold text-slate-900 block">${item.product_name} <span class="text-[10px] text-slate-400 font-mono">(${item.product_id})</span></span>
        <span class="text-[11px] text-slate-500">${item.category} &bull; ₹${item.unit_price_inr}/mo</span>
      </div>
      <div class="flex items-center space-x-2">
        <span class="font-extrabold text-slate-900">₹${item.line_monthly_inr}</span>
        <button class="text-slate-400 hover:text-airtel-red text-base font-black px-1" onclick="removeProduct('${item.product_id}')">&times;</button>
      </div>
    `;
    container.appendChild(div);
  });
}

function removeProduct(productId) {
  if (STATE.selectedBundle[productId]) {
    delete STATE.selectedBundle[productId];
    recalculateQuote();
  }
}

// --- 4-STEP DOWN-SELL SEQUENCE ---
async function handleDownsell() {
  try {
    const res = await fetch("/api/pricing/downsell", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        quantities: STATE.selectedBundle,
        step: STATE.downsellStep
      })
    });
    const quote = await res.json();
    STATE.activeQuote = quote;

    const newQuantities = {};
    quote.items.forEach(item => {
      newQuantities[item.product_id] = item.quantity;
    });
    STATE.selectedBundle = newQuantities;

    addAiChatMessage(`Step ${STATE.downsellStep} Down-sell: ${quote.explanation}`);
    STATE.downsellStep = (STATE.downsellStep % 4) + 1;

    recalculateQuote();
  } catch (err) {
    console.error("Downsell error:", err);
  }
}

// --- 3-BUCKET CATALOG MODAL ---
async function openCatalogModal() {
  const modal = document.getElementById("catalogModal");
  modal.classList.remove("hidden");

  const basePids = ["P01", "P02", "P03", "P04", "P05", "P06", "P07", "P08"];
  const currentBase = Object.keys(STATE.selectedBundle).find(id => basePids.includes(id)) || "P01";

  try {
    const res = await fetch("/api/catalog/buckets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        city_tier: STATE.profile.city_tier,
        employee_count: STATE.profile.employee_count,
        num_sites: STATE.profile.num_sites,
        has_gstin: STATE.profile.has_gstin,
        current_base_id: currentBase
      })
    });
    const buckets = await res.json();

    const aList = document.getElementById("bucketAList");
    aList.innerHTML = buckets.bucket_a_base_plans.map(p => `
      <div class="p-2.5 rounded-xl border border-blue-200 bg-blue-50/50 flex justify-between items-center">
        <div>
          <strong class="block text-slate-900">${p.product_name}</strong>
          <span class="text-slate-500">₹${p.price_min_inr_per_month}/mo</span>
        </div>
        <button class="bg-blue-600 hover:bg-blue-700 text-white px-2.5 py-1 rounded-lg font-bold text-[11px]" onclick="selectBasePlan('${p.product_id}')">Select</button>
      </div>
    `).join('');

    const bList = document.getElementById("bucketBList");
    bList.innerHTML = buckets.bucket_b_modular_addons.map(p => {
      const isSelected = !!STATE.selectedBundle[p.product_id];
      return `
        <div class="p-2.5 rounded-xl border border-emerald-200 bg-emerald-50/50 flex justify-between items-center">
          <div>
            <strong class="block text-slate-900">${p.product_name}</strong>
            <span class="text-slate-500">₹${p.price_min_inr_per_month}/mo</span>
          </div>
          <button class="${isSelected ? 'bg-emerald-800' : 'bg-emerald-600'} text-white px-2.5 py-1 rounded-lg font-bold text-[11px]" onclick="toggleAddon('${p.product_id}')">
            ${isSelected ? 'Added ✔' : '+ Add'}
          </button>
        </div>
      `;
    }).join('');

    const cList = document.getElementById("bucketCList");
    cList.innerHTML = buckets.bucket_c_locked_plans.map(p => `
      <div class="p-2 rounded-lg border border-slate-200 bg-slate-100 flex justify-between items-center text-slate-500">
        <div>
          <strong>${p.product_name}</strong> (${p.product_id})
        </div>
        <span class="text-[10px] bg-slate-200 text-slate-700 px-2 py-0.5 rounded font-medium">Locked: ${p.ineligible_reason}</span>
      </div>
    `).join('');

  } catch (err) {
    console.error("Bucket fetch error:", err);
  }
}

function closeCatalogModal() {
  document.getElementById("catalogModal").classList.add("hidden");
}

window.selectBasePlan = function(productId) {
  const basePids = ["P01", "P02", "P03", "P04", "P05", "P06", "P07", "P08"];
  basePids.forEach(p => delete STATE.selectedBundle[p]);
  STATE.selectedBundle[productId] = 1;
  recalculateQuote();
  closeCatalogModal();
};

window.toggleAddon = function(productId) {
  if (STATE.selectedBundle[productId]) {
    delete STATE.selectedBundle[productId];
  } else {
    STATE.selectedBundle[productId] = 1;
  }
  recalculateQuote();
  openCatalogModal();
};

// --- ORDER CONFIRMATION & TRACKER ---
async function handleConfirmOrder() {
  const confirmBtn = document.getElementById("confirmOrderBtn");
  confirmBtn.disabled = true;
  confirmBtn.innerText = STATE.language === 'hi' ? "ऑर्डर दर्ज हो रहा है..." : "Creating Order...";

  try {
    const res = await fetch("/api/orders/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        business_name: document.getElementById("extractedNameInput").value || "Star Electronics",
        contact_phone: "+91 98765 12345",
        bundle_data: STATE.activeQuote,
        kyc_status: "VERIFIED",
        language: STATE.language
      })
    });
    const order = await res.json();
    STATE.activeOrder = order;

    document.getElementById("kycCard").classList.add("hidden");
    document.getElementById("trackerCard").classList.remove("hidden");

    renderTracker(order);
  } catch (err) {
    alert("Order creation failed.");
    confirmBtn.disabled = false;
  }
}

function renderTracker(order) {
  document.getElementById("trackerOrderIdBadge").innerText = order.order_id;
  document.getElementById("installDateText").innerText = order.scheduled_install_date;

  const dict = LOCALES[STATE.language] || LOCALES.en;
  const timeline = document.getElementById("timelineList");
  timeline.innerHTML = `
    <div class="flex items-center space-x-3 text-xs">
      <span class="w-6 h-6 rounded-full bg-emerald-500 text-white flex items-center justify-center font-bold">✔</span>
      <div>
        <strong class="text-slate-900 block">${dict.step1_title}</strong>
        <span class="text-slate-500">${dict.step1_sub}</span>
      </div>
    </div>
    <div class="flex items-center space-x-3 text-xs">
      <span class="w-6 h-6 rounded-full bg-emerald-500 text-white flex items-center justify-center font-bold">✔</span>
      <div>
        <strong class="text-slate-900 block">${dict.step2_title}</strong>
        <span class="text-slate-500">${dict.step2_sub}</span>
      </div>
    </div>
    <div class="flex items-center space-x-3 text-xs">
      <span class="w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold animate-pulse">&bull;</span>
      <div>
        <strong class="text-slate-900 block">${dict.step3_title}</strong>
        <span class="text-slate-500">${STATE.language === 'hi' ? 'इंजीनियर आगमन:' : 'Engineer arrival:'} ${order.scheduled_install_date}</span>
      </div>
    </div>
    <div class="flex items-center space-x-3 text-xs opacity-50">
      <span class="w-6 h-6 rounded-full bg-slate-300 text-white flex items-center justify-center font-bold">4</span>
      <div>
        <strong class="text-slate-900 block">${dict.step4_title}</strong>
        <span class="text-slate-500">${dict.step4_sub}</span>
      </div>
    </div>
  `;
}

// Reschedule
async function handleReschedule() {
  if (!STATE.activeOrder) return;
  const promptText = STATE.language === 'hi' ? "नई इंस्टॉलेशन तारीख दर्ज करें (YYYY-MM-DD):" : "Enter new installation date (YYYY-MM-DD):";
  const newDate = prompt(promptText, "2026-07-25");
  if (!newDate) return;

  try {
    const res = await fetch(`/api/orders/${STATE.activeOrder.order_id}/reschedule`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ new_date: newDate })
    });
    const data = await res.json();
    document.getElementById("installDateText").innerText = newDate;
    alert(STATE.language === 'hi' ? `तारीख सफलतापूर्वक बदलकर ${newDate} कर दी गई है!` : `Installation rescheduled successfully to ${newDate}!`);
  } catch (err) {
    alert("Rescheduling failed.");
  }
}

// NPS Buttons
function initNpsButtons() {
  const container = document.getElementById("npsButtonsContainer");
  container.innerHTML = "";
  for (let i = 0; i <= 10; i++) {
    const btn = document.createElement("button");
    btn.className = "w-7 h-7 rounded text-xs font-bold border border-slate-300 hover:bg-airtel-red hover:text-white hover:border-airtel-red transition";
    btn.innerText = i;
    btn.addEventListener("click", () => handleNpsSubmit(i));
    container.appendChild(btn);
  }
}

async function handleNpsSubmit(rating) {
  if (!STATE.activeOrder) return;
  try {
    await fetch(`/api/orders/${STATE.activeOrder.order_id}/nps`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rating: rating })
    });
    document.getElementById("npsButtonsContainer").classList.add("hidden");
    document.getElementById("npsSubmittedText").classList.remove("hidden");
  } catch (err) {
    console.error("NPS submit error:", err);
  }
}

// --- PARTNER PORTAL ---
async function openPartnerModal() {
  const modal = document.getElementById("partnerModal");
  modal.classList.remove("hidden");

  try {
    const res = await fetch("/api/partner/leads");
    const leads = await res.json();

    const tbody = document.getElementById("partnerLeadsTableBody");
    tbody.innerHTML = leads.map(l => `
      <tr class="hover:bg-slate-50/80">
        <td class="p-2.5 font-mono font-bold">${l.lead_id}</td>
        <td class="p-2.5 font-semibold text-slate-900">${l.business_name} <span class="text-slate-400 block text-[10px]">${l.city}</span></td>
        <td class="p-2.5 text-slate-600">${l.stage_reached}</td>
        <td class="p-2.5 text-red-600 font-medium">${l.drop_reason}</td>
        <td class="p-2.5">
          <span class="px-2 py-0.5 rounded-full font-bold text-[10px] ${l.propensity_score >= 70 ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}">
            Score: ${l.propensity_score}/100 (${l.priority})
          </span>
        </td>
        <td class="p-2.5">
          <button class="bg-slate-900 hover:bg-black text-white px-2 py-1 rounded text-[10px] font-bold" onclick="alert('Partner callback initiated for ${l.business_name}')">
            ${STATE.language === 'hi' ? 'कॉल करें' : 'Call Lead'}
          </button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    console.error("Partner leads error:", err);
  }
}

function closePartnerModal() {
  document.getElementById("partnerModal").classList.add("hidden");
}
