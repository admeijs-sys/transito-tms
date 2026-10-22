/**
 * Transito Mobile - Smartphone Script voor Intermediair / Opdracht Bemiddeling
 */

let mobileClients = [];
let mobileOrders = [];
let mobileCompany = {};
let currentMobileCommissionMode = "percentage"; // 'percentage', 'fixed', 'margin', 'custom'

// Authenticatie & Pincode beheer
let authToken = localStorage.getItem("transito_auth_token") || "";
let enteredPin = "";

async function authFetch(url, options = {}) {
  options.headers = options.headers || {};
  if (authToken) {
    options.headers["Authorization"] = `Bearer ${authToken}`;
  }
  const res = await fetch(url, options);
  if (res.status === 401) {
    authToken = "";
    localStorage.removeItem("transito_auth_token");
    showMobileLockscreen();
    throw new Error("Pincode vereist of sessie verlopen");
  }
  return res;
}

function showMobileLockscreen() {
  const ls = document.getElementById("mob-lockscreen");
  if (ls) ls.classList.remove("hidden");
  clearPin();
}

function hideMobileLockscreen() {
  const ls = document.getElementById("mob-lockscreen");
  if (ls) ls.classList.add("hidden");
}

function updatePinDots() {
  for (let i = 1; i <= 4; i++) {
    const dot = document.getElementById(`pin-dot-${i}`);
    if (dot) {
      if (enteredPin.length >= i) {
        dot.className = "w-4 h-4 rounded-full border-2 border-blue-400 bg-blue-500 shadow-sm shadow-blue-500/50 scale-110 transition-all";
      } else {
        dot.className = "w-4 h-4 rounded-full border-2 border-slate-600 bg-transparent transition-all";
      }
    }
  }
}

function pressPinDigit(digit) {
  if (enteredPin.length < 4) {
    enteredPin += digit;
    updatePinDots();
    const errEl = document.getElementById("mob-pin-error");
    if (errEl) errEl.textContent = "";
    if (enteredPin.length === 4) {
      setTimeout(() => submitMobilePin(), 120);
    }
  }
}

function clearPin() {
  enteredPin = "";
  updatePinDots();
  const errEl = document.getElementById("mob-pin-error");
  if (errEl) errEl.textContent = "";
}

async function submitMobilePin() {
  if (enteredPin.length < 4) {
    document.getElementById("mob-pin-error").textContent = "Voer alle 4 cijfers in";
    return;
  }

  const errEl = document.getElementById("mob-pin-error");
  errEl.textContent = "Controleren...";

  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pin: enteredPin })
    });
    const data = await res.json();
    if (data.success && data.token) {
      authToken = data.token;
      localStorage.setItem("transito_auth_token", authToken);
      hideMobileLockscreen();
      if (navigator.vibrate) navigator.vibrate(50);
      showMobileToast("Toegang ontgrendeld", "success");
      refreshMobileData();
    } else {
      if (navigator.vibrate) navigator.vibrate([100, 50, 100]);
      errEl.textContent = data.error || "Onjuiste pincode";
      clearPin();
    }
  } catch (e) {
    errEl.textContent = "Verbindingsfout: " + e;
    clearPin();
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  const today = new Date().toISOString().split("T")[0];
  const dateInput = document.getElementById("mob-pickup-date");
  if (dateInput) dateInput.value = today;

  // Luister naar toetsenbord / hardware invoer voor pincode
  window.addEventListener("keydown", (e) => {
    const ls = document.getElementById("mob-lockscreen");
    if (ls && !ls.classList.contains("hidden")) {
      if (e.key >= "0" && e.key <= "9") {
        pressPinDigit(e.key);
      } else if (e.key === "Backspace" || e.key === "Delete") {
        clearPin();
      } else if (e.key === "Enter") {
        submitMobilePin();
      }
    }
  });

  // Valideer token met de server
  if (!authToken) {
    showMobileLockscreen();
  } else {
    try {
      const res = await fetch("/api/auth/status", {
        headers: { "Authorization": `Bearer ${authToken}` }
      });
      const data = await res.json();
      if (!data.authenticated) {
        authToken = "";
        localStorage.removeItem("transito_auth_token");
        showMobileLockscreen();
        return;
      }
      refreshMobileData();
    } catch (e) {
      // Netwerkfout of server ontwaakt
      showMobileToast("Server ontwaakt...", "info");
      refreshMobileData();
    }
  }
});

async function refreshMobileData() {
  const icon = document.getElementById("refresh-icon");
  if (icon) icon.classList.add("fa-spin");

  try {
    await Promise.all([loadCompanyInfo(), loadMobileClients(), loadMobileOrders()]);
    showMobileToast("Gesynchroniseerd met kantoor", "success");
  } catch (err) {
    showMobileToast("Fout: " + err, "error");
  } finally {
    if (icon) setTimeout(() => icon.classList.remove("fa-spin"), 500);
  }
}

