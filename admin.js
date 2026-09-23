/**
 * DARI / ADREC Document Verification Operations Center - Admin Controller
 * Multi-Delete Selection, Mobile-First UI & Settings / Credentials Management
 */

const STORAGE_KEY_DOCS = 'dari_registry_v1';
const STORAGE_KEY_AUDIT = 'dari_audit_log_v1';
const STORAGE_KEY_SETTINGS = 'dari_admin_settings_v1';
const SESSION_KEY_AUTH = 'dari_admin_session_v1';

let documents = [];
let auditLogs = [];
let adminSettings = {
  name: 'Regulatory Officer',
  role: 'System Admin',
  email: 'officer@adrec.gov.ae',
  passwordHash: 'admin123',
  auditLogging: true,
  publicPortalActive: true,
  defaultValidity: '1'
};

let currentFilterType = 'all';
let currentFilterStatus = 'all';
let currentSearchQuery = '';
let editingDocId = null;
let deletingDocId = null;

// Batch selection set
let selectedDocIds = new Set();

// Track which contract numbers have already been fully generated on the server.
// If a contract number is in this set, openContractModal() skips the loading
// screen entirely and renders pages instantly on every subsequent open.
const _generatedContracts = new Set();

// View mode: 'table' or 'cards'
let currentViewMode = window.innerWidth <= 768 ? 'cards' : 'table';

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', async () => {
  await loadData();
  loadSettings();
  setupAuthGuard();
  setupEventListeners();
  setupDocTabs();
  setupBatchActions();
  setupSettingsModal();
  setupContractModal();
  setupMobileNav();
  setupViewModeToggle();
  renderAll();
});

// Load documents, audit logs, and settings
async function loadData() {
  // Always fetch from server — never pre-load localStorage.
  // localStorage was causing deleted docs to flash back on every reload.
  try {
    const res = await fetch(`/api/documents?_t=${Date.now()}`, {
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache' }
    });
    if (res.ok) {
      const serverDocs = await res.json();
      if (Array.isArray(serverDocs)) {
        documents = serverDocs;
        localStorage.setItem(STORAGE_KEY_DOCS, JSON.stringify(documents));

        // Background: check which contracts are already generated server-side.
        documents.forEach(doc => {
          if (doc.documentNumber && !_generatedContracts.has(doc.documentNumber)) {
            fetch(`/api/contracts/${doc.documentNumber}/status`, { cache: 'no-store' })
              .then(r => r.ok ? r.json() : null)
              .then(data => { if (data && data.ready) _generatedContracts.add(doc.documentNumber); })
              .catch(() => {});
          }
        });
      }
    }
  } catch (e) {
    console.warn('Could not fetch /api/documents', e);
    // Only use localStorage as a last resort if server is completely unreachable
    const cachedDocs = localStorage.getItem(STORAGE_KEY_DOCS);
    if (cachedDocs) {
      try { documents = JSON.parse(cachedDocs); } catch (ex) {}
    }
  }

  try {
    const res = await fetch(`/api/audit?_t=${Date.now()}`, {
      cache: 'no-store',
      headers: { 'Cache-Control': 'no-cache' }
    });
    if (res.ok) {
      const serverAudit = await res.json();
      if (Array.isArray(serverAudit)) {
        auditLogs = serverAudit;
        localStorage.setItem(STORAGE_KEY_AUDIT, JSON.stringify(auditLogs));
      }
    }
  } catch (e) {
    console.warn('Could not fetch /api/audit', e);
    const cachedAudit = localStorage.getItem(STORAGE_KEY_AUDIT);
    if (cachedAudit) {
      try { auditLogs = JSON.parse(cachedAudit); } catch (ex) {}
    }
  }
}

function loadSettings() {
  const cached = localStorage.getItem(STORAGE_KEY_SETTINGS);
  if (cached) {
    try {
      adminSettings = { ...adminSettings, ...JSON.parse(cached) };
    } catch (e) {}
  }
  applySettingsToUI();
}

function saveSettings() {
  localStorage.setItem(STORAGE_KEY_SETTINGS, JSON.stringify(adminSettings));
  applySettingsToUI();
}

// ==================== QR UPLOAD HELPERS ====================
window.handleQrUpload = function(input, previewId, hiddenId) {
  const file = input.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (e) => {
    const b64 = e.target.result.split(',')[1]; // strip data URI prefix
    const preview = document.getElementById(previewId);
    const hidden = document.getElementById(hiddenId);
    if (preview) preview.src = e.target.result;
    if (hidden) hidden.value = b64;
  };
  reader.readAsDataURL(file);
};

window.clearQrUpload = function(previewId, fileInputId, hiddenId, defaultSrc) {
  const preview = document.getElementById(previewId);
  const fileInput = document.getElementById(fileInputId);
  const hidden = document.getElementById(hiddenId);
  if (preview) preview.src = defaultSrc + '?_t=' + Date.now();
  if (fileInput) fileInput.value = '';
  if (hidden) hidden.value = '';
};

function applySettingsToUI() {
  const navName = document.getElementById('navUserName');
  const navRole = document.getElementById('navUserRole');
  const navAvatar = document.getElementById('navAvatarInitials');

  if (navName) navName.textContent = adminSettings.name || 'Regulatory Officer';
  if (navRole) navRole.textContent = adminSettings.role || 'System Admin';
  if (navAvatar) {
    const initials = (adminSettings.name || 'AD')
      .split(' ')
      .map(w => w[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
    navAvatar.textContent = initials || 'AD';
  }
}

async function saveDocuments() {
  localStorage.setItem(STORAGE_KEY_DOCS, JSON.stringify(documents));
  try {
    const res = await fetch('/api/documents', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(documents)
    });
    return res.ok;
  } catch (err) {
    console.error('Failed to sync documents with server:', err);
    return false;
  }
}

async function saveAuditLogs() {
  localStorage.setItem(STORAGE_KEY_AUDIT, JSON.stringify(auditLogs));
  try {
    const res = await fetch('/api/audit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(auditLogs)
    });
    return res.ok;
  } catch (err) {
    console.error('Failed to sync audit logs with server:', err);
    return false;
  }
}

