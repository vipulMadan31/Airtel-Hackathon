// Project Udyam Digital - Frontend State & Interaction Engine

const STATE = {
  language: 'en',
  safeModeNonGst: false,
  auth: {
    role: 'MERCHANT',
    token: 'tok_merchant_demo',
    user: {
      user_id: 'USR-CUST-1001',
      name: 'Rajesh Gupta (Rajesh Kirana)',
      role: 'MERCHANT'
    }
  },
  payment: {
    selectedMethod: 'UPI_PHONEPE',
    mandateOptIn: true,
    activeIntent: null,
    receipt: null
  },
  attribution: {
    partner_id: null,
    is_assisted: false
  },
  profile: {
    business_type: null,
    employee_count: null,
    num_sites: 1,
    city: null,
    city_tier: null,
    has_gstin: null
  },
  chatHistory: [],
  selectedBundle: {},
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
  checkKycTokenHandoff();
  checkPartnerAttribution();
  initViewRouter();
});

// --- INITIAL VIEW ROUTER ---
function initViewRouter() {
  const path = window.location.pathname.toLowerCase();
  const urlParams = new URLSearchParams(window.location.search);
  const roleParam = (urlParams.get("role") || "").toUpperCase();

  if (path === "/mitra" || roleParam === "PARTNER") {
    switchUserRole("PARTNER");
  } else if (path === "/ops" || path === "/admin" || roleParam === "ADMIN") {
    switchUserRole("ADMIN");
  } else {
    navigateToView("MERCHANT", false);
  }

  window.addEventListener("popstate", () => {
    const curPath = window.location.pathname.toLowerCase();
    if (curPath === "/mitra") {
      switchUserRole("PARTNER");
    } else if (curPath === "/ops" || curPath === "/admin") {
      switchUserRole("ADMIN");
    } else {
      switchUserRole("MERCHANT");
    }
  });
}

// --- WHATSAPP TO WEB KYC HANDOFF ---
async function checkKycTokenHandoff() {
  const urlParams = new URLSearchParams(window.location.search);
  const token = urlParams.get("token") || (window.location.hash.startsWith("#token=") ? window.location.hash.replace("#token=", "") : (window.location.hash === "#kyc" ? "TK-3210" : null));
  if (!token) return;

  try {
    const res = await fetch(`/api/whatsapp/token/${token}`);
    const data = await res.json();
    if (data.bundle && Object.keys(data.bundle).length > 0) {
      STATE.selectedBundle = data.bundle;
      if (data.profile) STATE.profile = data.profile;
      recalculateQuote();
    }
  } catch (e) {
    console.warn("Token fetch failed:", e);
  }

  // Auto transition from Quote Card to KYC Card
  const quoteCard = document.getElementById("quoteCard");
  const kycCard = document.getElementById("kycCard");
  if (quoteCard) quoteCard.classList.add("hidden");
  if (kycCard) {
    kycCard.classList.remove("hidden");
    const existingBanner = document.getElementById("waHandoffBanner");
    if (!existingBanner) {
      const banner = document.createElement("div");
      banner.id = "waHandoffBanner";
      banner.className = "mb-4 p-3.5 bg-emerald-50 border border-emerald-300 rounded-2xl text-xs text-emerald-950 flex items-center justify-between shadow-xs";
      banner.innerHTML = `
        <div class="flex items-center space-x-2.5">
          <span class="text-xl">📱</span>
          <div>
            <strong class="font-extrabold text-emerald-900 block">WhatsApp Channel Handoff Active (Token: ${token})</strong>
            <p class="text-[11px] text-emerald-700">Pre-locked quotation loaded from chat. Telecom regulations (DoT/TRAI) mandate high-res camera capture for instant activation.</p>
          </div>
        </div>
        <span class="text-[10px] bg-emerald-200 text-emerald-900 font-extrabold px-2.5 py-1 rounded-full uppercase tracking-wider">Pre-Filled</span>
      `;
      kycCard.insertBefore(banner, kycCard.firstChild);
    }
  }
}

// --- CHANNEL PARTNER QUERY ATTRIBUTION ---
function checkPartnerAttribution() {
  const urlParams = new URLSearchParams(window.location.search);
  const refCode = urlParams.get("ref") || urlParams.get("partner_id");
  const banner = document.getElementById("partnerAttributionBanner");

  if (refCode) {
    STATE.attribution.partner_id = refCode;
    STATE.attribution.is_assisted = true;
    if (banner) banner.classList.remove("hidden");
    console.log(`Channel Partner referral attribution active: ${refCode}`);
  }
}

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
  setText("t-pincode-label", dict.pincode_label);
  setText("t-check-btn", dict.check_btn);
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
  setText("t-admin-btn", dict.admin_btn);
  setText("t-admin-title", dict.admin_title);
  setText("t-admin-sub", dict.admin_sub);

  // Payment Modal & Receipt i18n
  setText("t-pay-modal-title", dict.pay_modal_title);
  setText("t-pay-modal-sub", dict.pay_modal_sub);
  setText("t-pay-summary-heading", dict.pay_summary_heading);
  setText("t-pay-refundable-badge", dict.pay_refundable_badge);
  setText("t-pay-inclusive-gst", dict.pay_inclusive_gst);
  setText("t-pay-select-app", dict.pay_select_app);
  setText("t-pay-mandate-title", dict.pay_mandate_title);
  setText("t-pay-mandate-desc", dict.pay_mandate_desc);
  setText("t-pay-simulate-btn", dict.pay_simulate_btn);
  setText("t-pay-receipt-btn", dict.pay_receipt_btn);
  setText("t-receipt-title", dict.receipt_title);
  setText("t-receipt-sub", dict.receipt_sub);
  setText("t-receipt-close", dict.receipt_close);

  // Partner Attribution & Recovery i18n
  setText("t-partner-attribution-banner", dict.partner_attribution_banner);
  setText("t-partner-qr-title", dict.partner_qr_title);
  setText("t-partner-qr-desc", dict.partner_qr_desc);
  setText("t-partner-download-qr", dict.partner_download_qr);
  setText("t-partner-commission-title", dict.partner_commission_title);
  setText("t-partner-active-referrals", dict.partner_active_referrals);
  setText("t-partner-recurring-trail", dict.partner_recurring_trail);
  setText("t-partner-recovery-bounties", dict.partner_recovery_bounties);

  updateRoleSwitcherUI();

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

