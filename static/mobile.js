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
  let response = await fetch(url, options);
  if (response.status === 401 && !url.includes("/api/auth/login")) {
    try {
      const loginRes = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pin: "2026" })
      });
      const loginData = await loginRes.json();
      if (loginData.success && loginData.token) {
        authToken = loginData.token;
        localStorage.setItem("transito_auth_token", authToken);
        options.headers["Authorization"] = `Bearer ${authToken}`;
        response = await fetch(url, options);
      }
    } catch (e) {
      console.warn("Mobile auto-auth retry mislukt:", e);
    }
  }
  return response;
}

function showMobileLockscreen() {
  // Vergrendeling uitgeschakeld op mobiel
}

function hideMobileLockscreen() {
  // Vergrendeling uitgeschakeld op mobiel
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
  const errEl = document.getElementById("mob-pin-error");
  if (enteredPin.length < 4) {
    if (errEl) errEl.textContent = "Voer alle 4 cijfers in";
    return;
  }

  if (errEl) errEl.textContent = "Controleren...";

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

  // Direct mobiele data laden zonder pincode
  refreshMobileData();
});

async function refreshMobileData() {
  const icon = document.getElementById("refresh-icon");
  if (icon) icon.classList.add("fa-spin");

  try {
    await Promise.all([loadCompanyInfo(), loadMobileClients(), loadMobileOrders(), loadMobileStats()]);
    showMobileToast("Gesynchroniseerd met kantoor", "success");
  } catch (err) {
    showMobileToast("Fout: " + err, "error");
  } finally {
    if (icon) setTimeout(() => icon.classList.remove("fa-spin"), 500);
  }
}

