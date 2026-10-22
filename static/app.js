/**
 * Transito Intermediair & SDI Facturatie - Client Application Logic
 * Aangepast voor Intermediair / Makelaarsmodel optredend namens een vast Transportbedrijf.
 */

const API_BASE = "/api";

// Authenticatie & Pincode beheer
let authToken = localStorage.getItem("transito_auth_token") || "";

const originalFetch = window.fetch;
window.fetch = async function(url, options = {}) {
  if (typeof url === "string" && url.includes("/api/") && !url.includes("/api/auth/login") && !url.includes("/api/network-info")) {
    options = options || {};
    options.headers = options.headers || {};
    if (authToken) {
      if (options.headers instanceof Headers) {
        options.headers.set("Authorization", `Bearer ${authToken}`);
      } else {
        options.headers["Authorization"] = `Bearer ${authToken}`;
      }
    }
  }
  let response = await originalFetch(url, options);
  if (response.status === 401 && typeof url === "string" && url.includes("/api/") && !url.includes("/api/auth/login")) {
    // Probeer automatisch te her-authenticeren met default pincode 2026
    try {
      const loginRes = await originalFetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pin: "2026" })
      });
      const loginData = await loginRes.json();
      if (loginData.success && loginData.token) {
        authToken = loginData.token;
        localStorage.setItem("transito_auth_token", authToken);
        if (options.headers instanceof Headers) {
          options.headers.set("Authorization", `Bearer ${authToken}`);
        } else {
          options.headers["Authorization"] = `Bearer ${authToken}`;
        }
        response = await originalFetch(url, options);
      }
    } catch (e) {
      console.warn("Auto-auth retry mislukt:", e);
    }
  }
  return response;
};

function showDesktopLockscreen() {}
function hideDesktopLockscreen() {}
function lockApp() {}

async function submitDesktopPin(e) {
  if (e) e.preventDefault();
  const input = document.getElementById("desktop-pin-input");
  if (!input) return;
  const errEl = document.getElementById("desktop-pin-error");
  const btn = document.getElementById("btn-desktop-login");
  const pin = input.value.trim();

  if (!pin) return;
  if (errEl) errEl.textContent = "";
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Controleren...`;
  }

  try {
    const res = await originalFetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pin: pin })
    });
    const data = await res.json();
    if (data.success && data.token) {
      authToken = data.token;
      localStorage.setItem("transito_auth_token", authToken);
      hideDesktopLockscreen();
      showToast("Welkom terug! Toegang ontgrendeld.", "success");
      initApp();
    } else {
      errEl.textContent = data.error || "Onjuiste pincode. Probeer opnieuw.";
      input.select();
    }
  } catch (err) {
    errEl.textContent = "Verbindingsfout: " + err;
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-solid fa-key text-xs"></i> <span>Dashboard Ontgrendelen</span>`;
  }
}

async function changeAppPin(e) {
  e.preventDefault();
  const curr = document.getElementById("pin-current").value.trim();
  const newPin = document.getElementById("pin-new").value.trim();
  const conf = document.getElementById("pin-confirm").value.trim();
  const msgEl = document.getElementById("pin-change-msg");

  if (newPin !== conf) {
    msgEl.className = "text-xs font-semibold text-rose-600";
    msgEl.textContent = "Nieuwe pincodes komen niet overeen!";
    return;
  }

  if (newPin.length < 4) {
    msgEl.className = "text-xs font-semibold text-rose-600";
    msgEl.textContent = "Minimaal 4 cijfers/tekens vereist.";
    return;
  }

  try {
    const res = await fetch("/api/auth/change-pin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_pin: curr, new_pin: newPin })
    });
    const data = await res.json();
    if (data.success) {
      msgEl.className = "text-xs font-semibold text-emerald-600";
      msgEl.textContent = "Pincode succesvol gewijzigd!";
      document.getElementById("pin-current").value = "";
      document.getElementById("pin-new").value = "";
      document.getElementById("pin-confirm").value = "";
      showToast("Pincode succesvol gewijzigd!", "success");
    } else {
      msgEl.className = "text-xs font-semibold text-rose-600";
      msgEl.textContent = data.error || "Fout bij wijzigen pincode";
    }
  } catch (err) {
    msgEl.className = "text-xs font-semibold text-rose-600";
    msgEl.textContent = "Netwerkfout: " + err;
  }
}

// Global state
let currentTab = "dashboard";
let globalOrders = [];
let globalInvoices = [];
let globalParties = [];
let currentCompany = {};
let currentViewingXml = "";
let chartVolume = null;
let chartClients = null;

document.addEventListener("DOMContentLoaded", () => {
  initSidebar();
  if (!authToken) {
    showDesktopLockscreen();
  } else {
    initApp();
  }
});

function toggleSidebar() {
  const sidebar = document.getElementById("app-sidebar");
  const icon = document.getElementById("sidebar-toggle-icon");
  const backdrop = document.getElementById("sidebar-backdrop");
  if (!sidebar) return;

  const isMobile = window.innerWidth <= 768;

  if (isMobile) {
    sidebar.classList.toggle("mobile-open");
    if (backdrop) {
      if (sidebar.classList.contains("mobile-open")) {
        backdrop.classList.remove("hidden");
      } else {
        backdrop.classList.add("hidden");
      }
    }
  } else {
    sidebar.classList.toggle("sidebar-collapsed");
    const isCollapsed = sidebar.classList.contains("sidebar-collapsed");
    if (icon) {
      icon.className = isCollapsed ? "fa-solid fa-angles-right text-xs" : "fa-solid fa-angles-left text-xs";
    }
    localStorage.setItem("transito_sidebar_collapsed", isCollapsed ? "1" : "0");
  }
}

function closeMobileSidebar() {
  const sidebar = document.getElementById("app-sidebar");
  const backdrop = document.getElementById("sidebar-backdrop");
  if (sidebar) sidebar.classList.remove("mobile-open");
  if (backdrop) backdrop.classList.add("hidden");
}

function initSidebar() {
  const sidebar = document.getElementById("app-sidebar");
  const icon = document.getElementById("sidebar-toggle-icon");
  const saved = localStorage.getItem("transito_sidebar_collapsed");
  if (saved === "1" && window.innerWidth > 768 && sidebar) {
    sidebar.classList.add("sidebar-collapsed");
    if (icon) icon.className = "fa-solid fa-angles-right text-xs";
  }
}

async function initApp() {
  await loadCompany();
  await loadStats();
  await loadOrders();
  await loadInvoices();
  await loadParties();
}

// Tab Switching
function switchTab(tab) {
  if (window.innerWidth <= 768) {
    closeMobileSidebar();
  }
  currentTab = tab;
  
  const sections = ["dashboard", "orders", "invoices", "accounting", "parties", "principal", "settings"];
  sections.forEach(s => {
    const el = document.getElementById(`tab-${s}`);
    const nav = document.getElementById(`nav-${s}`);
    if (el) el.classList.add("hidden");
    if (nav) nav.classList.remove("active");
  });

  const targetEl = document.getElementById(`tab-${tab}`);
  const targetNav = document.getElementById(`nav-${tab}`);
  if (targetEl) targetEl.classList.remove("hidden");
  if (targetNav) targetNav.classList.add("active");

  const titles = {
    dashboard: "Dashboard - Overzicht Bemiddelingen",
    orders: "Bemiddelde Vrachten & Opdrachten",
    invoices: "SDI Commissiefacturen aan Vervoerder",
    accounting: "Italiaanse Boekhouding (*Contabilità e Fisco*)",
    parties: "Verladers (Klanten)",
    principal: "Partner Transportbedrijf (De Principal)",
    settings: "Eigen Bedrijf & SDI Instellingen"
  };
  document.getElementById("page-title").textContent = titles[tab] || "Transito Intermediair";

  if (tab === "dashboard") {
    loadStats();
    loadOrders();
  }
  if (tab === "orders") loadOrders();
  if (tab === "invoices") loadInvoices();
  if (tab === "accounting") loadAccountingData();
  if (tab === "parties") loadParties();
}

// 1. STATS & DASHBOARD
async function loadStats() {
  try {
    const res = await fetch(`${API_BASE}/stats`);
    const data = await res.json();

    document.getElementById("stat-commission").textContent = formatCurrency(data.total_earned_commissions);
    document.getElementById("stat-volume").textContent = formatCurrency(data.total_freight_volume);
    document.getElementById("stat-unbilled").textContent = formatCurrency(data.unbilled_commissions);
    document.getElementById("stat-sdi-invoices").textContent = `${data.total_commission_invoices} verstuurd`;
    document.getElementById("badge-active-orders").textContent = data.active_orders;

    if (document.getElementById("banner-principal-name")) {
      document.getElementById("banner-principal-name").textContent = data.principal_name;
    }

    // Fill Principal Card in Dashboard
    if (document.getElementById("dash-prin-name")) {
      document.getElementById("dash-prin-name").textContent = data.principal_name;
      document.getElementById("dash-prin-country").textContent = `${currentCompany.principal_country || 'NL'} (Art. 7-ter / Btw-verlegd)`;
      document.getElementById("dash-prin-vat").textContent = currentCompany.principal_vat || 'NL854729381B01';
      document.getElementById("dash-prin-rate").textContent = `${data.default_commission_rate}% per rit`;
      document.getElementById("dash-prin-unbilled").textContent = formatCurrency(data.unbilled_commissions);
    }
  } catch (err) {
    console.error("Fout bij ophalen statistieken:", err);
  }
}