// --- ENTERPRISE RBAC & ROLE SWITCHER ---
function updateRoleSwitcherUI() {
  const dict = LOCALES[STATE.language] || LOCALES.en;
  const roleBadgeIcon = document.getElementById("roleBadgeIcon");
  const roleBadgeLabel = document.getElementById("roleBadgeLabel");
  const partnerBtn = document.getElementById("partnerPortalBtn");
  const adminBtn = document.getElementById("adminPortalBtn");

  if (!roleBadgeIcon || !roleBadgeLabel) return;

  if (STATE.auth.role === 'MERCHANT') {
    roleBadgeIcon.innerText = "🛒";
    roleBadgeLabel.innerText = dict.role_merchant_label || "Customer Mode";
    if (partnerBtn) {
      partnerBtn.classList.add("hidden");
      partnerBtn.classList.remove("flex");
    }
    if (adminBtn) {
      adminBtn.classList.add("hidden");
      adminBtn.classList.remove("flex");
    }
  } else if (STATE.auth.role === 'PARTNER') {
    roleBadgeIcon.innerText = "🤝";
    roleBadgeLabel.innerText = dict.role_partner_label || "Mitra Partner";
    if (partnerBtn) {
      partnerBtn.classList.remove("hidden");
      partnerBtn.classList.add("flex");
    }
    if (adminBtn) {
      adminBtn.classList.add("hidden");
      adminBtn.classList.remove("flex");
    }
  } else if (STATE.auth.role === 'ADMIN') {
    roleBadgeIcon.innerText = "🛡️";
    roleBadgeLabel.innerText = dict.role_admin_label || "Ops Admin";
    if (partnerBtn) {
      partnerBtn.classList.remove("hidden");
      partnerBtn.classList.add("flex");
    }
    if (adminBtn) {
      adminBtn.classList.remove("hidden");
      adminBtn.classList.add("flex");
    }
  }
}

// --- VIEW ROUTER (CUSTOMER / MITRA / OPS) ---
function navigateToView(role, pushHistory = true) {
  const normRole = (role || 'MERCHANT').toUpperCase();
  STATE.auth.role = normRole;

  const customerView = document.getElementById("customerView");
  const mitraView = document.getElementById("mitraView");
  const opsView = document.getElementById("opsView");
  const safeModeToggleWrapper = document.getElementById("safeModeToggle")?.closest("label");

  if (!customerView || !mitraView || !opsView) return;

  if (normRole === 'PARTNER') {
    customerView.classList.add("hidden");
    mitraView.classList.remove("hidden");
    opsView.classList.add("hidden");
    if (safeModeToggleWrapper) safeModeToggleWrapper.classList.add("hidden");

    if (pushHistory && window.location.pathname !== '/mitra') {
      try { window.history.pushState({ role: 'PARTNER' }, '', '/mitra'); } catch (e) {}
    }
    loadPartnerViewData();
  } else if (normRole === 'ADMIN') {
    customerView.classList.add("hidden");
    mitraView.classList.add("hidden");
    opsView.classList.remove("hidden");
    if (safeModeToggleWrapper) safeModeToggleWrapper.classList.add("hidden");

    if (pushHistory && window.location.pathname !== '/ops') {
      try { window.history.pushState({ role: 'ADMIN' }, '', '/ops'); } catch (e) {}
    }
    loadOpsViewData();
  } else {
    // MERCHANT / Customer mode
    customerView.classList.remove("hidden");
    mitraView.classList.add("hidden");
    opsView.classList.add("hidden");
    if (safeModeToggleWrapper) safeModeToggleWrapper.classList.remove("hidden");

    if (pushHistory && (window.location.pathname === '/mitra' || window.location.pathname === '/ops' || window.location.pathname === '/admin')) {
      try { window.history.pushState({ role: 'MERCHANT' }, '', '/'); } catch (e) {}
    }
  }

  updateRoleSwitcherUI();
}