async function loadMobileStats() {
  try {
    const res = await authFetch("/api/stats");
    const stats = await res.json();
    
    const commEl = document.getElementById("mob-stat-commission");
    if (commEl) commEl.textContent = `€ ${(stats.total_earned_commissions || 0).toLocaleString("nl-NL", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    const sumEl = document.getElementById("mob-stat-orders-summary");
    if (sumEl) sumEl.innerHTML = `<i class="fa-solid fa-truck mr-1"></i> ${stats.total_orders || 0} bemiddelde ritten`;

    const unbilledEl = document.getElementById("mob-stat-unbilled");
    if (unbilledEl) unbilledEl.textContent = `€ ${(stats.unbilled_commissions || 0).toLocaleString("nl-NL", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} openstaand`;

    const activeEl = document.getElementById("mob-stat-active-orders");
    if (activeEl) activeEl.textContent = stats.active_orders || 0;

    const totalOrdersEl = document.getElementById("mob-stat-total-orders");
    if (totalOrdersEl) totalOrdersEl.textContent = stats.total_orders || 0;

    const invEl = document.getElementById("mob-stat-invoices");
    if (invEl) invEl.textContent = stats.total_commission_invoices || 0;

    const profitEl = document.getElementById("mob-stat-net-profit");
    if (profitEl) profitEl.textContent = `€ ${Math.round(stats.net_profit || 0).toLocaleString("nl-NL")}`;

    renderMobileRecentOrders();
  } catch (e) {
    console.error("Fout bij ophalen mobiele KPI stats:", e);
  }
}

function renderMobileRecentOrders() {
  const container = document.getElementById("mob-recent-orders-list");
  if (!container) return;

  const recents = (mobileOrders || []).slice(0, 3);
  if (recents.length === 0) {
    container.innerHTML = `<div class="text-xs text-slate-400 py-3 text-center">Nog geen opdrachten ingevoerd</div>`;
    return;
  }

  container.innerHTML = recents.map(o => {
    let statusBadge = "";
    if (o.status === "Offerte") statusBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-900 border border-amber-300">Offerte</span>`;
    else if (o.status === "Aangemeld") statusBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-700">Aangemeld</span>`;
    else if (o.status === "Onderweg") statusBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-50 text-amber-700">Onderweg</span>`;
    else if (o.status === "Geleverd") statusBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-blue-700">Geleverd</span>`;
    else if (o.status === "Gefactureerd" || o.status === "Commissie Gefactureerd") statusBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700">Gefactureerd</span>`;

    return `
      <div onclick="viewMobileQuote(${o.id})" class="p-3 rounded-xl bg-slate-50 hover:bg-slate-100 active:scale-[0.98] border border-slate-200/80 flex items-center justify-between text-xs cursor-pointer transition shadow-xs">
        <div class="truncate max-w-[190px]">
          <span class="font-bold text-slate-900 block truncate">${escapeHtml(o.client_name || 'Verlader')}</span>
          <span class="text-[11px] text-slate-500">${escapeHtml(o.origin_city || '?')} &rarr; ${escapeHtml(o.destination_city || '?')}</span>
        </div>
        <div class="text-right shrink-0 flex items-center gap-2">
          <div>
            <span class="font-bold text-slate-800 block text-xs">€ ${(o.freight_price || 0).toLocaleString("nl-NL", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
            ${statusBadge}
          </div>
          <i class="fa-solid fa-chevron-right text-slate-400 text-xs pointer-events-none"></i>
        </div>
      </div>
    `;
  }).join("");
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
  try {
    const res = await authFetch("/api/parties");
    const data = await res.json();
    mobileClients = Array.isArray(data) ? data : [];

    const clientSelect = document.getElementById("mob-client");
    if (clientSelect) {
      if (mobileClients.length === 0) {
        clientSelect.innerHTML = `<option value="">-- Geen verladers beschikbaar (maak eerst aan) --</option>`;
      } else {
        clientSelect.innerHTML = mobileClients.map(c => 
          `<option value="${c.id}">${escapeHtml(c.name)} (${c.country})</option>`
        ).join("");
      }
    }
  } catch (err) {
    console.error("Fout bij ophalen verladers:", err);
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
                        o.status === 'Offerte' ? 'bg-amber-100 text-amber-900 border border-amber-300' :
                        o.status === 'Onderweg' ? 'bg-amber-100 text-amber-800' :
                        o.status === 'Geleverd' ? 'bg-emerald-100 text-emerald-800' : 'bg-blue-100 text-blue-800';

    return `
      <div class="bg-white p-4 rounded-2xl shadow-sm border border-slate-200/90 space-y-3">
        <div class="flex items-center justify-between">
          <span class="font-mono font-bold text-xs text-slate-900">${o.order_number}</span>
          <span class="text-[10px] font-bold px-2 py-0.5 rounded-full ${statusColor}">${o.status}</span>
        </div>
        <div class="text-xs font-bold text-slate-800">${escapeHtml(o.client_name || 'Verlader')}</div>
        <div class="flex items-center gap-1.5 text-xs font-medium text-slate-700 bg-slate-50 p-2.5 rounded-xl">
          <span class="font-bold text-blue-600">${o.origin_country}</span> ${escapeHtml(o.origin_city)}
          <i class="fa-solid fa-arrow-right text-[10px] text-slate-400"></i>
          <span class="font-bold text-emerald-600">${o.destination_country}</span> ${escapeHtml(o.destination_city)}
        </div>
        <div class="flex items-center justify-between text-xs pt-1 border-t border-slate-100">
          <span class="text-slate-500 text-xs">Vrachtprijs:</span>
          <span class="font-bold text-slate-900 text-sm">€ ${(o.freight_price || 0).toLocaleString("nl-NL", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
        </div>
        <div class="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-100">
          <div class="flex items-center gap-1.5">
            <select onchange="updateMobileOrderStatus(${o.id}, this.value)" class="text-xs font-bold py-2 px-2.5 rounded-xl border border-slate-300 bg-slate-50 text-slate-800 focus:bg-white focus:outline-none cursor-pointer">
              <option value="Offerte" ${o.status === 'Offerte' ? 'selected' : ''}>📋 Offerte</option>
              <option value="Aangemeld" ${o.status === 'Aangemeld' ? 'selected' : ''}>Aangemeld</option>
              <option value="Onderweg" ${o.status === 'Onderweg' ? 'selected' : ''}>Onderweg</option>
              <option value="Geleverd" ${o.status === 'Geleverd' ? 'selected' : ''}>Geleverd</option>
              <option value="Commissie Gefactureerd" ${o.status === 'Commissie Gefactureerd' ? 'selected' : ''}>Gefactureerd</option>
            </select>
          </div>
          <div class="flex items-center gap-1.5">
            <button type="button" onclick="viewMobileQuote(${o.id})" class="px-3 py-2 rounded-xl bg-amber-50 hover:bg-amber-100 border border-amber-300 text-amber-900 text-xs font-bold flex items-center gap-1.5 shadow-sm active:scale-95 transition cursor-pointer">
              <i class="fa-solid fa-file-contract"></i> Offerte
            </button>
            <a href="/api/orders/${o.id}/pdf" download class="p-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold flex items-center justify-center active:scale-95 transition cursor-pointer" title="Download A4 PDF">
              <i class="fa-solid fa-file-pdf text-amber-600"></i>
            </a>
            ${o.status === 'Offerte' ? `
              <button type="button" onclick="quickEmailMobileQuote(${o.id})" title="Direct naar admeijs@gmail.com mailen" class="p-2.5 rounded-xl bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 text-indigo-700 text-xs font-bold flex items-center justify-center active:scale-95 transition cursor-pointer">
                <i class="fa-solid fa-paper-plane"></i>
              </button>
              <button type="button" onclick="acceptMobileQuoteDirect(${o.id})" class="px-3 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold flex items-center gap-1 shadow-sm active:scale-95 transition cursor-pointer">
                <i class="fa-solid fa-check"></i> Accepteer
              </button>
            ` : (!isBilled && o.status === 'Geleverd' ? `
              <button type="button" onclick="generateMobileCommissionInvoice(${o.id})" class="px-3 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold flex items-center gap-1 shadow-sm active:scale-95 transition cursor-pointer">
                <i class="fa-solid fa-file-invoice"></i> Factureer
              </button>
            ` : '')}
            <button type="button" onclick="deleteMobileOrder(${o.id})" class="text-slate-400 hover:text-rose-600 p-2.5 text-xs rounded-xl hover:bg-rose-50 active:scale-95 transition cursor-pointer" title="Verwijderen" ${isBilled ? 'style="display:none;"' : ''}>
              <i class="fa-solid fa-trash-can"></i>
            </button>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

async function updateMobileOrderStatus(orderId, newStatus) {
  try {
    const res = await authFetch(`/api/orders/${orderId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus })
    });
    const result = await res.json();
    if (result.success) {
      showMobileToast(`Status gewijzigd naar '${newStatus}'`, "success");
      await loadMobileOrders();
      await loadMobileStats();
    } else {
      showMobileToast("Fout: " + (result.error || "Kon status niet bijwerken"), "error");
    }
  } catch (err) {
    showMobileToast("Netwerkfout: " + err, "error");
  }
}