// 2. COMPANY & PRINCIPAL SETTINGS
async function loadCompany() {
  try {
    const res = await fetch(`${API_BASE}/company`);
    currentCompany = await res.json();

    // Fill Sidebar
    document.getElementById("sidebar-company-name").textContent = currentCompany.name || "Transito Intermediazioni S.r.l.";
    document.getElementById("sidebar-vat-number").textContent = `P.IVA: ${currentCompany.vat_number || 'IT09876543210'}`;
    document.getElementById("sidebar-principal-name").textContent = currentCompany.principal_name || "Veldhoven Transport B.V.";

    // Fill Principal Form
    if (document.getElementById("prin-name")) {
      document.getElementById("prin-name").value = currentCompany.principal_name || "";
      document.getElementById("prin-country").value = currentCompany.principal_country || "NL";
      document.getElementById("prin-vat").value = currentCompany.principal_vat || "";
      document.getElementById("prin-address").value = currentCompany.principal_address || "";
      document.getElementById("prin-city").value = `${currentCompany.principal_city || ''} ${currentCompany.principal_zip || ''}`.trim();
      document.getElementById("prin-comm-type").value = currentCompany.default_commission_type || "percentage";
      document.getElementById("prin-comm-rate").value = currentCompany.default_commission_rate || 10.0;
    }

    // Fill Company Settings Form
    if (document.getElementById("set-name")) {
      document.getElementById("set-name").value = currentCompany.name || "";
      document.getElementById("set-legal-form").value = currentCompany.legal_form || "S.r.l.";
      document.getElementById("set-vat").value = currentCompany.vat_number || "";
      document.getElementById("set-cf").value = currentCompany.fiscal_code || "";
      document.getElementById("set-address").value = currentCompany.address || "";
      document.getElementById("set-zip").value = currentCompany.zip || "";
      document.getElementById("set-city").value = currentCompany.city || "";
      document.getElementById("set-province").value = currentCompany.province || "";
      document.getElementById("set-pec").value = currentCompany.pec || "";
      document.getElementById("set-sdi").value = currentCompany.sdi_code || "";
      document.getElementById("set-iban").value = currentCompany.iban || "";
      document.getElementById("set-sdi-provider").value = currentCompany.sdi_provider || "Aruba / Fatture in Cloud API Gateway";
    }

    // Fill SMTP Form
    if (document.getElementById("set-smtp-host")) {
      document.getElementById("set-smtp-host").value = currentCompany.smtp_host || "smtp.gmail.com";
      document.getElementById("set-smtp-port").value = currentCompany.smtp_port || 587;
      document.getElementById("set-smtp-security").value = currentCompany.smtp_security || "tls";
      document.getElementById("set-smtp-user").value = currentCompany.smtp_user || "";
      document.getElementById("set-smtp-pass").value = currentCompany.smtp_pass || "";
      document.getElementById("set-smtp-sender-name").value = currentCompany.smtp_sender_name || "Transito Intermediazioni S.r.l.";
      document.getElementById("set-smtp-sender-email").value = currentCompany.smtp_sender_email || "";
      document.getElementById("set-principal-email").value = currentCompany.principal_email || "administratie@veldhoventransport.nl";
      document.getElementById("set-accountant-email").value = currentCompany.accountant_email || "studio.rossi@commercialisti.it";
    }

    // Set default commission rate in order modal
    if (document.getElementById("ord-comm-rate")) {
      document.getElementById("ord-comm-rate").value = currentCompany.default_commission_rate || 10.0;
    }
  } catch (err) {
    console.error("Fout bij ophalen instellingen:", err);
  }
}

async function saveCompanySettings(e) {
  e.preventDefault();
  const payload = {
    ...currentCompany,
    name: document.getElementById("set-name").value,
    legal_form: document.getElementById("set-legal-form").value,
    vat_number: document.getElementById("set-vat").value,
    fiscal_code: document.getElementById("set-cf").value,
    address: document.getElementById("set-address").value,
    zip: document.getElementById("set-zip").value,
    city: document.getElementById("set-city").value,
    province: document.getElementById("set-province").value,
    pec: document.getElementById("set-pec").value,
    sdi_code: document.getElementById("set-sdi").value,
    iban: document.getElementById("set-iban").value,
    sdi_provider: document.getElementById("set-sdi-provider").value
  };

  try {
    const res = await fetch(`${API_BASE}/company`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await res.json();
    if (result.success) {
      showToast("Bedrijfs- en SDI-instellingen opgeslagen!", "success");
      loadCompany();
    } else {
      showToast("Fout bij opslaan: " + (result.error || "Onbekende fout"), "error");
    }
  } catch (err) {
    showToast("Fout: " + err, "error");
  }
}

async function savePrincipalSettings(e) {
  e.preventDefault();
  const payload = {
    ...currentCompany,
    principal_name: document.getElementById("prin-name").value,
    principal_country: document.getElementById("prin-country").value.toUpperCase(),
    principal_vat: document.getElementById("prin-vat").value,
    principal_address: document.getElementById("prin-address").value,
    principal_city: document.getElementById("prin-city").value,
    default_commission_type: document.getElementById("prin-comm-type").value,
    default_commission_rate: parseFloat(document.getElementById("prin-comm-rate").value) || 10.0
  };

  try {
    const res = await fetch(`${API_BASE}/company`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await res.json();
    if (result.success) {
      showToast("Gegevens van het Partner Transportbedrijf succesvol opgeslagen!", "success");
      loadCompany();
      loadStats();
    } else {
      showToast("Fout bij opslaan: " + (result.error || "Onbekende fout"), "error");
    }
  } catch (err) {
    showToast("Fout bij opslaan: " + err, "error");
  }
}

// 3. ORDERS (BEMIDDELDE OPDRACHTEN)
async function loadOrders() {
  try {
    const res = await fetch(`${API_BASE}/orders`);
    globalOrders = await res.json();
    renderOrders(globalOrders);
    renderDashboardOrders(globalOrders.slice(0, 5));
    renderDashboardPipeline(globalOrders);
    renderCharts(globalOrders);
  } catch (err) {
    console.error("Fout bij ophalen van opdrachten:", err);
  }
}

function renderDashboardPipeline(orders) {
  const aangemeld = orders.filter(o => o.status === 'Aangemeld');
  const actief = orders.filter(o => o.status === 'Bevestigd door Vervoerder' || o.status === 'Onderweg');
  const teFactureren = orders.filter(o => o.status === 'Geleverd');
  const gefactureerd = orders.filter(o => o.status === 'Commissie Gefactureerd');

  const teFacturerenBedrag = teFactureren.reduce((a, o) => a + o.commission_amount, 0);
  const gefactureerdBedrag = gefactureerd.reduce((a, o) => a + o.commission_amount, 0);

  if (document.getElementById("pipe-aangemeld")) {
    document.getElementById("pipe-aangemeld").textContent = `${aangemeld.length} ritten`;
  }
  if (document.getElementById("pipe-actief")) {
    document.getElementById("pipe-actief").textContent = `${actief.length} ritten`;
  }
  if (document.getElementById("pipe-te-factureren")) {
    document.getElementById("pipe-te-factureren").textContent = `${teFactureren.length} ritten`;
    document.getElementById("pipe-te-factureren-bedrag").textContent = `${formatCurrency(teFacturerenBedrag)} provisie`;
  }
  if (document.getElementById("pipe-gefactureerd")) {
    document.getElementById("pipe-gefactureerd").textContent = `${gefactureerd.length} ritten`;
    document.getElementById("pipe-gefactureerd-bedrag").textContent = `${formatCurrency(gefactureerdBedrag)} gefactureerd`;
  }
}

function renderCharts(orders) {
  if (typeof Chart === "undefined" || orders.length === 0) return;

  // Chart 1: Volume vs Provisie per rit
  const ctxVol = document.getElementById("chart-volume-commission");
  if (ctxVol) {
    if (chartVolume) chartVolume.destroy();

    const labels = orders.map(o => o.order_number);
    const volumes = orders.map(o => o.freight_price);
    const commissions = orders.map(o => o.commission_amount);

    chartVolume = new Chart(ctxVol, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Bemiddeld Vrachtvolume (€)',
            data: volumes,
            backgroundColor: 'rgba(59, 130, 246, 0.75)',
            borderColor: '#2563eb',
            borderWidth: 1,
            borderRadius: 6
          },
          {
            label: 'Jouw Provisie (€)',
            data: commissions,
            backgroundColor: 'rgba(16, 185, 129, 0.85)',
            borderColor: '#059669',
            borderWidth: 1,
            borderRadius: 6
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'top', labels: { boxWidth: 12, font: { size: 11, family: 'sans-serif' } } },
          tooltip: {
            callbacks: {
              label: (context) => ` ${context.dataset.label}: € ${context.raw.toFixed(2)}`
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: (val) => '€ ' + val,
              font: { size: 10 }
            },
            grid: { color: '#f1f5f9' }
          },
          x: {
            ticks: { font: { size: 10 } },
            grid: { display: false }
          }
        }
      }
    });
  }

  // Chart 2: Top Verladers Vrachtaandeel (Donut)
  const ctxClients = document.getElementById("chart-clients-share");
  if (ctxClients) {
    if (chartClients) chartClients.destroy();

    const clientMap = {};
    orders.forEach(o => {
      const name = o.client_name || 'Overig';
      clientMap[name] = (clientMap[name] || 0) + o.freight_price;
    });

    const clientLabels = Object.keys(clientMap);
    const clientData = Object.values(clientMap);
    const colors = ['#2563eb', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4'];

    chartClients = new Chart(ctxClients, {
      type: 'doughnut',
      data: {
        labels: clientLabels,
        datasets: [{
          data: clientData,
          backgroundColor: colors.slice(0, clientLabels.length),
          borderWidth: 2,
          borderColor: '#ffffff',
          hoverOffset: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (context) => ` ${context.label}: € ${context.raw.toFixed(2)}`
            }
          }
        },
        cutout: '70%'
      }
    });

    // Custom Legend
    const legendEl = document.getElementById("chart-clients-legend");
    if (legendEl) {
      const totalVol = clientData.reduce((a, b) => a + b, 0) || 1;
      legendEl.innerHTML = clientLabels.map((lbl, idx) => {
        const val = clientData[idx];
        const pct = ((val / totalVol) * 100).toFixed(0);
        return `
          <div class="flex items-center justify-between py-0.5">
            <span class="flex items-center gap-1.5 truncate max-w-[150px]">
              <span class="w-2.5 h-2.5 rounded-full inline-block shrink-0" style="background-color: ${colors[idx]}"></span>
              <span class="truncate text-slate-700">${escapeHtml(lbl)}</span>
            </span>
            <span class="font-bold text-slate-900 font-mono text-[11px]">${pct}% (€ ${val.toFixed(0)})</span>
          </div>
        `;
      }).join("");
    }
  }
}