// Setup standard event listeners
function setupEventListeners() {
  // Search Input
  const searchInput = document.getElementById('searchRegistryInput');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      currentSearchQuery = e.target.value.trim().toLowerCase();
      renderRegistry();
    });
  }

  // Status Filter
  const statusFilter = document.getElementById('statusSelectFilter');
  if (statusFilter) {
    statusFilter.addEventListener('change', (e) => {
      currentFilterStatus = e.target.value;
      renderRegistry();
    });
  }

  // Tab Pills (All / Tenancy Contracts)
  const tabPills = document.querySelectorAll('.tab-pill');
  tabPills.forEach(pill => {
    pill.addEventListener('click', () => {
      tabPills.forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      currentFilterType = pill.getAttribute('data-type');
      renderRegistry();
    });
  });

  // Modal Open Buttons
  const btnAddDoc = document.getElementById('btnAddDocument');
  if (btnAddDoc) {
    btnAddDoc.addEventListener('click', () => openDocModal());
  }

  // Modal Close Buttons
  const btnCloseModal = document.getElementById('btnCloseDocModal');
  const btnCancelModal = document.getElementById('btnCancelDocModal');
  [btnCloseModal, btnCancelModal].forEach(btn => {
    if (btn) btn.addEventListener('click', closeDocModal);
  });

  // Modal Form Submit
  const form = document.getElementById('docEditForm');
  if (form) {
    form.addEventListener('submit', handleFormSubmit);
  }

  // Single Delete Modal Close
  const btnCloseDelete = document.getElementById('btnCloseDeleteModal');
  const btnCancelDelete = document.getElementById('btnCancelDeleteModal');
  [btnCloseDelete, btnCancelDelete].forEach(btn => {
    if (btn) btn.addEventListener('click', closeDeleteModal);
  });

  const btnConfirmDelete = document.getElementById('btnConfirmDelete');
  if (btnConfirmDelete) {
    btnConfirmDelete.addEventListener('click', handleConfirmDelete);
  }

  // Export CSV Button
  const btnExport = document.getElementById('btnExportCsv');
  if (btnExport) {
    btnExport.addEventListener('click', exportToCsv);
  }

  // Clear Audit Button
  const btnClearAudit = document.getElementById('btnClearAudit');
  if (btnClearAudit) {
    btnClearAudit.addEventListener('click', async () => {
      auditLogs = [];
      renderAuditLogs();
      showToast('Audit log stream cleared', 'success');
      await saveAuditLogs();
    });
  }

  // Close modals on overlay backdrop click
  window.addEventListener('click', (e) => {
    const docModal = document.getElementById('docModalOverlay');
    const deleteModal = document.getElementById('deleteModalOverlay');
    const batchModal = document.getElementById('batchDeleteModalOverlay');
    const settingsModal = document.getElementById('settingsModalOverlay');
    const contractModal = document.getElementById('contractModalOverlay');

    if (e.target === docModal) closeDocModal();
    if (e.target === deleteModal) closeDeleteModal();
    if (e.target === batchModal) closeBatchDeleteModal();
    if (e.target === settingsModal) closeSettingsModal();
    if (e.target === contractModal) closeContractModal();
  });
}

// ==================== AUTHENTICATION GUARD & LOGOUT CONTROLLER ====================
async function setupAuthGuard() {
  const btnLogoutNav = document.getElementById('btnLogoutNav');
  const btnLogoutSettings = document.getElementById('btnLogoutSettings');
  const btnNavLogout = document.getElementById('btnNavLogout');

  async function checkAuth() {
    try {
      const res = await fetch('/api/auth/me');
      if (!res.ok) {
        window.location.href = '/login';
        return;
      }
      const data = await res.json();
      if (!data || data.status !== 'success') {
        window.location.href = '/login';
        return;
      }
      if (data.user) {
        adminSettings.name = data.user.name || adminSettings.name;
        adminSettings.role = data.user.role || adminSettings.role;
        adminSettings.email = data.user.email || adminSettings.email;
        applySettingsToUI();
      }
    } catch (e) {
      const isAuthed = sessionStorage.getItem(SESSION_KEY_AUTH) === 'active';
      if (!isAuthed) {
        window.location.href = '/login';
      }
    }
  }

  [btnLogoutNav, btnLogoutSettings, btnNavLogout].forEach(btn => {
    if (btn) {
      btn.addEventListener('click', handleLogout);
    }
  });

  await checkAuth();
}

async function handleLogout() {
  sessionStorage.removeItem(SESSION_KEY_AUTH);
  sessionStorage.removeItem('dari_session_token');
  document.cookie = 'adrec_session=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
  try {
    await fetch('/api/auth/logout', { method: 'POST' });
  } catch (e) {}
  window.location.href = '/login';
}

// ==================== DOCUMENT FORM (SINGLE PAGE LAYOUT) ====================
function setupDocTabs() {
  // All sections are now displayed on a single page without tab switching
}

// Setup View Mode Toggle (Table / Cards)
function setupViewModeToggle() {
  const sectionRegistry = document.getElementById('sectionRegistry');
  const viewModeButtons = document.querySelectorAll('.btn-view-mode');

  function applyViewMode(mode) {
    currentViewMode = mode;
    if (sectionRegistry) {
      if (mode === 'cards') {
        sectionRegistry.classList.add('cards-active');
      } else {
        sectionRegistry.classList.remove('cards-active');
      }
    }
    viewModeButtons.forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-mode') === mode);
    });
    renderRegistry();
  }

  viewModeButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      applyViewMode(btn.getAttribute('data-mode'));
    });
  });

  // Apply default based on initial screen width
  if (window.innerWidth <= 768) {
    currentViewMode = 'cards';
  }
  applyViewMode(currentViewMode);

  // Auto-switch view mode on window resize if crossing 768px boundary
  let prevWidth = window.innerWidth;
  window.addEventListener('resize', () => {
    const nowWidth = window.innerWidth;
    if (prevWidth > 768 && nowWidth <= 768) {
      applyViewMode('cards');
    } else if (prevWidth <= 768 && nowWidth > 768) {
      applyViewMode('table');
    }
    prevWidth = nowWidth;
  });
}

// ==================== BATCH SELECTION & ACTIONS ====================
function setupBatchActions() {
  const selectAll = document.getElementById('selectAllCheckbox');
  if (selectAll) {
    selectAll.addEventListener('change', (e) => {
      const filtered = getFilteredDocuments();
      if (e.target.checked) {
        filtered.forEach(doc => selectedDocIds.add(doc.id));
      } else {
        filtered.forEach(doc => selectedDocIds.delete(doc.id));
      }
      updateBatchBar();
      renderRegistry();
    });
  }

  // Batch action buttons
  const btnBatchDelete = document.getElementById('btnBatchDelete');
  if (btnBatchDelete) {
    btnBatchDelete.addEventListener('click', openBatchDeleteModal);
  }

  const btnBatchActive = document.getElementById('btnBatchActive');
  if (btnBatchActive) {
    btnBatchActive.addEventListener('click', () => batchUpdateStatus('Active'));
  }

  const btnBatchExpire = document.getElementById('btnBatchExpire');
  if (btnBatchExpire) {
    btnBatchExpire.addEventListener('click', () => batchUpdateStatus('Expired'));
  }

  const btnBatchDeselect = document.getElementById('btnBatchDeselect');
  if (btnBatchDeselect) {
    btnBatchDeselect.addEventListener('click', () => {
      selectedDocIds.clear();
      updateBatchBar();
      renderRegistry();
    });
  }

  // Batch Delete Modal
  const btnCloseBatchModal = document.getElementById('btnCloseBatchDeleteModal');
  const btnCancelBatchModal = document.getElementById('btnCancelBatchDelete');
  [btnCloseBatchModal, btnCancelBatchModal].forEach(btn => {
    if (btn) btn.addEventListener('click', closeBatchDeleteModal);
  });

  const btnConfirmBatch = document.getElementById('btnConfirmBatchDelete');
  if (btnConfirmBatch) {
    btnConfirmBatch.addEventListener('click', handleConfirmBatchDelete);
  }
}

function handleRowCheckboxChange(docId, checked) {
  if (checked) {
    selectedDocIds.add(docId);
  } else {
    selectedDocIds.delete(docId);
  }
  updateBatchBar();
  updateSelectAllState();
}

function updateSelectAllState() {
  const selectAll = document.getElementById('selectAllCheckbox');
  if (!selectAll) return;

  const filtered = getFilteredDocuments();
  if (filtered.length === 0) {
    selectAll.checked = false;
    selectAll.indeterminate = false;
    return;
  }

  const countSelected = filtered.filter(doc => selectedDocIds.has(doc.id)).length;

  if (countSelected === 0) {
    selectAll.checked = false;
    selectAll.indeterminate = false;
  } else if (countSelected === filtered.length) {
    selectAll.checked = true;
    selectAll.indeterminate = false;
  } else {
    selectAll.checked = false;
    selectAll.indeterminate = true;
  }
}

