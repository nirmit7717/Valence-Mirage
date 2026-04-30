// ═══════════════════════════════════════════════
//  API wrapper — all backend endpoint calls
// ═══════════════════════════════════════════════

const API = '';

function getAuthHeaders() {
  const token = localStorage.getItem('token');
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

// ─── Auth ──────────────────────────────────────────────────────────────────

export async function login(username, password) {
  const res = await fetch(`${API}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Login failed: ${res.status}`);
  }
  return res.json();
}

export async function testerRequest(email) {
  const res = await fetch(`${API}/auth/tester-request`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export async function getUserMe() {
  const res = await fetch(`${API}/user/me`, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error(`Not authenticated: ${res.status}`);
  return res.json();
}

export async function getUserDashboard() {
  const res = await fetch(`${API}/user/dashboard`, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error(`Failed: ${res.status}`);
  return res.json();
}

// ─── Game (existing, now with optional auth) ──────────────────────────────

export async function createSession({ player_name, keywords, character_class, campaign_size }) {
  const res = await fetch(`${API}/session/new`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ player_name, keywords, character_class, campaign_size }),
  });
  if (!res.ok) throw new Error(`Server error: ${res.status}`);
  return res.json();
}

export async function submitAction(sessionId, action) {
  const res = await fetch(`${API}/session/${sessionId}/action`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ action }),
  });
  if (!res.ok) throw new Error(`Server error: ${res.status}`);
  return res.json();
}

export async function resolveCombat(sessionId, combatResult) {
  const res = await fetch(`${API}/session/${sessionId}/combat/resolve`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(combatResult),
  });
  if (!res.ok) throw new Error(`Server error: ${res.status}`);
  return res.json();
}

export async function getSession(sessionId) {
  const res = await fetch(`${API}/session/${sessionId}`, { headers: getAuthHeaders() });
  return res.json();
}

export async function getSessionHistory(sessionId) {
  const res = await fetch(`${API}/session/${sessionId}/history`, { headers: getAuthHeaders() });
  return res.json();
}

export async function listSessions() {
  const res = await fetch(`${API}/sessions`, { headers: getAuthHeaders() });
  return res.json();
}

export async function deleteSession(sessionId) {
  const res = await fetch(`${API}/session/${sessionId}`, { method: 'DELETE', headers: getAuthHeaders() });
  return res.json();
}
