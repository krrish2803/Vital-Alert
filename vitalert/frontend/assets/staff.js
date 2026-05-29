const API = (typeof API_URL !== 'undefined') ? API_URL : '/api/v1';
let selectedFiles = [];
let currentReport = null;

function getToken() {
  const token = localStorage.getItem('token');
  if (!token) window.location.href = 'index.html';
  return token;
}

function logout() {
  localStorage.clear();
  window.location.href = 'index.html';
}

async function api(path, opts = {}) {
  const headers = { 'Authorization': `Bearer ${getToken()}`, ...opts.headers };
  const res = await fetch(`${API}${path}`, { ...opts, headers });
  if (res.status === 401) { logout(); return null; }
  if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || 'API error'); }
  return res.json();
}

// Tab switching
document.addEventListener('DOMContentLoaded', () => {
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  document.getElementById('headerUser').textContent = user.name || 'Staff';
  loadDoctorsDropdown();
  loadPatientsDropdown();
  loadDownloads();

  // Tab clicks
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
      tab.classList.add('active');
      const section = document.getElementById(`section-${tab.dataset.tab}`);
      if (section) section.classList.add('active');
    });
  });

  // Drop zone
  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('fileInput');

  dropZone.addEventListener('click', () => fileInput.click());
  dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('drag-over'); });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    handleFiles(e.dataTransfer.files);
  });
  fileInput.addEventListener('change', (e) => handleFiles(e.target.files));

  // Register form
  document.getElementById('registerForm').addEventListener('submit', registerPatient);
  // Upload form
  document.getElementById('uploadForm').addEventListener('submit', uploadReports);
});

function handleFiles(files) {
  const arr = Array.from(files);
  const allowed = ['.jpg', '.jpeg', '.png', '.webp', '.pdf'];
  const maxSize = 10 * 1024 * 1024;

  for (const file of arr) {
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowed.includes(ext)) { alert(`${file.name}: File type not allowed`); continue; }
    if (file.size > maxSize) { alert(`${file.name}: File exceeds 10MB`); continue; }
    selectedFiles.push(file);
  }

  if (selectedFiles.length > 20) {
    alert('Maximum 20 files allowed');
    selectedFiles = selectedFiles.slice(0, 20);
  }

  renderThumbnails();
}

function renderThumbnails() {
  const grid = document.getElementById('thumbnailGrid');
  grid.innerHTML = selectedFiles.map((f, i) => {
    const isImage = f.type.startsWith('image/');
    const preview = isImage ? URL.createObjectURL(f) : '';
    const size = (f.size / 1024).toFixed(1);
    return `
      <div class="thumbnail-item">
        ${isImage ? `<img src="${preview}" alt="${f.name}">` : `<div style="height:100px;display:flex;align-items:center;justify-content:center;font-size:32px;background:var(--bg-secondary)">📄</div>`}
        <div class="thumbnail-info">${f.name}<br>${size} KB</div>
        <button class="thumbnail-remove" onclick="removeFile(${i})">&times;</button>
      </div>
    `;
  }).join('');
}

function removeFile(idx) {
  selectedFiles.splice(idx, 1);
  renderThumbnails();
}

async function loadDoctorsDropdown() {
  try {
    const data = await api('/doctors');
    if (!data || !data.doctors) return;
    const sel = document.getElementById('patDoctor');
    data.doctors.forEach(d => {
      const opt = document.createElement('option');
      opt.value = d.id;
      opt.textContent = `${d.name} (${d.specialization || 'General'})`;
      sel.appendChild(opt);
    });
  } catch (e) { console.error('Load doctors error:', e); }
}

async function loadPatientsDropdown() {
  try {
    const data = await api('/patients?limit=100');
    if (!data || !data.patients) return;
    const sel = document.getElementById('uploadPatient');
    data.patients.forEach(p => {
      const opt = document.createElement('option');
      opt.value = p.id;
      opt.textContent = `${p.name} | ${p.age}${p.gender ? p.gender[0] : ''} | ${p.phone}`;
      sel.appendChild(opt);
    });
  } catch (e) { console.error('Load patients error:', e); }
}