function updateBatchBar() {
  const bar = document.getElementById('batchActionsBar');
  const countPill = document.getElementById('batchSelectedCount');
  if (!bar || !countPill) return;

  const count = selectedDocIds.size;
  countPill.textContent = count;

  if (count > 0) {
    bar.classList.add('active');
  } else {
    bar.classList.remove('active');
  }
}

function openBatchDeleteModal() {
  if (selectedDocIds.size === 0) return;
  const modal = document.getElementById('batchDeleteModalOverlay');
  const countLabel = document.getElementById('batchDeleteCountLabel');
  const previewBox = document.getElementById('batchDeletePreviewBox');
  if (!modal || !countLabel || !previewBox) return;

  countLabel.textContent = selectedDocIds.size;

  const selectedDocs = documents.filter(d => selectedDocIds.has(d.id));
  previewBox.innerHTML = selectedDocs.map(doc => `
    <span class="batch-tag-item">
      <span>${escapeHtml(doc.documentNumber)}</span>
      <small style="color: var(--text-dim); font-weight: 400;">(${escapeHtml(doc.partyName || '')})</small>
    </span>
  `).join('');

  modal.classList.add('active');
}

function closeBatchDeleteModal() {
  const modal = document.getElementById('batchDeleteModalOverlay');
  if (modal) modal.classList.remove('active');
}

