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

  // Scenario 7: Web Smart KYC Handoff
  const handoffBtn = document.getElementById("webKycHandoffBtn");
  if (handoffBtn) {
    handoffBtn.addEventListener("click", () => {
      sendToWhatsApp("proceed to kyc");
    });
  }

  // QR Modal Event Listeners
  initQrModal();

  // Voice Chat (Web Speech API)
  initWaVoiceRecognition();
}

// --- REAL PHONE QR MODAL ---
function initQrModal() {
  const openBtn = document.getElementById("openQrModalBtn");
  const closeBtn = document.getElementById("closeQrModalBtn");
  const modal = document.getElementById("waQrModal");
  const copyBtn = document.getElementById("copyWebhookBtn");

  if (openBtn && modal) {
    openBtn.addEventListener("click", () => {
      // Update QR Code target with current origin if tunnel is used
      const host = window.location.host;
      const codeEl = document.getElementById("webhookUrlCode");
      if (codeEl) codeEl.innerText = `${window.location.origin}/api/whatsapp/webhook`;
      modal.classList.remove("hidden");
    });
  }

  if (closeBtn && modal) {
    closeBtn.addEventListener("click", () => {
      modal.classList.add("hidden");
    });
  }

  if (modal) {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) modal.classList.add("hidden");
    });
  }

  if (copyBtn) {
    copyBtn.addEventListener("click", () => {
      const url = `${window.location.origin}/api/whatsapp/webhook`;
      navigator.clipboard.writeText(url).then(() => {
        copyBtn.innerText = "Copied! ✓";
        setTimeout(() => { copyBtn.innerText = "Copy URL"; }, 2000);
      });
    });
  }
}

// --- VOICE CHAT ENGINE (WEB SPEECH API) ---
let waRecognitionInstance = null;
let isWaRecording = false;

function initWaVoiceRecognition() {
  const micBtn = document.getElementById("waMicBtn");
  if (!micBtn) return;

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (!SpeechRecognition) {
    micBtn.addEventListener("click", () => {
      alert(WA_LANG === 'hi' 
        ? "वॉयस इनपुट के लिए Google Chrome या Microsoft Edge का उपयोग करें।" 
        : "Speech Recognition is supported in Google Chrome & Microsoft Edge. Please type your message.");
    });
    return;
  }

  try {
    waRecognitionInstance = new SpeechRecognition();
    waRecognitionInstance.continuous = false;
    waRecognitionInstance.interimResults = false;

    waRecognitionInstance.onstart = () => {
      isWaRecording = true;
      micBtn.className = "w-8 h-8 rounded-full bg-emerald-600 text-white flex items-center justify-center shrink-0 shadow animate-pulse";
      const input = document.getElementById("waInputText");
      if (input) input.placeholder = WA_LANG === 'hi' ? "सुन रहे हैं... बोलिए..." : "Listening... Speak now...";
    };

    waRecognitionInstance.onresult = (event) => {
      if (event.results && event.results.length > 0) {
        const transcript = event.results[0][0].transcript;
        const input = document.getElementById("waInputText");
        if (input) input.value = "";
        sendVoiceToWhatsApp(transcript);
      }
    };

    waRecognitionInstance.onerror = (event) => {
      console.warn("WhatsApp Speech Recognition Error:", event.error);
      stopWaVoiceRecording();
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        alert(WA_LANG === 'hi' 
          ? "माइक्रोफ़ोन की अनुमति ब्लॉक है। कृपया अपने ब्राउज़र में माइक्रोफ़ोन की अनुमति (Allow) दें।" 
          : "Microphone permission is blocked. Please allow microphone access in your browser settings.");
      } else if (event.error === "audio-capture") {
        alert(WA_LANG === 'hi' 
          ? "कोई माइक्रोफ़ोन नहीं मिला। कृपया अपना माइक्रोफ़ोन कनेक्ट करें।" 
          : "No microphone detected. Please connect a microphone to your device.");
      } else if (event.error === "network") {
        alert(WA_LANG === 'hi' 
          ? "वॉयस रिकॉग्निशन नेटवर्क त्रुटि। कृपया इंटरनेट कनेक्शन जांचें।" 
          : "Voice recognition network error. Please check your internet connection.");
      }
    };

    waRecognitionInstance.onend = () => {
      stopWaVoiceRecording();
    };

    micBtn.addEventListener("click", () => {
      if (isWaRecording) {
        waRecognitionInstance.stop();
        stopWaVoiceRecording();
      } else {
        waRecognitionInstance.lang = WA_LANG === 'hi' ? 'hi-IN' : 'en-IN';
        try {
          waRecognitionInstance.start();
        } catch (err) {
          console.warn("WA recognition start failed:", err);
        }
      }
    });
  } catch (err) {
    console.warn("WA Web Speech API initialization:", err);
  }
}

function stopWaVoiceRecording() {
  isWaRecording = false;
  const micBtn = document.getElementById("waMicBtn");
  if (micBtn) {
    micBtn.className = "w-8 h-8 rounded-full bg-slate-200 hover:bg-slate-300 text-slate-700 flex items-center justify-center shrink-0 shadow transition";
  }
  const input = document.getElementById("waInputText");
  if (input) input.placeholder = "Type a message...";
}

function appendUserVoiceBubble(transcript) {
  const box = document.getElementById("waChatBox");
  const div = document.createElement("div");
  div.className = "flex justify-end";
  div.innerHTML = `
    <div class="wa-bubble-user p-2.5 text-xs text-slate-900 max-w-[85%] shadow-xs leading-relaxed border border-emerald-200">
      <div class="flex items-center space-x-2.5 mb-1.5 bg-emerald-100/60 p-2 rounded-xl">
        <div class="w-7 h-7 rounded-full bg-emerald-600 text-white flex items-center justify-center text-xs shrink-0 shadow">▶</div>
        <div class="flex-1 space-y-1">
          <div class="h-1 bg-emerald-400 rounded-full w-full"></div>
          <div class="flex justify-between text-[9px] text-emerald-800 font-mono">
            <span>0:03</span>
            <span>🎤 Voice Note</span>
          </div>
        </div>
      </div>
      <p class="text-[11px] text-slate-700 italic">"${formatWaMarkdown(transcript)}"</p>
      <div class="text-[9px] text-slate-500 text-right mt-1 font-mono flex items-center justify-end space-x-1">
        <span>${getTimeString()}</span>
        <span class="text-blue-500 font-bold">✓✓</span>
      </div>
    </div>
  `;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

async function sendVoiceToWhatsApp(transcript) {
  appendUserVoiceBubble(transcript);
  showTypingIndicator();

  try {
    const res = await fetch("/api/whatsapp/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        phone: WA_PHONE,
        message: transcript,
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
