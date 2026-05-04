const API = 'http://localhost:8000';
let cmdHistory = [];
let allDevices = [];

// ── CLOCK ──
function updateClock() {
  document.getElementById('clock').textContent = new Date().toLocaleTimeString();
}
setInterval(updateClock, 1000); updateClock();

// ── NAVIGATION ──
function showSection(id) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('sec-' + id).classList.add('active');
  event.currentTarget.classList.add('active');
  if (id === 'logs') loadLogs();
  if (id === 'rules') loadRules();
  if (id === 'protocols') loadProtocols();
}

// ── API HELPERS ──
async function apiFetch(path, opts = {}) {
  try {
    const r = await fetch(API + path, { ...opts, headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) } });
    return await r.json();
  } catch { return null; }
}

// ── DEVICES ──
async function loadDevices() {
  const data = await apiFetch('/devices');
  if (!data) return;
  allDevices = data;
  renderDeviceGrid(data);
  updateProtoCounts(data);
  updateStatCards(data);
}

function updateProtoCounts(devices) {
  const tuya   = devices.filter(d => d.protocol?.toLowerCase() === 'tuya').length;
  const zigbee = devices.filter(d => d.protocol?.toLowerCase() === 'zigbee').length;
  const x10    = devices.filter(d => d.protocol?.toLowerCase() === 'x10').length;
  document.getElementById('proto-tuya-count').textContent   = tuya   || '—';
  document.getElementById('proto-zigbee-count').textContent = zigbee || '—';
  document.getElementById('proto-x10-count').textContent    = x10    || '—';
  if (document.getElementById('tuya-dev-count'))   document.getElementById('tuya-dev-count').textContent   = tuya;
  if (document.getElementById('zigbee-dev-count')) document.getElementById('zigbee-dev-count').textContent = zigbee;
  if (document.getElementById('x10-dev-count'))    document.getElementById('x10-dev-count').textContent    = x10;
}

const DEVICE_ICONS = {
  light: '💡', lamp: '💡', bulb: '💡',
  plug: '🔌', outlet: '🔌', socket: '🔌',
  lock: '🔒', door: '🚪',
  thermostat: '🌡️', temp: '🌡️',
  sensor: '📡', outdoor: '📡',
  camera: '📷', fan: '🌀',
  default: '📱'
};
function getDeviceIcon(name) {
  const n = (name || '').toLowerCase();
  for (const [k, v] of Object.entries(DEVICE_ICONS)) {
    if (n.includes(k)) return v;
  }
  return DEVICE_ICONS.default;
}

function renderDeviceGrid(devices) {
  const grid = document.getElementById('device-grid');
  if (!devices || !devices.length) { grid.innerHTML = '<div class="empty-state">No devices available — is the API running?</div>'; return; }
  grid.innerHTML = devices.map(d => {
    const on = ['on','true','locked','active','open','running'].includes(String(d.state).toLowerCase());
    const icon = getDeviceIcon(d.name || d.id);
    const proto = (d.protocol || 'tuya').toLowerCase();
    return `<div class="device-item" onclick="toggleDevice('${d.id}', ${on})">
      <div class="device-left">
        <div class="device-ico">${icon}</div>
        <div>
          <div class="device-name">${d.name || d.id}</div>
          <div class="device-proto"><span class="tag ${proto}">${proto.toUpperCase()}</span></div>
        </div>
      </div>
      <button class="toggle ${on ? 'on' : ''}" title="Toggle ${d.name}"></button>
    </div>`;
  }).join('');
}

async function toggleDevice(id, currentlyOn) {
  const action = currentlyOn ? 'off' : 'on';
  const res = document.getElementById('cmd-response');
  if (res) { res.className = 'cmd-response thinking'; res.textContent = `→ Sending: turn ${action} ${id}…`; }
  const data = await apiFetch('/command', {
    method: 'POST',
    body: JSON.stringify({ user_id: 'dashboard', message: `turn ${action} ${id}` })
  });
  if (res && data) { res.className = 'cmd-response'; res.textContent = `→ ${data.response || 'Done'}`; }
  setTimeout(loadDevices, 600);
}

