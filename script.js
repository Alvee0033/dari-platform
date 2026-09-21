/**
 * DARI Document Verification - Client Controller
 * Connected with ADREC Document Registry & Operations Center
 */

const STORAGE_KEY_DOCS = 'dari_registry_v1';
const STORAGE_KEY_AUDIT = 'dari_audit_log_v1';

// Capture direct verification query parameter from URL (e.g. from scanned QR code)
const initialUrlParams = new URLSearchParams(window.location.search);
const initialContractParam = initialUrlParams.get('contractNumber') || 
                            initialUrlParams.get('contractNo') || 
                            initialUrlParams.get('documentNumber') || 
                            initialUrlParams.get('id') || 
                            initialUrlParams.get('c_no');

document.addEventListener('DOMContentLoaded', async () => {
  setupTabs();
  setupCaptcha();
  setupNav();
  setupPopups();
  setupResultView();
  await checkAutoVerify();
});

let isCaptchaDone = true;

// Retrieve documents from localStorage or dynamic API
async function getRegistry() {
  let docs = [];
  const cachedDocs = localStorage.getItem(STORAGE_KEY_DOCS);
  if (cachedDocs) {
    try {
      const parsed = JSON.parse(cachedDocs);
      if (Array.isArray(parsed)) {
        docs = parsed;
      }
    } catch (e) {
      console.warn('Error reading registry cache', e);
    }
  }

  try {
    const res = await fetch(`/api/documents?_t=${Date.now()}`, {
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache' }
    });
    if (res.ok) {
      const serverDocs = await res.json();
      if (Array.isArray(serverDocs)) {
        docs = serverDocs;
        localStorage.setItem(STORAGE_KEY_DOCS, JSON.stringify(docs));
        return docs;
      }
    }
  } catch (e) {
    console.warn('Could not fetch /api/documents', e);
  }
  return docs;
}

// Record verification inquiry into audit log
async function recordAuditLog(queryRef, docType, result, status, partyName = '-') {
  let auditLogs = [];
  const cachedAudit = localStorage.getItem(STORAGE_KEY_AUDIT);
  if (cachedAudit) {
    try {
      auditLogs = JSON.parse(cachedAudit);
    } catch (e) {}
  }

  try {
    const res = await fetch(`/api/audit?_t=${Date.now()}`, { cache: 'no-store' });
    if (res.ok) {
      const serverAudit = await res.json();
      if (Array.isArray(serverAudit)) {
        auditLogs = serverAudit;
      }
    }
  } catch (e) {}

  const isMobile = window.innerWidth <= 768 || navigator.userAgent.includes('Mobile');
  const typeMap = {
    tenancy: 'Tenancy Contract',
    certificate: 'Title Certificate',
    permit: 'Madhmoun Permit'
  };

  const newEntry = {
    id: 'AUDIT-' + Math.floor(1000 + Math.random() * 9000),
    timestamp: new Date().toISOString(),
    documentNumber: queryRef,
    documentType: typeMap[docType] || 'Tenancy Contract',
    result: result,
    status: status,
    partyName: partyName || '-',
    ip: '194.170.' + Math.floor(10 + Math.random() * 80) + '.' + Math.floor(2 + Math.random() * 250),
    device: isMobile ? 'Mobile (iPhone / Safari)' : 'Desktop (Chrome / Web)'
  };

  auditLogs.unshift(newEntry);
  if (auditLogs.length > 60) auditLogs = auditLogs.slice(0, 60);

  localStorage.setItem(STORAGE_KEY_AUDIT, JSON.stringify(auditLogs));
  fetch('/api/audit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(auditLogs)
  }).catch(() => {});
}

// Increment document verification count
async function incrementVerificationCount(docId) {
  try {
    const docs = await getRegistry();
    const doc = docs.find(d => d.id === docId);
    if (doc) {
      doc.verificationCount = (doc.verificationCount || 0) + 1;
      doc.updatedAt = new Date().toISOString();
      localStorage.setItem(STORAGE_KEY_DOCS, JSON.stringify(docs));
      fetch('/api/documents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(docs)
      }).catch(() => {});
    }
  } catch (e) {}
}