function renderOrders(orders) {
  const tbody = document.getElementById("orders-table-body");
  if (!tbody) return;

  if (orders.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-center py-8 text-slate-400">Nog geen bemiddelde opdrachten. Klik op "+ Nieuwe Bemiddeling" om te starten.</td></tr>`;
    return;
  }

  tbody.innerHTML = orders.map(o => {
    const isBilled = o.status === "Commissie Gefactureerd";
    return `
      <tr class="hover:bg-slate-50/70 transition-colors">
        <td class="py-3.5 px-4 font-mono font-semibold text-slate-900 text-xs">
          ${o.order_number}
          <div class="text-[10px] text-slate-400 font-normal">Namens: ${escapeHtml(currentCompany.principal_name || 'Vervoerder')}</div>
        </td>
        <td class="py-3.5 px-4">
          <div class="font-bold text-slate-900 text-xs">${escapeHtml(o.client_name || 'Onbekend')}</div>
          <div class="text-[11px] text-slate-400 font-mono">${o.client_country} &bull; SDI: ${o.client_sdi || '-'}</div>
        </td>
        <td class="py-3.5 px-4">
          <div class="flex items-center gap-1.5 text-xs font-medium text-slate-800">
            <span class="font-bold text-blue-600">${o.origin_country}</span> ${escapeHtml(o.origin_city)}
            <i class="fa-solid fa-arrow-right text-[10px] text-slate-400"></i>
            <span class="font-bold text-emerald-600">${o.destination_country}</span> ${escapeHtml(o.destination_city)}
          </div>
          <div class="text-[11px] text-slate-400">${o.pickup_date || '-'} &rarr; ${o.delivery_date || '-'}</div>
        </td>
        <td class="py-3.5 px-4">
          <div class="text-xs text-slate-800 font-medium">${escapeHtml(o.goods_description || '-')}</div>
          <div class="text-[11px] text-slate-400 font-mono">${o.weight_kg ? o.weight_kg + ' kg' : ''} ${o.cmr_number ? '&bull; CMR: ' + o.cmr_number : ''}</div>
        </td>
        <td class="py-3.5 px-4">
          <select onchange="updateOrderStatus(${o.id}, this.value)" class="text-xs font-semibold rounded-lg px-2.5 py-1.5 border border-slate-300 bg-white text-slate-800 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer">
            <option value="Aangemeld" ${o.status === 'Aangemeld' ? 'selected' : ''}>🔵 Aangemeld</option>
            <option value="Onderweg" ${o.status === 'Onderweg' ? 'selected' : ''}>🟠 Onderweg</option>
            <option value="Geleverd" ${o.status === 'Geleverd' ? 'selected' : ''}>🟢 Geleverd</option>
            <option value="Commissie Gefactureerd" ${o.status === 'Commissie Gefactureerd' ? 'selected' : ''}>🟣 Gefactureerd</option>
          </select>
        </td>
        <td class="py-3.5 px-4 text-right">
          <div class="font-bold text-slate-900 text-xs">${formatCurrency(o.freight_price)}</div>
          <div class="text-[10px] text-slate-400">Verlader betaalt</div>
        </td>
        <td class="py-3.5 px-4 text-right">
          <div class="font-bold text-emerald-600 text-xs">${formatCurrency(o.commission_amount)}</div>
          <div class="mt-0.5">${getCommissionBadge(o)}</div>
        </td>
        <td class="py-3.5 px-4 text-center">
          <div class="flex items-center justify-center gap-1.5">
            ${!isBilled ? `
              <button onclick="generateSingleCommissionInvoice(${o.id})" title="Genereer SDI Factuur voor deze commissie aan ${escapeHtml(currentCompany.principal_name)}" class="px-2.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors flex items-center justify-center gap-1">
                <i class="fa-solid fa-file-invoice"></i> Factureer
              </button>
            ` : `
              <span class="text-[11px] font-semibold text-purple-700 bg-purple-50 px-2 py-1 rounded border border-purple-200">
                <i class="fa-solid fa-check mr-1"></i> Gefactureerd
              </span>
            `}
            <button onclick="deleteOrder(${o.id})" title="Opdracht verwijderen" class="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition" ${isBilled ? 'disabled opacity-30 cursor-not-allowed' : ''}>
              <i class="fa-solid fa-trash-can text-xs"></i>
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join("");
}

function renderDashboardOrders(orders) {
  const tbody = document.getElementById("dashboard-recent-orders");
  if (!tbody) return;

  tbody.innerHTML = orders.map(o => {
    return `
      <tr class="hover:bg-slate-50/70">
        <td class="py-3 px-4 font-mono font-semibold text-xs text-slate-900">${o.order_number}</td>
        <td class="py-3 px-4 text-xs font-medium text-slate-800">${escapeHtml(o.client_name)}</td>
        <td class="py-3 px-4 text-xs">
          <span class="font-bold text-blue-600">${o.origin_country}</span> &rarr; <span class="font-bold text-emerald-600">${o.destination_country}</span> (${escapeHtml(o.destination_city)})
        </td>
        <td class="py-3 px-4">${getStatusBadge(o.status)}</td>
        <td class="py-3 px-4 text-right text-xs font-bold text-slate-900">${formatCurrency(o.freight_price)}</td>
        <td class="py-3 px-4 text-right text-xs">
          <div class="font-bold text-emerald-600">${formatCurrency(o.commission_amount)}</div>
          <div class="mt-0.5">${getCommissionBadge(o)}</div>
        </td>
        <td class="py-3 px-4 text-center text-xs">
          ${o.status === 'Commissie Gefactureerd' ? `
            <span class="text-purple-600 font-bold"><i class="fa-solid fa-circle-check"></i> Factuur gereed</span>
          ` : `
            <span class="text-amber-600 font-semibold"><i class="fa-solid fa-clock"></i> Te factureren</span>
          `}
        </td>
      </tr>
    `;
  }).join("");
}

function filterOrders() {
  const query = document.getElementById("order-search").value.toLowerCase();
  const filtered = globalOrders.filter(o => 
    o.order_number.toLowerCase().includes(query) ||
    (o.client_name && o.client_name.toLowerCase().includes(query)) ||
    (o.origin_city && o.origin_city.toLowerCase().includes(query)) ||
    (o.destination_city && o.destination_city.toLowerCase().includes(query)) ||
    (o.cmr_number && o.cmr_number.toLowerCase().includes(query))
  );
  renderOrders(filtered);
}

// 4. INVOICES (COMMISSIEFACTUREN AAN VERVOERDER)
async function loadInvoices() {
  try {
    const res = await fetch(`${API_BASE}/invoices`);
    globalInvoices = await res.json();
    renderInvoices(globalInvoices);
  } catch (err) {
    console.error("Fout bij ophalen commissiefacturen:", err);
  }
}

function renderInvoices(invoices) {
  const tbody = document.getElementById("invoices-table-body");
  if (!tbody) return;

  if (invoices.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-center py-8 text-slate-400">Nog geen commissiefacturen aangemaakt. Factureer een bemiddelde rit of klik op "Factureer Alle Openstaande Provisies".</td></tr>`;
    return;
  }

  tbody.innerHTML = invoices.map(i => {
    let sdiClass = "badge-sdi-consegnata";
    return `
      <tr class="hover:bg-slate-50/70">
        <td class="py-3.5 px-4 font-mono font-bold text-xs text-slate-900">
          ${i.invoice_number}
          ${i.email_sent_at ? `
            <div class="text-[10px] text-blue-600 font-sans font-normal flex items-center gap-1 mt-0.5" title="Verzonden op ${i.email_sent_at} naar ${escapeHtml(i.email_sent_to || '')}">
              <i class="fa-solid fa-envelope-circle-check text-[10px]"></i> Gemaild
            </div>
          ` : ''}
        </td>
        <td class="py-3.5 px-4">
          <div class="font-bold text-slate-900 text-xs">${escapeHtml(i.party_name)}</div>
          <div class="text-[11px] text-slate-400 font-mono">${i.party_country} &bull; ${i.party_vat}</div>
        </td>
        <td class="py-3.5 px-4 text-xs text-slate-600">${i.date}</td>
        <td class="py-3.5 px-4 text-right font-mono text-xs font-bold text-emerald-600">${formatCurrency(i.subtotal)}</td>
        <td class="py-3.5 px-4 text-center">
          <span class="px-2 py-0.5 rounded text-[11px] font-bold bg-blue-100 text-blue-800" title="${i.normative_ref}">${i.vat_nature} (Art. 7-ter / Btw-verlegd)</span>
        </td>
        <td class="py-3.5 px-4 text-right font-mono font-bold text-xs text-slate-900">${formatCurrency(i.total_amount)}</td>
        <td class="py-3.5 px-4 text-center">
          <span class="badge-status ${sdiClass}">
            <i class="fa-solid fa-circle text-[7px]"></i> ${i.sdi_status}
          </span>
        </td>
        <td class="py-3.5 px-4 text-center">
          <div class="flex items-center justify-center gap-1.5">
            <button onclick="viewInvoiceTemplate(${i.id})" title="Bekijk en print factuur sjabloon (PDF)" class="px-2 py-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded text-xs font-semibold shadow-sm transition-colors flex items-center gap-1 border border-indigo-200">
              <i class="fa-solid fa-file-invoice"></i> Sjabloon
            </button>
            <button onclick="openSendEmailModal(${i.id})" title="Verstuur factuur en XML per e-mail" class="px-2 py-1 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded text-xs font-semibold shadow-sm transition-colors flex items-center gap-1 border border-blue-200">
              <i class="fa-solid fa-envelope text-[10px]"></i> E-mail
            </button>
            <button onclick="viewInvoiceXml(${i.id})" title="Bekijk officiële FatturaPA XML" class="p-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded text-xs transition-colors">
              <i class="fa-solid fa-code"></i>
            </button>
            <a href="${API_BASE}/invoices/${i.id}/xml" download title="Download .XML bestand" class="p-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded text-xs transition-colors">
              <i class="fa-solid fa-download"></i>
            </a>
            ${!i.sdi_status.includes("Consegnata") ? `
              <button onclick="sendToSdi(${i.id})" title="Verzend digitaal naar SDI Gateway" class="px-2 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-xs font-semibold shadow-sm transition-colors flex items-center gap-1">
                <i class="fa-solid fa-paper-plane text-[10px]"></i> SDI
              </button>
            ` : `
              <span title="${escapeHtml(i.sdi_response_message || 'Geleverd')}" class="text-emerald-600 text-xs font-bold p-1">
                <i class="fa-solid fa-check-double"></i>
              </span>
            `}
            <button onclick="deleteInvoice(${i.id})" title="Factuur verwijderen en gekoppelde ritten herstellen" class="p-1.5 text-slate-400 hover:text-rose-600 rounded hover:bg-rose-50 transition">
              <i class="fa-solid fa-trash-can text-xs"></i>
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join("");
}

// 4B. ITALIAANSE BOEKHOUDING & FISCO (CONTABILITÀ ITALIANA)
let currentAccountingSubTab = "acc-conto";
let globalExpenses = [];
let globalChartOfAccounts = [];

function switchAccountingSubTab(subTab) {
  currentAccountingSubTab = subTab;
  ["acc-conto", "acc-lipe", "acc-acquisti", "acc-piano"].forEach(s => {
    const el = document.getElementById(`subtab-${s}`);
    const btn = document.getElementById(`subnav-${s}`);
    if (el) el.classList.add("hidden");
    if (btn) {
      btn.classList.remove("border-blue-600", "text-blue-600");
      btn.classList.add("border-transparent", "text-slate-500");
    }
  });

  const targetEl = document.getElementById(`subtab-${subTab}`);
  const targetBtn = document.getElementById(`subnav-${subTab}`);
  if (targetEl) targetEl.classList.remove("hidden");
  if (targetBtn) {
    targetBtn.classList.remove("border-transparent", "text-slate-500");
    targetBtn.classList.add("border-blue-600", "text-blue-600");
  }
}

async function loadAccountingData() {
  try {
    const res = await fetch(`${API_BASE}/accounting`);
    const data = await res.json();

    // 1. Conto Economico
    const ce = data.conto_economico || {};
    document.getElementById("ce-ricavi").textContent = formatCurrency(ce.ricavi_provvigioni || 0);
    document.getElementById("ce-costi-servizi").textContent = formatCurrency(ce.costi_servizi || 0);
    document.getElementById("ce-costi-godimento").textContent = formatCurrency(ce.costi_godimento || 0);
    document.getElementById("ce-oneri-diversi").textContent = formatCurrency(ce.oneri_diversi || 0);
    document.getElementById("ce-totale-costi").textContent = formatCurrency(ce.totale_costi_produzione || 0);
    document.getElementById("ce-ebitda").textContent = formatCurrency(ce.differenza_a_b || 0);
    document.getElementById("ce-ires").textContent = formatCurrency(ce.ires_24 || 0);
    document.getElementById("ce-irap").textContent = formatCurrency(ce.irap_3_9 || 0);
    document.getElementById("ce-utile-netto").textContent = formatCurrency(ce.utile_netto || 0);

    // 2. Stato Patrimoniale
    const sp = data.stato_patrimoniale || {};
    const att = sp.attivo_circolante || {};
    const pat = sp.patrimonio_netto || {};
    const deb = sp.debiti || {};

    document.getElementById("sp-banca").textContent = formatCurrency(att.disponibilita_liquide || 100000);
    document.getElementById("sp-crediti").textContent = formatCurrency(att.crediti_mandanti || 0);
    document.getElementById("sp-credito-iva").textContent = formatCurrency(att.crediti_iva || 0);
    document.getElementById("sp-capitale").textContent = formatCurrency(pat.capitale_sociale || 100000);
    document.getElementById("sp-utile").textContent = formatCurrency(pat.utile_esercizio || 0);
    document.getElementById("sp-debiti-fornitori").textContent = formatCurrency(deb.debiti_fornitori || 0);
    document.getElementById("sp-debiti-tributari").textContent = formatCurrency(deb.debiti_imposte_ires_irap || 0);

    // 3. Liquidazione IVA & F24
    const lipe = data.liquidazione_iva || {};
    document.getElementById("lipe-iva-debito").textContent = formatCurrency(lipe.iva_vendite_debito || 0);
    document.getElementById("lipe-iva-credito").textContent = formatCurrency(lipe.iva_acquisti_credito || 0);
    document.getElementById("lipe-saldo-bedrag").textContent = formatCurrency(Math.abs(lipe.saldo_iva || 0));
    document.getElementById("lipe-saldo-type").textContent = lipe.tipo_saldo || "Btw-tegoed (Te verrekenen / A credito)";
    document.getElementById("f24-tributo").textContent = lipe.saldo_iva > 0 ? "6031 (Btw 1e Kwartaal / IVA 1° Trim)" : "Geen af te dragen btw (Btw-krediet)";
    document.getElementById("f24-importo").textContent = formatCurrency(Math.max(0, lipe.saldo_iva || 0));

    // 4. Expenses (Registro IVA Acquisti)
    globalExpenses = data.expenses || [];
    renderExpenses(globalExpenses);

    // 5. Chart of Accounts
    loadChartOfAccounts();
  } catch (err) {
    console.error("Fout bij ophalen boekhouding:", err);
  }
}

function renderExpenses(expenses) {
  const tbody = document.getElementById("expenses-table-body");
  if (!tbody) return;

  if (expenses.length === 0) {
    tbody.innerHTML = `<tr><td colspan="10" class="text-center py-6 text-slate-400">Nog geen inkoopfacturen geregistreerd. Klik op "+ Nieuwe Kostenfactuur" om kosten in te voeren.</td></tr>`;
    return;
  }

  tbody.innerHTML = expenses.map(e => `
    <tr class="hover:bg-slate-50/70">
      <td class="py-3 px-4 font-mono text-slate-600">${e.date}</td>
      <td class="py-3 px-4">
        <div class="font-bold text-slate-900">${escapeHtml(e.supplier_name)}</div>
        <div class="text-[10px] text-slate-400 font-mono">${e.supplier_vat || '-'}</div>
      </td>
      <td class="py-3 px-4 font-mono text-slate-700">${escapeHtml(e.invoice_number || '-')}</td>
      <td class="py-3 px-4">
        <div class="font-medium text-slate-800">${escapeHtml(e.description)}</div>
        <div class="text-[10px] text-blue-600 font-medium">${e.account_code} - ${escapeHtml(e.account_name || 'Kosten')}</div>
      </td>
      <td class="py-3 px-4 text-right font-mono font-semibold text-slate-800">${formatCurrency(e.imponibile)}</td>
      <td class="py-3 px-4 text-center font-mono font-bold">${e.vat_rate}%</td>
      <td class="py-3 px-4 text-right font-mono font-bold text-emerald-600">${formatCurrency(e.vat_amount)}</td>
      <td class="py-3 px-4 text-right font-mono font-bold text-slate-900">${formatCurrency(e.total_amount)}</td>
      <td class="py-3 px-4 text-center">
        <span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${e.payment_status === 'Betaald' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}">
          ${e.payment_status}
        </span>
      </td>
      <td class="py-3 px-4 text-center">
        <button onclick="deleteExpenseItem(${e.id})" title="Verwijder kostenpost" class="p-1 text-slate-400 hover:text-red-600 transition">
          <i class="fa-solid fa-trash-can"></i>
        </button>
      </td>
    </tr>
  `).join("");
}

async function loadChartOfAccounts() {
  try {
    const res = await fetch(`${API_BASE}/chart-of-accounts`);
    globalChartOfAccounts = await res.json();
    const container = document.getElementById("piano-dei-conti-list");
    if (!container) return;

    container.innerHTML = globalChartOfAccounts.map(a => {
      const catColor = (a.category === 'Attivo' || a.category === 'Activa') ? 'bg-blue-50 text-blue-700 border border-blue-200' :
                       (a.category === 'Passivo' || a.category === 'Passiva') ? 'bg-purple-50 text-purple-700 border border-purple-200' :
                       (a.category === 'Ricavi' || a.category === 'Opbrengsten') ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
                       'bg-amber-50 text-amber-700 border border-amber-200';
      return `
        <div class="py-2.5 flex items-center justify-between">
          <div class="flex items-center gap-3">
            <span class="font-mono font-bold text-slate-900 w-12">${a.code}</span>
            <div>
              <span class="font-semibold text-slate-800">${escapeHtml(a.name)}</span>
              <span class="text-[11px] text-slate-400 block">${escapeHtml(a.subcategory || '')}</span>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-[10px] font-semibold px-2 py-0.5 rounded ${catColor}">${escapeHtml(a.category)}</span>
            <span class="text-[11px] font-mono text-slate-500">Aftrekbaar: ${a.tax_deductibility_pct}%</span>
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    console.error("Fout bij ophalen rekeningschema:", err);
  }
}

function openNewExpenseModal() {
  document.getElementById("modal-new-expense").classList.remove("hidden");
  calcExpenseTotals();
}

function calcExpenseTotals() {
  const imp = parseFloat(document.getElementById("exp-imponibile").value) || 0;
  const rate = parseFloat(document.getElementById("exp-vat-rate").value) || 0;
  const vat = Math.round(imp * (rate / 100.0) * 100) / 100;
  const total = Math.round((imp + vat) * 100) / 100;

  document.getElementById("exp-total").value = total.toFixed(2);
  document.getElementById("exp-vat-display").textContent = formatCurrency(vat);
}

async function saveNewExpense(e) {
  e.preventDefault();
  const imp = parseFloat(document.getElementById("exp-imponibile").value) || 0;
  const rate = parseFloat(document.getElementById("exp-vat-rate").value) || 0;

  const payload = {
    date: new Date().toISOString().split("T")[0],
    supplier_name: document.getElementById("exp-supplier").value,
    supplier_vat: document.getElementById("exp-vat").value,
    invoice_number: document.getElementById("exp-inv-num").value,
    account_code: document.getElementById("exp-account").value,
    description: document.getElementById("exp-desc").value,
    imponibile: imp,
    vat_rate: rate,
    payment_status: "Betaald",
    payment_method: "Bonifico Bancario (MP05)"
  };

  try {
    const res = await fetch(`${API_BASE}/expenses`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await res.json();
    if (result.success) {
      showToast(result.message, "success");
      closeModal("modal-new-expense");
      document.getElementById("expense-form").reset();
      await loadAccountingData();
      await loadStats();
    } else {
      showToast("Fout: " + result.error, "error");
    }
  } catch (err) {
    showToast("Netwerkfout: " + err, "error");
  }
}

async function deleteExpenseItem(id) {
  if (!confirm("Weet je zeker dat je deze kostenpost wilt verwijderen uit het Registro IVA Acquisti?")) return;
  try {
    const res = await fetch(`${API_BASE}/expenses/${id}`, { method: "DELETE" });
    const result = await res.json();
    if (result.success) {
      showToast("Kostenpost verwijderd", "success");
      await loadAccountingData();
      await loadStats();
    }
  } catch (err) {
    showToast("Fout: " + err, "error");
  }
}

// 5. RELATIES (VERLADERS)
async function loadParties() {
  try {
    const res = await fetch(`${API_BASE}/parties`);
    globalParties = await res.json();
    renderPartiesList("clients-list", globalParties);
    populateOrderClientDropdown(globalParties);
  } catch (err) {
    console.error("Fout bij ophalen verladers:", err);
  }
}

function renderPartiesList(containerId, list) {
  const container = document.getElementById(containerId);
  if (!container) return;

  if (list.length === 0) {
    container.innerHTML = `<p class="text-xs text-slate-400 py-4 text-center">Geen verladers geregistreerd.</p>`;
    return;
  }

  container.innerHTML = list.map(p => `
    <div class="py-3 flex items-start justify-between">
      <div>
        <h5 class="font-bold text-xs text-slate-900">${escapeHtml(p.name)}</h5>
        <div class="text-[11px] text-slate-500 font-mono mt-0.5">
          <span class="font-bold text-slate-700">${p.country}</span> &bull; BTW: ${p.vat_number || 'Geen'} &bull; SDI: <span class="text-blue-600 font-semibold">${p.sdi_code || '0000000'}</span>
        </div>
        <div class="text-[11px] text-slate-400 mt-0.5">
          ${p.city ? p.city + ', ' : ''}${p.address || ''} ${p.email ? '&bull; ' + p.email : ''}
        </div>
      </div>
      <div>
        <span class="text-[10px] font-semibold px-2 py-0.5 rounded bg-blue-50 text-blue-700">Verlader</span>
      </div>
    </div>
  `).join("");
}

function populateOrderClientDropdown(clients) {
  const clientSelect = document.getElementById("ord-client");
  if (clientSelect) {
    clientSelect.innerHTML = clients.map(c => 
      `<option value="${c.id}">${escapeHtml(c.name)} (${c.country})</option>`
    ).join("");
  }
}

// 6. FACTURATIE ACTIES (PROVISIES)
async function generateSingleCommissionInvoice(orderId) {
  const ord = globalOrders.find(o => o.id === orderId);
  const commAmount = ord ? ord.commission_amount : 0;
  if (!confirm(`Wil je een officiële FatturaPA XML commissiefactuur van € ${commAmount.toFixed(2)} genereren voor ${currentCompany.principal_name}?`)) return;

  try {
    const res = await fetch(`${API_BASE}/invoices/generate-commission`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ order_ids: [orderId] })
    });
    const result = await res.json();
    if (result.success) {
      showToast(result.message, "success");
      await loadOrders();
      await loadInvoices();
      await loadStats();
      switchTab("invoices");
    } else {
      showToast("Fout: " + result.error, "error");
    }
  } catch (err) {
    showToast("Netwerkfout: " + err, "error");
  }
}

