const API = (typeof API_URL !== 'undefined') ? API_URL : '/api/v1';
let refreshInterval = null;

function getToken() {
  const token = localStorage.getItem('token');
  if (!token) window.location.href = 'index.html';
  return token;
}

function logout() {
  localStorage.clear();
  window.location.href = 'index.html';
}

function formatTime(d) {
  const dt = new Date(d);
  return dt.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
}

function formatDate(d) {
  const dt = new Date(d);
  return dt.toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
}

async function api(path, opts = {}) {
  const headers = { 'Authorization': `Bearer ${getToken()}`, ...opts.headers };
  const res = await fetch(`${API}${path}`, { ...opts, headers });
  if (res.status === 401) { logout(); return null; }
  if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || 'API error'); }
  return res.json();
}

async function loadStats() {
  try {
    const data = await api('/dashboard/stats');
    if (!data) return;
    document.getElementById('statReports').textContent = data.total_reports_today || 0;
    const rChange = document.getElementById('statReportsChange');
    const rDiff = data.reports_vs_yesterday || 0;
    rChange.textContent = rDiff >= 0 ? `+${rDiff} vs yesterday` : `${rDiff} vs yesterday`;
    rChange.className = 'stat-card-change ' + (rDiff >= 0 ? 'positive' : 'negative');
    document.getElementById('statCritical').textContent = data.critical_alerts || 0;
    document.getElementById('statResolved').textContent = data.resolved_alerts || 0;
    document.getElementById('statResolvedChange').textContent = `${data.resolution_rate || 0}% rate`;
    document.getElementById('statPending').textContent = data.pending_alerts || 0;
  } catch (e) { console.error('Stats error:', e); }
}

async function loadReportsByType() {
  try {
    const data = await api('/dashboard/reports-by-type');
    if (!data || !data.report_types) return;
    const container = document.getElementById('reportsByTypeChart');
    const maxCount = Math.max(...data.report_types.map(r => r.count), 1);
    container.innerHTML = data.report_types.map(r => `
      <div class="chart-bar">
        <div class="chart-bar-label">${r.type}</div>
        <div class="chart-bar-track">
          <div class="chart-bar-fill" style="width:${(r.count / maxCount) * 100}%">${r.count}</div>
        </div>
        <div class="chart-bar-value">${r.count}</div>
      </div>
    `).join('');
  } catch (e) { console.error('Reports by type error:', e); }
}

async function loadAlertsByDay() {
  try {
    const data = await api('/dashboard/alerts-by-day');
    if (!data || !data.alerts_by_day) return;
    const container = document.getElementById('alertsLineChart');
    const maxCount = Math.max(...data.alerts_by_day.map(d => d.count), 1);
    container.innerHTML = data.alerts_by_day.map(d => `
      <div class="line-chart-bar">
        <div class="line-chart-fill" style="height:${(d.count / maxCount) * 140}px"></div>
        <div class="line-chart-label">${d.date}</div>
        <div style="font-size:13px;font-weight:600;color:var(--text-primary)">${d.count}</div>
      </div>
    `).join('');
  } catch (e) { console.error('Alerts by day error:', e); }
}

async function loadTopDoctors() {
  try {
    const data = await api('/dashboard/top-doctors');
    if (!data || !data.doctors) return;
    const container = document.getElementById('topDoctors');
    const maxRef = Math.max(...data.doctors.map(d => d.total_referrals), 1);
    container.innerHTML = data.doctors.map((d, i) => `
      <div class="leaderboard-item">
        <div class="leaderboard-rank">${i + 1}</div>
        <div class="leaderboard-info">
          <div class="leaderboard-name">${d.name}</div>
          <div class="leaderboard-spec">${d.specialization || ''}</div>
        </div>
        <div class="leaderboard-count">${d.total_referrals}</div>
      </div>
    `).join('');
  } catch (e) { console.error('Top doctors error:', e); }
}

async function loadRecentAlerts() {
  try {
    const data = await api('/dashboard/recent-alerts');
    if (!data || !data.alerts) return;
    const container = document.getElementById('recentAlerts');
    if (data.alerts.length === 0) {
      container.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:20px">No recent alerts</p>';
      return;
    }
    container.innerHTML = data.alerts.map(a => {
      const icon = a.status === 'sent' || a.status === 'pending' ? '&#128308;' : a.status === 'acknowledged' ? '&#128992;' : '&#9989;';
      const statusClass = a.status === 'sent' || a.status === 'pending' ? 'badge-warning' : a.status === 'acknowledged' ? 'badge-info' : 'badge-success';
      const statusLabel = a.status === 'sent' ? 'Pending' : a.status === 'acknowledged' ? 'Acknowledged' : a.status === 'resolved' ? 'Resolved' : a.status;
      return `
        <div class="live-feed-item">
          <div class="live-feed-time">${a.sent_at ? formatTime(a.sent_at) : '--'}</div>
          <div style="font-size:18px">${icon}</div>
          <div class="live-feed-info">
            <div class="live-feed-name">${a.patient_name || 'Unknown'}</div>
            <div class="live-feed-detail">${a.report_type || ''} ${a.critical_value ? '&bull; ' + a.critical_value : ''}</div>
          </div>
          <span class="badge ${statusClass}">${statusLabel}</span>
        </div>
      `;
    }).join('');
  } catch (e) { console.error('Recent alerts error:', e); }
}