function setupTabs() {
  const radioItems = document.querySelectorAll('.radio-item');
  const views = {
    tenancy: document.getElementById('viewTenancy'),
    certificate: document.getElementById('viewCertificate'),
    permit: document.getElementById('viewPermit')
  };
  const alertEl = document.getElementById('statusAlert');

  radioItems.forEach(item => {
    item.addEventListener('click', () => {
      radioItems.forEach(r => {
        r.classList.remove('active');
        const inp = r.querySelector('input');
        if (inp) inp.checked = false;
      });

      item.classList.add('active');
      const input = item.querySelector('input');
      if (input) input.checked = true;

      const type = item.getAttribute('data-type');
      Object.values(views).forEach(v => {
        if (v) v.classList.remove('active');
      });

      if (views[type]) {
        views[type].classList.add('active');
      }

      if (alertEl) {
        alertEl.style.display = 'none';
        alertEl.className = 'verify-alert-msg';
        alertEl.innerHTML = '';
      }
    });
  });
}

function setupCaptcha() {
  const chk = document.getElementById('recaptchaCheckbox');
  if (!chk) return;

  chk.addEventListener('click', () => {
    if (isCaptchaDone) return;
    chk.classList.add('loading');
    setTimeout(() => {
      chk.classList.remove('loading');
      chk.classList.add('checked');
      isCaptchaDone = true;
    }, 600);
  });
}