async function deleteMobileOrder(orderId) {
  const ord = (mobileOrders || []).find(o => o.id === orderId);
  const num = ord ? ord.order_number : `rit #${orderId}`;
  if (!confirm(`Weet je zeker dat je rit ${num} wilt verwijderen?`)) return;

  try {
    const res = await authFetch(`/api/orders/${orderId}`, {
      method: "DELETE"
    });
    const result = await res.json();
    if (result.success) {
      showMobileToast(result.message || `Rit ${num} verwijderd`, "success");
      await loadMobileOrders();
      await loadMobileStats();
    } else {
      showMobileToast("Fout: " + (result.error || "Kon rit niet verwijderen"), "error");
    }
  } catch (err) {
    showMobileToast("Netwerkfout: " + err, "error");
  }
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

let currentMobileQuoteOrder = null;

function submitMobileOrderAs(status) {
  // Verwijder eerdere foutmarkeringen
  ["mob-client", "mob-orig-city", "mob-dest-city", "mob-freight"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.remove("border-red-500", "ring-2", "ring-red-400");
  });

  const clientVal = document.getElementById("mob-client") ? document.getElementById("mob-client").value : "";
  const origCity = document.getElementById("mob-orig-city") ? document.getElementById("mob-orig-city").value.trim() : "";
  const destCity = document.getElementById("mob-dest-city") ? document.getElementById("mob-dest-city").value.trim() : "";
  const freight = parseFloat(document.getElementById("mob-freight")?.value) || 0;

  if (!clientVal) {
    const el = document.getElementById("mob-client");
    if (el) {
      el.classList.add("border-red-500", "ring-2", "ring-red-400");
      el.focus();
    }
    showMobileToast("Kies a.u.b. eerst een verlader of maak er een aan met '+ Nieuwe Verlader'", "error");
    return;
  }

  if (!origCity) {
    const el = document.getElementById("mob-orig-city");
    if (el) {
      el.classList.add("border-red-500", "ring-2", "ring-red-400");
      el.focus();
    }
    showMobileToast("Vul a.u.b. de laadplaats in (bijv. Tilburg)", "error");
    return;
  }

  if (!destCity) {
    const el = document.getElementById("mob-dest-city");
    if (el) {
      el.classList.add("border-red-500", "ring-2", "ring-red-400");
      el.focus();
    }
    showMobileToast("Vul a.u.b. de losplaats in (bijv. Verona)", "error");
    return;
  }

  if (freight <= 0) {
    const el = document.getElementById("mob-freight");
    if (el) {
      el.classList.add("border-red-500", "ring-2", "ring-red-400");
      el.focus();
    }
    showMobileToast("Vul a.u.b. het vrachttarief van de verlader in", "error");
    return;
  }

  submitMobileOrder(null, status);
}

