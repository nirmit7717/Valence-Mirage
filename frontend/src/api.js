// ═══════════════════════════════════════════════
//  API wrapper — all backend endpoint calls
// ═══════════════════════════════════════════════

import { getSessionToken, removeSessionToken, saveSessionToken } from './utils/sessionTokens';

const API = import.meta.env.VITE_API_URL || '';

function getAuthHeaders() {
  const token = localStorage.getItem('token');
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

// Headers for calls about one session: your login, plus the guest token if this
// browser created the session without one.
function sessionHeaders(sessionId) {
  const headers = getAuthHeaders();
  const guestToken = getSessionToken(sessionId);
  if (guestToken) headers['X-Session-Token'] = guestToken;
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

// Errors carry the HTTP status and the server's `detail` so callers can react
// (e.g. "Campaign has ended" → show the end screen).
async function apiError(res) {
  const body = await res.json().catch(() => ({}));
  const detail = typeof body.detail === 'string' ? body.detail : '';
  const err = new Error(detail || `Server error: ${res.status}`);
  err.status = res.status;
  err.detail = detail;
  return err;
}

// ─── Game (existing, now with optional auth) ──────────────────────────────

export async function createSession({ player_name, keywords, character_class, campaign_size }) {
  const res = await fetch(`${API}/session/new`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ player_name, keywords, character_class, campaign_size }),
  });
  if (!res.ok) throw await apiError(res);
  const data = await res.json();
  // Guests get a secret token once; every later call for this session must send it.
  if (data.guest_token) saveSessionToken(data.session_id, data.guest_token);
  return data;
}

export async function submitAction(sessionId, action) {
  const res = await fetch(`${API}/session/${sessionId}/action`, {
    method: 'POST',
    headers: sessionHeaders(sessionId),
    body: JSON.stringify({ action }),
  });
  if (!res.ok) throw await apiError(res);
  return res.json();
}

export async function resolveCombat(sessionId, combatResult) {
  const res = await fetch(`${API}/session/${sessionId}/combat/resolve`, {
    method: 'POST',
    headers: sessionHeaders(sessionId),
    body: JSON.stringify(combatResult),
  });
  if (!res.ok) throw await apiError(res);
  return res.json();
}

export async function getSession(sessionId) {
  const res = await fetch(`${API}/session/${sessionId}`, { headers: sessionHeaders(sessionId) });
  if (!res.ok) throw await apiError(res);
  return res.json();
}

export async function getSessionHistory(sessionId, limit = 500) {
  const res = await fetch(`${API}/session/${sessionId}/history?limit=${limit}`, { headers: sessionHeaders(sessionId) });
  if (!res.ok) throw await apiError(res);
  return res.json();
}

export async function listSessions() {
  const res = await fetch(`${API}/sessions`, { headers: getAuthHeaders() });
  if (!res.ok) throw await apiError(res);
  return res.json();
}

export async function hydrateSession(sessionId) {
  const res = await fetch(`${API}/session/${sessionId}/hydrate`, { headers: sessionHeaders(sessionId) });
  if (!res.ok) throw await apiError(res);
  return res.json();
}

export async function deleteSession(sessionId) {
  const res = await fetch(`${API}/session/${sessionId}`, { method: 'DELETE', headers: sessionHeaders(sessionId) });
  if (!res.ok) throw await apiError(res);
  removeSessionToken(sessionId);
  return res.json();
}