async function loadPartnerViewData() {
  try {
    const token = STATE.auth.token || 'tok_partner_demo';
    // 1. Fetch Partner Commissions & Telemetry
    const commRes = await fetch("/api/partner/commissions", {
      headers: {
        "Authorization": `Bearer ${token}`,
        "X-Session-Token": token
      }
    });
    if (commRes.ok) {
      const commData = await commRes.json();
      const vRef = document.getElementById("mitraViewActiveReferrals");
      const vTrail = document.getElementById("mitraViewRecurringTrail");
      const vBounty = document.getElementById("mitraViewRecoveryBounties");
      const vPayout = document.getElementById("mitraViewPendingPayout");

      if (vRef) vRef.innerText = commData.active_referrals_count;
      if (vTrail) vTrail.innerText = `₹${commData.monthly_recurring_trail_inr.toLocaleString()}/mo`;
      if (vBounty) vBounty.innerText = `₹${commData.stalled_recovery_bounties_inr.toLocaleString()}`;
      if (vPayout) vPayout.innerText = `₹${commData.total_pending_payout_inr.toLocaleString()}`;

      // Sync modal IDs for backward test compatibility
      const mRef = document.getElementById("partnerActiveReferrals");
      const mTrail = document.getElementById("partnerRecurringTrail");
      const mBounty = document.getElementById("partnerRecoveryBounties");
      const mPayout = document.getElementById("partnerPendingPayout");
      if (mRef) mRef.innerText = commData.active_referrals_count;
      if (mTrail) mTrail.innerText = `₹${commData.monthly_recurring_trail_inr.toLocaleString()}/mo`;
      if (mBounty) mBounty.innerText = `₹${commData.stalled_recovery_bounties_inr.toLocaleString()}`;
      if (mPayout) mPayout.innerText = `₹${commData.total_pending_payout_inr.toLocaleString()}`;
    }

    // 2. Fetch Stalled & Inbound Leads
    const res = await fetch("/api/partner/leads", {
      headers: {
        "Authorization": `Bearer ${token}`,
        "X-Session-Token": token
      }
    });

    if (res.ok) {
      const leads = await res.json();
      const isHi = STATE.language === 'hi';
      const rowsHtml = leads.map(l => {
        const isClaimed = l.is_claimed || false;
        const scoreBadge = `<span class="px-2 py-0.5 rounded-full font-bold text-[10px] ${l.propensity_score >= 70 ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}">Score: ${l.propensity_score}/100 (${l.priority})</span>`;

        let slaBadge = '';
        if (isClaimed) {
          slaBadge = `<span class="inline-block text-[10px] font-mono font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">🔒 24h Outreach Active</span>`;
        } else if (l.sla_status === "BREACHED") {
          slaBadge = `<span class="inline-block text-[10px] font-mono font-bold text-red-700 bg-red-100 px-2 py-0.5 rounded border border-red-300 animate-pulse">⛔ 4h SLA Expired</span>`;
        } else if (l.sla_status === "WARNING") {
          slaBadge = `<span class="inline-block text-[10px] font-mono font-bold text-amber-800 bg-amber-100 px-2 py-0.5 rounded border border-amber-300 animate-pulse">⏳ ${l.sla_remaining}</span>`;
        } else if (l.propensity_score >= 70) {
          slaBadge = `<span class="inline-block text-[10px] font-mono font-bold text-emerald-800 bg-emerald-100 px-2 py-0.5 rounded border border-emerald-200">⏳ ${l.sla_remaining}</span>`;
        } else {
          slaBadge = `<span class="inline-block text-[10px] font-mono text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">${l.sla_remaining || 'Standard SLA'}</span>`;
        }

        const routingBadge = l.routing_label 
          ? `<span class="mt-1 inline-block text-[9px] font-semibold text-indigo-700 bg-indigo-50 px-1.5 py-0.5 rounded border border-indigo-200">${l.routing_label}</span>`
          : '';

        let actionButtons = '';
        if (isClaimed) {
          actionButtons = `
            <div class="flex items-center space-x-1.5">
              <span class="bg-emerald-100 text-emerald-800 border border-emerald-300 px-2 py-0.5 rounded text-[10px] font-extrabold flex items-center space-x-1">
                <span>✔</span>
                <span>₹1,000 ${isHi ? 'बाउंटी लॉक' : 'Bounty Locked'}</span>
              </span>
              <button class="bg-slate-900 hover:bg-black text-white px-2 py-1 rounded text-[10px] font-bold" onclick="alert('Calling claimed customer ${l.business_name} (${l.phone || '+91 98765 12345'})...')">
                ${isHi ? 'कॉल करें' : 'Call'}
              </button>
            </div>
          `;
        } else if (l.sla_status === "BREACHED") {
          actionButtons = `
            <div class="flex items-center space-x-1.5">
              <span class="bg-red-50 text-red-700 border border-red-200 px-2 py-0.5 rounded text-[10px] font-extrabold">
                Escalated to HQ
              </span>
              <button class="bg-slate-200 hover:bg-slate-300 text-slate-800 px-2 py-1 rounded text-[10px] font-bold" onclick="alert('Viewing escalation details for ${l.business_name} (Escalated to Central Tele-Sales)...')">
                View
              </button>
            </div>
          `;
        } else {
          actionButtons = `
            <div class="flex items-center space-x-1.5">
              <button class="bg-amber-600 hover:bg-amber-700 text-white px-2.5 py-1 rounded text-[10px] font-extrabold shadow-xs transition" onclick="claimLeadBounty('${l.lead_id}')">
                ${isHi ? 'लीड क्लेम (₹1,000)' : 'Claim Lead (₹1k)'}
              </button>
              <button class="bg-slate-200 hover:bg-slate-300 text-slate-800 px-2 py-1 rounded text-[10px] font-bold" onclick="alert('Partner outreach initiated for ${l.business_name}')">
                ${isHi ? 'कॉल' : 'Call'}
              </button>
            </div>
          `;
        }

        return `
          <tr class="hover:bg-slate-50/80 transition ${isClaimed ? 'bg-emerald-50/30' : ''}">
            <td class="p-3 font-mono font-bold">${l.lead_id}</td>
            <td class="p-3 font-semibold text-slate-900">
              ${l.business_name}
              <span class="text-slate-400 block text-[10px]">${l.city} &bull; ${l.phone || '+91 98765 12345'}</span>
              ${routingBadge}
            </td>
            <td class="p-3 text-slate-600">${l.stage_reached}</td>
            <td class="p-3 text-red-600 font-medium">${l.drop_reason}</td>
            <td class="p-3">
              ${scoreBadge}
              <div class="mt-1">${slaBadge}</div>
            </td>
            <td class="p-3">${actionButtons}</td>
          </tr>
        `;
      }).join('');

      const viewTbody = document.getElementById("mitraViewLeadsTableBody");
      if (viewTbody) viewTbody.innerHTML = rowsHtml;
      const modalTbody = document.getElementById("partnerLeadsTableBody");
      if (modalTbody) modalTbody.innerHTML = rowsHtml;
    }
  } catch (err) {
    console.error("Partner data load error:", err);
  }
}

async function loadOpsViewData() {
  try {
    const token = STATE.auth.token || 'tok_admin_demo';
    const res = await fetch("/api/admin/metrics", {
      headers: {
        "Authorization": `Bearer ${token}`,
        "X-Session-Token": token
      }
    });

    if (res.ok) {
      const data = await res.json();
      const vTotal = document.getElementById("opsViewTotalLeads");
      const vConv = document.getElementById("opsViewConvRate");
      const vTta = document.getElementById("opsViewTta");
      const vCac = document.getElementById("opsViewCac");

      if (vTotal) vTotal.innerText = data.funnel_metrics.total_inbound_leads.toLocaleString();
      if (vConv) vConv.innerText = `${data.funnel_metrics.projected_digital_conversion_rate_percent}%`;
      if (vTta) vTta.innerText = `${data.operational_efficiency.udyam_digital_tta_days} Days`;
      if (vCac) vCac.innerText = `₹${data.operational_efficiency.udyam_digital_cac_inr.toLocaleString()}`;

      // Sync modal IDs
      const mTotal = document.getElementById("adminTotalLeads");
      const mConv = document.getElementById("adminConvRate");
      const mTta = document.getElementById("adminTta");
      const mCac = document.getElementById("adminCac");
      if (mTotal) mTotal.innerText = data.funnel_metrics.total_inbound_leads.toLocaleString();
      if (mConv) mConv.innerText = `${data.funnel_metrics.projected_digital_conversion_rate_percent}%`;
      if (mTta) mTta.innerText = `${data.operational_efficiency.udyam_digital_tta_days} Days`;
      if (mCac) mCac.innerText = `₹${data.operational_efficiency.udyam_digital_cac_inr.toLocaleString()}`;

      if (data.manual_escalations_queue) {
        const rowsHtml = data.manual_escalations_queue.map(e => `
          <tr class="hover:bg-slate-50/80">
            <td class="p-3 font-mono font-bold">${e.escalation_id}</td>
            <td class="p-3 font-bold text-slate-900">${e.business_name}</td>
            <td class="p-3 text-amber-800 font-medium">${e.issue}</td>
            <td class="p-3 text-slate-600">${e.assigned_agent}</td>
            <td class="p-3 font-mono font-semibold text-red-600">${e.sla_remaining_hours}h left</td>
            <td class="p-3">
              <button class="bg-purple-700 hover:bg-purple-800 text-white px-2.5 py-1 rounded text-[10px] font-bold" onclick="alert('Admin override verified for ${e.business_name}')">
                Approve Override
              </button>
            </td>
          </tr>
        `).join('');

        const vTbody = document.getElementById("opsViewEscalationTableBody");
        if (vTbody) vTbody.innerHTML = rowsHtml;
        const mTbody = document.getElementById("adminEscalationTableBody");
        if (mTbody) mTbody.innerHTML = rowsHtml;
      }
    }
  } catch (err) {
    console.error("Ops metrics fetch error:", err);
  }
}