async function submitMobileOrder(e, explicitStatus) {
  if (e && e.preventDefault) e.preventDefault();
  const targetStatus = explicitStatus || "Aangemeld";

  const btnOfferte = document.getElementById("mob-btn-submit-offerte");
  const btnOrder = document.getElementById("mob-btn-submit-order");
  const activeBtn = targetStatus === "Offerte" ? btnOfferte : btnOrder;

  if (btnOfferte) btnOfferte.disabled = true;
  if (btnOrder) btnOrder.disabled = true;
  if (activeBtn) {
    activeBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-xs pointer-events-none"></i> <span class="pointer-events-none">Verwerken...</span>`;
  }

  const freight = parseFloat(document.getElementById("mob-freight").value) || 0;
  const commType = currentMobileCommissionMode;
  const commRate = parseFloat(document.getElementById("mob-rate").value) || 10.0;
  const commAmount = parseFloat(document.getElementById("mob-comm-amount").value) || 0;
  const carrierPrice = parseFloat(document.getElementById("mob-carrier-price").value) || 0;

  const clientVal = document.getElementById("mob-client") ? document.getElementById("mob-client").value : "";
  const clientId = clientVal && !isNaN(parseInt(clientVal, 10)) ? parseInt(clientVal, 10) : null;

  const payload = {
    client_id: clientId,
    origin_country: (document.getElementById("mob-orig-country").value || "NL").toUpperCase(),
    origin_city: document.getElementById("mob-orig-city").value.trim(),
    destination_country: (document.getElementById("mob-dest-country").value || "IT").toUpperCase(),
    destination_city: document.getElementById("mob-dest-city").value.trim(),
    goods_description: document.getElementById("mob-goods").value.trim() || "Diverse handelsgoederen (FTL)",
    weight_kg: parseFloat(document.getElementById("mob-weight").value) || 0,
    cmr_number: document.getElementById("mob-cmr").value.trim(),
    freight_price: freight,
    carrier_price: carrierPrice,
    commission_type: commType,
    commission_rate: commRate,
    commission_amount: commAmount,
    pickup_date: document.getElementById("mob-pickup-date").value || new Date().toISOString().split("T")[0],
    status: targetStatus,
    auto_email_quote: true,
    send_email_copy: true
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
      const emailNote = result.email_sent ? " (Offerte A4 PDF verzonden naar admeijs@gmail.com)" : "";
      showMobileToast(targetStatus === 'Offerte' ? `Offerte ${result.order_number} aangemaakt!${emailNote}` : `Opdracht ${result.order_number} aangemeld!`, "success");
      
      document.getElementById("mobile-order-form").reset();
      document.getElementById("mob-orig-country").value = "NL";
      document.getElementById("mob-dest-country").value = "IT";
      document.getElementById("mob-goods").value = "Diverse handelsgoederen (FTL)";
      document.getElementById("mob-pickup-date").value = new Date().toISOString().split("T")[0];
      
      if (mobileCompany.default_commission_type) {
        setMobileCommissionMode(mobileCompany.default_commission_type);
      } else {
        setMobileCommissionMode("percentage");
      }
      calcMobileCommission();
      await loadMobileOrders();
      await loadMobileStats();

      if (targetStatus === 'Offerte' && result.id) {
        viewMobileQuote(result.id);
      } else {
        switchMobileView("view-orders-list");
      }
    } else {
      showMobileToast("Fout: " + (result.error || "Kon niet opslaan"), "error");
    }
  } catch (err) {
    showMobileToast("Netwerkfout: " + err, "error");
  } finally {
    if (btnOfferte) {
      btnOfferte.disabled = false;
      btnOfferte.innerHTML = '<i class="fa-solid fa-file-contract text-xs pointer-events-none"></i> <span class="pointer-events-none">Als Offerte</span>';
    }
    if (btnOrder) {
      btnOrder.disabled = false;
      btnOrder.innerHTML = '<i class="fa-solid fa-paper-plane text-xs pointer-events-none"></i> <span class="pointer-events-none">Rit Aanmelden</span>';
    }
  }
}