async function updateOrderStatus(orderId, newStatus) {
  try {
    const res = await fetch(`${API_BASE}/orders/${orderId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus })
    });
    const result = await res.json();
    if (result.success) {
      showToast(`Ritstatus bijgewerkt naar '${newStatus}'`, "success");
      await loadOrders();
      await loadStats();
    } else {
      showToast("Fout bij bijwerken: " + (result.error || "Onbekende fout"), "error");
    }
  } catch (err) {
    showToast("Netwerkfout: " + err, "error");
  }
}

async function deleteOrder(orderId) {
  const ord = (globalOrders || []).find(o => o.id === orderId);
  const num = ord ? ord.order_number : `rit #${orderId}`;
  if (!confirm(`Weet je zeker dat je bemiddeling ${num} wilt verwijderen?`)) return;

  try {
    const res = await fetch(`${API_BASE}/orders/${orderId}`, {
      method: "DELETE"
    });
    const result = await res.json();
    if (result.success) {
      showToast(result.message || `Opdracht ${num} verwijderd`, "success");
      await loadOrders();
      await loadStats();
    } else {
      showToast("Fout bij verwijderen: " + (result.error || "Onbekende fout"), "error");
    }
  } catch (err) {
    showToast("Netwerkfout: " + err, "error");
  }
}

async function deleteInvoice(invoiceId) {
  const inv = (globalInvoices || []).find(i => i.id === invoiceId);
  const num = inv ? inv.invoice_number : `factuur #${invoiceId}`;
  if (!confirm(`Weet je zeker dat je ${num} wilt verwijderen?\n\nGekoppelde ritten worden automatisch teruggezet naar 'Geleverd'.`)) return;

  try {
    const res = await fetch(`${API_BASE}/invoices/${invoiceId}`, {
      method: "DELETE"
    });
    const result = await res.json();
    if (result.success) {
      showToast(result.message || `Factuur ${num} verwijderd`, "success");
      await loadInvoices();
      await loadOrders();
      await loadStats();
    } else {
      showToast("Fout bij verwijderen: " + (result.error || "Onbekende fout"), "error");
    }
  } catch (err) {
    showToast("Netwerkfout: " + err, "error");
  }
}

async function generateBatchCommissionInvoice() {
  const unbilled = globalOrders.filter(o => o.status !== "Commissie Gefactureerd");
  if (unbilled.length === 0) {
    showToast("Er zijn momenteel geen openstaande provisies om te factureren.", "info");
    return;
  }

  const totalComm = unbilled.reduce((acc, o) => acc + o.commission_amount, 0);
  if (!confirm(`Wil je een verzamel-commissiefactuur maken voor alle ${unbilled.length} openstaande ritten?\n\nTotaal te factureren aan ${currentCompany.principal_name}: € ${totalComm.toFixed(2)}`)) {
    return;
  }

  const ids = unbilled.map(o => o.id);
  try {
    const res = await fetch(`${API_BASE}/invoices/generate-commission`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ order_ids: ids })
    });
    const result = await res.json();
    if (result.success) {
      showToast(result.message, "success");
      await loadOrders();
      await loadInvoices();
      await loadStats();
      switchTab("invoices");
    } else {
      showToast("Fout: " + result.error, "error");
    }
  } catch (err) {
    showToast("Netwerkfout: " + err, "error");
  }
}