async function registerPatient(e) {
  e.preventDefault();
  const data = {
    name: document.getElementById('patName').value,
    age: parseInt(document.getElementById('patAge').value),
    gender: document.getElementById('patGender').value,
    phone: document.getElementById('patPhone').value,
    referring_doctor_id: document.getElementById('patDoctor').value || null,
  };

  try {
    const res = await api('/patients', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    document.getElementById('registerResult').innerHTML =
      `<div class="alert alert-success">✅ Patient registered. Patient ID: ${res.patient_id}. Now upload reports.</div>`;
    document.getElementById('patName').value = '';
    document.getElementById('patAge').value = '';
    document.getElementById('patGender').value = '';
    document.getElementById('patPhone').value = '';
    document.getElementById('patDoctor').value = '';
    loadPatientsDropdown();
  } catch (e) {
    document.getElementById('registerResult').innerHTML =
      `<div class="alert alert-danger">❌ ${e.message}</div>`;
  }
}

async function uploadReports(e) {
  e.preventDefault();
  const patientId = document.getElementById('uploadPatient').value;
  const reportType = document.getElementById('reportType').value;
  const notes = document.getElementById('uploadNotes').value;

  if (!patientId) { alert('Please select a patient'); return; }
  if (!reportType) { alert('Please select report type'); return; }
  if (selectedFiles.length === 0) { alert('Please upload at least one file'); return; }

  // Show loading
  document.getElementById('loadingSection').style.display = 'block';
  document.getElementById('analyzeBtn').disabled = true;
  document.getElementById('resultsTab').style.display = 'none';

  // Animate steps
  const steps = document.querySelectorAll('.loading-step');
  steps.forEach(s => s.className = 'loading-step');

  function setStep(idx, state) {
    if (idx < steps.length) {
      steps[idx].className = `loading-step ${state}`;
    }
  }

  const formData = new FormData();
  formData.append('patient_id', patientId);
  formData.append('report_type', reportType);
  formData.append('notes', notes);
  selectedFiles.forEach(f => formData.append('files', f));

  setStep(0, 'active');

  try {
    await new Promise(r => setTimeout(r, 500));
    setStep(0, 'done');
    setStep(1, 'active');
    await new Promise(r => setTimeout(r, 800));
    setStep(1, 'done');
    setStep(2, 'active');

    const step2El = steps[2];
    let elapsed = 0;
    const timer = setInterval(() => {
      elapsed += 5;
      const label = step2El.querySelector('.step-label');
      if (label) label.textContent = `Analyzing with AI... (${elapsed}s)`;
    }, 5000);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000);

    const res = await fetch(`${API}/reports/upload`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${getToken()}` },
      body: formData,
      signal: controller.signal,
    });

    clearInterval(timer);
    clearTimeout(timeoutId);

    if (res.status === 401) { logout(); return; }
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Upload failed');
    }

    const data = await res.json();
    setStep(2, 'done');
    setStep(3, 'active');
    await new Promise(r => setTimeout(r, 600));
    setStep(3, 'done');
    setStep(4, 'active');
    await new Promise(r => setTimeout(r, 600));
    setStep(4, 'done');

    currentReport = data.report;
    await new Promise(r => setTimeout(r, 400));

    document.getElementById('loadingSection').style.display = 'none';
    showResults(data);
  } catch (e) {
    document.getElementById('loadingSection').style.display = 'none';
    document.getElementById('analyzeBtn').disabled = false;
    alert('Error: ' + e.message);
  }
}

function showResults(data) {
  const r = data.report;
  document.getElementById('resultsTab').style.display = 'block';
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelector('.tab[data-tab="results"]').classList.add('active');
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.getElementById('section-results').classList.add('active');

  const patientSelect = document.getElementById('uploadPatient');
  const patientName = patientSelect.options[patientSelect.selectedIndex]?.text?.split('|')[0]?.trim() || 'Patient';
  const now = new Date().toLocaleString('en-IN');

  const severityIcon = r.severity === 'critical' ? '🔴' : r.severity === 'high' ? '🟠' : r.severity === 'medium' ? '🟡' : '🟢';

  let hasValues = r.extracted_values && r.extracted_values.length > 0;
  let hasFindings = r.critical_findings && r.critical_findings.length > 0;
  let valuesHtml = '';
  let findingsHtml = '';

  if (hasValues) {
    r.extracted_values.forEach(v => {
      const icon = v.status.includes('critical') ? '🔴' : v.status === 'normal' ? '✅' : '⚠️';
      valuesHtml += `
        <div class="value-row">
          <span class="value-name">${v.test_name}</span>
          <div class="value-result">
            <span class="value-number">${v.value}</span>
            <span class="value-unit">${v.unit || ''}</span>
            <span style="font-size:12px">${icon}</span>
          </div>
        </div>
      `;
    });
  }

  if (hasFindings) {
    r.critical_findings.forEach(f => {
      findingsHtml += `<div class="value-row"><span class="value-name">🔴 ${f}</span></div>`;
    });
  }

  let content = `
    <div class="card" style="margin-bottom:16px">
      <div class="alert alert-success" style="margin-bottom:16px">
        <span style="font-size:24px">✅</span> Analysis Complete
      </div>
      <p><strong>Patient:</strong> ${patientName} | <strong>Report:</strong> ${r.report_type} | ${now}</p>
    </div>

    ${r.impression ? `
    <div class="card result-section">
      <h3>📋 Radiologist Impression</h3>
      <p style="color:var(--text-secondary);line-height:1.7">${r.impression}</p>
    </div>` : ''}
    <div class="card result-section">
      <h3>🤖 AI Health Summary</h3>
      <p style="color:var(--text-secondary);line-height:1.7">${r.health_summary || 'No summary generated'}</p>
    </div>

    ${hasValues ? `
    <div class="card result-section">
      <h3>📊 Extracted Test Values</h3>
      ${valuesHtml}
    </div>` : ''}
    ${hasFindings && !hasValues ? `
    <div class="card result-section">
      <h3>🔍 Key Findings</h3>
      ${findingsHtml}
    </div>` : ''}
    ${hasFindings && hasValues ? `
    <div class="card result-section">
      <h3>⚠️ Critical Findings</h3>
      ${findingsHtml}
    </div>` : ''}
    <div class="card result-section">
      <h3>Analysis Overview</h3>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
        <div>
          <p style="color:var(--text-muted);font-size:12px">Severity</p>
          <p style="font-size:18px;font-weight:700">${severityIcon} ${r.severity.toUpperCase()}</p>
        </div>
        <div>
          <p style="color:var(--text-muted);font-size:12px">AI Confidence</p>
          <p style="font-size:18px;font-weight:700">${Math.round((r.confidence_score || 0) * 100)}%</p>
        </div>
      </div>
    </div>
  `;

  if (r.alert_status === 'sent') {
    content += `
      <div class="alert alert-info">
        🚨 Doctor Auto-Alerted on WhatsApp<br>
        <span style="font-size:13px">Dr. notified at ${now}</span>
      </div>
    `;
  } else if (r.requires_human_review) {
    content += `
      <div class="alert alert-warning">
        ⚠️ AI needs human review<br>
        <span style="font-size:13px">Confidence: ${Math.round((r.confidence_score || 0) * 100)}% — Too low for auto alert</span>
      </div>
      <div style="display:flex;gap:12px;flex-wrap:wrap">
        <button class="btn btn-danger" onclick="manualAlert('${r.id}')">🚨 Alert Doctor Now</button>
        <button class="btn btn-warning" onclick="logCall('${r.id}')">📞 Call Doctor</button>
      </div>
    `;
  } else {
    content += `
      <div class="alert alert-success">
        ✅ No critical findings — Report saved
      </div>
    `;
  }

  content += `
    <div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:16px">
      <button class="btn btn-primary" onclick="exportPDF()" style="flex:1;min-width:200px">
        📥 Download PDF Report
      </button>
      <button class="btn btn-secondary" onclick="resetUpload()" style="flex:1;min-width:200px">
        📄 Analyze Another Report
      </button>
      <button class="btn btn-outline" onclick="window.location.href='/dashboard.html'" style="flex:1;min-width:200px">
        📊 Go to Dashboard
      </button>
    </div>
  `;

  document.getElementById('resultsContent').innerHTML = content;
  document.getElementById('analyzeBtn').disabled = false;

  // Scroll to results
  document.getElementById('section-results').scrollIntoView({ behavior: 'smooth' });
}

function resetUpload() {
  document.getElementById('resultsTab').style.display = 'none';
  document.getElementById('uploadForm').reset();
  document.getElementById('thumbnailGrid').innerHTML = '';
  selectedFiles = [];
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelector('.tab[data-tab="upload"]')?.classList.add('active');
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.getElementById('section-upload')?.classList.add('active');
}

async function manualAlert(reportId) {
  try {
    const res = await api('/alerts/manual-whatsapp', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ report_id: reportId }),
    });
    alert('✅ WhatsApp alert sent to doctor!');
  } catch (e) {
    alert('Error: ' + e.message);
  }
}

async function logCall(reportId) {
  try {
    await api('/alerts/log-call', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ report_id: reportId, note: 'Manual call from staff' }),
    });
    alert('📞 Call logged');
  } catch (e) {
    alert('Error: ' + e.message);
  }
}

// Sidebar page switching
function switchPage(page) {
  document.querySelectorAll('.sidebar-link').forEach(l => l.classList.remove('active'));
  document.querySelector(`.sidebar-link[data-page="${page}"]`)?.classList.add('active');
  document.querySelectorAll('.page').forEach(p => p.style.display = 'none');
  const el = document.getElementById(`page-${page}`);
  if (el) el.style.display = 'block';
  if (page === 'downloads') loadDownloads();
  if (page === 'review') loadReviews();
}

// PDF Export
function exportPDF(patientName) {
  if (!currentReport) { alert('No report to export. Analyze a report first.'); return; }
  const r = currentReport;
  if (!patientName) {
    patientName = document.querySelector('#uploadPatient option:checked')?.text?.split('|')[0]?.trim() || 'Patient';
  }
  const now = new Date().toLocaleString('en-IN');
  const icon = r.severity === 'critical' ? '🔴' : r.severity === 'high' ? '🟠' : r.severity === 'medium' ? '🟡' : '🟢';

  let valuesRows = '';
  if (r.extracted_values && r.extracted_values.length > 0) {
    r.extracted_values.forEach(v => {
      const statusIcon = v.status.includes('critical') ? '🔴' : v.status === 'normal' ? '✅' : '⚠️';
      valuesRows += `<tr><td>${v.test_name}</td><td>${v.value} ${v.unit || ''}</td><td>${statusIcon} ${v.status}</td></tr>`;
    });
  }

  document.body.innerHTML = `
    <div style="padding:40px;font-family:sans-serif;max-width:800px;margin:0 auto">
      <div style="text-align:center;margin-bottom:32px">
        <h1 style="color:#00D4AA;margin:0">VitalAlert</h1>
        <p style="color:#666">AI-Powered Diagnostic Report</p>
        <hr style="border-color:#ddd;margin:16px 0">
      </div>
      <div style="margin-bottom:24px">
        <h2>Report Analysis</h2>
        <p><strong>Patient:</strong> ${patientName}</p>
        <p><strong>Report Type:</strong> ${r.report_type || 'N/A'}</p>
        <p><strong>Date:</strong> ${now}</p>
        <p><strong>Severity:</strong> ${icon} ${(r.severity || 'unknown').toUpperCase()}</p>
        <p><strong>AI Confidence:</strong> ${Math.round((r.confidence_score || 0) * 100)}%</p>
        <p><strong>Status:</strong> ${r.is_critical ? '⚠️ CRITICAL - Action Required' : '✅ Normal'}</p>
      </div>
      <div style="margin-bottom:24px">
        <h3>AI Health Summary</h3>
        <div style="background:#f8f9fa;padding:16px;border-radius:8px;line-height:1.7">
          ${r.health_summary || 'No summary generated'}
        </div>
      </div>
      ${r.extracted_values && r.extracted_values.length > 0 ? `
      <div style="margin-bottom:24px">
        <h3>Extracted Test Values</h3>
        <table style="width:100%;border-collapse:collapse">
          <thead><tr style="background:#f0f0f0"><th style="padding:10px;text-align:left;border:1px solid #ddd">Test</th><th style="padding:10px;text-align:left;border:1px solid #ddd">Value</th><th style="padding:10px;text-align:left;border:1px solid #ddd">Status</th></tr></thead>
          <tbody>${valuesRows}</tbody>
        </table>
      </div>` : ''}
      ${r.suggested_action ? `
      <div style="margin-bottom:24px;background:#fff3cd;padding:16px;border-radius:8px;border:1px solid #ffc107">
        <strong>Suggested Action:</strong> ${r.suggested_action}
      </div>` : ''}
      <div style="margin-top:48px;text-align:center;color:#999;font-size:12px">
        Generated by VitalAlert AI System on ${now}
      </div>
    </div>
  `;
  window.print();
}

function exportReportAsPDF(reportId, encodedName) {
  const patientName = encodedName ? decodeURIComponent(encodedName) : '';
  api(`/reports/${reportId}`).then(r => {
    currentReport = r.report || r;
    exportPDF(patientName);
  }).catch(e => alert('Error loading report: ' + e.message));
}

// Downloads
let allReports = [];
let patientLookup = {};

async function loadDownloads() {
  try {
    const container = document.getElementById('downloadsList');
    if (container) container.innerHTML = `<div style="text-align:center;padding:40px;color:var(--text-muted)">Loading reports...</div>`;
    const results = await Promise.allSettled([
      api('/reports'),
      api('/patients?limit=200')
    ]);
    const reportsData = results[0].status === 'fulfilled' ? results[0].value : null;
    const patientsData = results[1].status === 'fulfilled' ? results[1].value : null;
    if (!reportsData) {
      if (container) container.innerHTML = `<div class="alert alert-danger">Failed to load reports. Check console for details.</div>`;
      return;
    }
    // Build patient name lookup
    patientLookup = {};
    if (patientsData && patientsData.patients) {
      patientsData.patients.forEach(p => { patientLookup[p.id] = p.name; });
    }
    const reports = reportsData.reports || reportsData;
    // Only show reports that were fully analyzed by AI
    const nonRadTypes = ['x-ray', 'mri', 'ct scan', 'ultrasound', 'echo'];
    allReports = reports.filter(r => {
      const isRad = nonRadTypes.includes((r.report_type || '').toLowerCase());
      const hasValues = r.extracted_values && r.extracted_values.length > 0;
      const hasFindings = r.critical_findings && r.critical_findings.length > 0;
      return (hasValues || (isRad && hasFindings)) &&
        r.is_critical !== null && r.is_critical !== undefined &&
        r.severity !== null && r.severity !== undefined;
    });
    renderDownloads(allReports);
  } catch (e) {
    document.getElementById('downloadsList').innerHTML = `<div class="alert alert-danger">Error loading reports: ${e.message}</div>`;
  }
}

function renderDownloads(reports) {
  const container = document.getElementById('downloadsList');
  if (!reports || reports.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">&#128196;</div>
        <h3>No reports found</h3>
        <p>Upload and analyze reports to see them here</p>
      </div>
    `;
    return;
  }
  container.innerHTML = reports.map(r => {
    const isCritical = r.is_critical;
    const tag = isCritical ? '<span class="report-tag critical">CRITICAL</span>' : '<span class="report-tag normal">NORMAL</span>';
    const date = r.processed_at || r.uploaded_at || '';
    const dateStr = date ? new Date(date).toLocaleString('en-IN') : 'Unknown';
    const fileCount = r.files ? r.files.length : 0;
    const valueCount = r.extracted_values ? r.extracted_values.length : 0;
    const findingCount = r.critical_findings ? r.critical_findings.length : 0;
    const detailStr = valueCount > 0 ? `${valueCount} test(s)` : findingCount > 0 ? `${findingCount} finding(s)` : 'analyzed';
    const patientName = patientLookup[r.patient_id] || 'Patient';
    return `
      <div class="download-item">
        <div class="download-icon">${isCritical ? '🚨' : '📋'}</div>
        <div class="download-info">
          <div class="download-name">${patientName} — ${r.report_type || 'Report'} ${tag}</div>
          <div class="download-meta">${dateStr} &bull; ${fileCount} file(s) &bull; ${detailStr}</div>
        </div>
        <button class="btn btn-primary btn-sm" onclick="exportReportAsPDF('${r.id}','${encodeURIComponent(patientName)}')">&#128229; Download PDF</button>
      </div>
    `;
  }).join('');
}

function filterDownloads() {
  const search = (document.getElementById('downloadSearch')?.value || '').toLowerCase();
  const filter = document.getElementById('downloadFilter')?.value || 'all';
  if (!Array.isArray(allReports)) { renderDownloads([]); return; }
  let filtered = allReports;
  if (filter === 'critical') filtered = filtered.filter(r => r.is_critical);
  if (filter === 'normal') filtered = filtered.filter(r => !r.is_critical);
  if (search) {
    filtered = filtered.filter(r =>
      (r.report_type || '').toLowerCase().includes(search) ||
      (r.patient_name || '').toLowerCase().includes(search) ||
      (r.id || '').toLowerCase().includes(search) ||
      (r.health_summary || '').toLowerCase().includes(search) ||
      ((r.critical_findings || []).join(' ')).toLowerCase().includes(search)
    );
  }
  renderDownloads(filtered);
}

function refreshDownloads() {
  const searchEl = document.getElementById('downloadSearch');
  const filterEl = document.getElementById('downloadFilter');
  if (searchEl) searchEl.value = '';
  if (filterEl) filterEl.value = 'all';
  loadDownloads();
}

// ===== Review Queue =====
let currentReview = null;

async function loadReviews() {
  try {
    const data = await api('/reviews');
    const reviews = data.reviews || [];
    renderReviews(reviews);
  } catch (e) {
    document.getElementById('reviewList').innerHTML = `<div class="alert alert-danger">Error: ${e.message}</div>`;
  }
}

function renderReviews(reviews) {
  const container = document.getElementById('reviewList');
  if (!reviews || reviews.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">✅</div>
        <h3>No pending reviews</h3>
        <p>All reports have sufficient AI confidence. Nothing needs manual review.</p>
      </div>
    `;
    return;
  }
  container.innerHTML = reviews.map(r => {
    const conf = Math.round((r.confidence_score || 0) * 100);
    const date = r.uploaded_at ? new Date(r.uploaded_at).toLocaleString('en-IN') : 'Unknown';
    const name = r.patient_name || 'Unknown';
    const gender = r.patient_gender ? r.patient_gender[0] : '';
    const age = r.patient_age || '';
    return `
      <div class="review-card" onclick="showReviewDetail('${r.id}')">
        <div class="review-icon">⚠️</div>
        <div class="review-info">
          <div class="review-name">${name} ${age}${gender} — ${r.report_type || 'Report'}</div>
          <div class="review-meta">${date} &bull; ${r.critical_findings ? r.critical_findings.length : 0} critical finding(s)</div>
        </div>
        <div class="review-conf">${conf}% confidence</div>
      </div>
    `;
  }).join('');
}

async function showReviewDetail(reportId) {
  try {
    const data = await api(`/reviews/${reportId}`);
    if (!data) return;
    currentReview = data;

    document.getElementById('reviewList').style.display = 'none';
    document.getElementById('reviewDetail').style.display = 'block';

    const r = data.report || {};
    const patient = data.patient || {};
    const doctor = data.doctor || {};

    const conf = Math.round((r.confidence_score || 0) * 100);
    const severityIcon = r.severity === 'critical' ? '🔴' : r.severity === 'high' ? '🟠' : '🟡';
    const date = r.uploaded_at ? new Date(r.uploaded_at).toLocaleString('en-IN') : 'Unknown';

    let valuesHtml = '';
    const values = r.extracted_values || [];
    values.forEach(v => {
      const icon = v.status.includes('critical') ? '🔴' : v.status === 'normal' ? '✅' : '⚠️';
      valuesHtml += `
        <div class="review-value-row">
          <span style="font-weight:500">${v.test_name}</span>
          <span>${v.value} ${v.unit || ''} <span style="font-size:12px">${icon}</span></span>
        </div>
      `;
    });

    let findingsHtml = '';
    const findings = r.critical_findings || [];
    findings.forEach(f => {
      findingsHtml += `<div class="review-value-row"><span>🔴 ${f}</span></div>`;
    });

    const doctorInfo = doctor.name
      ? `<p><strong>Referring Doctor:</strong> ${doctor.name} (${doctor.phone || ''})</p>`
      : '<p style="color:var(--text-muted)">No referring doctor assigned</p>';

    document.getElementById('reviewDetailContent').innerHTML = `
      <div class="card" style="margin-bottom:16px">
        <div class="alert alert-warning" style="margin-bottom:16px">
          <span style="font-size:24px">⚠️</span> Manual Review Required
          <span style="font-size:12px;display:block;margin-top:4px">AI confidence was ${conf}% — below 75% threshold for auto-alert</span>
        </div>
        <div class="two-col">
          <div>
            <p><strong>Patient:</strong> ${patient.name || 'Unknown'} ${patient.age || ''}${patient.gender ? patient.gender[0] : ''}</p>
            <p><strong>Phone:</strong> ${patient.phone || '--'}</p>
          </div>
          <div>
            <p><strong>Report:</strong> ${r.report_type || 'N/A'}</p>
            <p><strong>Date:</strong> ${date}</p>
          </div>
        </div>
        ${doctorInfo}
        <div style="display:flex;gap:16px;margin-top:12px">
          <div><span style="color:var(--text-muted);font-size:12px">Severity</span><br><span style="font-size:18px;font-weight:700">${severityIcon} ${(r.severity || 'unknown').toUpperCase()}</span></div>
          <div><span style="color:var(--text-muted);font-size:12px">AI Confidence</span><br><span style="font-size:18px;font-weight:700">${conf}%</span></div>
          <div><span style="color:var(--text-muted);font-size:12px">Critical</span><br><span style="font-size:18px;font-weight:700">${r.is_critical ? '🔴 YES' : '✅ NO'}</span></div>
        </div>
      </div>

      ${findings.length > 0 ? `
      <div class="card" style="margin-bottom:16px">
        <h3 style="margin-bottom:12px">⚠️ Critical Findings</h3>
        ${findingsHtml}
      </div>` : ''}

      <div class="card" style="margin-bottom:16px">
        <h3 style="margin-bottom:12px">📊 Extracted Values</h3>
        ${valuesHtml || '<p style="color:var(--text-muted)">No values extracted</p>'}
      </div>

      <div class="card" style="margin-bottom:16px">
        <h3 style="margin-bottom:12px">🤖 AI Health Summary</h3>
        <p style="color:var(--text-secondary);line-height:1.7">${r.health_summary || 'No summary generated'}</p>
      </div>

      ${r.suggested_action ? `
      <div class="card" style="margin-bottom:16px;background:rgba(255,179,71,0.08);border-color:rgba(255,179,71,0.2)">
        <h3 style="margin-bottom:8px">💡 Suggested Action</h3>
        <p style="color:var(--warning);font-weight:600">${r.suggested_action}</p>
      </div>` : ''}

      <div class="card" style="margin-bottom:16px">
        <h3 style="margin-bottom:12px">Review Decision</h3>
        <div class="form-group">
          <textarea class="form-input" id="reviewNotes" placeholder="Add review notes (optional)..." rows="3" style="margin-bottom:16px"></textarea>
        </div>
        <div class="review-actions">
          <button class="btn btn-success" onclick="approveReview('${r.id}')">✅ Approve & Alert Doctor</button>
          <button class="btn btn-danger" onclick="rejectReview('${r.id}')">✕ Reject (False Alarm)</button>
        </div>
      </div>
    `;

    document.getElementById('reviewDetail').scrollIntoView({ behavior: 'smooth' });
  } catch (e) {
    alert('Error: ' + e.message);
  }
}

async function approveReview(reportId) {
  if (!confirm('Approve this report and send WhatsApp alert to the doctor?')) return;
  const notes = document.getElementById('reviewNotes')?.value || '';
  try {
    const res = await api(`/reviews/${reportId}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notes }),
    });
    if (res.alert_sent) {
      alert('✅ Report approved. Doctor alerted on WhatsApp!');
    } else {
      alert('⚠️ Report approved but WhatsApp failed. Check Twilio config.');
    }
    backToReviewList();
  } catch (e) {
    alert('Error: ' + e.message);
  }
}

async function rejectReview(reportId) {
  if (!confirm('Reject this report as a false alarm? No alert will be sent.')) return;
  const notes = document.getElementById('reviewNotes')?.value || '';
  try {
    await api(`/reviews/${reportId}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notes }),
    });
    alert('✕ Report rejected (false alarm)');
    backToReviewList();
  } catch (e) {
    alert('Error: ' + e.message);
  }
}

function backToReviewList() {
  document.getElementById('reviewList').style.display = 'block';
  document.getElementById('reviewDetail').style.display = 'none';
  currentReview = null;
  loadReviews();
}

// Search patients for dropdown
document.getElementById('uploadPatient')?.addEventListener('focus', async function() {
  if (this.options.length <= 1) {
    try {
      const data = await api('/patients?limit=100');
      if (data && data.patients) {
        this.innerHTML = '<option value="">Search and select patient...</option>';
        data.patients.forEach(p => {
          const opt = document.createElement('option');
          opt.value = p.id;
          opt.textContent = `${p.name} | ${p.age}${p.gender ? p.gender[0] : ''} | ${p.phone}`;
          this.appendChild(opt);
        });
      }
    } catch (e) { console.error(e); }
  }
});