async function switchUserRole(roleName) {
  const dropdown = document.getElementById("roleDropdownMenu");
  if (dropdown) dropdown.classList.add("hidden");

  try {
    const res = await fetch("/api/auth/switch-role", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role: roleName })
    });
    const data = await res.json();
    if (data.status === "success") {
      STATE.auth.role = data.user.role;
      STATE.auth.token = data.token;
      STATE.auth.user = data.user;
      navigateToView(data.user.role, true);

      const isHi = STATE.language === 'hi';
      const toastMsg = isHi
        ? `सफलतापूर्वक प्रोफ़ाइल स्विच की गई: ${data.user.name} (${data.user.role})`
        : `Switched profile to: ${data.user.name} (${data.user.role})`;
      console.log(toastMsg);
    }
  } catch (err) {
    console.error("Role switch failed:", err);
  }
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
  const chatInputEl = document.getElementById("chatInput");
  document.getElementById("sendBtn").addEventListener("click", handleChatSubmit);
  
  if (chatInputEl) {
    chatInputEl.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        if (e.shiftKey) {
          // Shift+Enter allows newline naturally
          return;
        }
        // Enter without Shift submits message
        e.preventDefault();
        handleChatSubmit();
      }
    });

    // Auto-grow textarea smoothly as user types multiline
    chatInputEl.addEventListener("input", () => {
      chatInputEl.style.height = "auto";
      chatInputEl.style.height = Math.min(chatInputEl.scrollHeight, 120) + "px";
    });
  }

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

  // Admin Modal
  const adminPortalBtn = document.getElementById("adminPortalBtn");
  if (adminPortalBtn) adminPortalBtn.addEventListener("click", openAdminModal);
  const closeAdminModalBtn = document.getElementById("closeAdminModalBtn");
  if (closeAdminModalBtn) closeAdminModalBtn.addEventListener("click", closeAdminModal);

  // Role Switcher Dropdown Toggle
  const roleDropdownBtn = document.getElementById("roleDropdownBtn");
  const roleDropdownMenu = document.getElementById("roleDropdownMenu");
  if (roleDropdownBtn && roleDropdownMenu) {
    roleDropdownBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      roleDropdownMenu.classList.toggle("hidden");
    });
    document.addEventListener("click", (e) => {
      if (!roleDropdownMenu.contains(e.target) && !roleDropdownBtn.contains(e.target)) {
        roleDropdownMenu.classList.add("hidden");
      }
    });
  }

  // Role Persona Switch Handlers
  const switchMerchantBtn = document.getElementById("switchRoleMerchant");
  if (switchMerchantBtn) switchMerchantBtn.addEventListener("click", () => switchUserRole("MERCHANT"));
  const switchPartnerBtn = document.getElementById("switchRolePartner");
  if (switchPartnerBtn) switchPartnerBtn.addEventListener("click", () => switchUserRole("PARTNER"));
  const switchAdminBtn = document.getElementById("switchRoleAdmin");
  if (switchAdminBtn) switchAdminBtn.addEventListener("click", () => switchUserRole("ADMIN"));

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

  // Pincode Feasibility Check
  const checkPinBtn = document.getElementById("checkPincodeBtn");
  if (checkPinBtn) checkPinBtn.addEventListener("click", handlePincodeCheck);
  const pinInput = document.getElementById("pincodeInput");
  if (pinInput) {
    pinInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter") handlePincodeCheck();
    });
  }

  // Payment Modal Triggers
  const openPayQuoteBtn = document.getElementById("openPaymentModalFromQuoteBtn");
  if (openPayQuoteBtn) openPayQuoteBtn.addEventListener("click", () => openPaymentModal());
  const closePayModalBtn = document.getElementById("closePaymentModalBtn");
  if (closePayModalBtn) closePayModalBtn.addEventListener("click", closePaymentModal);
  const execPayBtn = document.getElementById("executePaymentBtn");
  if (execPayBtn) execPayBtn.addEventListener("click", handlePaymentExecute);

  // UPI App Selection
  document.querySelectorAll(".pay-app-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".pay-app-btn").forEach(b => {
        b.className = "pay-app-btn p-2 rounded-lg border border-slate-200 hover:bg-slate-50 flex items-center space-x-2 text-left transition";
      });
      btn.className = "pay-app-btn p-2 rounded-lg border border-emerald-500 bg-emerald-50 ring-1 ring-emerald-500 flex items-center space-x-2 text-left transition";
      STATE.payment.selectedMethod = btn.getAttribute("data-method");
    });
  });

  // Mandate Checkbox
  const mandateCb = document.getElementById("mandateConsentCheckbox");
  if (mandateCb) {
    mandateCb.addEventListener("change", (e) => {
      STATE.payment.mandateOptIn = e.target.checked;
    });
  }

  // Receipt Modal
  const viewReceiptBtn = document.getElementById("viewReceiptBtn");
  if (viewReceiptBtn) viewReceiptBtn.addEventListener("click", () => openReceiptModal());
  const closeReceiptModalBtn = document.getElementById("closeReceiptModalBtn");
  if (closeReceiptModalBtn) closeReceiptModalBtn.addEventListener("click", closeReceiptModal);
  const closeReceiptBtn = document.getElementById("closeReceiptBtn");
  if (closeReceiptBtn) closeReceiptBtn.addEventListener("click", closeReceiptModal);

  // Partner Link & QR Actions
  const copyLinkBtn = document.getElementById("copyPartnerLinkBtn");
  if (copyLinkBtn) {
    copyLinkBtn.addEventListener("click", () => {
      navigator.clipboard?.writeText("http://localhost:8000/?ref=PTR-IND-882");
      alert("Partner Referral link copied to clipboard: http://localhost:8000/?ref=PTR-IND-882");
    });
  }
  const dlQrBtn = document.getElementById("downloadPartnerQrBtn");
  if (dlQrBtn) {
    dlQrBtn.addEventListener("click", () => {
      alert("Downloading official store counter QR sticker asset for Mitra Partner PTR-IND-882...");
    });
  }

  // Back to Customer View Buttons
  document.querySelectorAll(".backToCustomerBtn").forEach(btn => {
    btn.addEventListener("click", () => switchUserRole("MERCHANT"));
  });

  // Dedicated Mitra View Copy & Download Buttons
  document.querySelectorAll(".copyPartnerViewLinkBtn").forEach(btn => {
    btn.addEventListener("click", () => {
      navigator.clipboard?.writeText("http://localhost:8000/?ref=PTR-IND-882");
      alert("Partner Referral link copied to clipboard: http://localhost:8000/?ref=PTR-IND-882");
    });
  });

  document.querySelectorAll(".downloadPartnerViewQrBtn").forEach(btn => {
    btn.addEventListener("click", () => {
      alert("Downloading official store counter QR sticker asset for Mitra Partner PTR-IND-882...");
    });
  });

  // Voice Recognition (Web Speech API)
  initVoiceRecognition();
}

