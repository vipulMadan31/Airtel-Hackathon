// Project Udyam Digital - WhatsApp Simulator Client Logic

let WA_PHONE = "919876543210";
let WA_LANG = "en";

document.addEventListener("DOMContentLoaded", () => {
  initWaEventListeners();
});

function initWaEventListeners() {
  const sendBtn = document.getElementById("waSendBtn");
  const inputEl = document.getElementById("waInputText");

  sendBtn.addEventListener("click", () => handleSendUserMessage());
  inputEl.addEventListener("keypress", (e) => {
    if (e.key === "Enter") handleSendUserMessage();
  });

  // Action Tray Buttons
  document.querySelectorAll(".wa-chip").forEach(btn => {
    btn.addEventListener("click", () => {
      const msg = btn.getAttribute("data-msg");
      if (msg) sendToWhatsApp(msg);
    });
  });

  // Scenario Buttons on Sidebar
  document.querySelectorAll(".scenario-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const msg = btn.getAttribute("data-text");
      if (msg) sendToWhatsApp(msg);
    });
  });

  // 1-Click Valid Specimen (K12)
  document.getElementById("uploadValidSpecimenBtn").addEventListener("click", () => {
    uploadSpecimenFile("/specimen/K12_gst_certificate.png", "K12_gst_certificate.png");
  });

  // 1-Click Blurry Specimen (K04)
  document.getElementById("uploadBlurrySpecimenBtn").addEventListener("click", () => {
    uploadSpecimenFile("/specimen/K04_address_proof.png", "K04_address_proof.png");
  });

  // Real File Uploads
  document.getElementById("waDocFileInput").addEventListener("change", handleWaFileUpload);
  document.getElementById("waCameraInput").addEventListener("change", handleWaFileUpload);

  // Language Toggle
  document.getElementById("langToggleBtn").addEventListener("click", () => {
    WA_LANG = WA_LANG === 'en' ? 'hi' : 'en';
    document.getElementById("langToggleBtn").innerText = WA_LANG === 'hi' ? "Switch to English" : "Switch to हिंदी";
    sendToWhatsApp(WA_LANG === 'hi' ? "हिंदी" : "english");
  });

  // Reset Session
  document.getElementById("resetWaBtn").addEventListener("click", () => {
    sendToWhatsApp("reset");
  });
}