async function handleVerifySubmit(e, isInstant = false) {
  if (e && e.preventDefault) e.preventDefault();
  const alertEl = document.getElementById('statusAlert');
  if (!alertEl) return false;

  const activeItem = document.querySelector('.radio-item.active');
  const docType = activeItem ? activeItem.getAttribute('data-type') : 'tenancy';

  let value = '';
  let field = '';

  if (docType === 'tenancy') {
    const el = document.getElementById('tenancyNumberInput');
    value = el ? el.value.trim() : '';
    field = 'tenancy contract number';
  } else if (docType === 'certificate') {
    const typeEl = document.getElementById('certTypeSelect');
    const dateEl = document.getElementById('certDateInput');
    const numEl = document.getElementById('certNumberInput');
    
    if (typeEl && !typeEl.value) {
      showMsg('Please select a certificate type.', 'error');
      return false;
    }
    if (dateEl && !dateEl.value) {
      showMsg('Please enter an issuance date.', 'error');
      return false;
    }
    value = numEl ? numEl.value.trim() : '';
    field = 'certificate number';
  } else if (docType === 'permit') {
    const el = document.getElementById('permitNumberInput');
    value = el ? el.value.trim() : '';
    field = 'permit number';
  }

  if (!value) {
    showMsg(`Please enter a valid ${field}.`, 'error');
    return false;
  }

  // Trigger DARI authentic loading spinner overlay
  const loader = document.getElementById('dariLoadingOverlay');
  if (loader) loader.classList.add('active');

  const docVerifyForm = document.getElementById('docVerifyForm');
  const verifyResultView = document.getElementById('verifyResultView');
  const verifyNotFoundView = document.getElementById('verifyNotFoundView');

  const searchVal = value.toLowerCase().trim();
  const notFoundKeywords = ['notfound', 'not_found', 'not-found', 'invalid', 'fail', 'error', '404', 'none'];
  const isExplicitNotFound = notFoundKeywords.some(k => searchVal.includes(k)) || 
                             searchVal === '0' || 
                             searchVal === '123' || 
                             searchVal === '9999999999' ||
                             searchVal === '1234567890';

  const docs = await getRegistry();
  
  // Find matching document by documentNumber, unitOrPlot, or exact id
  let matched = docs.find(d => 
    (d.documentNumber && d.documentNumber.toLowerCase() === searchVal) ||
    (d.unitOrPlot && d.unitOrPlot.toLowerCase() === searchVal) ||
    (d.id && d.id.toLowerCase() === searchVal)
  );

  // Fallback: search within string if length >= 4
  if (!matched && searchVal.length >= 4 && !isExplicitNotFound) {
    matched = docs.find(d => 
      (d.documentNumber && d.documentNumber.toLowerCase().includes(searchVal)) ||
      (d.partyName && d.partyName.toLowerCase().includes(searchVal))
    );
  }

  setTimeout(() => {
    if (loader) loader.classList.remove('active');
    if (docVerifyForm) docVerifyForm.style.display = 'none';

    if (!matched || isExplicitNotFound) {
      // Document Not Found
      if (verifyResultView) verifyResultView.style.display = 'none';
      if (verifyNotFoundView) {
        const nfIcon = document.getElementById('nfStatusIcon');
        const nfText = document.getElementById('nfStatusText');
        const nfDesc = document.getElementById('nfDetailsDesc');
        if (nfIcon) nfIcon.src = 'assets/refused.svg';
        if (nfText) nfText.textContent = 'Document not found';
        if (nfDesc) nfDesc.textContent = 'No registered document was found matching the entered reference number. Please check the contract or certificate number and try again.';
        verifyNotFoundView.style.display = 'flex';
        verifyNotFoundView.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
      recordAuditLog(value, docType, 'Not Found', 'Not Found', '-');
      ensureCleanUrl();
    } else if (matched.status !== 'Active') {
      // Document Found but Status is Inactive / Expired / Closed
      if (verifyResultView) verifyResultView.style.display = 'none';
      if (verifyNotFoundView) {
        const nfIcon = document.getElementById('nfStatusIcon');
        const nfText = document.getElementById('nfStatusText');
        const nfDesc = document.getElementById('nfDetailsDesc');
        if (nfIcon) nfIcon.src = 'assets/refused.svg';
        if (nfText) nfText.textContent = `${matched.type === 'tenancy' ? 'Tenancy contract' : 'Document'} is ${matched.status.toLowerCase()}`;
        if (nfDesc) {
          nfDesc.textContent = `The registered record (${matched.documentNumber}) for ${matched.partyName} is currently marked as ${matched.status}. Period: ${matched.startDate || '-'} to ${matched.endDate || '-'}. For inquiries, please contact the Abu Dhabi Real Estate Centre (ADREC).`;
        }
        verifyNotFoundView.style.display = 'flex';
        verifyNotFoundView.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
      recordAuditLog(value, docType, matched.status, matched.status, matched.partyName);
      ensureCleanUrl();
    } else {
      // Document Active & Verified
      if (verifyNotFoundView) verifyNotFoundView.style.display = 'none';
      if (verifyResultView) {
        const resIcon = document.getElementById('resStatusIcon');
        const resText = document.getElementById('resStatusText');
        const resUsageLabel = document.getElementById('resUsageLabel');
        const resUsageValue = document.getElementById('resUsageValue');
        const resStartDateValue = document.getElementById('resStartDateValue');
        const resEndDateValue = document.getElementById('resEndDateValue');
        const resPartyLabel = document.getElementById('resPartyLabel');
        const resPartyValue = document.getElementById('resPartyValue');
        const resUnitLabel = document.getElementById('resUnitLabel');
        const resUnitValue = document.getElementById('resUnitValue');

        if (resIcon) resIcon.src = 'assets/successIconV2.svg';
        if (resText) {
          resText.textContent = matched.type === 'tenancy' 
            ? 'Tenancy contract is active and verified' 
            : (matched.type === 'certificate' ? 'Title deed certificate is active and verified' : 'Real estate permit is active and verified');
        }
        if (resUsageLabel) resUsageLabel.textContent = matched.type === 'permit' ? 'Permit Type' : 'Actual usage type';
        if (resUsageValue) resUsageValue.textContent = matched.usageType || 'Residential';
        if (resStartDateValue) resStartDateValue.textContent = matched.startDate || '2026-02-01';
        if (resEndDateValue) resEndDateValue.textContent = matched.endDate || '2027-01-31';
        if (resPartyLabel) resPartyLabel.textContent = matched.type === 'tenancy' ? 'Tenant' : (matched.type === 'certificate' ? 'Owner / Beneficiary' : 'Permit Holder');
        if (resPartyValue) resPartyValue.textContent = matched.partyName || 'RANJITH SOURINGAL RAMACHANDRAN';
        if (resUnitLabel) resUnitLabel.textContent = matched.type === 'permit' ? 'Permit / Ad Reference' : (matched.type === 'certificate' ? 'Plot / Sector Reference' : 'Registered units');
        if (resUnitValue) resUnitValue.textContent = matched.unitOrPlot || matched.documentNumber;

        verifyResultView.style.display = 'flex';
        verifyResultView.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
      incrementVerificationCount(matched.id);
      recordAuditLog(value, docType, 'Verified', 'Active', matched.partyName);
      ensureCleanUrl();
    }
  }, isInstant ? 150 : 800);

  return false;
}

// Auto-fill and execute verification if navigated from Admin Dashboard "Test in Portal" or via direct QR code link
async function checkAutoVerify() {
  const autoNum = initialContractParam || localStorage.getItem('dari_auto_verify_number');
  if (!autoNum) return;

  if (localStorage.getItem('dari_auto_verify_number')) {
    localStorage.removeItem('dari_auto_verify_number');
  }

  const cleanNum = String(autoNum).trim();
  const docs = await getRegistry();
  const matched = docs.find(d => 
    (d.documentNumber && String(d.documentNumber).trim() === cleanNum) || 
    (d.id && String(d.id).trim() === cleanNum)
  );
  const docType = matched ? matched.type : 'tenancy';

  // Switch to corresponding tab
  const radio = document.querySelector(`.radio-item[data-type="${docType}"]`);
  if (radio) radio.click();

  // Populate input
  if (docType === 'tenancy') {
    const el = document.getElementById('tenancyNumberInput');
    if (el) el.value = cleanNum;
  } else if (docType === 'certificate') {
    const el = document.getElementById('certNumberInput');
    const select = document.getElementById('certTypeSelect');
    const dateInput = document.getElementById('certDateInput');
    if (el) el.value = cleanNum;
    if (select) select.selectedIndex = 1;
    if (dateInput) dateInput.value = matched?.startDate || '2025-01-15';
  } else if (docType === 'permit') {
    const el = document.getElementById('permitNumberInput');
    if (el) el.value = cleanNum;
  }

  // Execute verification immediately with instant rendering
  handleVerifySubmit({}, true);
}

function ensureCleanUrl() {
  if (!window.location.protocol.startsWith('http')) return;
  const target = '/en?app/verify-document';
  if (window.location.pathname + window.location.search !== target) {
    window.history.replaceState({}, '', target);
  }
}

function showMsg(html, type) {
  const alertEl = document.getElementById('statusAlert');
  if (!alertEl) return;
  alertEl.className = `verify-alert-msg ${type}`;
  alertEl.innerHTML = html;
  alertEl.style.display = 'block';
  alertEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function setupNav() {
  const bottomItems = document.querySelectorAll('.bottom-nav-item');
  bottomItems.forEach(item => {
    item.addEventListener('click', () => {
      bottomItems.forEach(i => i.classList.remove('active'));
      item.classList.add('active');
    });
  });

  const loginBtns = document.querySelectorAll('.btn-login');
  loginBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      window.location.href = '/admin';
    });
  });
}