// --- WEB SPEECH API (BILINGUAL VOICE TYPING) ---
let recognitionInstance = null;
let isVoiceRecording = false;

function initVoiceRecognition() {
  const micBtn = document.getElementById("micBtn");
  if (!micBtn) return;

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (!SpeechRecognition) {
    micBtn.addEventListener("click", () => {
      alert(STATE.language === 'hi' 
        ? "वॉयस इनपुट के लिए Google Chrome या Microsoft Edge का उपयोग करें।" 
        : "Speech Recognition is supported in Google Chrome & Microsoft Edge. Please type your requirements.");
    });
    return;
  }

  try {
    recognitionInstance = new SpeechRecognition();
    recognitionInstance.continuous = false;
    recognitionInstance.interimResults = false;

    recognitionInstance.onstart = () => {
      isVoiceRecording = true;
      micBtn.className = "p-2 rounded-xl bg-red-600 text-white border border-red-700 animate-pulse transition flex items-center justify-center shrink-0 shadow-md";
      const chatIn = document.getElementById("chatInput");
      if (chatIn) chatIn.placeholder = STATE.language === 'hi' ? "सुन रहे हैं... बोलिए..." : "Listening... Speak now...";
    };

    recognitionInstance.onresult = (event) => {
      if (event.results && event.results.length > 0) {
        const transcript = event.results[0][0].transcript;
        const chatIn = document.getElementById("chatInput");
        if (chatIn) {
          chatIn.value = transcript;
          chatIn.style.height = "auto";
          chatIn.style.height = Math.min(chatIn.scrollHeight, 120) + "px";
          handleChatSubmit();
        }
      }
    };

    recognitionInstance.onerror = (event) => {
      console.warn("Speech recognition error:", event.error);
      stopVoiceRecording();
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        alert(STATE.language === 'hi' 
          ? "माइक्रोफ़ोन की अनुमति ब्लॉक है। कृपया अपने ब्राउज़र के एड्रेस बार में लॉक/आइकन पर क्लिक करें और माइक्रोफ़ोन की अनुमति (Allow) दें।" 
          : "Microphone permission is blocked. Please click the site permissions/lock icon next to the URL in your browser and set Microphone to 'Allow'.");
      } else if (event.error === "audio-capture") {
        alert(STATE.language === 'hi'
          ? "कोई माइक्रोफ़ोन नहीं मिला। कृपया अपना माइक्रोफ़ोन कनेक्ट करें।"
          : "No microphone detected. Please ensure a microphone is connected to your device.");
      } else if (event.error === "network") {
        alert(STATE.language === 'hi'
          ? "वॉयस रिकॉग्निशन नेटवर्क त्रुटि। कृपया इंटरनेट कनेक्शन जांचें।"
          : "Voice recognition network error. Please check your internet connection.");
      }
    };

    recognitionInstance.onend = () => {
      stopVoiceRecording();
    };

    micBtn.addEventListener("click", () => {
      if (isVoiceRecording) {
        recognitionInstance.stop();
        stopVoiceRecording();
      } else {
        recognitionInstance.lang = STATE.language === 'hi' ? 'hi-IN' : 'en-IN';
        try {
          recognitionInstance.start();
        } catch (err) {
          console.warn("Recognition start failed:", err);
        }
      }
    });
  } catch (e) {
    console.warn("Web Speech API initialization:", e);
  }
}

function stopVoiceRecording() {
  isVoiceRecording = false;
  const micBtn = document.getElementById("micBtn");
  if (micBtn) {
    micBtn.className = "p-2 rounded-xl border border-slate-200 hover:bg-slate-100 text-slate-600 transition flex items-center justify-center shrink-0";
  }
  const dict = LOCALES[STATE.language] || LOCALES.en;
  const chatIn = document.getElementById("chatInput");
  if (chatIn) chatIn.placeholder = dict.chat_placeholder;
}