function updateStatCards(devices) {
  const total = devices.length;
  const online = devices.filter(d => ['on','true','locked','active'].includes(String(d.state).toLowerCase())).length;
  document.getElementById('stat-devices').textContent = total;
  document.getElementById('stat-online').textContent = online;
}

// ── LOGS ──
async function loadLogs() {
  const data = await apiFetch('/logs');
  if (!data || !data.logs) return;
  const logs = data.logs;
  document.getElementById('stat-logs').textContent = logs.length;

  // Overview mini-logs
  const overviewEl = document.getElementById('overview-logs');
  if (overviewEl) {
    overviewEl.innerHTML = logs.slice(0, 8).map(l =>
      `<div style="display:flex;gap:8px;padding:7px 0;border-bottom:1px solid rgba(27,46,74,0.4);align-items:flex-start">
        <span style="font-size:10px;color:var(--muted);white-space:nowrap;margin-top:1px">${formatTime(l.timestamp)}</span>
        <span style="font-size:12px;flex:1;color:var(--white)">${l.user_input || l.ai_action || '—'}</span>
        <span style="font-size:10px;color:${l.result?.toLowerCase().includes('err') ? 'var(--red)' : 'var(--green)'}">${l.result?.slice(0,8) || 'ok'}</span>
      </div>`
    ).join('') || '<div class="empty-state">No logs yet</div>';
  }

  // Full log table
  const tbody = document.getElementById('log-tbody');
  if (tbody) {
    tbody.innerHTML = logs.map(l =>
      `<tr>
        <td style="color:var(--muted)">#${l.id}</td>
        <td style="font-family:monospace;color:var(--muted)">${formatTime(l.timestamp)}</td>
        <td><span class="log-source">${l.source || '—'}</span></td>
        <td style="max-width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${l.user_input || '—'}</td>
        <td style="color:var(--teal);font-family:monospace">${l.device || '—'}</td>
        <td class="log-result ${(l.result || '').toLowerCase().includes('err') ? 'err' : 'ok'}">${l.result || '—'}</td>
      </tr>`
    ).join('') || '<tr><td colspan="6" class="empty-state">No logs</td></tr>';
  }

  renderActivityChart(logs);
}

function formatTime(ts) {
  if (!ts) return '—';
  try { return new Date(ts).toLocaleTimeString(); } catch { return ts.slice(11, 19) || ts; }
}

// ── ACTIVITY CHART (hourly) ──
function renderActivityChart(logs) {
  const hours = Array(24).fill(0);
  logs.forEach(l => {
    if (l.timestamp) {
      const h = new Date(l.timestamp).getHours();
      if (!isNaN(h)) hours[h]++;
    }
  });
  const recent = hours.slice(Math.max(0, new Date().getHours() - 11), new Date().getHours() + 1);
  const max = Math.max(...recent, 1);
  const labels = [];
  for (let i = Math.max(0, new Date().getHours() - 11); i <= new Date().getHours(); i++) {
    labels.push(i + ':00');
  }
  const chartEl = document.getElementById('activity-chart');
  const labelsEl = document.getElementById('chart-labels');
  if (!chartEl) return;
  chartEl.innerHTML = recent.map((v, i) =>
    `<div class="chart-bar" style="height:${Math.max(4, Math.round((v/max)*180))}px">
      ${v > 0 ? `<span class="bar-tip">${v}</span>` : ''}
    </div>`
  ).join('');
  if (labelsEl) labelsEl.innerHTML = labels.map((l, i) => `<div class="chart-label">${i % 3 === 0 ? l : ''}</div>`).join('');
}