async function handleConfirmBatchDelete() {
  const count = selectedDocIds.size;
  const idsToDelete = [...selectedDocIds];

  // Remove from in-memory array and localStorage immediately
  idsToDelete.forEach(id => {
    const d = documents.find(doc => doc.id === id);
    if (d && d.documentNumber) _generatedContracts.delete(d.documentNumber);
  });
  documents = documents.filter(doc => !selectedDocIds.has(doc.id));
  selectedDocIds.clear();
  localStorage.setItem(STORAGE_KEY_DOCS, JSON.stringify(documents));

  renderAll();
  closeBatchDeleteModal();
  updateBatchBar();
  showToast(`Successfully deleted ${count} documents from registry`, 'success');

  // Fire DELETE for each doc in parallel — atomic per-record DB deletes
  try {
    await Promise.all(
      idsToDelete.map(id =>
        fetch(`/api/documents/${encodeURIComponent(id)}`, { method: 'DELETE' })
          .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status} for ${id}`); })
      )
    );
  } catch (err) {
    console.error('Batch delete partial failure, re-syncing full list:', err);
    await saveDocuments(); // fallback: full sync
  }
}

function batchUpdateStatus(status) {
  if (selectedDocIds.size === 0) return;

  const count = selectedDocIds.size;
  const now = new Date().toISOString();

  documents.forEach(doc => {
    if (selectedDocIds.has(doc.id)) {
      doc.status = status;
      doc.updatedAt = now;
    }
  });

  saveDocuments();
  renderAll();
  showToast(`Marked ${count} documents as ${status}`, 'success');
}

// ==================== SETTINGS & CREDENTIALS CONTROLLER ====================
function setupSettingsModal() {
  const btnOpen = document.getElementById('btnOpenSettings');
  const btnUserPill = document.getElementById('btnUserPill');
  const modal = document.getElementById('settingsModalOverlay');
  const btnClose = document.getElementById('btnCloseSettingsModal');
  const btnCancel = document.getElementById('btnCancelSettingsModal');
  const form = document.getElementById('settingsForm');

  function openSettings() {
    // Populate form with current settings
    document.getElementById('settingDisplayName').value = adminSettings.name || '';
    document.getElementById('settingEmail').value = adminSettings.email || '';
    document.getElementById('settingRole').value = adminSettings.role || '';
    document.getElementById('settingCurrentPassword').value = '';
    document.getElementById('settingNewPassword').value = '';
    document.getElementById('settingConfirmPassword').value = '';
    document.getElementById('settingAuditLogging').checked = adminSettings.auditLogging !== false;
    document.getElementById('settingPublicPortalActive').checked = adminSettings.publicPortalActive !== false;
    document.getElementById('settingDefaultValidity').value = adminSettings.defaultValidity || '1';

    resetPasswordStrength();
    if (modal) modal.classList.add('active');
  }

  if (btnOpen) btnOpen.addEventListener('click', openSettings);
  if (btnUserPill) btnUserPill.addEventListener('click', openSettings);
  if (btnClose) btnClose.addEventListener('click', closeSettingsModal);
  if (btnCancel) btnCancel.addEventListener('click', closeSettingsModal);

  // Settings Tabs
  const tabs = document.querySelectorAll('.settings-tab-btn');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const targetId = tab.getAttribute('data-tab');
      document.querySelectorAll('.settings-tab-pane').forEach(p => p.classList.remove('active'));
      const targetPane = document.getElementById(targetId);
      if (targetPane) targetPane.classList.add('active');
    });
  });

  // Show/Hide Password Eye Buttons
  document.querySelectorAll('.btn-toggle-password').forEach(btn => {
    btn.addEventListener('click', () => {
      const inputId = btn.getAttribute('data-target');
      const input = document.getElementById(inputId);
      if (input) {
        if (input.type === 'password') {
          input.type = 'text';
          btn.textContent = '🔒';
        } else {
          input.type = 'password';
          btn.textContent = '👁️';
        }
      }
    });
  });

  // Password Strength Meter
  const newPwdInp = document.getElementById('settingNewPassword');
  if (newPwdInp) {
    newPwdInp.addEventListener('input', (e) => {
      evaluatePasswordStrength(e.target.value);
    });
  }

  // Form Submit
  if (form) {
    form.addEventListener('submit', handleSettingsSubmit);
  }
}

function closeSettingsModal() {
  const modal = document.getElementById('settingsModalOverlay');
  if (modal) modal.classList.remove('active');
}

function evaluatePasswordStrength(val) {
  const bar = document.getElementById('pwdStrengthFill');
  const label = document.getElementById('pwdStrengthLabel');
  if (!bar || !label) return;

  if (!val) {
    resetPasswordStrength();
    return;
  }

  let score = 0;
  if (val.length >= 6) score += 25;
  if (val.length >= 10) score += 25;
  if (/[A-Z]/.test(val)) score += 20;
  if (/[0-9]/.test(val)) score += 15;
  if (/[^A-Za-z0-9]/.test(val)) score += 15;

  bar.style.width = score + '%';

  if (score < 40) {
    bar.style.backgroundColor = 'var(--adrec-red)';
    label.textContent = 'Weak password (must be at least 6 characters)';
  } else if (score < 75) {
    bar.style.backgroundColor = 'var(--adrec-amber)';
    label.textContent = 'Medium password strength';
  } else {
    bar.style.backgroundColor = 'var(--adrec-green-main)';
    label.textContent = 'Strong password';
  }
}

function resetPasswordStrength() {
  const bar = document.getElementById('pwdStrengthFill');
  const label = document.getElementById('pwdStrengthLabel');
  if (bar) {
    bar.style.width = '0%';
    bar.style.backgroundColor = 'var(--adrec-red)';
  }
  if (label) {
    label.textContent = 'Enter a new password to check strength';
  }
}

function handleSettingsSubmit(e) {
  e.preventDefault();

  const name = document.getElementById('settingDisplayName').value.trim();
  const email = document.getElementById('settingEmail').value.trim();
  const role = document.getElementById('settingRole').value.trim();
  const currentPwd = document.getElementById('settingCurrentPassword').value;
  const newPwd = document.getElementById('settingNewPassword').value;
  const confirmPwd = document.getElementById('settingConfirmPassword').value;
  const auditLogging = document.getElementById('settingAuditLogging').checked;
  const publicPortalActive = document.getElementById('settingPublicPortalActive').checked;
  const defaultValidity = document.getElementById('settingDefaultValidity').value;

  if (!name || !email) {
    showToast('Name and email are required', 'error');
    return;
  }

  // Handle password change if specified
  if (newPwd || confirmPwd || currentPwd) {
    const activeStoredHash = adminSettings.passwordHash || 'admin123';
    if (currentPwd !== activeStoredHash) {
      showToast('Current password incorrect', 'error');
      return;
    }
    if (newPwd.length < 6) {
      showToast('New password must be at least 6 characters', 'error');
      return;
    }
    if (newPwd !== confirmPwd) {
      showToast('New passwords do not match', 'error');
      return;
    }
    adminSettings.passwordHash = newPwd;
  }

  adminSettings.name = name;
  adminSettings.email = email;
  adminSettings.role = role;
  adminSettings.auditLogging = auditLogging;
  adminSettings.publicPortalActive = publicPortalActive;
  adminSettings.defaultValidity = defaultValidity;

  saveSettings();
  closeSettingsModal();
  showToast('Settings and credentials updated successfully', 'success');
}

// ==================== MOBILE BOTTOM NAVIGATION & VIEW SWITCHING ====================
function setupMobileNav() {
  const btnNavDashboard = document.getElementById('btnNavDashboard');
  const btnNavRegistry = document.getElementById('btnNavRegistry');
  const btnNavAddDoc = document.getElementById('btnNavAddDoc');
  const btnNavSettings = document.getElementById('btnNavSettings');
  const btnGoToRegistry = document.getElementById('btnGoToRegistry');
  const dashCardTenancy = document.getElementById('dashCardTenancy');

  function setMobileView(viewName, filterType) {
    document.body.classList.remove('mobile-view-dashboard', 'mobile-view-registry');
    document.body.classList.add(`mobile-view-${viewName}`);

    if (btnNavDashboard) btnNavDashboard.classList.toggle('active', viewName === 'dashboard');
    if (btnNavRegistry) btnNavRegistry.classList.toggle('active', viewName === 'registry');

    if (filterType) {
      currentFilterType = filterType;
      document.querySelectorAll('.tab-pill').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-type') === filterType);
      });
      renderRegistry();
    }

    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // Initial mobile view is Dashboard only
  document.body.classList.add('mobile-view-dashboard');

  if (btnNavDashboard) {
    btnNavDashboard.addEventListener('click', () => setMobileView('dashboard'));
  }

  if (btnNavRegistry) {
    btnNavRegistry.addEventListener('click', () => setMobileView('registry'));
  }

  if (btnGoToRegistry) {
    btnGoToRegistry.addEventListener('click', () => setMobileView('registry'));
  }

  if (dashCardTenancy) {
    dashCardTenancy.addEventListener('click', () => setMobileView('registry', 'tenancy'));
  }

  if (btnNavAddDoc) {
    btnNavAddDoc.addEventListener('click', () => openDocModal());
  }

  if (btnNavSettings) {
    btnNavSettings.addEventListener('click', () => {
      const btnOpen = document.getElementById('btnOpenSettings');
      if (btnOpen) btnOpen.click();
    });
  }
}

// ==================== RENDER PIPELINES ====================
function renderAll() {
  renderKPIs();
  renderRegistry();
  renderAuditLogs();
}

function renderKPIs() {
  const totalDocs = documents.length;
  const activeDocs = documents.filter(d => d.status === 'Active').length;
  const inactiveDocs = documents.filter(d => ['Expired', 'Closed', 'Cancelled', 'Terminate'].includes(d.status)).length;
  const totalInquiries = auditLogs.length;

  const tenancyCount = documents.filter(d => d.type === 'tenancy' || !d.type).length;

  const elTotal = document.getElementById('kpiTotalDocs');
  const elActive = document.getElementById('kpiActiveDocs');
  const elInactive = document.getElementById('kpiInactiveDocs');
  const elInquiries = document.getElementById('kpiTotalInquiries');

  const elDashTenancy = document.getElementById('dashCountTenancy');

  if (elTotal) elTotal.textContent = totalDocs.toLocaleString();
  if (elActive) elActive.textContent = activeDocs.toLocaleString();
  if (elInactive) elInactive.textContent = inactiveDocs.toLocaleString();
  if (elInquiries) elInquiries.textContent = totalInquiries.toLocaleString();

  if (elDashTenancy) elDashTenancy.textContent = tenancyCount.toLocaleString();
}

function getFilteredDocuments() {
  return documents.filter(doc => {
    // Type filter
    if (currentFilterType !== 'all' && doc.type !== currentFilterType) {
      return false;
    }
    // Status filter
    if (currentFilterStatus !== 'all' && doc.status !== currentFilterStatus) {
      return false;
    }
    // Search query
    if (currentSearchQuery) {
      const numMatch = (doc.documentNumber || '').toLowerCase().includes(currentSearchQuery);
      const partyMatch = (doc.partyName || '').toLowerCase().includes(currentSearchQuery);
      const unitMatch = (doc.unitOrPlot || '').toLowerCase().includes(currentSearchQuery);
      const usageMatch = (doc.usageType || '').toLowerCase().includes(currentSearchQuery);
      if (!numMatch && !partyMatch && !unitMatch && !usageMatch) {
        return false;
      }
    }
    return true;
  });
}

function renderRegistry() {
  renderTable();
  renderMobileCards();
  updateSelectAllState();
}

// Render Desktop/Tablet Data Table
function renderTable() {
  const tbody = document.getElementById('registryTableBody');
  if (!tbody) return;

  const filtered = getFilteredDocuments();

  if (filtered.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="9" class="empty-state-row">
          <div class="empty-state-box">
            <svg viewBox="0 0 24 24"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V5h14v14zM7 10h2v7H7zm4-3h2v10h-2zm4 6h2v4h-2z"/></svg>
            <p>No registered documents found matching the filter criteria.</p>
          </div>
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = filtered.map(doc => {
    const isSelected = selectedDocIds.has(doc.id);
    const statusClass = (doc.status || 'Active').toLowerCase();
    const typeLabel = 'Tenancy Contract';
    const period = doc.startDate && doc.endDate ? `${doc.startDate} &rarr; ${doc.endDate}` : '-';

    return `
      <tr data-id="${escapeHtml(doc.id)}" class="${isSelected ? 'selected' : ''}">
        <td class="col-checkbox">
          <input type="checkbox" class="custom-checkbox doc-row-checkbox" value="${escapeHtml(doc.id)}" ${isSelected ? 'checked' : ''} onchange="handleRowCheckboxChange('${escapeHtml(doc.id)}', this.checked)">
        </td>
        <td>
          <div class="doc-ref-cell">
            <span class="doc-ref-num">${escapeHtml(doc.documentNumber)}</span>
          </div>
        </td>
        <td>
          <span class="doc-type-badge">${escapeHtml(typeLabel)}</span>
        </td>
        <td>
          <div class="party-name-cell" title="${escapeHtml(doc.partyName || '-')}">
            <span class="party-real-name">${escapeHtml(doc.partyName || '-')}</span>
          </div>
        </td>
        <td>
          <div class="contact-num-cell">
            <span class="contact-phone-badge">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M6.62 10.79c1.44 2.83 3.76 5.14 6.59 6.59l2.2-2.2c.27-.27.67-.36 1.02-.24 1.12.37 2.33.57 3.57.57.55 0 1 .45 1 1V20c0 .55-.45 1-1 1-9.39 0-17-7.61-17-17 0-.55.45-1 1-1h3.5c.55 0 1 .45 1 1 0 1.25.2 2.45.57 3.57.11.35.03.74-.25 1.02l-2.2 2.2z"/></svg>
              ${escapeHtml(doc.tenantMobile || doc.contactMobile || doc.lessorMobile || '-')}
            </span>
          </div>
        </td>
        <td>
          <span class="unit-plot-cell">${escapeHtml(doc.unitOrPlot || '-')}</span>
        </td>
        <td>
          <span class="date-period-cell">${period}</span>
        </td>
        <td>
          <span class="status-badge ${statusClass}">${escapeHtml(doc.status)}</span>
        </td>
        <td>
          <div class="table-actions-cell">
            ${doc.type === 'tenancy' ? `
              <button class="btn-icon-action contract" title="Generate & View Official 9-Page Contract" onclick="openContractModal('${escapeHtml(doc.id)}')">
                <svg viewBox="0 0 24 24"><path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/></svg>
              </button>
            ` : ''}
            <button class="btn-icon-action test" title="Test in Public Verification Portal" onclick="testInPortal('${escapeHtml(doc.documentNumber)}')">
              <svg viewBox="0 0 24 24"><path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/></svg>
            </button>
            <button class="btn-icon-action" title="Edit Document" onclick="openDocModal('${escapeHtml(doc.id)}')">
              <svg viewBox="0 0 24 24"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>
            </button>
            <button class="btn-icon-action delete" title="Delete Document" onclick="openDeleteModal('${escapeHtml(doc.id)}')">
              <svg viewBox="0 0 24 24"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

// Render Mobile Document Cards
function renderMobileCards() {
  const container = document.getElementById('mobileDocCardsList');
  if (!container) return;

  const filtered = getFilteredDocuments();

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="empty-state-box" style="padding: 30px 16px;">
        <p style="font-size: 13px; color: var(--text-muted);">No documents found matching the filter criteria.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = filtered.map(doc => {
    const isSelected = selectedDocIds.has(doc.id);
    const statusClass = (doc.status || 'Active').toLowerCase();
    const typeLabel = 'Tenancy Contract';
    const period = doc.startDate && doc.endDate ? `${doc.startDate} &rarr; ${doc.endDate}` : '-';

    return `
      <div class="mobile-doc-card ${isSelected ? 'selected' : ''}" data-id="${escapeHtml(doc.id)}">
        <div class="mobile-card-top">
          <div class="mobile-card-left">
            <input type="checkbox" class="custom-checkbox doc-row-checkbox" value="${escapeHtml(doc.id)}" ${isSelected ? 'checked' : ''} onchange="handleRowCheckboxChange('${escapeHtml(doc.id)}', this.checked)">
            <span class="mobile-card-ref">${escapeHtml(doc.documentNumber)}</span>
          </div>
          <span class="status-badge ${statusClass}">${escapeHtml(doc.status)}</span>
        </div>

        <div class="mobile-card-body">
          <div class="mobile-card-party">${escapeHtml(doc.partyName || '-')}</div>
          <div class="mobile-card-contact">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M6.62 10.79c1.44 2.83 3.76 5.14 6.59 6.59l2.2-2.2c.27-.27.67-.36 1.02-.24 1.12.37 2.33.57 3.57.57.55 0 1 .45 1 1V20c0 .55-.45 1-1 1-9.39 0-17-7.61-17-17 0-.55.45-1 1-1h3.5c.55 0 1 .45 1 1 0 1.25.2 2.45.57 3.57.11.35.03.74-.25 1.02l-2.2 2.2z"/></svg>
            <span>${escapeHtml(doc.tenantMobile || doc.contactMobile || doc.lessorMobile || '-')}</span>
          </div>
          <div class="mobile-card-meta">
            <span class="doc-type-badge">${escapeHtml(typeLabel)}</span>
            <span class="mobile-card-meta-item">📍 ${escapeHtml(doc.unitOrPlot || '-')}</span>
            <span class="mobile-card-meta-item">🗓️ ${period}</span>
          </div>
        </div>

        <div class="mobile-card-actions">
          ${doc.type === 'tenancy' ? `
            <button type="button" class="btn-mobile-action contract" onclick="openContractModal('${escapeHtml(doc.id)}')">
              <svg viewBox="0 0 24 24"><path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/></svg>
              <span>PDF</span>
            </button>
          ` : ''}
          <button type="button" class="btn-mobile-action test" onclick="testInPortal('${escapeHtml(doc.documentNumber)}')">
            <svg viewBox="0 0 24 24"><path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/></svg>
            <span>Test</span>
          </button>
          <button type="button" class="btn-mobile-action" onclick="openDocModal('${escapeHtml(doc.id)}')">
            <svg viewBox="0 0 24 24"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>
            <span>Edit</span>
          </button>
          <button type="button" class="btn-mobile-action delete" onclick="openDeleteModal('${escapeHtml(doc.id)}')">
            <svg viewBox="0 0 24 24"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
            <span>Delete</span>
          </button>
        </div>
      </div>
    `;
  }).join('');
}

// Render Audit Logs
function renderAuditLogs() {
  const tbody = document.getElementById('auditTableBody');
  if (!tbody) return;

  if (auditLogs.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" class="empty-state-row">
          <div class="empty-state-box">
            <p>No verification inquiries logged yet.</p>
          </div>
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = auditLogs.map(item => {
    const formattedDate = new Date(item.timestamp).toLocaleString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });

    const statusPillClass = item.result === 'Verified' ? 'verified' : (item.result === 'Not Found' ? 'not-found' : 'expired');

    return `
      <tr>
        <td style="font-size: 11.5px; color: var(--text-dim); white-space: nowrap;">${escapeHtml(formattedDate)}</td>
        <td style="font-weight: 700; color: var(--adrec-green-dark);">${escapeHtml(item.documentNumber)}</td>
        <td><span class="doc-type-badge">${escapeHtml(item.documentType || '-')}</span></td>
        <td><span class="audit-status-pill ${statusPillClass}">${escapeHtml(item.result)}</span></td>
        <td style="font-weight: 500;">${escapeHtml(item.partyName || '-')}</td>
        <td style="font-size: 11.5px; color: var(--text-muted);">${escapeHtml(item.ip || '127.0.0.1')} &bull; ${escapeHtml(item.device || 'Browser')}</td>
      </tr>
    `;
  }).join('');
}

// ==================== DOCUMENT CRUD MODAL ====================
function openDocModal(id = null) {
  editingDocId = id;
  const modal = document.getElementById('docModalOverlay');
  const title = document.getElementById('docModalTitle');
  const form = document.getElementById('docEditForm');
  if (!modal || !form) return;

  form.reset();

  // Reset QR previews to defaults
  const tntPrev = document.getElementById('tenantQrPreview');
  const lsrPrev = document.getElementById('lessorQrPreview');
  const tntB64 = document.getElementById('tenantQrB64');
  const lsrB64 = document.getElementById('lessorQrB64');
  if (tntPrev) tntPrev.src = '/api/contracts/default-qr/tenant';
  if (lsrPrev) lsrPrev.src = '/api/contracts/default-qr/lessor';
  if (tntB64) tntB64.value = '';
  if (lsrB64) lsrB64.value = '';

  const modalBody = modal.querySelector('.doc-modal-body');
  if (modalBody) modalBody.scrollTop = 0;

  const setVal = (elemId, val) => {
    const el = document.getElementById(elemId);
    if (el) el.value = (val !== undefined && val !== null) ? val : '';
  };

  if (id) {
    const doc = documents.find(d => d.id === id);
    if (!doc) return;
    title.textContent = `Edit Contract (${doc.documentNumber})`;

    // 1. Contract Details
    setVal('formDocNumber', doc.documentNumber || '');
    setVal('formIssueDate', doc.issueDate || doc.startDate || '');
    setVal('formStartDate', doc.startDate || '');
    setVal('formEndDate', doc.endDate || '');
    setVal('formAnnualRent', doc.annualRent || '');
    setVal('formContractValue', doc.contractValue || doc.annualRent || '');
    setVal('formSecurityDeposit', doc.securityDeposit || '');
    setVal('formStatus', doc.status || 'Active');

    // 2. Lessor
    setVal('formLessorCompanyEn', doc.lessorCompanyEn || '');
    setVal('formLessorCompanyAr', doc.lessorCompanyAr || '');
    setVal('formLessorLicenseNo', doc.lessorLicenseNo || '');
    setVal('formLessorMobile', doc.lessorMobile || '');
    setVal('formLessorEmail', doc.lessorEmail || '');
    setVal('formLessorContactEn', doc.lessorContactEn || '');
    setVal('formLessorContactAr', doc.lessorContactAr || '');
    setVal('formContactMobile', doc.contactMobile || doc.lessorContactMobile || '');
    setVal('formContactEmail', doc.contactEmail || doc.lessorContactEmail || '');

    // 3. Tenant
    setVal('formPartyName', doc.partyName || doc.tenantNameEn || '');
    setVal('formTenantNameAr', doc.tenantNameAr || '');
    setVal('formTenantEmiratesId', doc.tenantEmiratesId || '');
    setVal('formTenantMobile', doc.tenantMobile || '');
    setVal('formTenantNationalityEn', doc.tenantNationalityEn || '');
    setVal('formTenantNationalityAr', doc.tenantNationalityAr || '');
    setVal('formTenantEmail', doc.tenantEmail || '');

    // 4. Unit
    setVal('formPremiseNo', doc.premiseNo || '');
    setVal('formUnitPlot', doc.unitOrPlot || doc.unitNo || '');
    setVal('formUnitRegNo', doc.unitRegNo || '');
    setVal('formNoOfRooms', doc.noOfRooms || '');
    setVal('formArea', doc.area || '');
    setVal('formUnitUsageEn', doc.unitUsageEn || '');
    setVal('formUnitUsageAr', doc.unitUsageAr || '');
    setVal('formUnitTypeEn', doc.unitTypeEn || '');
    setVal('formUnitTypeAr', doc.unitTypeAr || '');

    // 5. Occupants
    setVal('formOccupantName', doc.occupantName || doc.partyName || doc.tenantNameEn || '');
    setVal('formOccupantNameAr', doc.occupantNameAr || doc.tenantNameAr || '');
    setVal('formOccupantEmiratesId', doc.occupantEmiratesId || doc.tenantEmiratesId || '');

    // Restore saved QR previews if any
    const savedQr = doc.signatureQR || {};
    if (savedQr.tenantQR && tntPrev) {
      tntPrev.src = `data:image/png;base64,${savedQr.tenantQR}`;
      if (tntB64) tntB64.value = savedQr.tenantQR;
    }
    if (savedQr.lessorQR && lsrPrev) {
      lsrPrev.src = `data:image/png;base64,${savedQr.lessorQR}`;
      if (lsrB64) lsrB64.value = savedQr.lessorQR;
    }
  } else {
    // New document
    title.textContent = 'Register Document';
    // Auto-fill today's date as issue date
    const today = new Date().toISOString().slice(0, 10);
    setVal('formIssueDate', today);
  }

  // Live: as contract number changes, auto-sync issue date (today) and contract value = annual rent
  const docNumInput = document.getElementById('formDocNumber');
  const annualRentInput = document.getElementById('formAnnualRent');
  const contractValueInput = document.getElementById('formContractValue');

  if (docNumInput && !docNumInput._autoFillBound) {
    docNumInput._autoFillBound = true;
    docNumInput.addEventListener('input', () => {
      if (!id) { // only for new docs
        const todayVal = new Date().toISOString().slice(0, 10);
        const issueDateEl = document.getElementById('formIssueDate');
        if (issueDateEl && !issueDateEl.value) issueDateEl.value = todayVal;
      }
    });
  }
  if (annualRentInput && contractValueInput && !annualRentInput._syncBound) {
    annualRentInput._syncBound = true;
    annualRentInput.addEventListener('input', () => {
      if (!contractValueInput.value) contractValueInput.value = annualRentInput.value;
    });
  }

  modal.classList.add('active');
}

function closeDocModal() {
  const modal = document.getElementById('docModalOverlay');
  if (modal) modal.classList.remove('active');
  editingDocId = null;
}

async function handleFormSubmit(e) {
  e.preventDefault();

  const getVal = (elemId) => {
    const el = document.getElementById(elemId);
    return el ? el.value.trim() : '';
  };

  // 1. Contract Details — defaults from Gohar Ali Irshad Muhammad official PDF
  const docNumber = getVal('formDocNumber') || '202401451594';
  const issueDate = getVal('formIssueDate') || '2026-02-20';
  const startDate = getVal('formStartDate') || '2026-03-16';
  const endDate = getVal('formEndDate') || '2027-03-15';
  const annualRent = getVal('formAnnualRent') || '43,000.00';
  const contractValue = getVal('formContractValue') || annualRent || '43,000.00';
  const securityDeposit = getVal('formSecurityDeposit') || '___';
  const status = getVal('formStatus') || 'Active';

  // 2. First Party / Lessor Details (Page 1) — defaults from official contract template
  const lessorCompanyEn = getVal('formLessorCompanyEn') || 'INTERNATIONAL CONSTRUCTION CONTRACTING LLC';
  const lessorCompanyAr = getVal('formLessorCompanyAr') || 'شركة انترناشونال للمقاولات الانشائية ذ.م.م';
  const lessorLicenseNo = getVal('formLessorLicenseNo') || 'CN-1048007';
  const lessorMobile = getVal('formLessorMobile') || '-';
  const lessorEmail = getVal('formLessorEmail') || '-';
  const lessorContactEn = getVal('formLessorContactEn') || 'SHINE PILLAI HARIDASAN PILLAI SANTHA KUMARI';
  const lessorContactAr = getVal('formLessorContactAr') || 'شاين بيلاي هاريداسان بيلاي سانثا كوماري';
  const contactMobile = getVal('formContactMobile') || '971588973810';
  const contactEmail = getVal('formContactEmail') || 'shinepillaihs@gmail.com';

  // 3. Second Party / Tenant Details — defaults from Gohar Ali PDF
  const partyName = getVal('formPartyName') || 'Gohar Ali Irshad Muhammad';
  const tenantNameAr = getVal('formTenantNameAr') || 'جوهر على ارشاد محمد';
  const tenantEmiratesId = getVal('formTenantEmiratesId') || '784198883321535';
  const tenantMobile = getVal('formTenantMobile') || '971522414519';
  const tenantNationalityEn = getVal('formTenantNationalityEn') || 'Pakistan';
  const tenantNationalityAr = getVal('formTenantNationalityAr') || 'باكستان';
  const tenantEmail = getVal('formTenantEmail') || 'goharali220@gmail.com';

  // 4. Unit Details — defaults from Gohar Ali PDF
  const premiseNo = getVal('formPremiseNo') || '6391801694';
  const unitOrPlot = getVal('formUnitPlot') || 'Flat No. 254';
  const unitRegNo = getVal('formUnitRegNo') || 'UNT302977';
  const noOfRooms = getVal('formNoOfRooms') || '2';
  const area = getVal('formArea') || '110';
  const unitUsageEn = getVal('formUnitUsageEn') || 'RESIDENTIAL';
  const unitUsageAr = getVal('formUnitUsageAr') || 'سكني';
  const unitTypeEn = getVal('formUnitTypeEn') || 'APARTMENT';
  const unitTypeAr = getVal('formUnitTypeAr') || 'شقة';

  // 5. Occupants Details
  const occupantName = getVal('formOccupantName') || partyName;
  const occupantNameAr = getVal('formOccupantNameAr') || tenantNameAr;
  const occupantEmiratesId = getVal('formOccupantEmiratesId') || tenantEmiratesId;

  const now = new Date().toISOString();

  const docPayload = {
    type: 'tenancy',
    documentNumber: docNumber,
    status,
    issueDate,
    startDate,
    endDate,
    annualRent,
    contractValue,
    securityDeposit,

    // Lessor
    lessorCompanyEn,
    lessorCompanyAr,
    lessorLicenseNo,
    lessorMobile,
    lessorEmail,
    lessorContactEn,
    lessorContactAr,
    contactMobile,
    lessorContactMobile: contactMobile,
    contactEmail,
    lessorContactEmail: contactEmail,

    // Tenant
    partyName,
    tenantNameEn: partyName,
    tenantNameAr,
    tenantEmiratesId,
    tenantMobile,
    tenantNationalityEn,
    tenantNationalityAr,
    tenantEmail,

    // Unit
    premiseNo,
    unitOrPlot: unitOrPlot || docNumber,
    unitNo: unitOrPlot,
    unitRegNo,
    noOfRooms,
    area,
    unitUsageEn,
    unitUsageAr,
    unitTypeEn,
    unitTypeAr,

    // Occupants
    occupantName,
    occupantNameAr,
    occupantEmiratesId,

    // Signature QR (base64, stored so re-generation uses same QR)
    signatureQR: {
      tenantQR: (document.getElementById('tenantQrB64') || {}).value || '',
      lessorQR: (document.getElementById('lessorQrB64') || {}).value || ''
    },

    updatedAt: now
  };

  if (editingDocId) {
    const idx = documents.findIndex(d => d.id === editingDocId);
    if (idx !== -1) {
      documents[idx] = {
        ...documents[idx],
        ...docPayload
      };
      showToast(`Contract ${docNumber} updated successfully`, 'success');
    }
  } else {
    const newDoc = {
      id: 'DOC-' + (1000 + documents.length + 1),
      ...docPayload,
      verificationCount: 0,
      createdAt: now
    };
    documents.unshift(newDoc);
    showToast(`Contract ${docNumber} registered successfully`, 'success');
  }

  _generatedContracts.delete(docNumber);
  await saveDocuments();
  renderAll();
  closeDocModal();

  // Pre-generate contract in the background right after saving with full payload
  const _tenantQrB64 = (document.getElementById('tenantQrB64') || {}).value || '';
  const _lessorQrB64 = (document.getElementById('lessorQrB64') || {}).value || '';
  fetch('/api/generate-contract', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ...docPayload,
      documentNumber: docNumber,
      force: true,
      signatureQR: { tenantQR: _tenantQrB64, lessorQR: _lessorQrB64 }
    })
  }).then(r => { if (r.ok) _generatedContracts.add(docNumber); }).catch(() => {});

  if (window.innerWidth <= 768) {
    document.body.classList.remove('mobile-view-dashboard');
    document.body.classList.add('mobile-view-registry');
    const bReg = document.getElementById('btnNavRegistry');
    const bDash = document.getElementById('btnNavDashboard');
    if (bReg) bReg.classList.add('active');
    if (bDash) bDash.classList.remove('active');
  }
}