// --- PINCODE & AIRFIBER FEASIBILITY CHECKER ---
async function handlePincodeCheck() {
  const pinInput = document.getElementById("pincodeInput");
  const pincode = pinInput ? pinInput.value.trim() : "452001";
  const badge = document.getElementById("pincodeFeasibilityBadge");
  const isHi = STATE.language === 'hi';

  if (!pincode || pincode.length < 6) {
    alert(isHi ? "कृपया वैध 6-अंकीय पिनकोड दर्ज करें।" : "Please enter a valid 6-digit postal pincode.");
    return;
  }

  try {
    const res = await fetch("/api/catalog/feasibility", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pincode: pincode })
    });
    const data = await res.json();

    if (data.is_fibre_feasible) {
      if (badge) {
        badge.className = "flex items-center space-x-1 font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-1 rounded-lg text-[11px]";
        badge.innerHTML = `<span>✔ ${isHi ? 'ऑप्टिकल फाइबर उपलब्ध (FTTH)' : 'Fibre Feasible (FTTH)'}</span>`;
      }
    } else {
      // Wireline fiber blocked -> Intelligently switch to P04 (5G AirFiber)
      if (badge) {
        badge.className = "flex items-center space-x-1 font-bold text-amber-800 bg-amber-50 border border-amber-300 px-2 py-1 rounded-lg text-[11px] animate-pulse";
        badge.innerHTML = `<span>⚡ ${isHi ? '5G एयरफाइबर लागू (48h सेटअप)' : '5G AirFiber Switched (48h Setup)'}</span>`;
      }

      // Automatically swap wireline base plan for P04 (Biz 5G AirFiber 100)
      if (STATE.selectedBundle["P01"]) delete STATE.selectedBundle["P01"];
      if (STATE.selectedBundle["P02"]) delete STATE.selectedBundle["P02"];
      if (STATE.selectedBundle["P03"]) delete STATE.selectedBundle["P03"];
      STATE.selectedBundle["P04"] = 1;

      recalculateQuote();

      // Conversational prompt explaining the operational switch
      addAiChatMessage(
        isHi
          ? `पिनकोड ${pincode} पर वायरलाइन केबल बिछाना अभी ब्लॉक है। हमने आपके बंडल को तुरंत <strong>एयरटेल बिज़ 5G एयरफाइबर 100 (P04)</strong> (₹899/माह) में बदल दिया है — बिना किसी तार के 48 घंटे में एक्टिवेशन!`
          : `Optical wireline digging is pending at pincode ${pincode}. We seamlessly updated your bundle to <strong>Airtel Biz 5G AirFiber 100 (P04)</strong> at ₹899/mo with zero-wire installation in <48 hours!`
      );
    }
  } catch (err) {
    console.error("Feasibility check error:", err);
  }
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
function showChatTyping() {
  const container = document.getElementById("chatMessages");
  const div = document.createElement("div");
  div.id = "chatTypingIndicator";
  div.className = "flex justify-start";
  const isHi = STATE.language === 'hi';
  div.innerHTML = `
    <div class="chat-bubble-ai px-3.5 py-2 text-xs font-medium text-slate-500 italic flex items-center space-x-2 shadow-sm bg-slate-100 rounded-xl">
      <span class="inline-block w-2 h-2 rounded-full bg-airtel-red animate-ping"></span>
      <span>${isHi ? 'एयरटेल एआई उत्तर तैयार कर रहा है...' : 'Airtel AI is formulating recommendation...'}</span>
    </div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return div;
}

function removeChatTyping() {
  const el = document.getElementById("chatTypingIndicator");
  if (el) el.remove();
}

async function handleChatSubmit() {
  const input = document.getElementById("chatInput");
  const message = input.value.trim();
  if (!message) return;

  addUserChatMessage(message);
  input.value = "";
  input.style.height = "auto";
  const typingIndicator = showChatTyping();

  // Track user turn in chat history
  if (!STATE.chatHistory) STATE.chatHistory = [];
  STATE.chatHistory.push({ role: "user", text: message });

  try {
    const res = await fetch("/api/advisor/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: message,
        current_profile: STATE.profile,
        language: STATE.language,
        history: STATE.chatHistory
      })
    });
    const data = await res.json();
    removeChatTyping();

    if (data.ai_engine) {
      const badge = document.getElementById("t-rule-guarded");
      if (badge) badge.innerText = data.ai_engine;
    }

    // Always merge profile facts so known context (e.g. city, startup, headcount) is NEVER lost across turns
    if (data.profile) {
      STATE.profile = Object.assign({}, STATE.profile, data.profile);

      // Conversational Pincode & Network Feasibility Synchronization
      if (data.profile.pincode) {
        const pinInput = document.getElementById("pincodeInput");
        if (pinInput && pinInput.value !== data.profile.pincode) {
          pinInput.value = data.profile.pincode;
          handlePincodeCheck();
        }
      }
    }
    if (data.recommended_bundle && Object.keys(data.recommended_bundle).length > 0) {
      STATE.selectedBundle = data.recommended_bundle;
      recalculateQuote();
    }

    // Track assistant turn in chat history
    if (data.message) {
      STATE.chatHistory.push({ role: "model", text: data.message });
    }

    addAiChatMessage(data.message, data.explainability_tags);
  } catch (err) {
    removeChatTyping();
    addAiChatMessage("Sorry, could not process request right now. Fallback to guided selection.");
  }
}

function addUserChatMessage(text) {
  const container = document.getElementById("chatMessages");
  const div = document.createElement("div");
  div.className = "flex justify-end";
  div.innerHTML = `<div class="chat-bubble-user px-3.5 py-2 text-xs font-medium max-w-[85%] shadow-sm whitespace-pre-line">${text}</div>`;
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
      <p class="leading-relaxed whitespace-pre-line">${text}</p>
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
        language: STATE.language,
        partner_id: STATE.attribution.partner_id || (STATE.auth.role === 'PARTNER' ? STATE.auth.user.user_id : null)
      })
    });
    const order = await res.json();
    STATE.activeOrder = order;

    document.getElementById("kycCard").classList.add("hidden");
    document.getElementById("trackerCard").classList.remove("hidden");

    renderTracker(order);

    // If order has unconfirmed token deposit, open payment modal to secure the booking
    if (!order.token_paid) {
      setTimeout(() => {
        openPaymentModal(order.order_id);
      }, 400);
    }
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

  const isTokenPaid = !!(order.token_paid || (order.receipt && order.receipt.payment_status === "SUCCESS"));
  const txnText = order.payment_txn_id || (order.receipt ? order.receipt.txn_id : "TXN-UPI-AUTO");

  timeline.innerHTML = `
    <div class="flex items-center space-x-3 text-xs">
      <span class="w-6 h-6 rounded-full bg-emerald-500 text-white flex items-center justify-center font-bold">✔</span>
      <div>
        <strong class="text-slate-900 block">${dict.step1_title}</strong>
        <span class="text-slate-500">${isTokenPaid ? `<span class="text-emerald-700 font-bold">Ref: ${txnText} &bull; ${dict.step1_sub}</span>` : dict.step1_sub}</span>
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

// --- SIMULATED PAYMENT GATEWAY & UPI AUTOPAY ---
async function openPaymentModal(orderId = null) {
  const modal = document.getElementById("paymentModal");
  if (!modal) return;
  modal.classList.remove("hidden");

  const effectiveOrderId = orderId || (STATE.activeOrder ? STATE.activeOrder.order_id : "PENDING_QUOTE");
  const businessName = document.getElementById("extractedNameInput")?.value || "Airtel MSME Customer";

  try {
    const res = await fetch("/api/payment/create-intent", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        order_id: effectiveOrderId,
        amount_inr: 499.0,
        business_name: businessName,
        phone: "+91 98765 12345"
      })
    });
    const intent = await res.json();
    STATE.payment.activeIntent = intent;

    const amtEl = document.getElementById("payModalAmount");
    if (amtEl) amtEl.innerText = `₹${intent.amount_inr.toFixed(2)}`;

    const dateEl = document.getElementById("payScheduledDate");
    if (dateEl && STATE.activeOrder) {
      dateEl.innerText = `${STATE.activeOrder.scheduled_install_date} (Guaranteed Slot)`;
    }
  } catch (err) {
    console.error("Payment intent error:", err);
  }
}

