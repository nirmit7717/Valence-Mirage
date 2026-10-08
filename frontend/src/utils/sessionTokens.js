// Guest session tokens. A guest's campaign is only reachable with the secret token
// the server returns once at creation, so it is kept per session in localStorage.

const KEY = 'vm_session_tokens';

function defaultStorage() {
  try {
    return globalThis.localStorage ?? null;
  } catch {
    return null; // storage disabled (privacy mode, sandboxed frame)
  }
}

function readAll(storage) {
  if (!storage) return {};
  try {
    const parsed = JSON.parse(storage.getItem(KEY) || '{}');
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
  } catch {
    return {}; // corrupted value — start over rather than crash
  }
}

function writeAll(storage, tokens) {
  if (!storage) return;
  try {
    storage.setItem(KEY, JSON.stringify(tokens));
  } catch {
    // quota exceeded or storage disabled — the session simply won't survive a reload
  }
}

export function getSessionToken(sessionId, storage = defaultStorage()) {
  if (!sessionId) return null;
  const token = readAll(storage)[sessionId];
  return typeof token === 'string' && token ? token : null;
}

export function saveSessionToken(sessionId, token, storage = defaultStorage()) {
  if (!sessionId || !token) return;
  writeAll(storage, { ...readAll(storage), [sessionId]: token });
}

export function removeSessionToken(sessionId, storage = defaultStorage()) {
  const tokens = readAll(storage);
  if (!(sessionId in tokens)) return;
  delete tokens[sessionId];
  writeAll(storage, tokens);
}
