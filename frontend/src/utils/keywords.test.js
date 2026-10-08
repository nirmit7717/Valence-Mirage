import { test } from 'node:test';
import assert from 'node:assert/strict';
import { MAX_KEYWORDS, addKeywords, keywordsToText, splitKeywords } from './keywords.js';

test('splits pasted text on commas, semicolons and newlines', () => {
  assert.deepEqual(splitKeywords(' haunted castle, undead;siege\n  heist ,, '), ['haunted castle', 'undead', 'siege', 'heist']);
});

test('adds keywords without duplicates (case-insensitive)', () => {
  assert.deepEqual(addKeywords(['Heist'], ['heist', 'neon city', '  Neon   City ']), ['Heist', 'neon city']);
});

test('caps the number of keywords and the total length the server accepts', () => {
  const many = Array.from({ length: 20 }, (_, i) => `kw${i}`);
  assert.equal(addKeywords([], many).length, MAX_KEYWORDS);

  const long = Array.from({ length: 10 }, (_, i) => `${'x'.repeat(30)}${i}`);
  assert.ok(keywordsToText(addKeywords([], long)).length <= 200);
});

test('joins the list into the single string the server expects', () => {
  assert.equal(keywordsToText(['haunted castle', 'undead siege']), 'haunted castle, undead siege');
  assert.equal(keywordsToText([]), '');
});