async function loadCompanyInfo() {
  const res = await authFetch("/api/company");
  mobileCompany = await res.json();
  const el = document.getElementById("mob-header-principal");
  if (el) {
    el.textContent = `Agent namens ${mobileCompany.principal_name || 'Vervoerder'}`;
  }
  
  if (mobileCompany.default_commission_type) {
    setMobileCommissionMode(mobileCompany.default_commission_type);
  } else {
    setMobileCommissionMode("percentage");
  }

  if (document.getElementById("mob-rate") && mobileCompany.default_commission_rate) {
    document.getElementById("mob-rate").value = mobileCompany.default_commission_rate;
  }
  if (document.getElementById("mob-fixed-fee") && mobileCompany.default_commission_fixed) {
    document.getElementById("mob-fixed-fee").value = mobileCompany.default_commission_fixed;
  }
  calcMobileCommission();
}

async function loadMobileClients() {
  const res = await authFetch("/api/parties");
  mobileClients = await res.json();

  const clientSelect = document.getElementById("mob-client");
  if (clientSelect) {
    clientSelect.innerHTML = mobileClients.map(c => 
      `<option value="${c.id}">${escapeHtml(c.name)} (${c.country})</option>`
    ).join("");
  }
}

async function loadMobileOrders() {
  const res = await authFetch("/api/orders");
  mobileOrders = await res.json();
  
  const countBadge = document.getElementById("mob-orders-count");
  if (countBadge) countBadge.textContent = mobileOrders.length;

  const container = document.getElementById("mob-orders-container");
  if (!container) return;

  if (mobileOrders.length === 0) {
    container.innerHTML = `<div class="bg-white p-6 rounded-2xl text-center text-slate-400 text-xs border border-slate-200">Nog geen bemiddelde opdrachten. Voer je eerste rit in via het tabblad 'Nieuwe Rit'.</div>`;
    return;
  }

  container.innerHTML = mobileOrders.map(o => {
    const isBilled = o.status === "Commissie Gefactureerd";
    const statusColor = isBilled ? 'bg-purple-100 text-purple-800' :
                        o.status === 'Onderweg' ? 'bg-amber-100 text-amber-800' :
                        o.status === 'Geleverd' ? 'bg-emerald-100 text-emerald-800' : 'bg-blue-100 text-blue-800';

    const commType = o.commission_type || 'percentage';
    let commTag = `${o.commission_rate}% fee`;
    if (commType === 'fixed') commTag = 'Vaste fee';
    else if (commType === 'margin') commTag = `Marge (${o.commission_rate}%)`;
    else if (commType === 'custom') commTag = `Vrij (${o.commission_rate}%)`;

    return `
      <div class="bg-white p-3.5 rounded-2xl shadow-sm border border-slate-200/90 space-y-2">
        <div class="flex items-center justify-between">
          <span class="font-mono font-bold text-xs text-slate-900">${o.order_number}</span>
          <span class="text-[10px] font-bold px-2 py-0.5 rounded-full ${statusColor}">${o.status}</span>
        </div>
        <div class="text-xs font-bold text-slate-800">${escapeHtml(o.client_name || 'Verlader')}</div>
        <div class="flex items-center gap-1.5 text-xs font-medium text-slate-700 bg-slate-50 p-2 rounded-lg">
          <span class="font-bold text-blue-600">${o.origin_country}</span> ${escapeHtml(o.origin_city)}
          <i class="fa-solid fa-arrow-right text-[10px] text-slate-400"></i>
          <span class="font-bold text-emerald-600">${o.destination_country}</span> ${escapeHtml(o.destination_city)}
        </div>
        <div class="flex items-center justify-between text-xs pt-1 border-t border-slate-100">
          <span class="text-slate-500 text-[11px]">Vracht: € ${o.freight_price.toFixed(2)}</span>
          <div class="text-right">
            <span class="font-bold text-emerald-600 text-xs">+ € ${o.commission_amount.toFixed(2)} provisie</span>
            <span class="text-[10px] font-semibold text-slate-500 block">${commTag}</span>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

// ================= FLEXIBELE COMMISSIE MOBILE =================
function setMobileCommissionMode(mode) {
  currentMobileCommissionMode = mode;
  const inputType = document.getElementById("mob-comm-type");
  if (inputType) inputType.value = mode;

  const btnPct = document.getElementById("mob-btn-pct");
  const btnFixed = document.getElementById("mob-btn-fixed");
  const btnMargin = document.getElementById("mob-btn-margin");
  const btnCustom = document.getElementById("mob-btn-custom");

  const wrapPct = document.getElementById("mob-wrap-pct");
  const wrapFixed = document.getElementById("mob-wrap-fixed");
  const wrapMargin = document.getElementById("mob-wrap-margin");

  [btnPct, btnFixed, btnMargin, btnCustom].forEach(b => {
    if (b) b.className = "py-1.5 rounded-lg text-slate-600 hover:text-slate-900 text-center";
  });

  if (wrapPct) wrapPct.classList.add("hidden");
  if (wrapFixed) wrapFixed.classList.add("hidden");
  if (wrapMargin) wrapMargin.classList.add("hidden");

  if (mode === "percentage") {
    if (btnPct) btnPct.className = "py-1.5 rounded-lg bg-blue-600 text-white font-bold text-center shadow-sm";
    if (wrapPct) wrapPct.classList.remove("hidden");
  } else if (mode === "fixed") {
    if (btnFixed) btnFixed.className = "py-1.5 rounded-lg bg-purple-600 text-white font-bold text-center shadow-sm";
    if (wrapFixed) wrapFixed.classList.remove("hidden");
  } else if (mode === "margin") {
    if (btnMargin) btnMargin.className = "py-1.5 rounded-lg bg-amber-600 text-white font-bold text-center shadow-sm";
    if (wrapMargin) wrapMargin.classList.remove("hidden");
  } else if (mode === "custom") {
    if (btnCustom) btnCustom.className = "py-1.5 rounded-lg bg-emerald-600 text-white font-bold text-center shadow-sm";
    setTimeout(() => {
      const el = document.getElementById("mob-comm-amount");
      if (el) el.focus();
    }, 50);
  }

  calcMobileCommission();
}

function setMobileRate(pct) {
  document.getElementById("mob-rate").value = pct;
  calcMobileCommission();
}

function setMobileFixedFee(fee) {
  document.getElementById("mob-fixed-fee").value = fee;
  calcMobileCommission();
}

function calcMobileCommission() {
  const freight = parseFloat(document.getElementById("mob-freight").value) || 0;
  const mode = currentMobileCommissionMode;
  let comm = 0;
  let rate = 0;

  if (mode === "percentage") {
    rate = parseFloat(document.getElementById("mob-rate").value) || 10.0;
    comm = Math.round(freight * (rate / 100.0) * 100) / 100;
  } else if (mode === "fixed") {
    comm = parseFloat(document.getElementById("mob-fixed-fee").value) || 200.0;
    rate = freight > 0 ? Math.round((comm / freight) * 1000) / 10 : 0;
  } else if (mode === "margin") {
    const carrier = parseFloat(document.getElementById("mob-carrier-price").value) || 0;
    comm = Math.round(Math.max(0, freight - carrier) * 100) / 100;
    rate = freight > 0 ? Math.round((comm / freight) * 1000) / 10 : 0;
  } else if (mode === "custom") {
    comm = parseFloat(document.getElementById("mob-comm-amount").value) || 0;
    rate = freight > 0 ? Math.round((comm / freight) * 1000) / 10 : 0;
  }

  if (mode !== "custom") {
    const commInput = document.getElementById("mob-comm-amount");
    if (commInput) commInput.value = comm.toFixed(2);
  }

  const el = document.getElementById("mob-live-comm");
  if (el) {
    const tag = mode === "percentage" ? `${rate}%` :
                mode === "fixed" ? "Vast" :
                mode === "margin" ? `Marge ${rate}%` : "Vrij";
    el.textContent = `Provisie: € ${comm.toFixed(2)} (${tag})`;
  }

  const hint = document.getElementById("mob-effective-hint");
  if (hint) {
    hint.textContent = `${rate}% marge`;
  }
}

function onMobileDirectCommissionInput() {
  const freight = parseFloat(document.getElementById("mob-freight").value) || 0;
  const comm = parseFloat(document.getElementById("mob-comm-amount").value) || 0;
  const rate = freight > 0 ? Math.round((comm / freight) * 1000) / 10 : 0;

  const hint = document.getElementById("mob-effective-hint");
  if (hint) hint.textContent = `${rate}% marge`;

  const el = document.getElementById("mob-live-comm");
  if (el) el.textContent = `Provisie: € ${comm.toFixed(2)} (${rate}%)`;

  if (currentMobileCommissionMode === "percentage" && freight > 0) {
    document.getElementById("mob-rate").value = rate;
  } else if (currentMobileCommissionMode === "fixed") {
    document.getElementById("mob-fixed-fee").value = comm;
  }
}

async function submitMobileOrder(e) {
  e.preventDefault();
  const btn = document.getElementById("mob-submit-btn");
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Bezig met opslaan...`;

  const freight = parseFloat(document.getElementById("mob-freight").value) || 0;
  const commType = currentMobileCommissionMode;
  const commRate = parseFloat(document.getElementById("mob-rate").value) || 10.0;
  const commAmount = parseFloat(document.getElementById("mob-comm-amount").value) || 0;
  const carrierPrice = parseFloat(document.getElementById("mob-carrier-price").value) || 0;

  const payload = {
    client_id: parseInt(document.getElementById("mob-client").value),
    origin_country: document.getElementById("mob-orig-country").value.toUpperCase(),
    origin_city: document.getElementById("mob-orig-city").value,
    destination_country: document.getElementById("mob-dest-country").value.toUpperCase(),
    destination_city: document.getElementById("mob-dest-city").value,
    goods_description: document.getElementById("mob-goods").value,
    weight_kg: parseFloat(document.getElementById("mob-weight").value) || 0,
    cmr_number: document.getElementById("mob-cmr").value,
    freight_price: freight,
    carrier_price: carrierPrice,
    commission_type: commType,
    commission_rate: commRate,
    commission_amount: commAmount,
    pickup_date: document.getElementById("mob-pickup-date").value,
    status: "Aangemeld"
  };

  try {
    const res = await authFetch("/api/orders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await res.json();
    if (result.success) {
      if (navigator.vibrate) navigator.vibrate(80);
      showMobileToast(`Opdracht ${result.order_number} aangemeld! (Provisie: € ${commAmount.toFixed(2)})`, "success");
      document.getElementById("mobile-order-form").reset();
      document.getElementById("mob-pickup-date").value = new Date().toISOString().split("T")[0];
      if (mobileCompany.default_commission_type) {
        setMobileCommissionMode(mobileCompany.default_commission_type);
      } else {
        setMobileCommissionMode("percentage");
      }
      calcMobileCommission();
      await loadMobileOrders();
      switchMobileView("view-orders-list");
    } else {
      showMobileToast("Fout: " + result.error, "error");
    }
  } catch (err) {
    showMobileToast("Netwerkfout: " + err, "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-solid fa-paper-plane text-xs"></i> <span>Opdracht Aanmelden voor Vervoerder</span>`;
  }
}

async function submitMobileClient(e) {
  e.preventDefault();
  const payload = {
    type: "client",
    name: document.getElementById("mob-new-name").value,
    country: document.getElementById("mob-new-country").value.toUpperCase(),
    vat_number: document.getElementById("mob-new-vat").value,
    city: document.getElementById("mob-new-city").value
  };

  try {
    const res = await authFetch("/api/parties", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await res.json();
    if (result.success) {
      showMobileToast(`Verlader '${payload.name}' opgeslagen!`, "success");
      await loadMobileClients();
      document.getElementById("mob-client").value = result.id;
      switchMobileView("view-new-order");
    } else {
      showMobileToast("Fout: " + (result.error || "Onbekende fout"), "error");
    }
  } catch (err) {
    showMobileToast("Netwerkfout: " + err, "error");
  }
}

function switchMobileView(viewId) {
  ["view-new-order", "view-orders-list", "view-new-client"].forEach(v => {
    const el = document.getElementById(v);
    if (el) el.classList.add("hidden");
  });

  const target = document.getElementById(viewId);
  if (target) target.classList.remove("hidden");

  document.getElementById("tab-btn-order").classList.remove("active");
  document.getElementById("tab-btn-list").classList.remove("active");
  document.getElementById("tab-btn-client").classList.remove("active");

  if (viewId === "view-new-order") document.getElementById("tab-btn-order").classList.add("active");
  if (viewId === "view-orders-list") document.getElementById("tab-btn-list").classList.add("active");
  if (viewId === "view-new-client") document.getElementById("tab-btn-client").classList.add("active");

  window.scrollTo({ top: 0, behavior: "smooth" });
}

function showMobileToast(msg, type = "success") {
  const toast = document.getElementById("mob-toast");
  const text = document.getElementById("mob-toast-text");
  const content = document.getElementById("mob-toast-content");

  text.textContent = msg;
  if (type === "error") {
    content.className = "bg-red-900 text-white px-4 py-3 rounded-xl shadow-2xl text-xs font-medium flex items-center gap-2.5 border border-red-700";
  } else {
    content.className = "bg-slate-900 text-white px-4 py-3 rounded-xl shadow-2xl text-xs font-medium flex items-center gap-2.5 border border-slate-700";
  }

  toast.classList.remove("-translate-y-24", "opacity-0");
  toast.classList.add("translate-y-0", "opacity-100");

  setTimeout(() => {
    toast.classList.add("-translate-y-24", "opacity-0");
    toast.classList.remove("translate-y-0", "opacity-100");
  }, 3500);
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
