const API_BASE = 'http://localhost:8000';
const tokenKey = 'unknown_detection_token';

const loginView = document.querySelector('#login-view');
const dashboardView = document.querySelector('#dashboard-view');
const loginForm = document.querySelector('#login-form');
const loginError = document.querySelector('#login-error');
const logoutButton = document.querySelector('#logout-button');

loginForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  loginError.textContent = '';
  try {
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: document.querySelector('#username').value,
        password: document.querySelector('#password').value,
      }),
    });
    if (!response.ok) throw new Error('Đăng nhập thất bại');
    const data = await response.json();
    localStorage.setItem(tokenKey, data.access_token);
    await showDashboard();
  } catch (error) {
    loginError.textContent = error.message;
  }
});

logoutButton.addEventListener('click', () => {
  localStorage.removeItem(tokenKey);
  showLogin();
});

async function apiGet(path) {
  const token = localStorage.getItem(tokenKey);
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (response.status === 401 || response.status === 403) {
    localStorage.removeItem(tokenKey);
    showLogin();
    throw new Error('Phiên đăng nhập hết hạn');
  }
  if (!response.ok) throw new Error(`API lỗi: ${path}`);
  return response.json();
}

async function showDashboard() {
  loginView.classList.add('hidden');
  dashboardView.classList.remove('hidden');
  await loadDashboard();
}

function showLogin() {
  dashboardView.classList.add('hidden');
  loginView.classList.remove('hidden');
}

async function loadDashboard() {
  const [health, alerts, cameras, rules, employees] = await Promise.all([
    fetch(`${API_BASE}/system/health`).then((response) => response.json()),
    apiGet('/alerts'),
    apiGet('/cameras'),
    apiGet('/rules'),
    apiGet('/employees'),
  ]);

  document.querySelector('#health-status').textContent = `System: ${health.status} | Postgres: ${health.postgres} | Qdrant: ${health.qdrant}`;
  document.querySelector('#metric-alerts').textContent = alerts.length;
  document.querySelector('#metric-cameras').textContent = cameras.length;
  document.querySelector('#metric-rules').textContent = rules.length;
  document.querySelector('#metric-employees').textContent = employees.length;

  renderAlerts(alerts);
  renderCameras(cameras);
  renderRules(rules);
  renderEmployees(employees.slice(0, 12));
}

function renderAlerts(alerts) {
  const container = document.querySelector('#alerts-list');
  if (!alerts.length) {
    container.innerHTML = '<div class="item"><strong>Chưa có cảnh báo</strong><span>unknown_events hiện đang trống</span></div>';
    return;
  }
  container.innerHTML = alerts.map((alert) => `
    <div class="item">
      <strong>${alert.warning_type}<span class="badge">${alert.warning_level}</span></strong>
      <span>${alert.camera_id} | ${alert.zone} | ${alert.created_at}</span>
    </div>
  `).join('');
}

function renderCameras(cameras) {
  document.querySelector('#cameras-list').innerHTML = cameras.map((camera) => `
    <div class="item">
      <strong>${camera.name}<span class="badge">${camera.is_active ? 'active' : 'inactive'}</span></strong>
      <span>${camera.camera_id} | ${camera.source_type} | ${camera.location}</span>
    </div>
  `).join('');
}

function renderRules(rules) {
  document.querySelector('#rules-list').innerHTML = rules.map((rule) => `
    <div class="item">
      <strong>${rule.name}<span class="badge">${rule.warning_level}</span></strong>
      <span>${rule.rule_code} | ${rule.is_enabled ? 'enabled' : 'disabled'}</span>
    </div>
  `).join('');
}

function renderEmployees(employees) {
  document.querySelector('#employees-list').innerHTML = employees.map((employee) => `
    <div class="item">
      <strong>${employee.name}<span class="badge">${employee.emp_code || 'N/A'}</span></strong>
      <span>${employee.department || 'No department'} | ${employee.is_active ? 'active' : 'inactive'}</span>
    </div>
  `).join('');
}

if (localStorage.getItem(tokenKey)) {
  showDashboard().catch(() => showLogin());
} else {
  showLogin();
}
