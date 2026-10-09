import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  classIcon,
  createFlavor,
  enemyIcon,
  enemyRef,
  fill,
  resultDetail,
  weaponCategory,
} from './combatFlavor.js';

// Deterministic "random": cycles through the given values.
const sequence = (...values) => {
  let i = 0;
  return () => values[i++ % values.length];
};

test('weapons are grouped by how they hit', () => {
  assert.equal(weaponCategory('Iron Longsword'), 'blade');
  assert.equal(weaponCategory('Twin Daggers'), 'blade');
  assert.equal(weaponCategory('Holy Mace'), 'blunt');
  assert.equal(weaponCategory('Oak Staff'), 'arcane');
  assert.equal(weaponCategory('Lute of Embers'), 'music');
  assert.equal(weaponCategory('Plasma Rifle'), 'ranged');
  assert.equal(weaponCategory('Unarmed Strike'), 'unarmed');
  assert.equal(weaponCategory('Mysterious Relic'), 'blade'); // a sensible default
});

test('enemy and class icons', () => {
  assert.equal(enemyIcon('construct'), '🤖');
  assert.equal(enemyIcon('undead'), '💀');
  assert.equal(enemyIcon('beast'), '🐺');
  assert.equal(enemyIcon(undefined), '👹');
  assert.equal(classIcon('bard'), '🎵');
  assert.equal(classIcon('wizard'), '🔮');
});

test('enemies are referred to naturally', () => {
  assert.equal(enemyRef('Goblin Scavenger'), 'the Goblin Scavenger');
  assert.equal(enemyRef('Captain Vex'), 'Captain Vex');
  assert.equal(enemyRef('Malachar'), 'Malachar');
  assert.equal(enemyRef('The Hollow King'), 'The Hollow King');
});

test('lines fill in the weapon, the enemy and what the blow lands on', () => {
  const flavor = createFlavor({ enemy: 'Security Drone', archetype: 'construct', genre: 'scifi', rng: () => 0 });
  assert.equal(flavor.attackLine('Iron Longsword', 'hit'), 'Your Iron Longsword bites into the Security Drone');
  assert.match(flavor.attackLine('Iron Longsword', 'glance'), /chassis|Security Drone|glances/);
  assert.equal(fill('{a} and {b}', { a: 1 }), '1 and ');
});

test('the same line never comes twice in a row', () => {
  const flavor = createFlavor({ enemy: 'Bandit', archetype: 'skirmisher', rng: () => 0 });
  let previous = '';
  for (let i = 0; i < 12; i += 1) {
    const line = flavor.attackLine('Iron Longsword', 'hit');
    assert.notEqual(line, previous);
    previous = line;
  }
});

test('enemy moves read differently by archetype and name their special moves', () => {
  const beast = createFlavor({ enemy: 'Corrupted Wolf', archetype: 'beast', rng: () => 0 });
  const machine = createFlavor({ enemy: 'Security Drone', archetype: 'construct', rng: () => 0 });
  assert.notEqual(beast.enemyMoveLine('Attack', 'hit'), machine.enemyMoveLine('Attack', 'hit'));
  assert.match(beast.enemyMoveLine('Savage Bite', 'hit'), /Savage Bite/);
  assert.match(beast.enemyMoveLine('Howl', 'debuff', 'weaken'), /weaken/);
  assert.match(machine.enemyMoveLine('Attack', 'stunned'), /Security Drone/);
});

test('taunts fit the enemy: speech for people, actions for beasts and machines', () => {
  const soldier = createFlavor({ enemy: 'Tower Guard', archetype: 'soldier', rng: sequence(0.1, 0.6) });
  const wolf = createFlavor({ enemy: 'Corrupted Wolf', archetype: 'beast', rng: sequence(0.1, 0.6) });
  assert.match(soldier.tauntLine('start'), /^"/);
  assert.match(wolf.tauntLine('start'), /Corrupted Wolf/);
  assert.match(wolf.tauntLine('half'), /Corrupted Wolf/);
  assert.match(wolf.tauntLine('defeat'), /Corrupted Wolf/);
});

test('the boss gets its own opening line', () => {
  const boss = createFlavor({ enemy: 'Malachar', archetype: 'caster', threat: 'boss', rng: () => 0.9 });
  assert.match(boss.tauntLine('start'), /Malachar|ends here/);
});

test('numbers stay small and separate from the story line', () => {
  assert.equal(resultDetail({ damage: { target: 'enemy', amount: 7 } }), '\u22127');
  assert.equal(resultDetail({ damage: { target: 'enemy', amount: 11, crit: true } }), '\u221211 crit');
  assert.equal(resultDetail({ damage: { target: 'player', amount: 20, heal: true } }), '+20 HP');
  assert.equal(resultDetail({ diceInfo: { roll: 4, target: 12, success: false } }), 'rolled 4 vs 12');
  assert.equal(resultDetail({ effect: 'stun' }, () => '💫'), '💫 stun');
  assert.equal(resultDetail(null), '');
});

test('effects read naturally inside a sentence', () => {
  const flavor = createFlavor({ enemy: 'Shadow Mage', archetype: 'caster', rng: () => 0 });
  assert.equal(flavor.enemyMoveLine('Hex', 'debuff', 'weaken'), "The Shadow Mage's Hex leaves you weakened");
});

test('lines for the new enemy moves: healing, charging and a boss\'s second phase', () => {
  const flavor = createFlavor({ enemy: 'Malachar', archetype: 'caster', threat: 'boss', rng: () => 0 });
  assert.match(flavor.enemyMoveLine('Dark Mending', 'heal'), /Dark Mending/);
  assert.match(flavor.enemyMoveLine('Charging Up', 'charge'), /Malachar/);
  assert.match(flavor.tauntLine('phase'), /power/);
});

test('details mention hits, blunted blows, drains, immunity and lost wind-ups', () => {
  assert.equal(resultDetail({ damage: { amount: 18 }, hits: 2 }), '\u221218 · 2 hits');
  assert.equal(resultDetail({ damage: { amount: 14 }, blunted: true }), '\u221214 · blunted');
  assert.equal(resultDetail({ damage: { amount: 16 }, drained: 8 }), '\u221216 · drains 8');
  assert.equal(resultDetail({ damage: { amount: 9 }, immune: 'bleed' }), '\u22129 · immune to bleed');
  assert.equal(resultDetail({ effect: 'stun', cancelled: 'Crushing Blow' }, () => '💫'), '💫 stun · Crushing Blow lost');
});