async function loadRecentPatients() {
  try {
    const data = await api('/dashboard/recent-patients');
    if (!data || !data.patients) return;
    const container = document.getElementById('recentPatients');
    if (data.patients.length === 0) {
      container.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:20px">No recent patients</p>';
      return;
    }
    container.innerHTML = data.patients.map(p => {
      const badge = p.is_critical
        ? '<span class="badge badge-danger">Critical</span>'
        : '<span class="badge badge-success">Normal</span>';
      return `
        <div class="live-feed-item">
          <div class="live-feed-time">${p.uploaded_at ? formatTime(p.uploaded_at) : '--'}</div>
          <div class="live-feed-info">
            <div class="live-feed-name">${p.name || 'Unknown'}</div>
            <div class="live-feed-detail">${p.age || ''}${p.gender ? p.gender[0] : ''} &bull; ${p.report_type || ''}</div>
          </div>
          ${badge}
        </div>
      `;
    }).join('');
  } catch (e) { console.error('Recent patients error:', e); }
}

function refreshDashboard() {
  loadStats();
  loadReportsByType();
  loadAlertsByDay();
  loadTopDoctors();
  loadRecentAlerts();
  loadRecentPatients();
}

// ===== Modal Helpers =====
function openModal(id) {
  document.getElementById(id).classList.add('active');
}
function closeModal(id) {
  document.getElementById(id).classList.remove('active');
}
// Close modal on overlay click
document.addEventListener('click', (e) => {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('active');
  }
});

// ===== Add Staff =====
function openAddStaffModal() {
  document.getElementById('addStaffForm').reset();
  document.getElementById('addStaffResult').innerHTML = '';
  openModal('addStaffModal');
}

document.getElementById('addStaffForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('addStaffBtn');
  const name = document.getElementById('staffName').value;
  const email = document.getElementById('staffEmail').value;
  const password = document.getElementById('staffPassword').value;
  const clinic = document.getElementById('staffClinic').value;
  btn.disabled = true; btn.textContent = 'Registering...';
  try {
    const res = await api('/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password, role: 'staff', clinic_name: clinic }),
    });
    document.getElementById('addStaffResult').innerHTML =
      `<div class="alert alert-success">✅ Staff registered: ${res.user.name} (${res.user.email})</div>`;
    document.getElementById('addStaffForm').reset();
  } catch (e) {
    document.getElementById('addStaffResult').innerHTML =
      `<div class="alert alert-danger">❌ ${e.message}</div>`;
  }
  btn.disabled = false; btn.textContent = 'Register Staff';
});

// ===== Add Doctor =====
function openAddDoctorModal() {
  document.getElementById('addDoctorForm').reset();
  document.getElementById('addDoctorResult').innerHTML = '';
  openModal('addDoctorModal');
}

document.getElementById('addDoctorForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = document.getElementById('addDoctorBtn');
  const name = document.getElementById('docName').value;
  const phone = document.getElementById('docPhone').value;
  const whatsapp = document.getElementById('docWhatsApp').value;
  const spec = document.getElementById('docSpec').value;
  const backup = document.getElementById('docBackup').value;
  btn.disabled = true; btn.textContent = 'Adding...';
  try {
    const res = await api('/doctors', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, phone, whatsapp_number: whatsapp, specialization: spec, backup_contact: backup || null }),
    });
    document.getElementById('addDoctorResult').innerHTML =
      `<div class="alert alert-success">✅ Doctor added: ${name}</div>`;
    document.getElementById('addDoctorForm').reset();
  } catch (e) {
    document.getElementById('addDoctorResult').innerHTML =
      `<div class="alert alert-danger">❌ ${e.message}</div>`;
  }
  btn.disabled = false; btn.textContent = 'Add Doctor';
});