async function updateOrderStatus(orderId, newStatus) {
  try {
    const res = await fetch(`${API_BASE}/orders/${orderId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus })
    });
    const result = await res.json();
    if (result.success) {
      showToast(`Ritstatus bijgewerkt naar '${newStatus}'`, "success");
      await loadOrders();
      await loadStats();
    } else {
      showToast("Fout bij bijwerken: " + (result.error || "Onbekende fout"), "error");
    }
  } catch (err) {
    showToast("Netwerkfout: " + err, "error");
  }
}

async function deleteOrder(orderId) {
  const ord = (globalOrders || []).find(o => o.id === orderId);
  const num = ord ? ord.order_number : `rit #${orderId}`;
  if (!confirm(`Weet je zeker dat je bemiddeling ${num} wilt verwijderen?`)) return;

  try {
    const res = await fetch(`${API_BASE}/orders/${orderId}`, {
      method: "DELETE"
    });
    const result = await res.json();
    if (result.success) {
      showToast(result.message || `Opdracht ${num} verwijderd`, "success");
      await loadOrders();
      await loadStats();
    } else {
      showToast("Fout bij verwijderen: " + (result.error || "Onbekende fout"), "error");
    }
  } catch (err) {
    showToast("Netwerkfout: " + err, "error");
  }
}

async function deleteInvoice(invoiceId) {
  const inv = (globalInvoices || []).find(i => i.id === invoiceId);
  const num = inv ? inv.invoice_number : `factuur #${invoiceId}`;
  if (!confirm(`Weet je zeker dat je ${num} wilt verwijderen?\n\nGekoppelde ritten worden automatisch teruggezet naar 'Geleverd'.`)) return;

  try {
    const res = await fetch(`${API_BASE}/invoices/${invoiceId}`, {
      method: "DELETE"
    });
    const result = await res.json();
    if (result.success) {
      showToast(result.message || `Factuur ${num} verwijderd`, "success");
      await loadInvoices();
      await loadOrders();
      await loadStats();
    } else {
      showToast("Fout bij verwijderen: " + (result.error || "Onbekende fout"), "error");
    }
  } catch (err) {
    showToast("Netwerkfout: " + err, "error");
  }
}

// ================= FLEXIBELE COMMISSIE FUNCTIES =================
let currentDesktopCommissionMode = "percentage"; // 'percentage', 'fixed', 'margin', 'custom'

function setDesktopCommissionMode(mode) {
  currentDesktopCommissionMode = mode;
  document.getElementById("ord-comm-type").value = mode;

  const btnPct = document.getElementById("btn-mode-pct");
  const btnFixed = document.getElementById("btn-mode-fixed");
  const btnMargin = document.getElementById("btn-mode-margin");
  const btnCustom = document.getElementById("btn-mode-custom");

  const wrapPct = document.getElementById("wrapper-ord-pct");
  const wrapFixed = document.getElementById("wrapper-ord-fixed");
  const wrapMargin = document.getElementById("wrapper-ord-margin");

  // Reset button styles
  [btnPct, btnFixed, btnMargin, btnCustom].forEach(b => {
    if (b) {
      b.className = "py-1.5 px-2 rounded-md text-slate-600 hover:text-slate-900 transition-all text-center";
    }
  });

  // Hide all dynamic wrappers
  if (wrapPct) wrapPct.classList.add("hidden");
  if (wrapFixed) wrapFixed.classList.add("hidden");
  if (wrapMargin) wrapMargin.classList.add("hidden");

  if (mode === "percentage") {
    if (btnPct) btnPct.className = "py-1.5 px-2 rounded-md bg-blue-600 text-white shadow-sm font-bold text-center";
    if (wrapPct) wrapPct.classList.remove("hidden");
  } else if (mode === "fixed") {
    if (btnFixed) btnFixed.className = "py-1.5 px-2 rounded-md bg-purple-600 text-white shadow-sm font-bold text-center";
    if (wrapFixed) wrapFixed.classList.remove("hidden");
  } else if (mode === "margin") {
    if (btnMargin) btnMargin.className = "py-1.5 px-2 rounded-md bg-amber-600 text-white shadow-sm font-bold text-center";
    if (wrapMargin) wrapMargin.classList.remove("hidden");
  } else if (mode === "custom") {
    if (btnCustom) btnCustom.className = "py-1.5 px-2 rounded-md bg-emerald-600 text-white shadow-sm font-bold text-center";
    setTimeout(() => {
      const commInput = document.getElementById("ord-comm-amount");
      if (commInput) commInput.focus();
    }, 50);
  }

  calcDesktopCommission();
}

function setDesktopRate(pct) {
  document.getElementById("ord-comm-rate").value = pct;
  calcDesktopCommission();
}

function setDesktopFixedFee(fee) {
  document.getElementById("ord-comm-fixed").value = fee;
  calcDesktopCommission();
}

function calcDesktopCommission() {
  const freight = parseFloat(document.getElementById("ord-freight").value) || 0;
  const mode = currentDesktopCommissionMode;
  let comm = 0;
  let rate = 0;

  if (mode === "percentage") {
    rate = parseFloat(document.getElementById("ord-comm-rate").value) || 10.0;
    comm = roundNum(freight * (rate / 100.0), 2);
  } else if (mode === "fixed") {
    comm = parseFloat(document.getElementById("ord-comm-fixed").value) || 200.0;
    rate = freight > 0 ? roundNum((comm / freight) * 100.0, 1) : 0;
  } else if (mode === "margin") {
    const carrier = parseFloat(document.getElementById("ord-carrier-price").value) || 0;
    comm = roundNum(Math.max(0, freight - carrier), 2);
    rate = freight > 0 ? roundNum((comm / freight) * 100.0, 1) : 0;
  } else if (mode === "custom") {
    comm = parseFloat(document.getElementById("ord-comm-amount").value) || 0;
    rate = freight > 0 ? roundNum((comm / freight) * 100.0, 1) : 0;
  }

  if (mode !== "custom") {
    document.getElementById("ord-comm-amount").value = comm.toFixed(2);
  }

  const display = document.getElementById("ord-calc-display");
  if (display) {
    const modeLabel = mode === "percentage" ? `${rate}% fee` :
                      mode === "fixed" ? "Vaste fee" :
                      mode === "margin" ? `Marge (${rate}%)` : "Vrij bedrag";
    display.textContent = `Provisie: € ${comm.toFixed(2)} (${modeLabel})`;
  }

  const hint = document.getElementById("ord-effective-pct-hint");
  if (hint) {
    hint.textContent = `Effectief: ${rate}% marge van vrachtprijs`;
  }
}

function onDesktopDirectCommissionInput() {
  const freight = parseFloat(document.getElementById("ord-freight").value) || 0;
  const comm = parseFloat(document.getElementById("ord-comm-amount").value) || 0;
  const rate = freight > 0 ? roundNum((comm / freight) * 100.0, 1) : 0;

  const hint = document.getElementById("ord-effective-pct-hint");
  if (hint) {
    hint.textContent = `Effectief: ${rate}% marge van vrachtprijs`;
  }

  const display = document.getElementById("ord-calc-display");
  if (display) {
    display.textContent = `Provisie: € ${comm.toFixed(2)} (${rate}%)`;
  }

  // Update in percentage veld als we in percentage modus zijn
  if (currentDesktopCommissionMode === "percentage" && freight > 0) {
    document.getElementById("ord-comm-rate").value = rate;
  } else if (currentDesktopCommissionMode === "fixed") {
    document.getElementById("ord-comm-fixed").value = comm;
  }
}

async function saveNewOrder(e) {
  e.preventDefault();
  const freight = parseFloat(document.getElementById("ord-freight").value) || 0;
  const commType = currentDesktopCommissionMode;
  const commRate = parseFloat(document.getElementById("ord-comm-rate").value) || 10.0;
  const commAmount = parseFloat(document.getElementById("ord-comm-amount").value) || 0;
  const carrierPrice = parseFloat(document.getElementById("ord-carrier-price").value) || 0;

  const clientVal = document.getElementById("ord-client") ? document.getElementById("ord-client").value : "";
  const clientId = clientVal && !isNaN(parseInt(clientVal, 10)) ? parseInt(clientVal, 10) : null;

  const payload = {
    client_id: clientId,
    origin_country: (document.getElementById("ord-orig-country").value || "NL").toUpperCase(),
    origin_city: document.getElementById("ord-orig-city").value,
    destination_country: (document.getElementById("ord-dest-country").value || "IT").toUpperCase(),
    destination_city: document.getElementById("ord-dest-city").value,
    goods_description: document.getElementById("ord-goods").value,
    weight_kg: parseFloat(document.getElementById("ord-weight").value) || 0,
    cmr_number: document.getElementById("ord-cmr").value,
    freight_price: freight,
    carrier_price: carrierPrice,
    commission_type: commType,
    commission_rate: commRate,
    commission_amount: commAmount,
    status: "Aangemeld",
    pickup_date: new Date().toISOString().split("T")[0]
  };

  try {
    const res = await fetch(`${API_BASE}/orders`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await res.json();
    if (result.success) {
      showToast(result.message, "success");
      closeModal("modal-new-order");
      document.getElementById("order-form").reset();
      await loadOrders();
      await loadStats();
      switchTab("orders");
    } else {
      showToast("Fout bij opslaan: " + (result.error || result.message || "Onbekende fout"), "error");
    }
  } catch (err) {
    showToast("Fout bij opslaan opdracht: " + err, "error");
  }
}

async function saveNewParty(e) {
  e.preventDefault();
  const payload = {
    type: "client",
    country: document.getElementById("party-country").value.toUpperCase(),
    name: document.getElementById("party-name").value,
    vat_number: document.getElementById("party-vat").value,
    email: document.getElementById("party-email").value,
    city: document.getElementById("party-city").value
  };

  try {
    const res = await fetch(`${API_BASE}/parties`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await res.json();
    if (result.success) {
      showToast(`Verlader '${payload.name}' succesvol toegevoegd!`, "success");
      closeModal("modal-new-party");
      await loadParties();
    } else {
      showToast("Fout bij opslaan: " + (result.error || "Onbekende fout"), "error");
    }
  } catch (err) {
    showToast("Fout: " + err, "error");
  }
}

// 7. XML & SDI
async function viewInvoiceXml(invoiceId) {
  const inv = globalInvoices.find(i => i.id === invoiceId);
  if (!inv) return;

  currentViewingXml = inv.xml_content || "";
  document.getElementById("xml-modal-title").innerHTML = `<i class="fa-solid fa-code text-blue-400"></i> Commissiefactuur: ${inv.invoice_number}`;
  document.getElementById("xml-content-display").textContent = currentViewingXml;
  document.getElementById("xml-download-link").href = `${API_BASE}/invoices/${invoiceId}/xml`;
  document.getElementById("modal-xml-viewer").classList.remove("hidden");
}

function copyXmlToClipboard() {
  if (!currentViewingXml) return;
  navigator.clipboard.writeText(currentViewingXml).then(() => {
    showToast("FatturaPA XML naar klembord gekopieerd!", "success");
  });
}

async function sendToSdi(invoiceId) {
  try {
    const res = await fetch(`${API_BASE}/invoices/${invoiceId}/sdi-send`, { method: "POST" });
    const result = await res.json();
    if (result.success) {
      showToast(result.message, "success");
      await loadInvoices();
      await loadStats();
    }
  } catch (err) {
    showToast("Fout bij verzenden: " + err, "error");
  }
}

// ================= FACTUUR SJABLOON & COPIA DI CORTESIA =================
let currentTemplateInvoice = null;
let currentTemplateOrders = [];
let currentTemplateCompany = null;

async function viewInvoiceTemplate(invoiceId) {
  try {
    const res = await fetch(`${API_BASE}/invoices/${invoiceId}`);
    if (!res.ok) throw new Error("Factuur details konden niet worden opgehaald");
    const data = await res.json();

    currentTemplateInvoice = data.invoice;
    currentTemplateCompany = data.company || currentCompany;
    currentTemplateOrders = data.orders || [];

    const inv = currentTemplateInvoice;
    const comp = currentTemplateCompany;

    // Header modal
    document.getElementById("tpl-modal-inv-num").textContent = `Factuur ${inv.invoice_number}`;
    const badgeEl = document.getElementById("tpl-modal-sdi-badge");
    if (badgeEl) {
      badgeEl.textContent = `SDI: ${inv.sdi_status}`;
      badgeEl.className = inv.sdi_status.includes("Consegnata") 
        ? "text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-semibold"
        : "text-[10px] px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 font-semibold";
    }

    // Bedrijfsgegevens (Cedente Prestatore)
    document.getElementById("tpl-company-name").textContent = comp.name || "Transito Intermediazioni S.r.l.";
    document.getElementById("tpl-company-address").textContent = `${comp.address || 'Via Macello 18'} • ${comp.zip || '39100'} ${comp.city || 'Bolzano'} (${comp.province || 'BZ'}), ${comp.country || 'IT'}`;
    document.getElementById("tpl-company-vat").textContent = comp.vat_number || "IT09876543210";
    document.getElementById("tpl-company-cf").textContent = comp.fiscal_code || "09876543210";
    document.getElementById("tpl-company-rea").textContent = comp.rea_number || "BZ-241598";
    document.getElementById("tpl-company-pec").textContent = comp.pec || "-";
    document.getElementById("tpl-company-sdi").textContent = comp.sdi_code || "0000000";

    // Vervoerder (Cessionario Committente)
    document.getElementById("tpl-party-name").textContent = inv.party_name || comp.principal_name;
    document.getElementById("tpl-party-address").textContent = comp.principal_address || "Transportlaan 14";
    document.getElementById("tpl-party-city").textContent = `${comp.principal_zip || '5504 KR'} ${comp.principal_city || 'Veldhoven'} • ${inv.party_country === 'NL' ? 'Nederland (NL)' : inv.party_country}`;
    document.getElementById("tpl-party-vat").textContent = inv.party_vat || comp.principal_vat;
    document.getElementById("tpl-party-sdi").textContent = inv.party_sdi || comp.principal_sdi || "XXXXXXX";

    // Factuur meta
    document.getElementById("tpl-inv-number").textContent = inv.invoice_number;
    document.getElementById("tpl-inv-date").textContent = inv.date;
    document.getElementById("tpl-inv-due").textContent = inv.due_date;
    document.getElementById("tpl-inv-sdi-id").textContent = inv.sdi_identifier || "Klaar voor verzending";
    document.getElementById("tpl-ref-num").textContent = inv.invoice_number;

    // Bank
    document.getElementById("tpl-bank-beneficiary").textContent = comp.name;
    document.getElementById("tpl-bank-iban").textContent = comp.iban || "-";
    document.getElementById("tpl-bank-swift").textContent = comp.swift || "-";

    // BTW vrijstellingsclausule
    const isEU = inv.party_country !== "IT";
    document.getElementById("tpl-vat-clause-title").textContent = isEU 
      ? "Btw Verlegd / Inversione Contabile (Reverse Charge - Art. 7-ter)"
      : "Vrijgesteld van btw / Non imponibile (Art. 9 DPR 633/72)";
    document.getElementById("tpl-vat-clause-text").textContent = inv.normative_ref || (isEU 
      ? "Operazione non soggetta ad IVA ai sensi dell'art. 7-ter DPR 633/1972 (Natura SDI: N6). De btw wordt verlegd naar de medecontractant in Nederland (art. 196 EU-Richtlijn 2006/112/EG)."
      : "Operazione non imponibile IVA ai sensi dell'art. 9 DPR 633/1972 (Natura SDI: N3.2).");

    // Orders / Lines rendering
    renderTemplateLines();

    // Totalen
    document.getElementById("tpl-subtotal").textContent = formatCurrency(inv.subtotal);
    document.getElementById("tpl-vat-amount").textContent = formatCurrency(inv.vat_amount);
    document.getElementById("tpl-total-due").textContent = formatCurrency(inv.total_amount);

    document.getElementById("modal-invoice-template").classList.remove("hidden");
  } catch (err) {
    showToast("Fout bij laden factuur sjabloon: " + err, "error");
  }
}

function renderTemplateLines() {
  const tbody = document.getElementById("tpl-lines-tbody");
  if (!tbody) return;

  const orders = currentTemplateOrders;
  const inv = currentTemplateInvoice;
  const detail = document.getElementById("tpl-custom-detail") ? document.getElementById("tpl-custom-detail").value : "full";

  document.getElementById("tpl-order-count-badge").textContent = `${orders.length || 1} bemiddelde ${orders.length === 1 ? 'rit' : 'ritten'}`;

  if (orders.length > 0) {
    tbody.innerHTML = orders.map((o, idx) => {
      const commType = o.commission_type || "percentage";
      let modelText = `${o.commission_rate}% fee`;
      if (commType === "fixed") modelText = "Vaste fee";
      else if (commType === "margin") modelText = `Marge ${o.commission_rate}%`;
      else if (commType === "custom") modelText = "Vrij tarief";

      return `
        <tr class="hover:bg-slate-50/60">
          <td class="py-2.5 px-3 text-center font-mono font-bold text-slate-400">${idx + 1}</td>
          <td class="py-2.5 px-3">
            <div class="font-bold text-slate-900 font-mono">${o.order_number}</div>
            <div class="text-[11px] text-slate-600">
              <span class="font-semibold text-blue-600">${o.origin_country}</span> ${escapeHtml(o.origin_city)}
              &rarr;
              <span class="font-semibold text-emerald-600">${o.destination_country}</span> ${escapeHtml(o.destination_city)}
            </div>
            ${detail === 'full' && o.cmr_number ? `<div class="text-[10px] text-slate-400 font-mono">CMR: ${escapeHtml(o.cmr_number)}</div>` : ''}
          </td>
          <td class="py-2.5 px-3">
            <div class="font-semibold text-slate-800">${escapeHtml(o.client_name || 'Verlader')}</div>
            ${detail === 'full' && o.goods_description ? `<div class="text-[10px] text-slate-400">${escapeHtml(o.goods_description)}</div>` : ''}
          </td>
          <td class="py-2.5 px-3 text-right font-mono text-slate-700">
            ${formatCurrency(o.freight_price)}
          </td>
          <td class="py-2.5 px-3 text-center">
            <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">${modelText}</span>
          </td>
          <td class="py-2.5 px-3 text-right font-mono font-bold text-emerald-700 text-xs">
            ${formatCurrency(o.commission_amount)}
          </td>
        </tr>
      `;
    }).join("");
  } else {
    // Handmatige regels of fallback
    tbody.innerHTML = `
      <tr>
        <td class="py-3 px-3 text-center font-mono font-bold text-slate-400">1</td>
        <td class="py-3 px-3" colspan="4">
          <div class="font-bold text-slate-900">Bemiddelingsvergoeding en provisies transport</div>
          <div class="text-[11px] text-slate-500">Diensten verleend als intermediair namens het transportbedrijf</div>
        </td>
        <td class="py-3 px-3 text-right font-mono font-bold text-emerald-700 text-xs">
          ${formatCurrency(inv.subtotal)}
        </td>
      </tr>
    `;
  }
}

function toggleTemplateCustomizer() {
  const bar = document.getElementById("template-customizer-bar");
  if (bar) {
    bar.classList.toggle("hidden");
  }
}

function updateTemplateLivePreview() {
  const titleInput = document.getElementById("tpl-custom-title");
  if (titleInput && document.getElementById("tpl-doc-title")) {
    document.getElementById("tpl-doc-title").textContent = titleInput.value || "PROVISIEFACTUUR";
  }

  const notesInput = document.getElementById("tpl-custom-notes");
  const notesDisplay = document.getElementById("tpl-custom-notes-display");
  if (notesInput && notesDisplay) {
    if (notesInput.value.trim()) {
      notesDisplay.innerHTML = `<span class="font-bold">Opmerking / Clausule:</span> ${escapeHtml(notesInput.value.trim())}`;
      notesDisplay.classList.remove("hidden");
    } else {
      notesDisplay.classList.add("hidden");
    }
  }

  renderTemplateLines();
}

function printInvoiceTemplate() {
  window.print();
}

function openDraftInvoiceModal() {
  const comp = currentCompany || {};
  document.getElementById("draft-party-name").value = comp.principal_name || "Veldhoven International Transport B.V.";
  document.getElementById("draft-party-country").value = comp.principal_country || "NL";
  document.getElementById("draft-party-vat").value = comp.principal_vat || "NL854729381B01";
  
  const today = new Date().toISOString().split("T")[0];
  const due = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split("T")[0];
  document.getElementById("draft-inv-date").value = today;
  document.getElementById("draft-inv-due").value = due;

  document.getElementById("modal-draft-invoice").classList.remove("hidden");
}

async function saveCustomDraftInvoice(e) {
  e.preventDefault();
  const partyName = document.getElementById("draft-party-name").value;
  const partyCountry = document.getElementById("draft-party-country").value.toUpperCase();
  const partyVat = document.getElementById("draft-party-vat").value;
  const date = document.getElementById("draft-inv-date").value;
  const dueDate = document.getElementById("draft-inv-due").value;
  const subtotal = parseFloat(document.getElementById("draft-subtotal").value) || 0;
  const vatRate = parseFloat(document.getElementById("draft-vat-rate").value) || 0;
  const desc = document.getElementById("draft-line-desc").value;

  const payload = {
    party_name: partyName,
    party_country: partyCountry,
    party_vat: partyVat,
    date: date,
    due_date: dueDate,
    subtotal: subtotal,
    vat_rate: vatRate,
    lines: [{
      description: desc,
      quantity: 1.0,
      unit_price: subtotal,
      total_price: subtotal
    }]
  };

  try {
    const res = await fetch(`${API_BASE}/invoices/custom`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await res.json();
    if (result.success) {
      showToast(result.message, "success");
      closeModal("modal-draft-invoice");
      document.getElementById("draft-invoice-form").reset();
      await loadInvoices();
      await loadStats();
      switchTab("invoices");
      viewInvoiceTemplate(result.invoice_id);
    } else {
      showToast("Fout: " + result.error, "error");
    }
  } catch (err) {
    showToast("Netwerkfout: " + err, "error");
  }
}

// ================= E-MAILKOPPELING & FACTUURVERZENDING =================
async function saveSmtpSettings(e) {
  e.preventDefault();
  const payload = {
    ...currentCompany,
    smtp_host: document.getElementById("set-smtp-host").value,
    smtp_port: parseInt(document.getElementById("set-smtp-port").value) || 587,
    smtp_security: document.getElementById("set-smtp-security").value,
    smtp_user: document.getElementById("set-smtp-user").value,
    smtp_pass: document.getElementById("set-smtp-pass").value,
    smtp_sender_name: document.getElementById("set-smtp-sender-name").value,
    smtp_sender_email: document.getElementById("set-smtp-sender-email").value,
    principal_email: document.getElementById("set-principal-email").value,
    accountant_email: document.getElementById("set-accountant-email").value
  };

  try {
    const res = await fetch(`${API_BASE}/company`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await res.json();
    if (result.success) {
      showToast("E-mailkoppeling en mailserverinstellingen succesvol opgeslagen!", "success");
      loadCompany();
    }
  } catch (err) {
    showToast("Fout: " + err, "error");
  }
}

async function testEmailConnection() {
  const host = document.getElementById("set-smtp-host").value;
  const port = document.getElementById("set-smtp-port").value;
  const user = document.getElementById("set-smtp-user").value;
  const targetEmail = document.getElementById("set-principal-email").value || user;

  showToast("Bezig met testen van de e-mailverbinding...", "info");

  try {
    const res = await fetch(`${API_BASE}/email/test`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        smtp_host: host,
        smtp_port: parseInt(port) || 587,
        smtp_security: document.getElementById("set-smtp-security").value,
        smtp_user: user,
        smtp_pass: document.getElementById("set-smtp-pass").value,
        smtp_sender_name: document.getElementById("set-smtp-sender-name").value,
        smtp_sender_email: document.getElementById("set-smtp-sender-email").value,
        to_email: targetEmail
      })
    });
    const result = await res.json();
    if (result.success) {
      showToast(result.message, "success");
    } else {
      showToast("E-mail test mislukt: " + (result.error || "Onbekende fout"), "error");
    }
  } catch (err) {
    showToast("Netwerkfout bij test: " + err, "error");
  }
}

function openSendEmailModal(invoiceId) {
  const inv = globalInvoices.find(i => i.id === invoiceId) || currentTemplateInvoice || {};
  document.getElementById("mail-invoice-id").value = invoiceId;

  const to = (currentCompany && currentCompany.principal_email) || "administratie@veldhoventransport.nl";
  const cc = (currentCompany && currentCompany.accountant_email) || "";
  
  document.getElementById("mail-to").value = to;
  document.getElementById("mail-cc").value = cc;
  document.getElementById("mail-subject").value = `Commissiefactuur ${inv.invoice_number || 'PROV-2026-001'} - ${currentCompany.name || 'Transito Intermediazioni'}`;
  document.getElementById("mail-message").value = `Beste collega's,\n\nHierbij ontvangt u de commissiefactuur ${inv.invoice_number} voor de bemiddelde transportopdrachten. Het officiële FatturaPA XML-bestand is bijgevoegd voor uw administratie.\n\nMet vriendelijke groet,\n${currentCompany.name || 'Transito Intermediazioni S.r.l.'}`;

  const previewLink = document.getElementById("mail-preview-link");
  if (previewLink) {
    previewLink.href = `${API_BASE}/invoices/${invoiceId}/email-preview`;
  }

  document.getElementById("modal-send-email").classList.remove("hidden");
}

async function submitSendEmail(e) {
  e.preventDefault();
  const invoiceId = parseInt(document.getElementById("mail-invoice-id").value);
  const btn = document.getElementById("btn-submit-send-email");
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Bezig met verzenden...`;

  const payload = {
    to_email: document.getElementById("mail-to").value,
    cc_email: document.getElementById("mail-cc").value,
    subject: document.getElementById("mail-subject").value,
    message: document.getElementById("mail-message").value,
    attach_xml: document.getElementById("mail-attach-xml").checked
  };

  try {
    const res = await fetch(`${API_BASE}/invoices/${invoiceId}/send-email`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await res.json();
    if (result.success) {
      showToast(result.message, "success");
      closeModal("modal-send-email");
      await loadInvoices();
    } else {
      showToast("Fout bij verzenden: " + result.error, "error");
    }
  } catch (err) {
    showToast("Netwerkfout: " + err, "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-solid fa-paper-plane"></i> Factuur Nu Verzenden`;
  }
}

// Helpers
function openNewOrderModal() {
  document.getElementById("modal-new-order").classList.remove("hidden");
  const defaultMode = (currentCompany && currentCompany.default_commission_type) || "percentage";
  setDesktopCommissionMode(defaultMode);

  if (currentCompany && currentCompany.default_commission_rate) {
    const rateEl = document.getElementById("ord-comm-rate");
    if (rateEl) rateEl.value = currentCompany.default_commission_rate;
  }
  if (currentCompany && currentCompany.default_commission_fixed) {
    const fixedEl = document.getElementById("ord-comm-fixed");
    if (fixedEl) fixedEl.value = currentCompany.default_commission_fixed;
  }
  calcDesktopCommission();
}

function getCommissionBadge(o) {
  const type = o.commission_type || 'percentage';
  if (type === 'fixed') {
    return `<span class="text-[10px] font-semibold text-purple-700 bg-purple-50 px-1.5 py-0.5 rounded border border-purple-200" title="Vaste afspraak per rit">Vaste Fee</span>`;
  } else if (type === 'margin') {
    const carrier = o.carrier_price ? ` (Vervoerder: € ${parseFloat(o.carrier_price).toFixed(0)})` : '';
    return `<span class="text-[10px] font-semibold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200" title="Marge: Verlader € ${o.freight_price.toFixed(0)}${carrier}">Marge ${o.commission_rate}%</span>`;
  } else if (type === 'custom') {
    return `<span class="text-[10px] font-semibold text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200" title="Vrij bedrag (${o.commission_rate}% effectief)">Vrij tarief</span>`;
  } else {
    return `<span class="text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">${o.commission_rate}% fee</span>`;
  }
}

function openNewPartyModal() {
  document.getElementById("modal-new-party").classList.remove("hidden");
}

async function openMobileAppModal() {
  const qrImg = document.getElementById("mobile-qr-code");
  const urlDisplay = document.getElementById("mobile-url-display");

  // Bepaal mobiele URL via actieve tunnel of lokaal netwerk
  let mobileUrl = `${window.location.origin}/mobile`;
  try {
    const res = await fetch(`${API_BASE}/network-info`);
    const info = await res.json();
    if (info.mobile_url) mobileUrl = info.mobile_url;
  } catch (err) {
    console.warn("Kon netwerk info niet automatisch ophalen:", err);
  }

  if (qrImg) {
    qrImg.src = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(mobileUrl)}`;
  }
  if (urlDisplay) {
    urlDisplay.textContent = mobileUrl;
    urlDisplay.href = mobileUrl;
  }
  document.getElementById("modal-mobile-app").classList.remove("hidden");
}

function closeModal(modalId) {
  document.getElementById(modalId).classList.add("hidden");
}

function roundNum(num, dec) {
  return Math.round(num * Math.pow(10, dec)) / Math.pow(10, dec);
}

function formatCurrency(val) {
  const num = parseFloat(val) || 0;
  return new Intl.NumberFormat("nl-NL", { style: "currency", currency: "EUR" }).format(num);
}

function getStatusBadge(status) {
  const map = {
    'Aangemeld': 'badge-gepland',
    'Bevestigd door Vervoerder': 'badge-onderweg',
    'Onderweg': 'badge-onderweg',
    'Geleverd': 'badge-geleverd',
    'Commissie Gefactureerd': 'badge-gefactureerd'
  };
  const cls = map[status] || 'badge-sdi-gegenereerd';
  return `<span class="badge-status ${cls}"><i class="fa-solid fa-circle text-[7px]"></i> ${status}</span>`;
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function showToast(msg, type = "info") {
  const container = document.getElementById("toast-container");
  const el = document.createElement("div");
  const bg = type === "success" ? "bg-emerald-600" : type === "error" ? "bg-red-600" : "bg-blue-600";
  el.className = `toast ${bg} text-white px-4 py-3 rounded-xl shadow-xl text-xs flex items-center gap-2 max-w-sm`;
  el.innerHTML = `<i class="fa-solid fa-circle-info text-sm"></i> <span>${escapeHtml(msg)}</span>`;
  container.appendChild(el);
  setTimeout(() => {
    el.style.opacity = "0";
    el.style.transform = "translateY(10px)";
    setTimeout(() => el.remove(), 300);
  }, 4000);
}
