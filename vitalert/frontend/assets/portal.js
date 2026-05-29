const API = (typeof API_URL !== 'undefined') ? API_URL : '/api/v1';

function getToken() {
  return localStorage.getItem('token');
}

function logout() {
  localStorage.clear();
  window.location.href = 'index.html';
}

async function api(path, opts = {}) {
  const token = getToken();
  const headers = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  Object.assign(headers, opts.headers || {});
  const res = await fetch(`${API}${path}`, { ...opts, headers });
  if (res.status === 401) { logout(); return null; }
  if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || 'API error'); }
  return res.json();
}

document.addEventListener('DOMContentLoaded', () => {
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  document.getElementById('headerUser').textContent = user.name || 'Doctor';

  // Check for alert_id in URL first
  const alertId = getAlertIdFromUrl();
  if (alertId) {
    loadAlert(alertId);
  } else {
    loadAlertList();
  }
});

function getAlertIdFromUrl() {
  const path = window.location.pathname;
  const hash = window.location.hash;
  const params = new URLSearchParams(window.location.search);

  if (hash.startsWith('#alert_')) return hash.replace('#alert_', '');
  if (params.get('alert_id')) return params.get('alert_id');
  const pathMatch = path.match(/\/portal\/(.+)/);
  if (pathMatch) return pathMatch[1];

  return null;
}

function showListView() {
  document.getElementById('alertView').style.display = 'none';
  document.getElementById('noAlertView').style.display = 'none';
  document.getElementById('listView').style.display = 'block';
  loadAlertList();
}

function hideAll() {
  document.getElementById('listView').style.display = 'none';
  document.getElementById('noAlertView').style.display = 'none';
  document.getElementById('alertView').style.display = 'none';
  document.getElementById('noSetupView').style.display = 'none';
  document.getElementById('loadingView').style.display = 'block';
}

async function loadAlertList() {
  hideAll();
  try {
    const data = await api('/alerts/my');
    if (!data) return;

    document.getElementById('loadingView').style.display = 'none';
    document.getElementById('listView').style.display = 'block';

    const alerts = data.alerts || [];
    document.getElementById('alertCount').textContent = `${alerts.length} alert${alerts.length !== 1 ? 's' : ''}`;

    const container = document.getElementById('alertListContainer');
    if (alerts.length === 0) {
      container.innerHTML = '<div style="text-align:center;padding:60px;color:var(--text-muted)"><p>No alerts yet. When a critical report is detected for one of your patients, it will appear here.</p></div>';
      return;
    }

    container.innerHTML = alerts.map(a => {
      const status = a.status || 'sent';
      const icon = status === 'acknowledged' || status === 'resolved' ? '✅' : status === 'escalated' ? '🔴' : '⏳';
      const iconClass = status === 'acknowledged' || status === 'resolved' ? 'acknowledged' : '';
      const date = a.sent_at ? new Date(a.sent_at).toLocaleString('en-IN') : '--';
      return `<div class="alert-list-item" onclick="loadAlert('${a.id}')">
        <div class="alert-icon ${iconClass}">${icon}</div>
        <div class="alert-list-info">
          <div class="alert-list-name">${a.patient_name || 'Unknown Patient'}</div>
          <div class="alert-list-meta">${a.report_type || 'Report'} &bull; ${date}</div>
        </div>
        <span class="alert-list-status ${status}">${status.charAt(0).toUpperCase() + status.slice(1)}</span>
      </div>`;
    }).join('');
  } catch (e) {
    document.getElementById('loadingView').style.display = 'none';
    if (e.message.includes('setup')) {
      document.getElementById('noSetupView').style.display = 'block';
    } else {
      document.getElementById('noAlertView').style.display = 'block';
      document.querySelector('#noAlertView .card h2').textContent = 'Error loading alerts';
      document.querySelector('#noAlertView .card p').textContent = e.message;
    }
  }
}

async function loadAlert(alertId) {
  hideAll();
  try {
    const data = await api(`/alerts/${alertId}`);
    if (!data) return;

    const alert = data.alert;
    const patient = data.patient || {};
    const doctor = data.doctor || {};
    const report = data.report || {};

    document.getElementById('loadingView').style.display = 'none';
    document.getElementById('alertView').style.display = 'block';
    
    // Render formatted report view
    renderFormattedAlertView(alert, patient, doctor, report);
    
    window.currentAlertId = alert.id;
    window.currentPatientPhone = patient.phone;
  } catch (e) {
    document.getElementById('loadingView').style.display = 'none';
    document.getElementById('noAlertView').style.display = 'block';
    document.querySelector('#noAlertView .card h2').textContent = 'Alert not found';
    document.querySelector('#noAlertView .card p').textContent = e.message;
  }
}