// ── RULES ──
async function loadRules() {
  const data = await apiFetch('/rules');
  if (!data || !data.rules) return;
  const rules = data.rules;
  document.getElementById('stat-rules').textContent = rules.length;
  document.getElementById('rule-count-badge').textContent = rules.length + ' rules';

  const el = document.getElementById('rules-list');
  el.innerHTML = rules.length === 0
    ? '<div class="empty-state">No automation rules yet. Add one above.</div>'
    : rules.map(r => {
        let action = r.action;
        try { const j = JSON.parse(r.action); action = `${j.command || ''} ${j.device || ''}`; } catch {}
        return `<div class="rule-item">
          <div>
            <div class="rule-name">⚡ ${r.name}</div>
            <div class="rule-meta">🕐 ${r.trigger_value}  •  ${action}  •  Created ${formatTime(r.created_at)}</div>
          </div>
          <div style="display:flex;gap:8px;align-items:center">
            <span class="rule-badge active">ACTIVE</span>
            <button class="del-btn" onclick="deleteRule(${r.id})">Delete</button>
          </div>
        </div>`;
      }).join('');
}

async function addRule() {
  const name   = document.getElementById('rule-name').value.trim();
  const time   = document.getElementById('rule-time').value;
  const device = document.getElementById('rule-device').value;
  const action = document.getElementById('rule-action').value;
  if (!name || !time) { alert('Please fill in rule name and time.'); return; }
  await apiFetch('/rules/add', { method: 'POST', body: JSON.stringify({ name, time, device, action }) });
  document.getElementById('rule-name').value = '';
  document.getElementById('rule-time').value = '';
  loadRules();
}

async function deleteRule(id) {
  if (!confirm('Delete this rule?')) return;
  await apiFetch('/rules/' + id, { method: 'DELETE' });
  loadRules();
}

// ── COMMAND ──
function setCmd(text) { document.getElementById('cmd-input').value = text; }

async function sendCommand() {
  const input = document.getElementById('cmd-input');
  const msg = input.value.trim();
  if (!msg) return;
  const res = document.getElementById('cmd-response');
  res.className = 'cmd-response thinking';
  res.textContent = '→ Sending to AI…';

  const data = await apiFetch('/command', {
    method: 'POST',
    body: JSON.stringify({ user_id: 'dashboard', message: msg })
  });

  if (data) {
    res.className = 'cmd-response';
    res.textContent = '→ ' + (data.response || JSON.stringify(data));
    cmdHistory.unshift({ msg, resp: data.response, time: new Date().toLocaleTimeString() });
    renderCmdHistory();
  } else {
    res.className = 'cmd-response error';
    res.textContent = '→ Error: Could not reach API at ' + API + '. Is the server running?';
  }
  input.value = '';
  setTimeout(loadDevices, 800);
}

function renderCmdHistory() {
  const el = document.getElementById('cmd-history');
  el.innerHTML = cmdHistory.slice(0, 20).map(c =>
    `<div style="padding:8px 0;border-bottom:1px solid rgba(27,46,74,0.4)">
      <div style="display:flex;justify-content:space-between;margin-bottom:4px">
        <span style="font-size:12px;color:var(--white)">"${c.msg}"</span>
        <span style="font-size:10px;color:var(--muted)">${c.time}</span>
      </div>
      <div style="font-size:11px;color:var(--teal);font-family:monospace">→ ${c.resp || '—'}</div>
    </div>`
  ).join('') || '<div class="empty-state">No commands yet</div>';
}

// ── PROTOCOLS ──
async function loadProtocols() {
  const [x10, zigbee] = await Promise.all([apiFetch('/x10'), apiFetch('/zigbee')]);
  if (x10) document.getElementById('x10-status').textContent = '● ' + (x10.info?.status || 'Active');
  if (zigbee) document.getElementById('zigbee-status').textContent = '● ' + (zigbee.info?.status || 'Active');
}

// ── REFRESH ALL ──
async function refreshAll() {
  await Promise.all([loadDevices(), loadLogs()]);
}

// ── INIT ──
refreshAll();
setInterval(refreshAll, 15000); 