// ===== Settings =====
async function openSettingsModal() {
  openModal('settingsModal');
  document.getElementById('settingsContent').innerHTML = '<p style="color:var(--text-muted)">Loading...</p>';
  try {
    const health = await fetch('/api/health').then(r => r.json()).catch(() => ({}));

      <div class="settings-row"><span class="label">API URL</span><span class="value">/api</span></div>
      <div class="settings-row"><span class="label">Frontend URL</span><span class="value">/frontend</span></div>
      <div class="settings-row"><span class="label">Database</span>
        <span class="value"><span class="status-indicator"><span class="status-dot ok"></span> MongoDB</span></span>
      </div>
      <div class="settings-row"><span class="label">AI Vision Model</span><span class="value">meta/llama-3.2-11b-vision-instruct</span></div>
      <div class="settings-row"><span class="label">AI Language Model</span><span class="value">mistralai/mistral-small-4-119b-2603</span></div>
      <div class="settings-row"><span class="label">Escalation Timeout</span><span class="value">30 minutes</span></div>
      <div class="settings-row"><span class="label">Max Escalations</span><span class="value">3</span></div>
      <div class="settings-row"><span class="label">Auto Refresh</span><span class="value">Every 30s</span></div>
      <div style="margin-top:16px;padding-top:16px;border-top:1px solid var(--border)">
        <p style="color:var(--text-muted);font-size:12px">VitalAlert v1.0.0 &bull; Powered by NVIDIA NIM &bull; Twilio WhatsApp</p>
      </div>
    `;
    document.getElementById('settingsContent').innerHTML = html;
  } catch (e) {
    document.getElementById('settingsContent').innerHTML = `<p style="color:var(--danger)">Error loading settings</p>`;
  }
}

// ===== View All Patients =====
let allPatientsData = [];

async function openPatientsModal() {
  openModal('patientsModal');
  document.getElementById('patientsContent').innerHTML = '<p style="color:var(--text-muted)">Loading...</p>';
  document.getElementById('patientsSearch').value = '';
  try {
    const data = await api('/patients?limit=200');
    allPatientsData = data.patients || [];
    renderPatientsTable(allPatientsData);
  } catch (e) {
    document.getElementById('patientsContent').innerHTML = `<p style="color:var(--danger)">Error: ${e.message}</p>`;
  }
}

function renderPatientsTable(patients) {
  if (!patients.length) {
    document.getElementById('patientsContent').innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:20px">No patients found</p>';
    return;
  }
  const rows = patients.map(p => {
    const gender = p.gender ? p.gender[0] : '--';
    const doctorName = p.doctor_name || '--';
    return `<tr><td>${p.name}</td><td>${p.age}${gender}</td><td>${p.phone}</td><td>${doctorName}</td></tr>`;
  }).join('');
  document.getElementById('patientsContent').innerHTML = `
    <table class="patient-table">
      <thead><tr><th>Name</th><th>Age/Gender</th><th>Phone</th><th>Doctor</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
    <p style="color:var(--text-muted);font-size:12px;margin-top:8px">${patients.length} patient(s)</p>
  `;
}

function filterPatientsTable() {
  const q = document.getElementById('patientsSearch').value.toLowerCase();
  const filtered = allPatientsData.filter(p =>
    (p.name || '').toLowerCase().includes(q) ||
    (p.phone || '').includes(q)
  );
  renderPatientsTable(filtered);
}

// ===== Download Dashboard Report =====
async function downloadDashboardReport() {
  try {
    const data = await api('/dashboard/stats');
    if (!data) return;

    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const now = new Date().toLocaleString('en-IN');

    let statsRows = `
      <tr><td>Reports Today</td><td>${data.total_reports_today || 0}</td></tr>
      <tr><td>Critical Alerts</td><td>${data.critical_alerts || 0}</td></tr>
      <tr><td>Resolved Alerts</td><td>${data.resolved_alerts || 0}</td></tr>
      <tr><td>Pending Alerts</td><td>${data.pending_alerts || 0}</td></tr>
      <tr><td>Resolution Rate</td><td>${data.resolution_rate || 0}%</td></tr>
    `;

    document.body.innerHTML = `
      <div style="padding:40px;font-family:sans-serif;max-width:800px;margin:0 auto">
        <div style="text-align:center;margin-bottom:32px">
          <h1 style="color:#00D4AA;margin:0">VitalAlert</h1>
          <p style="color:#666">Dashboard Report</p>
          <hr style="border-color:#ddd;margin:16px 0">
        </div>
        <p><strong>Clinic:</strong> ${user.clinic_name || 'N/A'}</p>
        <p><strong>Generated:</strong> ${now}</p>
        <h2 style="margin-top:24px">Key Metrics</h2>
        <table style="width:100%;border-collapse:collapse;margin-top:12px">
          <thead><tr style="background:#f0f0f0"><th style="padding:10px;text-align:left;border:1px solid #ddd">Metric</th><th style="padding:10px;text-align:left;border:1px solid #ddd">Value</th></tr></thead>
          <tbody>${statsRows}</tbody>
        </table>
        <div style="margin-top:48px;text-align:center;color:#999;font-size:12px">
          Generated by VitalAlert AI System on ${now}
        </div>
      </div>
    `;
    window.print();
  } catch (e) {
    alert('Error generating report: ' + e.message);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  document.getElementById('headerUser').textContent = user.name || 'User';
  document.getElementById('dashSubtitle').textContent = `${user.clinic_name || 'Clinic'} — ${formatDate(new Date())}`;

  // Fix Add Doctor button — redirect to open modal instead
  const addDocBtn = document.querySelector('[onclick*="staff.html"]');
  if (addDocBtn) {
    addDocBtn.onclick = (e) => {
      e.preventDefault();
      openAddDoctorModal();
    };
  }

  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
  document.getElementById('greeting').textContent = `${greeting}, ${user.name || 'User'} 👋`;

  refreshDashboard();
  refreshInterval = setInterval(refreshDashboard, 30000);
});