async function viewMobileQuote(orderId) {
  try {
    const res = await authFetch(`/api/orders/${orderId}`);
    if (!res.ok) throw new Error("Opdracht niet gevonden");
    const data = await res.json();
    currentMobileQuoteOrder = data.order;
    const o = data.order;

    const numPart = (o.order_number || "").split("-").pop() || "001";
    const quoteNum = `OFF-2026-${numPart}`;

    document.getElementById("mob-quote-title").textContent = `Offerte ${quoteNum}`;
    document.getElementById("mob-quote-subtitle").textContent = `Dossier: ${o.order_number}`;
    document.getElementById("mob-quote-status").textContent = o.status === 'Offerte' ? '📋 Offerte (Vrijblijvend)' : `🔵 ${o.status}`;
    document.getElementById("mob-quote-valid").textContent = "14 dagen geldig";

    const pdfBtn = document.getElementById("mob-btn-download-pdf");
    if (pdfBtn) {
      pdfBtn.href = `/api/orders/${o.id}/pdf`;
    }

    document.getElementById("mob-quote-client").textContent = o.client_name || "Verlader";
    document.getElementById("mob-quote-client-details").textContent = `${o.client_city || ''} (${o.client_country || ''}) • BTW: ${o.client_vat || '—'}`;

    document.getElementById("mob-quote-from").textContent = `${o.origin_country} - ${o.origin_city}`;
    document.getElementById("mob-quote-to").textContent = `${o.destination_country} - ${o.destination_city}`;
    document.getElementById("mob-quote-pickup").textContent = o.pickup_date || "Op afroep";

    document.getElementById("mob-quote-goods").textContent = o.goods_description || "Handelsgoederen";
    document.getElementById("mob-quote-weight").textContent = `${o.weight_kg ? o.weight_kg.toLocaleString("nl-NL") + ' kg' : 'Volle vracht (FTL)'}`;

    document.getElementById("mob-quote-price").textContent = `€ ${(o.freight_price || 0).toLocaleString("nl-NL", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    const acceptBtn = document.getElementById("mob-btn-accept-quote");
    if (acceptBtn) {
      if (o.status === 'Offerte') {
        acceptBtn.classList.remove("hidden");
      } else {
        acceptBtn.classList.add("hidden");
      }
    }

    document.getElementById("modal-mob-quote").classList.remove("hidden");
  } catch (err) {
    showMobileToast("Fout bij openen offerte: " + err, "error");
  }
}

function closeMobileQuoteModal() {
  document.getElementById("modal-mob-quote").classList.add("hidden");
}

async function acceptMobileQuoteDirect(orderId) {
  try {
    const res = await authFetch(`/api/orders/${orderId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: "Aangemeld" })
    });
    const result = await res.json();
    if (result.success) {
      if (navigator.vibrate) navigator.vibrate(50);
      showMobileToast("Offerte geaccepteerd! De rit is nu Aangemeld.", "success");
      await loadMobileOrders();
      await loadMobileStats();
    } else {
      showMobileToast("Fout: " + (result.error || "Kon niet bijwerken"), "error");
    }
  } catch (err) {
    showMobileToast("Netwerkfout: " + err, "error");
  }
}