function getTimeString() {
  const now = new Date();
  return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatWaMarkdown(text) {
  if (!text) return "";
  let html = text
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/\*(.*?)\*/g, "<strong>$1</strong>")
    .replace(/_(.*?)_/g, "<em>$1</em>")
    .replace(/~(.*?)~/g, "<del>$1</del>")
    .replace(/`([^`]+)`/g, "<code class='bg-slate-100 text-slate-800 px-1 py-0.5 rounded text-[11px] font-mono'>$1</code>");
  return html;
}

function appendUserBubble(text) {
  const box = document.getElementById("waChatBox");
  const div = document.createElement("div");
  div.className = "flex justify-end";
  div.innerHTML = `
    <div class="wa-bubble-user p-2.5 text-xs text-slate-900 max-w-[85%] shadow-xs leading-relaxed whitespace-pre-line">
      ${formatWaMarkdown(text)}
      <div class="text-[9px] text-slate-500 text-right mt-1 font-mono flex items-center justify-end space-x-1">
        <span>${getTimeString()}</span>
        <span class="text-blue-500 font-bold">✓✓</span>
      </div>
    </div>
  `;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

function appendBotBubble(text, buttons = []) {
  const box = document.getElementById("waChatBox");
  const div = document.createElement("div");
  div.className = "flex justify-start flex-col space-y-1.5";

  let buttonsHtml = "";
  if (buttons && buttons.length > 0) {
    buttonsHtml = `
      <div class="mt-2 pt-2 border-t border-slate-100 flex flex-col space-y-1">
        ${buttons.map(b => `
          <button class="wa-action-btn w-full bg-slate-50 hover:bg-emerald-50 text-emerald-800 hover:text-emerald-900 border border-slate-200 hover:border-emerald-300 font-bold py-1.5 px-3 rounded-lg text-xs transition text-center shadow-xs" data-payload="${b.payload}">
            ${b.title}
          </button>
        `).join('')}
      </div>
    `;
  }

  div.innerHTML = `
    <div class="wa-bubble-bot p-2.5 text-xs text-slate-900 max-w-[88%] shadow-xs leading-relaxed whitespace-pre-line border border-slate-100">
      ${formatWaMarkdown(text)}
      ${buttonsHtml}
      <div class="text-[9px] text-slate-400 text-right mt-1 font-mono">${getTimeString()}</div>
    </div>
  `;
  box.appendChild(div);

  // Wire up button click handlers
  div.querySelectorAll(".wa-action-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const payload = btn.getAttribute("data-payload");
      if (payload) sendToWhatsApp(payload);
    });
  });

  box.scrollTop = box.scrollHeight;
}

function showTypingIndicator() {
  const box = document.getElementById("waChatBox");
  const div = document.createElement("div");
  div.id = "waTyping";
  div.className = "flex justify-start";
  div.innerHTML = `
    <div class="wa-bubble-bot px-3 py-1.5 text-xs text-slate-400 italic shadow-xs flex items-center space-x-1.5">
      <span class="w-1.5 h-1.5 rounded-full bg-slate-400 animate-pulse"></span>
      <span class="w-1.5 h-1.5 rounded-full bg-slate-400 animate-pulse"></span>
      <span class="w-1.5 h-1.5 rounded-full bg-slate-400 animate-pulse"></span>
      <span class="text-[10px] ml-1">Airtel is typing...</span>
    </div>
  `;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

function removeTypingIndicator() {
  const el = document.getElementById("waTyping");
  if (el) el.remove();
}

async function handleSendUserMessage() {
  const input = document.getElementById("waInputText");
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  await sendToWhatsApp(text);
}

async function sendToWhatsApp(text) {
  appendUserBubble(text);
  showTypingIndicator();

  try {
    const res = await fetch("/api/whatsapp/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        phone: WA_PHONE,
        message: text,
        language: WA_LANG
      })
    });
    const data = await res.json();
    removeTypingIndicator();

    if (data.responses && data.responses.length > 0) {
      data.responses.forEach((msg, idx) => {
        const btns = (idx === data.responses.length - 1) ? data.buttons : [];
        appendBotBubble(msg, btns);
      });
    }

    updateTrayButtons(data.buttons);
  } catch (err) {
    removeTypingIndicator();
    appendBotBubble("⚠️ Connection error. Please check your network and retry.");
  }
}

function updateTrayButtons(buttons) {
  const tray = document.getElementById("waActionTray");
  if (!buttons || buttons.length === 0) {
    tray.classList.add("hidden");
    return;
  }
  tray.classList.remove("hidden");
  tray.innerHTML = "";
  buttons.forEach(b => {
    const btn = document.createElement("button");
    btn.className = "wa-chip bg-slate-100 hover:bg-emerald-50 hover:text-emerald-800 text-slate-700 border border-slate-200 px-2.5 py-1 rounded-full text-[11px] font-semibold transition";
    btn.innerText = b.title;
    btn.addEventListener("click", () => sendToWhatsApp(b.payload));
    tray.appendChild(btn);
  });
}

// --- FILE UPLOADS ---
async function handleWaFileUpload(e) {
  const file = e.target.files[0];
  if (!file) return;
  await uploadFileBlob(file, file.name);
}

async function uploadSpecimenFile(url, fileName) {
  appendUserBubble(`📸 [Sending Photo]: ${fileName}`);
  showTypingIndicator();

  try {
    const blob = await fetch(url).then(r => r.blob());
    await uploadFileBlob(blob, fileName, false);
  } catch (err) {
    removeTypingIndicator();
    appendBotBubble("Could not load specimen document.");
  }
}

async function uploadFileBlob(blob, fileName, appendBubble = true) {
  if (appendBubble) {
    appendUserBubble(`📸 [Sending Photo]: ${fileName}`);
    showTypingIndicator();
  }

  const formData = new FormData();
  formData.append("file", blob, fileName);
  formData.append("phone", WA_PHONE);
  formData.append("language", WA_LANG);

  try {
    const res = await fetch("/api/whatsapp/simulate/upload", {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    removeTypingIndicator();

    if (data.responses && data.responses.length > 0) {
      data.responses.forEach((msg, idx) => {
        const btns = (idx === data.responses.length - 1) ? data.buttons : [];
        appendBotBubble(msg, btns);
      });
    }

    updateTrayButtons(data.buttons);
  } catch (err) {
    removeTypingIndicator();
    appendBotBubble("⚠️ Document upload failed. Please verify format.");
  }
}
