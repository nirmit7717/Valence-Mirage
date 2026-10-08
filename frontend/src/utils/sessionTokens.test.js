import { test } from 'node:test';
import assert from 'node:assert/strict';
import { getSessionToken, removeSessionToken, saveSessionToken } from './sessionTokens.js';

function fakeStorage(initial = {}) {
  const data = { ...initial };
  return {
    getItem: (key) => (key in data ? data[key] : null),
    setItem: (key, value) => { data[key] = String(value); },
    data,
  };
}

test('saves and reads a token per session', () => {
  const storage = fakeStorage();
  saveSessionToken('a', 'token-a', storage);
  saveSessionToken('b', 'token-b', storage);
  assert.equal(getSessionToken('a', storage), 'token-a');
  assert.equal(getSessionToken('b', storage), 'token-b');
  assert.equal(getSessionToken('missing', storage), null);
});

test('removing one token keeps the others', () => {
  const storage = fakeStorage();
  saveSessionToken('a', 'token-a', storage);
  saveSessionToken('b', 'token-b', storage);
  removeSessionToken('a', storage);
  assert.equal(getSessionToken('a', storage), null);
  assert.equal(getSessionToken('b', storage), 'token-b');
});

test('corrupted storage does not crash and is replaced on save', () => {
  const storage = fakeStorage({ vm_session_tokens: '{not json' });
  assert.equal(getSessionToken('a', storage), null);
  saveSessionToken('a', 'token-a', storage);
  assert.equal(getSessionToken('a', storage), 'token-a');
});

test('missing storage and empty values are ignored', () => {
  assert.equal(getSessionToken('a', null), null);
  saveSessionToken('a', 'token-a', null); // no throw
  const storage = fakeStorage();
  saveSessionToken('', 'token', storage);
  saveSessionToken('a', '', storage);
  assert.deepEqual(storage.data, {});
});
