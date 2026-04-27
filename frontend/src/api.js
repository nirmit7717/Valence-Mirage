// ═══════════════════════════════════════════════
//  API wrapper — all backend endpoint calls
// ═══════════════════════════════════════════════

const API = '';

export async function createSession({ player_name, keywords, character_class, campaign_size }) {
  const res = await fetch(`${API}/session/new`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ player_name, keywords, character_class, campaign_size }),
  });
  if (!res.ok) throw new Error(`Server error: ${res.status}`);
  return res.json();
}

export async function submitAction(sessionId, action) {
  const res = await fetch(`${API}/session/${sessionId}/action`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action }),
  });
  if (!res.ok) throw new Error(`Server error: ${res.status}`);
  return res.json();
}

export async function resolveCombat(sessionId, combatResult) {
  const res = await fetch(`${API}/session/${sessionId}/combat/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(combatResult),
  });
  if (!res.ok) throw new Error(`Server error: ${res.status}`);
  return res.json();
}

export async function getSession(sessionId) {
  const res = await fetch(`${API}/session/${sessionId}`);
  return res.json();
}

export async function getSessionHistory(sessionId) {
  const res = await fetch(`${API}/session/${sessionId}/history`);
  return res.json();
}

export async function listSessions() {
  const res = await fetch(`${API}/sessions`);
  return res.json();
}

export async function deleteSession(sessionId) {
  const res = await fetch(`${API}/session/${sessionId}`, { method: 'DELETE' });
  return res.json();
}