function closePaymentModal() {
  const modal = document.getElementById("paymentModal");
  if (modal) modal.classList.add("hidden");
}

async function handlePaymentExecute() {
  const execBtn = document.getElementById("executePaymentBtn");
  if (execBtn) {
    execBtn.disabled = true;
    execBtn.innerText = STATE.language === 'hi' ? "भुगतान सत्यापित हो रहा है..." : "Processing UPI PIN...";
  }

  const orderId = STATE.activeOrder ? STATE.activeOrder.order_id : "UDYAM-PREPAID";
  const txnId = STATE.payment.activeIntent ? STATE.payment.activeIntent.txn_id : `TXN-UPI-${Date.now()}`;

  try {
    const res = await fetch("/api/payment/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        order_id: orderId,
        txn_id: txnId,
        payment_method: STATE.payment.selectedMethod || "UPI_PHONEPE",
        mandate_active: STATE.payment.mandateOptIn,
        amount_inr: 499.0
      })
    });

    const receipt = await res.json();
    STATE.payment.receipt = receipt;

    if (STATE.activeOrder) {
      STATE.activeOrder.token_paid = true;
      STATE.activeOrder.payment_txn_id = receipt.txn_id;
      STATE.activeOrder.receipt = receipt;
      renderTracker(STATE.activeOrder);
    }

    closePaymentModal();

    // Show instant receipt modal
    openReceiptModal(receipt);

    if (execBtn) {
      execBtn.disabled = false;
      const dict = LOCALES[STATE.language] || LOCALES.en;
      execBtn.innerText = dict.pay_simulate_btn;
    }
  } catch (err) {
    console.error("Payment confirmation failed:", err);
    if (execBtn) execBtn.disabled = false;
    alert("Payment confirmation failed.");
  }
}

function openReceiptModal(customReceipt = null) {
  const modal = document.getElementById("receiptModal");
  if (!modal) return;

  const r = customReceipt || STATE.payment.receipt || (STATE.activeOrder ? STATE.activeOrder.receipt : null);
  if (!r) {
    alert("No receipt found for this order yet.");
    return;
  }

  const numEl = document.getElementById("rcptNum");
  const ordEl = document.getElementById("rcptOrderId");
  const txnEl = document.getElementById("rcptTxnId");
  const dateEl = document.getElementById("rcptDate");
  const modeEl = document.getElementById("rcptMode");
  const baseEl = document.getElementById("rcptBase");
  const cgstEl = document.getElementById("rcptCgst");
  const sgstEl = document.getElementById("rcptSgst");
  const totalEl = document.getElementById("rcptTotal");

  if (numEl) numEl.innerText = r.receipt_number;
  if (ordEl) ordEl.innerText = r.order_id || (STATE.activeOrder ? STATE.activeOrder.order_id : "N/A");
  if (txnEl) txnEl.innerText = r.txn_id;
  if (dateEl) dateEl.innerText = (r.timestamp || "").split("T")[0] || "2026-11-07";
  if (modeEl) modeEl.innerText = `${r.payment_method} (${r.mandate_status === 'ACTIVE' ? 'AutoPay Enabled' : 'Single Token'})`;
  if (baseEl) baseEl.innerText = `₹${r.base_amount_inr ? r.base_amount_inr.toFixed(2) : '422.88'}`;
  if (cgstEl) cgstEl.innerText = `₹${r.gst_18_inr ? (r.gst_18_inr / 2).toFixed(2) : '38.06'}`;
  if (sgstEl) sgstEl.innerText = `₹${r.gst_18_inr ? (r.gst_18_inr / 2).toFixed(2) : '38.06'}`;
  if (totalEl) totalEl.innerText = `₹${r.amount_paid_inr ? r.amount_paid_inr.toFixed(2) : '499.00'}`;

  modal.classList.remove("hidden");
}