// Single Delete
function openDeleteModal(id) {
  deletingDocId = id;
  const doc = documents.find(d => d.id === id);
  const modal = document.getElementById('deleteModalOverlay');
  const targetLabel = document.getElementById('deleteTargetLabel');
  if (targetLabel && doc) {
    targetLabel.textContent = `${doc.documentNumber} (${doc.partyName})`;
  }
  if (modal) modal.classList.add('active');
}

function closeDeleteModal() {
  const modal = document.getElementById('deleteModalOverlay');
  if (modal) modal.classList.remove('active');
  deletingDocId = null;
}

async function handleConfirmDelete() {
  if (!deletingDocId) return;
  const doc = documents.find(d => d.id === deletingDocId);
  const docNumber = doc ? doc.documentNumber : '';
  const idToDelete = deletingDocId;

  // Remove from in-memory array and localStorage immediately
  if (docNumber) _generatedContracts.delete(docNumber);
  documents = documents.filter(d => d.id !== idToDelete);
  selectedDocIds.delete(idToDelete);
  localStorage.setItem(STORAGE_KEY_DOCS, JSON.stringify(documents));

  renderAll();
  closeDeleteModal();
  updateBatchBar();
  showToast(`Document ${docNumber} removed from registry`, 'success');

  // Fire DELETE directly to DB — no full-array POST race condition
  try {
    const res = await fetch(`/api/documents/${encodeURIComponent(idToDelete)}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
  } catch (err) {
    console.error('Delete failed on server, re-syncing full list:', err);
    await saveDocuments(); // fallback: full sync
  }
}

// Direct Test in Public Portal
function testInPortal(docNumber) {
  localStorage.setItem('dari_auto_verify_number', docNumber);
  window.open(`/en?app/verify-document`, '_blank');
}

// Export CSV
function exportToCsv() {
  const headers = ['ID', 'Type', 'Reference Number', 'Status', 'Party Name', 'Unit / Plot', 'Start Date', 'End Date', 'Verifications Count'];
  const rows = documents.map(d => [
    d.id,
    d.type,
    `"${(d.documentNumber || '').replace(/"/g, '""')}"`,
    d.status,
    `"${(d.partyName || '').replace(/"/g, '""')}"`,
    `"${(d.unitOrPlot || '').replace(/"/g, '""')}"`,
    d.startDate,
    d.endDate,
    d.verificationCount || 0
  ]);

  const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `ADREC_Document_Registry_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
  showToast('Registry exported to CSV', 'success');
}

// Toast notification
let toastTimeout = null;
function showToast(msg, type = 'success') {
  const toast = document.getElementById('adminToast');
  if (!toast) return;
  toast.textContent = msg;
  toast.className = `admin-toast ${type} active`;
  if (toastTimeout) clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => {
    toast.classList.remove('active');
  }, 3200);
}

// Helper: Escape HTML
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// ==================== CONTRACT PREVIEW & CAROUSEL CONTROLLER ====================
let currentContractDoc = null;
let currentContractPage = 1;
let isContractZoomed = false;

function setupContractModal() {
  const modal = document.getElementById('contractModalOverlay');
  const btnClose = document.getElementById('btnCloseContractModal');
  const btnCloseFooter = document.getElementById('btnCloseContractModalFooter');
  const btnZoom = document.getElementById('btnContractZoomToggle');

  if (btnClose) btnClose.addEventListener('click', closeContractModal);
  if (btnCloseFooter) btnCloseFooter.addEventListener('click', closeContractModal);

  if (btnZoom) {
    btnZoom.addEventListener('click', () => {
      const stage = document.getElementById('contractPageStage');
      const zoomText = document.getElementById('zoomToggleText');
      if (stage) {
        isContractZoomed = !isContractZoomed;
        stage.classList.toggle('zoomed', isContractZoomed);
        if (zoomText) zoomText.textContent = isContractZoomed ? 'Zoom Out' : 'Fit to View';
      }
    });
  }

  // Keyboard navigation inside modal
  window.addEventListener('keydown', (e) => {
    if (!modal || !modal.classList.contains('active')) return;
    if (e.key === 'Escape') {
      closeContractModal();
    }
  });
}

// ==================== CONTRACT MODAL CONTROLLER & LOADER ====================
function showContractLoader(show, title = '', status = '') {
  const loader = document.getElementById('contractStageLoader');
  const titleEl = document.getElementById('stageLoaderTitle');
  const statusEl = document.getElementById('stageLoaderStatus');
  const stage = document.getElementById('contractPageStage');

  if (loader) {
    if (show) {
      loader.classList.remove('hidden');
      loader.style.display = 'flex';
      if (title && titleEl) titleEl.textContent = title;
      if (status && statusEl) statusEl.textContent = status;
      if (stage) stage.style.display = 'none';
    } else {
      loader.classList.add('hidden');
      setTimeout(() => {
        if (loader.classList.contains('hidden')) {
          loader.style.display = 'none';
        }
      }, 250);
      if (stage) stage.style.display = 'flex';
    }
  }
}

// Preloads all 8 pages in memory to ensure complete decoding before revealing
function preloadContractPages(docNum, totalPages = 8, vTag = null) {
  const promises = [];
  const tag = vTag || Date.now();

  for (let p = 1; p <= totalPages; p++) {
    promises.push(new Promise((resolve) => {
      const img = new Image();
      let timer = null;

      const finish = () => {
        if (timer) clearTimeout(timer);
        resolve(true);
      };

      img.onload = finish;
      img.onerror = () => {
        setTimeout(() => {
          const retryImg = new Image();
          retryImg.onload = finish;
          retryImg.onerror = finish;
          retryImg.src = `/api/contracts/${docNum}/${p}.png?_r=${Date.now()}`;
        }, 300);
      };

      timer = setTimeout(finish, 5000); // safety fallback
      img.src = `/api/contracts/${docNum}/${p}.png?_v=${tag}`;
    }));
  }

  return Promise.all(promises);
}

// Self-healing retry handler on image load error
window.handleContractPageImgError = function(imgEl, docNum, pageNum) {
  const retryCount = parseInt(imgEl.getAttribute('data-retries') || '0', 10);
  if (retryCount < 6) {
    imgEl.setAttribute('data-retries', retryCount + 1);
    imgEl.style.opacity = '0.3';
    setTimeout(() => {
      imgEl.src = `/api/contracts/${docNum}/${pageNum}.png?_retry=${Date.now()}_${retryCount}`;
    }, 450 * (retryCount + 1));
  }
};

window.handleContractPageImgLoad = function(imgEl) {
  imgEl.style.opacity = '1';
};

async function openContractModal(docId) {
  const doc = documents.find(d => d.id === docId);
  if (!doc) return;

  currentContractDoc = doc;
  isContractZoomed = false;

  const modal = document.getElementById('contractModalOverlay');
  const docNumEl = document.getElementById('contractModalDocNum');
  const statusEl = document.getElementById('contractModalStatus');
  const dlBtn = document.getElementById('btnContractDownloadPdf');
  const footerDlBtn = document.getElementById('btnContractFooterDownload');
  const tenantEl = document.getElementById('contractFooterTenant');
  const periodEl = document.getElementById('contractFooterPeriod');
  const unitEl = document.getElementById('contractFooterUnit');
  const stage = document.getElementById('contractPageStage');
  const zoomText = document.getElementById('zoomToggleText');

  if (stage) {
    stage.classList.remove('zoomed');
    stage.style.display = 'none';
  }
  if (zoomText) zoomText.textContent = 'Fit to View';

  if (docNumEl) docNumEl.textContent = doc.documentNumber;
  if (statusEl) {
    statusEl.textContent = doc.status || 'Active';
    statusEl.className = `contract-status-pill ${(doc.status || 'Active').toLowerCase()}`;
  }

  const vTag = doc.updatedAt ? new Date(doc.updatedAt).getTime() : Date.now();
  const pdfUrl = `/api/contracts/${doc.documentNumber}.pdf?_v=${vTag}`;
  if (dlBtn) dlBtn.href = pdfUrl;
  if (footerDlBtn) footerDlBtn.href = pdfUrl;

  if (tenantEl) tenantEl.textContent = doc.partyName || '-';
  if (periodEl) periodEl.textContent = (doc.startDate && doc.endDate) ? `${doc.startDate} → ${doc.endDate}` : (doc.startDate || '-');
  if (unitEl) unitEl.textContent = doc.unitOrPlot || '-';

  // FAST PATH: contract already generated in this session — skip loader, render immediately
  if (_generatedContracts.has(doc.documentNumber)) {
    renderContinuousContractPages();
    showContractLoader(false);
    if (modal) modal.classList.add('active');
    const container = document.getElementById('contractViewerContainer');
    if (container) container.scrollTop = 0;
    return;
  }

  // 1. Show modal immediately with loading indicator
  showContractLoader(true, 'Initializing Official Contract Preview...', 'Connecting to document engine...');
  if (modal) modal.classList.add('active');

  const container = document.getElementById('contractViewerContainer');
  if (container) container.scrollTop = 0;

  try {
    showContractLoader(true, 'Rendering Contract Pages & Official Stamps...', 'Compiling Page 1 to 8...');

    // 2. Request generation on server and wait for it to complete with full doc data
    const res = await fetch('/api/generate-contract', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...doc,
        documentNumber: doc.documentNumber,
        force: true
      })
    });

    if (!res.ok) {
      throw new Error(`Server returned HTTP ${res.status}`);
    }

    showContractLoader(true, 'Verifying Document Viewability...', 'Validating high-res stream...');

    // 3. Preload pages in memory to ensure complete decoding
    await preloadContractPages(doc.documentNumber, 8, vTag);

    // 4. Render pages into DOM
    renderContinuousContractPages();

    // 5. Hide loader and reveal stage
    showContractLoader(false);

    // Mark as generated so every subsequent open is instant
    _generatedContracts.add(doc.documentNumber);
  } catch (err) {
    console.warn('Contract generation notice:', err);
    // Graceful fallback — still mark ready if we have a response
    renderContinuousContractPages();
    showContractLoader(false);
  }
}

function closeContractModal() {
  const modal = document.getElementById('contractModalOverlay');
  if (modal) modal.classList.remove('active');
}

function renderContinuousContractPages() {
  if (!currentContractDoc) return;

  const stage = document.getElementById('contractPageStage');
  if (!stage) return;

  const docNum = currentContractDoc.documentNumber;
  const pageCount = 8;
  const vTag = currentContractDoc.updatedAt ? new Date(currentContractDoc.updatedAt).getTime() : Date.now();

  let html = '';
  for (let p = 1; p <= pageCount; p++) {
    html += `
      <div class="contract-page-card" id="contractPage_${p}">
        <span class="page-badge">Page ${p} of ${pageCount}</span>
        <img ${p === 1 ? 'id="contractViewerImage"' : ''} 
             class="contract-page-img" 
             src="/api/contracts/${docNum}/${p}.png?_v=${vTag}" 
             alt="Contract Page ${p}" 
             loading="eager"
             onerror="handleContractPageImgError(this, '${docNum}', ${p})"
             onload="handleContractPageImgLoad(this)">
      </div>
    `;
  }
  stage.innerHTML = html;
}