function setupPopups() {
  const cookieBanner = document.getElementById('onetrust-consent-sdk');
  const btnAllowCookies = document.getElementById('btnAllowAllCookies');
  const btnManageCookies = document.getElementById('btnManageCookies');

  const mobileInterstitial = document.getElementById('mobileAppInterstitial');
  const btnContinueMobile = document.getElementById('btnContinueMobile');
  const btnDownloadApp = document.getElementById('btnDownloadApp');

  function dismissCookieBanner() {
    if (cookieBanner) {
      cookieBanner.classList.add('collapsed');
    }
  }

  if (btnAllowCookies) {
    btnAllowCookies.addEventListener('click', dismissCookieBanner);
  }
  if (btnManageCookies) {
    btnManageCookies.addEventListener('click', dismissCookieBanner);
  }

  // Mobile App Interstitial
  if (mobileInterstitial) {
    if (initialContractParam || document.documentElement.classList.contains('qr-mode')) {
      mobileInterstitial.classList.remove('active');
      mobileInterstitial.classList.add('dismissed');
      mobileInterstitial.style.display = 'none';
      return;
    }

    const isMobile = window.innerWidth <= 768 || /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent);
    const urlParams = new URLSearchParams(window.location.search);
    const forceInterstitial = urlParams.get('interstitial') === '1' || urlParams.get('app') === 'open';
    const isDismissed = sessionStorage.getItem('adrec_app_interstitial_dismissed') === 'true' && !forceInterstitial;

    if (isMobile && !isDismissed) {
      mobileInterstitial.classList.add('active');
      mobileInterstitial.classList.remove('dismissed');
    } else {
      mobileInterstitial.classList.remove('active');
      mobileInterstitial.classList.add('dismissed');
      mobileInterstitial.style.display = 'none';
    }

    if (btnContinueMobile) {
      btnContinueMobile.addEventListener('click', () => {
        sessionStorage.setItem('adrec_app_interstitial_dismissed', 'true');
        mobileInterstitial.classList.add('dismissed');
        mobileInterstitial.classList.remove('active');
      });
    }

    if (btnDownloadApp) {
      btnDownloadApp.addEventListener('click', () => {
        window.open('https://apps.apple.com/ae/app/dari/id1607496296', '_blank');
      });
    }
  }
}