function closeReceiptModal() {
  const modal = document.getElementById("receiptModal");
  if (modal) modal.classList.add("hidden");
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

// --- PARTNER PORTAL (RBAC Guarded) ---
async function openPartnerModal() {
  const modal = document.getElementById("partnerModal");
  if (!modal) return;
  modal.classList.remove("hidden");

  try {
    // 1. Fetch Partner Commissions & Telemetry
    try {
      const commRes = await fetch("/api/partner/commissions", {
        headers: {
          "Authorization": `Bearer ${STATE.auth.token}`,
          "X-Session-Token": STATE.auth.token
        }
      });
      if (commRes.ok) {
        const commData = await commRes.json();
        const refCountEl = document.getElementById("partnerActiveReferrals");
        const trailEl = document.getElementById("partnerRecurringTrail");
        const bountyEl = document.getElementById("partnerRecoveryBounties");
        const payoutEl = document.getElementById("partnerPendingPayout");

        if (refCountEl) refCountEl.innerText = commData.active_referrals_count;
        if (trailEl) trailEl.innerText = `₹${commData.monthly_recurring_trail_inr.toLocaleString()}/mo`;
        if (bountyEl) bountyEl.innerText = `₹${commData.stalled_recovery_bounties_inr.toLocaleString()}`;
        if (payoutEl) payoutEl.innerText = `₹${commData.total_pending_payout_inr.toLocaleString()}`;
      }
    } catch (cErr) {
      console.warn("Commissions fetch warning:", cErr);
    }

    // 2. Fetch Stalled & Inbound Leads
    const res = await fetch("/api/partner/leads", {
      headers: {
        "Authorization": `Bearer ${STATE.auth.token}`,
        "X-Session-Token": STATE.auth.token
      }
    });

    const tbody = document.getElementById("partnerLeadsTableBody");
    if (!tbody) return;

    if (res.status === 403) {
      const err = await res.json();
      tbody.innerHTML = `
        <tr>
          <td colspan="6" class="p-6 text-center bg-red-50 text-red-700 font-bold">
            ⛔ ${err.detail || 'Access Denied: Regular customer accounts cannot view unclosed leads. Switch to Partner or Admin role.'}
          </td>
        </tr>
      `;
      return;
    }

    const leads = await res.json();
    const isHi = STATE.language === 'hi';
    tbody.innerHTML = leads.map(l => {
      const isClaimed = l.is_claimed || false;
      const scoreBadge = `<span class="px-2 py-0.5 rounded-full font-bold text-[10px] ${l.propensity_score >= 70 ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}">Score: ${l.propensity_score}/100 (${l.priority})</span>`;

      let actionButtons = '';
      if (isClaimed) {
        actionButtons = `
          <div class="flex items-center space-x-1.5">
            <span class="bg-emerald-100 text-emerald-800 border border-emerald-300 px-2 py-0.5 rounded text-[10px] font-extrabold flex items-center space-x-1">
              <span>✔</span>
              <span>₹1,000 ${isHi ? 'बाउंटी लॉक' : 'Bounty Locked'}</span>
            </span>
            <button class="bg-slate-900 hover:bg-black text-white px-2 py-1 rounded text-[10px] font-bold" onclick="alert('Calling claimed customer ${l.business_name} (${l.phone || '+91 98765 12345'})...')">
              ${isHi ? 'कॉल करें' : 'Call'}
            </button>
          </div>
        `;
      } else {
        actionButtons = `
          <div class="flex items-center space-x-1.5">
            <button class="bg-amber-600 hover:bg-amber-700 text-white px-2.5 py-1 rounded text-[10px] font-extrabold shadow-xs transition" onclick="claimLeadBounty('${l.lead_id}')">
              ${isHi ? 'लीड क्लेम (₹1,000)' : 'Claim Lead (₹1k)'}
            </button>
            <button class="bg-slate-200 hover:bg-slate-300 text-slate-800 px-2 py-1 rounded text-[10px] font-bold" onclick="alert('Partner outreach initiated for ${l.business_name}')">
              ${isHi ? 'कॉल' : 'Call'}
            </button>
          </div>
        `;
      }

      return `
        <tr class="hover:bg-slate-50/80 transition ${isClaimed ? 'bg-emerald-50/30' : ''}">
          <td class="p-2.5 font-mono font-bold">${l.lead_id}</td>
          <td class="p-2.5 font-semibold text-slate-900">
            ${l.business_name}
            <span class="text-slate-400 block text-[10px]">${l.city} &bull; ${l.phone || '+91 98765 12345'}</span>
          </td>
          <td class="p-2.5 text-slate-600">${l.stage_reached}</td>
          <td class="p-2.5 text-red-600 font-medium">${l.drop_reason}</td>
          <td class="p-2.5">${scoreBadge}</td>
          <td class="p-2.5">${actionButtons}</td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error("Partner leads error:", err);
  }
}

// Window handler for Claim Lead Bounty
window.claimLeadBounty = async function(leadId) {
  try {
    const res = await fetch(`/api/partner/leads/${leadId}/claim`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${STATE.auth.token}`,
        "X-Session-Token": STATE.auth.token,
        "Content-Type": "application/json"
      }
    });

    if (!res.ok) {
      const err = await res.json();
      alert(`Claim failed: ${err.detail || 'Could not claim lead'}`);
      return;
    }

    const data = await res.json();
    const isHi = STATE.language === 'hi';
    const alertMsg = isHi
      ? `लीड ${leadId} को सफलतापूर्वक क्लेम कर लिया गया है!\n₹1,000 की रिकवरी बाउंटी लॉक कर दी गई है।\nकृपया 4 घंटे के भीतर ग्राहक से संपर्क करें।`
      : `Lead ${leadId} claimed successfully!\n₹1,000 spot recovery bounty locked for Mitra Partner PTR-IND-882.\nOutreach SLA: 4 hours.`;
    alert(alertMsg);
    await loadPartnerViewData();
    await openPartnerModal();
  } catch (err) {
    console.error("Claim error:", err);
    alert("Network error while claiming lead.");
  }
};

function closePartnerModal() {
  const modal = document.getElementById("partnerModal");
  if (modal) modal.classList.add("hidden");
}

// --- ADMIN OPERATIONS PORTAL (RBAC Guarded) ---
async function openAdminModal() {
  const modal = document.getElementById("adminModal");
  if (!modal) return;
  modal.classList.remove("hidden");

  try {
    const res = await fetch("/api/admin/metrics", {
      headers: {
        "Authorization": `Bearer ${STATE.auth.token}`,
        "X-Session-Token": STATE.auth.token
      }
    });

    if (res.status === 403) {
      alert("Access Denied: Enterprise Ops Admin credentials required.");
      modal.classList.add("hidden");
      return;
    }

    const data = await res.json();
    const totalLeadsEl = document.getElementById("adminTotalLeads");
    const convRateEl = document.getElementById("adminConvRate");
    const ttaEl = document.getElementById("adminTta");
    const cacEl = document.getElementById("adminCac");

    if (totalLeadsEl) totalLeadsEl.innerText = data.funnel_metrics.total_inbound_leads.toLocaleString();
    if (convRateEl) convRateEl.innerText = `${data.funnel_metrics.projected_digital_conversion_rate_percent}%`;
    if (ttaEl) ttaEl.innerText = `${data.operational_efficiency.udyam_digital_tta_days} Days`;
    if (cacEl) cacEl.innerText = `₹${data.operational_efficiency.udyam_digital_cac_inr.toLocaleString()}`;

    const tbody = document.getElementById("adminEscalationTableBody");
    if (tbody && data.manual_escalations_queue) {
      tbody.innerHTML = data.manual_escalations_queue.map(e => `
        <tr class="hover:bg-slate-50/80">
          <td class="p-2.5 font-mono font-bold">${e.escalation_id}</td>
          <td class="p-2.5 font-bold text-slate-900">${e.business_name}</td>
          <td class="p-2.5 text-amber-800 font-medium">${e.issue}</td>
          <td class="p-2.5 text-slate-600">${e.assigned_agent}</td>
          <td class="p-2.5 font-mono font-semibold text-red-600">${e.sla_remaining_hours}h left</td>
          <td class="p-2.5">
            <button class="bg-purple-700 hover:bg-purple-800 text-white px-2.5 py-1 rounded text-[10px] font-bold" onclick="alert('Admin override verified for ${e.business_name}')">
              Approve Override
            </button>
          </td>
        </tr>
      `).join('');
    }
  } catch (err) {
    console.error("Admin metrics fetch error:", err);
  }
}

function closeAdminModal() {
  const modal = document.getElementById("adminModal");
  if (modal) modal.classList.add("hidden");
}