function renderFormattedAlertView(alert, patient, doctor, report) {
  const container = document.getElementById('alertView');
  const date = alert.sent_at 
    ? new Date(alert.sent_at).toLocaleString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit', hour12: true
    }) : '--';
  
  const values = report.extracted_values || [];
  const isCritical = report.is_critical;
  const confidence = report.confidence_score || 0;
  const severity = report.severity || 'normal';
  
  let html = `<div class="formatted-report">`;
  
  // Header
  html += `<div class="fr-line">━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</div>`;
  html += `<div class="fr-line" style="font-size:18px;font-weight:700">✅ Analysis Complete</div>`;
  html += `<div class="fr-line">━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</div>`;
  html += `<div class="fr-space"></div>`;
  
  // Patient info
  html += `<div class="fr-line">Patient: ${patient.name || 'Unknown'}</div>`;
  html += `<div class="fr-line">Age: ${patient.age || '--'} | ${patient.gender || '--'}</div>`;
  html += `<div class="fr-line">Phone: ${patient.phone || '--'}</div>`;
  html += `<div class="fr-line">Report Type: ${report.report_type || '--'}</div>`;
  html += `<div class="fr-line">Analyzed at: ${date}</div>`;
  html += `<div class="fr-space"></div>`;
  
  // Health Summary
  html += `<div class="fr-line">━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</div>`;
  html += `<div class="fr-line" style="font-size:16px;font-weight:600">🤖 AI Health Summary</div>`;
  html += `<div class="fr-line">━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</div>`;
  html += `<div class="fr-space"></div>`;
  
  const summary = report.health_summary || 'No summary available';
  html += `<div class="fr-summary">${summary.replace(/\n/g, '<br>')}</div>`;
  html += `<div class="fr-space"></div>`;
  
  // Test Results
  html += `<div class="fr-line">━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</div>`;
  html += `<div class="fr-line" style="font-size:16px;font-weight:600">📊 Test Results</div>`;
  html += `<div class="fr-line">━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</div>`;
  html += `<div class="fr-space"></div>`;
  
  if (values.length > 0) {
    html += `<div class="fr-table">`;
    html += `<div class="fr-row fr-header">
      <div class="fr-cell fr-test">Test</div>
      <div class="fr-cell fr-value">Value</div>
      <div class="fr-cell fr-status">Status</div>
    </div>`;
    html += `<div class="fr-divider">─────────────────────────────────────────────</div>`;
    
    values.forEach(v => {
      const status = v.status || 'unknown';
      const statusIcon = status.includes('critical') ? '🔴' : status === 'normal' ? '✅' : '⚠️';
      const displayValue = typeof v.value === 'number' ? `${v.value}${v.unit || ''}` : v.value || '--';
      html += `<div class="fr-row">
        <div class="fr-cell fr-test">${v.test_name || 'Test'}</div>
        <div class="fr-cell fr-value">${displayValue}</div>
        <div class="fr-cell fr-status">${statusIcon} ${status.toUpperCase()}</div>
      </div>`;
    });
    html += `</div>`;
  } else {
    html += `<div class="fr-text" style="color:var(--text-muted)">No values extracted</div>`;
  }
  html += `<div class="fr-space"></div>`;
  
  // Severity + Confidence
  html += `<div class="fr-line">━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</div>`;
  const severityIcon = isCritical ? '⚠️' : '✅';
  html += `<div class="fr-line" style="font-weight:600">${severityIcon} Severity: ${severity.toUpperCase()}</div>`;
  html += `<div class="fr-line" style="font-weight:600">🎯 AI Confidence: ${Math.round(confidence * 100)}%</div>`;
  html += `<div class="fr-line">━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</div>`;
  html += `<div class="fr-space"></div>`;
  
  // Suggested Action
  html += `<div class="fr-line" style="font-weight:500">Suggested Action:</div>`;
  html += `<div class="fr-text">${report.suggested_action || 'No specific action suggested.'}</div>`;
  html += `<div class="fr-space"></div>`;
  
  // Alert Status
  html += `<div class="fr-line">━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</div>`;
  html += `<div class="fr-line" style="font-size:16px;font-weight:600">🚨 Alert Status</div>`;
  html += `<div class="fr-line">━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</div>`;
  html += `<div class="fr-space"></div>`;
  
  if (alert.status === 'sent' || alert.status === 'acknowledged') {
    html += `<div class="fr-line" style="color:var(--success)">✅ Doctor Alerted on WhatsApp</div>`;
    html += `<div class="fr-line">Doctor notified at ${date}</div>`;
  } else if (alert.status === 'escalated') {
    html += `<div class="fr-line" style="color:var(--warning)">⚠️ Alert escalated</div>`;
  } else {
    html += `<div class="fr-line" style="color:var(--success)">✅ No critical issues found</div>`;
  }
  html += `<div class="fr-space"></div>`;
  
  html += `<div class="fr-line">━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</div>`;
  html += `</div>`; // end formatted-report
  
  // Action buttons
  html += `<div style="display:flex;gap:12px;margin-top:20px;flex-wrap:wrap">
    <button class="btn btn-primary" onclick="acknowledgeAlert()">✅ Mark as Acknowledged</button>
    <button class="btn btn-outline" onclick="callPatient()">📞 Call Patient</button>
    <button class="btn btn-outline" onclick="toggleMessageBox()">💬 Message Patient</button>
  </div>`;
  
  // Message box (initially hidden)
  html += `<div id="messageArea" style="display:none;margin-top:16px;padding:16px;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius)">
    <h3 style="margin-top:0;margin-bottom:12px">Send Message to Patient</h3>
    <textarea id="messageText" rows="3" placeholder="Type your message here..." style="width:100%;padding:8px;border:1px solid var(--border);border-radius:4px;resize:vertical;"></textarea>
    <div style="margin-top:8px;text-align:right">
      <button class="btn btn-outline" onclick="toggleMessageBox()">Cancel</button>
      <button class="btn btn-primary" onclick="sendMessage()">Send</button>
    </div>
  </div>`;
  
  container.innerHTML = html;
}