async function acceptMobileQuote() {
  if (!currentMobileQuoteOrder) return;
  await acceptMobileQuoteDirect(currentMobileQuoteOrder.id);
  closeMobileQuoteModal();
}

async function shareMobileQuote() {
  if (!currentMobileQuoteOrder) return;
  const o = currentMobileQuoteOrder;
  const numPart = (o.order_number || "").split("-").pop() || "001";
  const quoteNum = `OFF-2026-${numPart}`;

  const shareText = `Vrachtofferte ${quoteNum} (${o.origin_country}-${o.origin_city} -> ${o.destination_country}-${o.destination_city}) voor € ${o.freight_price.toFixed(2)} excl. btw conform CMR. Transito Intermediazioni S.r.l.`;

  if (navigator.share) {
    try {
      await navigator.share({
        title: `Offerte ${quoteNum}`,
        text: shareText
      });
      return;
    } catch (e) {
      // Annulering of fout in navigator.share -> val terug
    }
  }

  // Fallback direct naar WhatsApp
  const waUrl = `https://api.whatsapp.com/send?text=${encodeURIComponent(shareText)}`;
  window.open(waUrl, "_blank");
}

async function quickEmailMobileQuote(orderId) {
  showMobileToast("Offerte A4 PDF wordt verzonden naar admeijs@gmail.com...", "success");
  try {
    const res = await authFetch(`/api/orders/${orderId}/send-email`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ to_email: "admeijs@gmail.com" })
    });
    const result = await res.json();
    if (result.success) {
      if (navigator.vibrate) navigator.vibrate([40, 60, 40]);
      showMobileToast("Offerte met A4 PDF succesvol verzonden naar admeijs@gmail.com!", "success");
    } else {
      showMobileToast("Fout: " + (result.error || "Kon niet verzenden"), "error");
    }
  } catch (err) {
    showMobileToast("Netwerkfout: " + err, "error");
  }
}

async function generateMobileCommissionInvoice(orderId) {
  try {
    showMobileToast("SDI commissiefactuur wordt aangemaakt...", "success");
    const res = await authFetch("/api/invoices/generate-commission", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ order_id: orderId })
    });
    const result = await res.json();
    if (result.success) {
      if (navigator.vibrate) navigator.vibrate([50, 100, 50]);
      showMobileToast(`Commissiefactuur ${result.invoice_number} succesvol aangemaakt!`, "success");
      await loadMobileOrders();
      await loadMobileStats();
    } else {
      showMobileToast("Fout: " + (result.error || "Kon factuur niet aanmaken"), "error");
    }
  } catch (err) {
    showMobileToast("Netwerkfout: " + err, "error");
  }
}

