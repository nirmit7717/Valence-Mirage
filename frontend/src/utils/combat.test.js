// Run with: npm test   (Node's built-in test runner, no extra dependencies)
import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  applyEffect,
  buildResolvePayload,
  cloneCombatState,
  createCombatState,
  enemyIntro,
  getDamageModifier,
  getStatusIcon,
  planIntent,
  resolveEnemyTurn,
  resolvePlayerAttack,
  resolvePlayerItem,
  resolvePlayerSkill,
} from './combat.js';

const combatData = () => ({
  combat_id: 'c1',
  enemy: { name: 'Corporate Security Drone', hp: 20, max_hp: 20, armor: 0, attack_bonus: 30, abilities: [] },
  player: { name: 'Ash', hp: 50, max_hp: 50, mana: 40, max_mana: 40, armor: 0, attack_bonus: 30 },
  abilities: [],
  inventory: [{ name: 'Health Potion', type: 'consumable', hp_restore: 20, mana_restore: 0 }],
  enemy_tier: 1,
});

// Bug: the player's HP dropped before the enemy's dice animation finished, because the
// enemy turn mutated the very object React was rendering. Turns now run on a copy.
test('enemy turn on a clone leaves the displayed state untouched', (t) => {
  t.mock.method(Math, 'random', () => 0.5); // roll 11, no dodge; attack bonus guarantees a hit
  const shown = createCombatState(combatData());
  shown.enemy.status_effects.push({ name: 'bleed', duration: 2 });

  const next = cloneCombatState(shown);
  const result = resolveEnemyTurn(next);

  assert.ok(result.damage, 'enemy should hit');
  assert.ok(next.player.hp < 50, 'the copy takes the damage');
  assert.equal(shown.player.hp, 50, 'what is on screen does not change until committed');
  assert.equal(shown.enemy.hp, 20, 'damage-over-time ticks only hit the copy');
  assert.equal(shown.enemy.status_effects[0].duration, 2, 'effect durations are not shared');
});

test('player attack on a clone does not touch the displayed enemy', (t) => {
  t.mock.method(Math, 'random', () => 0.5);
  const shown = createCombatState(combatData());
  const next = cloneCombatState(shown);

  resolvePlayerAttack(next, 'Iron Sword', '1d8+2');

  assert.ok(next.enemy.hp < 20);
  assert.equal(shown.enemy.hp, 20);
});

test('a skill costs its mana exactly once', () => {
  const state = cloneCombatState(createCombatState(combatData()));
  resolvePlayerSkill(state, { name: 'Focus Mind', ability_type: 'support', mana_cost: 8, status_effect: 'focus', status_duration: 1 });
  assert.equal(state.player.mana, 32);
});

test('enemy intro uses the campaign name as-is', () => {
  assert.equal(enemyIntro('Corporate Security Drone'), '⚔️ Corporate Security Drone appears!');
  assert.equal(enemyIntro(''), '⚔️ An enemy appears!');
});

// ─── Ability targets ───

const warCry = { name: 'War Cry', ability_type: 'support', mana_cost: 5, status_effect: 'weaken', status_duration: 2, target: 'enemy' };
const lullaby = { name: 'Lullaby', ability_type: 'support', mana_cost: 10, status_effect: 'stun', status_duration: 1, target: 'enemy' };
const guard = { name: 'Guard', ability_type: 'defend', mana_cost: 0, status_effect: 'blocking', status_duration: 1, target: 'self' };

test('War Cry weakens the enemy, not the player', () => {
  const state = createCombatState(combatData());
  resolvePlayerSkill(state, warCry);
  assert.deepEqual(state.enemy.status_effects.map(e => e.name), ['weaken']);
  assert.deepEqual(state.player.status_effects, []);
  assert.equal(state.player.mana, 35);
});

test('Lullaby stuns the enemy so it skips its turn', () => {
  const state = createCombatState(combatData());
  resolvePlayerSkill(state, lullaby);
  const turn = resolveEnemyTurn(state);
  assert.match(turn.log, /stunned/);
  assert.equal(state.player.hp, 50);
});

test('Guard still protects the player', () => {
  const state = createCombatState(combatData());
  resolvePlayerSkill(state, guard);
  assert.deepEqual(state.player.status_effects.map(e => e.name), ['blocking']);
  assert.deepEqual(state.enemy.status_effects, []);
});

test('old payloads without a target still send debuffs to the enemy', () => {
  const state = createCombatState(combatData());
  const { target, ...legacyWarCry } = warCry; // eslint-disable-line no-unused-vars
  resolvePlayerSkill(state, legacyWarCry);
  assert.deepEqual(state.enemy.status_effects.map(e => e.name), ['weaken']);
});

// ─── What the server receives ───