async function acknowledgeAlert() {
  const alertId = window.currentAlertId;
  if (!alertId) { alert('No alert selected'); return; }

  try {
    const res = await api(`/alerts/${alertId}/acknowledge`, { method: 'POST' });
    if (res) {
      const statusBanner = document.getElementById('statusBanner');
      statusBanner.className = 'status-banner';
      statusBanner.style.background = 'rgba(0,200,81,0.1)';
      statusBanner.style.border = '1px solid rgba(0,200,81,0.2)';
      statusBanner.innerHTML = '<span style="font-size:20px">✅</span>';
      document.getElementById('statusText').textContent = 'Acknowledged';
      document.getElementById('alertCard').classList.add('acknowledged');
      document.getElementById('acknowledgeBtn').disabled = true;
      document.getElementById('acknowledgeBtn').textContent = '✅ Acknowledged';
      document.getElementById('alertStatus').textContent = 'acknowledged';
    }
  } catch (e) {
    alert('Error: ' + e.message);
  }
}

function callPatient() {
  const phone = window.currentPatientPhone;
  if (phone) {
    window.location.href = `tel:${phone}`;
    if (window.currentAlertId) {
      api('/alerts/log-call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          alert_id: window.currentAlertId,
          note: 'Doctor called patient from portal',
        }),
      }).catch(() => {});
    }
  } else {
    alert('Patient phone number not available');
  }
}

function toggleMessageBox() {
  const area = document.getElementById('messageArea');
  area.style.display = area.style.display === 'block' ? 'none' : 'block';
}

async function sendMessage() {
  const text = document.getElementById('messageText').value.trim();
  if (!text) { alert('Please type a message'); return; }
  if (!window.currentAlertId) { alert('No alert selected'); return; }

  try {
    const res = await api(`/alerts/${window.currentAlertId}/message-patient`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
    });
    if (res) {
      alert('✅ Message sent to patient via WhatsApp!');
      document.getElementById('messageText').value = '';
      document.getElementById('messageArea').style.display = 'none';
    }
  } catch (e) {
    alert('Error: ' + e.message);
  }
}