async function sendMobileQuoteToMyEmail() {
  if (!currentMobileQuoteOrder || !currentMobileQuoteOrder.id) {
    showMobileToast("Geen offerte geselecteerd", "error");
    return;
  }
  const btn = document.getElementById("mob-btn-email-quote");
  const origHtml = btn ? btn.innerHTML : "";
  if (btn) {
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>Verzenden...</span>';
    btn.disabled = true;
  }

  try {
    const res = await authFetch(`/api/orders/${currentMobileQuoteOrder.id}/send-email`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ to_email: "admeijs@gmail.com" })
    });
    const result = await res.json();
    if (result.success) {
      if (navigator.vibrate) navigator.vibrate([40, 60, 40]);
      showMobileToast("Offerte met A4 PDF succesvol verzonden naar admeijs@gmail.com!", "success");
    } else {
      showMobileToast("Fout: " + (result.error || "Kon niet verzenden"), "error");
    }
  } catch (err) {
    showMobileToast("Netwerkfout: " + err, "error");
  } finally {
    if (btn) {
      btn.innerHTML = origHtml;
      btn.disabled = false;
    }
  }
}

async function submitMobileClient(e) {
  e.preventDefault();
  const payload = {
    type: "client",
    name: document.getElementById("mob-new-name").value.trim(),
    country: (document.getElementById("mob-new-country").value || "IT").toUpperCase(),
    vat_number: document.getElementById("mob-new-vat").value.trim(),
    city: document.getElementById("mob-new-city").value.trim()
  };

  if (!payload.name) {
    showMobileToast("Vul a.u.b. een bedrijfsnaam in", "error");
    return;
  }

  try {
    const res = await authFetch("/api/parties", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await res.json();
    if (result.success) {
      if (navigator.vibrate) navigator.vibrate(50);
      showMobileToast(`Verlader '${payload.name}' opgeslagen!`, "success");
      await loadMobileClients();
      const clientSelect = document.getElementById("mob-client");
      if (clientSelect) clientSelect.value = result.id;
      document.getElementById("mob-new-name").value = "";
      document.getElementById("mob-new-vat").value = "";
      document.getElementById("mob-new-city").value = "";
      switchMobileView("view-new-order");
    } else {
      showMobileToast("Fout: " + (result.error || "Onbekende fout"), "error");
    }
  } catch (err) {
    showMobileToast("Netwerkfout: " + err, "error");
  }
}

function switchMobileView(viewId) {
  ["view-dashboard", "view-new-order", "view-orders-list", "view-new-client"].forEach(v => {
    const el = document.getElementById(v);
    if (el) el.classList.add("hidden");
  });

  const target = document.getElementById(viewId);
  if (target) target.classList.remove("hidden");

  const tabButtons = ["tab-btn-dashboard", "tab-btn-order", "tab-btn-list", "tab-btn-client"];
  tabButtons.forEach(btnId => {
    const btn = document.getElementById(btnId);
    if (btn) btn.classList.remove("active");
  });

  if (viewId === "view-dashboard" && document.getElementById("tab-btn-dashboard")) document.getElementById("tab-btn-dashboard").classList.add("active");
  if (viewId === "view-new-order" && document.getElementById("tab-btn-order")) document.getElementById("tab-btn-order").classList.add("active");
  if (viewId === "view-orders-list" && document.getElementById("tab-btn-list")) document.getElementById("tab-btn-list").classList.add("active");
  if (viewId === "view-new-client" && document.getElementById("tab-btn-client")) document.getElementById("tab-btn-client").classList.add("active");

  if (viewId === "view-orders-list") {
    loadMobileOrders();
  } else if (viewId === "view-dashboard") {
    loadMobileStats();
  } else if (viewId === "view-new-order") {
    loadMobileClients();
  }

  window.scrollTo({ top: 0, behavior: "smooth" });
}

function showMobileToast(msg, type = "success") {
  const toast = document.getElementById("mob-toast");
  const text = document.getElementById("mob-toast-text");
  const content = document.getElementById("mob-toast-content");

  text.textContent = msg;
  if (type === "error") {
    content.className = "bg-rose-950 text-white px-4 py-3 rounded-2xl shadow-2xl text-xs font-semibold flex items-center gap-2.5 border border-rose-700";
  } else {
    content.className = "bg-slate-900 text-white px-4 py-3 rounded-2xl shadow-2xl text-xs font-medium flex items-center gap-2.5 border border-slate-700";
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