function setupResultView() {
  const btnVerifyAnother = document.getElementById('btnVerifyAnother');
  const btnVerifyAnotherNotFound = document.getElementById('btnVerifyAnotherNotFound');
  const verifyResultView = document.getElementById('verifyResultView');
  const verifyNotFoundView = document.getElementById('verifyNotFoundView');
  const docVerifyForm = document.getElementById('docVerifyForm');

  if (!initialContractParam) {
    ensureCleanUrl();
  }

  function showForm() {
    if (verifyResultView) verifyResultView.style.display = 'none';
    if (verifyNotFoundView) verifyNotFoundView.style.display = 'none';
    if (docVerifyForm) {
      docVerifyForm.style.display = 'block';
      docVerifyForm.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    ensureCleanUrl();
  }

  if (btnVerifyAnother) {
    btnVerifyAnother.addEventListener('click', showForm);
  }

  if (btnVerifyAnotherNotFound) {
    btnVerifyAnotherNotFound.addEventListener('click', showForm);
  }

  // Header & footer "Verify Document" buttons
  const btnHeaderVerify = document.querySelector('.btn-header-verify');
  const btnFooterVerify = document.querySelector('.btn-footer-verify');
  [btnHeaderVerify, btnFooterVerify].forEach(btn => {
    if (btn) {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        showForm();
      });
    }
  });

  const closeSmartBanner = document.getElementById('closeSmartBanner');
  const smartAppBanner = document.getElementById('smartAppBanner');
  if (initialContractParam || document.documentElement.classList.contains('qr-mode')) {
    if (smartAppBanner) smartAppBanner.style.display = 'none';
  }
  if (closeSmartBanner && smartAppBanner) {
    closeSmartBanner.addEventListener('click', () => {
      smartAppBanner.style.display = 'none';
    });
  }

  // Ensure clean url on init only if no query param
  if (!initialContractParam) {
    ensureCleanUrl();
  }
}