test('keeps the combat id and records items used', () => {
  const state = createCombatState(combatData());
  assert.equal(state.combat_id, 'c1');
  assert.deepEqual(state.items_used, []);

  resolvePlayerItem(state, 'Health Potion', 20, 0);
  assert.deepEqual(state.items_used, ['Health Potion']);
  assert.equal(state.inventory.length, 0);
});

test('the resolve payload carries everything the server checks', () => {
  const state = createCombatState(combatData());
  resolvePlayerItem(state, 'Health Potion', 20, 0);
  state.turn = 4;
  state.logEntries = ['⚔️ Corporate Security Drone appears!', 'You strike for 6 damage!'];

  const payload = buildResolvePayload('victory', state);

  assert.equal(payload.combat_id, 'c1');
  assert.equal(payload.result, 'victory');
  assert.equal(payload.enemy_name, 'Corporate Security Drone');
  assert.deepEqual(payload.items_used, ['Health Potion']);
  assert.equal(payload.turns_taken, 4);
  assert.deepEqual(payload.combat_log[1], { actor: 'player', message: 'You strike for 6 damage!' });
  assert.equal(payload.combat_log[0].message, 'Corporate Security Drone appears!');
});

test('a defeat always reports 0 HP', () => {
  const state = createCombatState(combatData());
  state.player.hp = -7;
  assert.equal(buildResolvePayload('defeat', state).player_hp, 0);
});

// ─── Enemy effects (Task 5) ───

const woundedEnemy = (abilities) => {
  const state = createCombatState(combatData());
  state.enemy.abilities = abilities;
  state.enemy.hp = 6; // below half: the enemy reaches for its abilities
  state.enemyIntent = planIntent(state); // plan with the new abilities and HP
  return state;
};

test('empowered raises damage by half, lasts at most two turns and has an icon', () => {
  const enemy = { status_effects: [] };
  applyEffect(enemy, 'empowered', 3);
  assert.deepEqual(enemy.status_effects, [{ name: 'empowered', duration: 2 }]);
  assert.equal(getDamageModifier(enemy), 1.5);
  assert.equal(getStatusIcon('empowered'), '💢');
});

test('a self-buff empowers the enemy instead of hitting the player', (t) => {
  t.mock.method(Math, 'random', () => 0.5);
  const state = woundedEnemy([{ name: 'Blood Frenzy', status_effect: 'empowered', status_duration: 3, target: 'self' }]);

  const turn = resolveEnemyTurn(state);

  assert.deepEqual(state.enemy.status_effects.map(e => e.name), ['empowered']);
  assert.deepEqual(state.player.status_effects, []);
  assert.equal(state.player.hp, 50);
  assert.match(turn.log, /Blood Frenzy/);
  assert.equal(turn.damage, undefined);
});

test('a status-only move applies its effect without damage', (t) => {
  t.mock.method(Math, 'random', () => 0.5);
  const state = woundedEnemy([{ name: 'Hex', status_effect: 'weaken', status_duration: 2 }]);

  const turn = resolveEnemyTurn(state);

  assert.equal(state.player.hp, 50);
  assert.deepEqual(state.player.status_effects.map(e => e.name), ['weaken']);
  assert.match(turn.log, /Hex/);
});

test('an empowered enemy hits harder', (t) => {
  t.mock.method(Math, 'random', () => 0.5);
  const calm = createCombatState(combatData());
  const raging = createCombatState(combatData());
  applyEffect(raging.enemy, 'empowered', 2);

  const normal = resolveEnemyTurn(calm).damage.amount;
  const boosted = resolveEnemyTurn(raging).damage.amount;

  assert.equal(boosted, Math.floor(normal * 1.5));
});

// ─── Story-aware log (Task 6) ───

test('only the story line of each log entry goes to the server', () => {
  const state = createCombatState({ ...combatData(), genre: 'scifi', scene: 'Neon rain.' });
  state.logEntries = [
    { text: 'Sparks burst from the drone\u2019s chassis', detail: '\u22127', type: 'player' },
    { text: 'The drone slams into you', detail: '\u22125', type: 'enemy' },
  ];

  const { combat_log: log } = buildResolvePayload('victory', state);

  assert.deepEqual(log, [
    { actor: 'player', message: 'Sparks burst from the drone\u2019s chassis' },
    { actor: 'enemy', message: 'The drone slams into you' },
  ]);
  assert.equal(state.genre, 'scifi');
  assert.equal(state.scene, 'Neon rain.');
});

test('results say what kind of moment they were', (t) => {
  t.mock.method(Math, 'random', () => 0.5);
  const state = createCombatState(combatData());
  assert.equal(resolvePlayerAttack(state, 'Iron Sword', '1d8+2').kind, 'hit');
  const enemyTurn = resolveEnemyTurn(state);
  assert.equal(enemyTurn.kind, 'hit');
  assert.equal(enemyTurn.move, 'Attack');
});
