import { test } from 'node:test';
import assert from 'node:assert/strict';
import { describeLevelUps, xpBadgeText } from './progression.js';

test('xp badge shows what the turn earned', () => {
  assert.equal(xpBadgeText(25), '+25 XP');
  assert.equal(xpBadgeText(0), '');
  assert.equal(xpBadgeText(undefined), '');
});

test('a single level-up lists its gains', () => {
  const summary = describeLevelUps([
    { level: 2, hp_gain: 8, mana_gain: 3, stats: { strength: 1, control: 1 } },
  ]);
  assert.deepEqual(summary, { level: 2, levelsGained: 1, gains: ['+8 max HP', '+3 max mana', '+1 STR', '+1 CON'] });
});

test('several level-ups at once are added up', () => {
  const summary = describeLevelUps([
    { level: 2, hp_gain: 5, mana_gain: 8, stats: { intelligence: 1, control: 1 } },
    { level: 3, hp_gain: 5, mana_gain: 8, stats: { intelligence: 1 } },
  ]);
  assert.equal(summary.level, 3);
  assert.equal(summary.levelsGained, 2);
  assert.deepEqual(summary.gains, ['+10 max HP', '+16 max mana', '+2 INT', '+1 CON']);
});

test('no level-ups means no banner', () => {
  assert.equal(describeLevelUps([]), null);
  assert.equal(describeLevelUps(undefined), null);
  assert.equal(describeLevelUps({}), null); // the old dict shape
});
