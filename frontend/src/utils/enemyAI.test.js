import { test } from 'node:test';
import assert from 'node:assert/strict';
import { applyEffect, canAct, createCombatState, hasEffect, resolvePlayerSkill } from './combat.js';
import {
  FLURRY_MULTIPLIER,
  HEAVY_MULTIPLIER,
  OVERCHARGE_MULTIPLIER,
  executeIntent,
  planIntent,
  reactToPlayer,
  resolveEnemyTurn,
} from './enemyAI.js';

// With Math.random() = 0.5: d20 rolls 11, a basic enemy hit is 3 + 1 + attack bonus.
const ATTACK_BONUS = 12;
const BASIC_HIT = 3 + 1 + ATTACK_BONUS;

const fight = ({ archetype, threat = 'standard', abilities = [], hp = 40 } = {}) => createCombatState({
  combat_id: 'c1',
  enemy: { name: 'Foe', hp, max_hp: 40, armor: 0, attack_bonus: ATTACK_BONUS, abilities, archetype, threat },
  player: { name: 'Ash', hp: 200, max_hp: 200, mana: 40, max_mana: 40, armor: 0, attack_bonus: 30 },
  abilities: [],
  inventory: [],
  enemy_tier: 1,
});

// Put the enemy at a point in its rotation and re-plan.
const atTurn = (state, turn) => {
  state.enemy.ai.turn = turn;
  state.enemyIntent = planIntent(state);
  return state.enemyIntent;
};

const focus = { name: 'Shadow Step', ability_type: 'support', mana_cost: 0, status_effect: 'focus', status_duration: 1, target: 'self' };
const cleave = { name: 'Cleave', ability_type: 'attack', damage_dice: '1d12+5', mana_cost: 0, status_effect: 'bleed', status_duration: 3 };
const poisonBlade = { name: 'Poison Blade', ability_type: 'attack', damage_dice: '1d6+2', mana_cost: 0, status_effect: 'poisoned', status_duration: 3 };

test('the first move is planned when the fight starts', () => {
  const state = fight({ archetype: 'soldier' });
  assert.equal(state.enemyIntent.name, 'Attack');
  assert.equal(state.enemyIntent.label, 'Attack');
});

// ─── Brute ───

test('a brute winds up a heavy blow every third turn, with a warning', (t) => {
  t.mock.method(Math, 'random', () => 0.5);
  const state = fight({ archetype: 'brute' });
  assert.equal(atTurn(state, 0).style, 'attack');
  const heavy = atTurn(state, 2);
  assert.equal(heavy.style, 'heavy');
  assert.equal(heavy.label, 'Crushing Blow ⚠');

  const result = resolveEnemyTurn(state);

  assert.equal(result.damage.amount, Math.floor(BASIC_HIT * HEAVY_MULTIPLIER));
  assert.notEqual(state.enemyIntent.style, 'heavy'); // the next move is planned
});

test('a stun cancels the wind-up', (t) => {
  t.mock.method(Math, 'random', () => 0.5);
  const state = fight({ archetype: 'brute' });
  atTurn(state, 2);
  applyEffect(state.enemy, 'stun', 1);

  const result = resolveEnemyTurn(state);

  assert.equal(result.kind, 'stunned');
  assert.equal(result.cancelled, 'Crushing Blow');
  assert.equal(state.player.hp, 200);
  assert.notEqual(state.enemyIntent.style, 'heavy');
});

test('blocking blunts a heavy blow', (t) => {
  t.mock.method(Math, 'random', () => 0.5);
  const state = fight({ archetype: 'brute' });
  atTurn(state, 2);
  applyEffect(state.player, 'blocking', 1);

  const result = executeIntent(state, state.enemyIntent);

  assert.equal(result.blunted, true);
  assert.equal(result.damage.amount, Math.floor(Math.floor(BASIC_HIT * HEAVY_MULTIPLIER) / 2));
});

// ─── Soldier ───

test('a soldier answers a buff by weakening the player', () => {
  const state = fight({ archetype: 'soldier' });
  resolvePlayerSkill(state, focus);
  assert.equal(state.enemyIntent.key, 'suppress');
  assert.equal(state.enemyIntent.effect, 'weaken');
  assert.equal(state.enemyIntent.reaction, true);
});

test('a hurt soldier raises its guard', () => {
  const state = fight({ archetype: 'soldier', hp: 20 });
  const guard = atTurn(state, 1);
  assert.equal(guard.name, 'Raise Guard');
  executeIntent(state, guard);
  assert.ok(hasEffect(state.enemy, 'blocking'));
});

// ─── Skirmisher ───

test('a skirmisher strikes twice at reduced damage', (t) => {
  t.mock.method(Math, 'random', () => 0.5);
  const state = fight({ archetype: 'skirmisher' });
  const flurry = atTurn(state, 0);
  assert.equal(flurry.hits, 2);

  const result = executeIntent(state, flurry);

  assert.equal(result.hits, 2);
  assert.equal(result.damage.amount, 2 * Math.floor(BASIC_HIT * FLURRY_MULTIPLIER));
});

test('a skirmisher\'s cut makes the player bleed', (t) => {
  t.mock.method(Math, 'random', () => 0.5);
  const state = fight({ archetype: 'skirmisher' });
  executeIntent(state, atTurn(state, 1));
  assert.ok(hasEffect(state.player, 'bleed'));
});

// ─── Beast ───

test('a beast pounces to stun, and never twice in a row', (t) => {
  t.mock.method(Math, 'random', () => 0.5);
  const state = fight({ archetype: 'beast' });
  assert.equal(atTurn(state, 1).key, 'pounce');

  resolveEnemyTurn(state);

  assert.equal(canAct(state.player), false); // the player loses a turn
  assert.notEqual(state.enemyIntent.key, 'pounce');
});

test('a wounded beast frenzies once', (t) => {
  t.mock.method(Math, 'random', () => 0.5);
  const state = fight({ archetype: 'beast', hp: 15 });
  assert.equal(reactToPlayer(state).key, 'frenzy');
  resolveEnemyTurn(state);
  assert.ok(hasEffect(state.enemy, 'empowered'));
  state.enemyIntent = planIntent(state);
  assert.notEqual(reactToPlayer(state).key, 'frenzy');
});

// ─── Caster ───

test('a caster opens with a hex that weakens without damage', (t) => {
  t.mock.method(Math, 'random', () => 0.5);
  const state = fight({ archetype: 'caster' });
  assert.equal(state.enemyIntent.key, 'hex');

  const result = resolveEnemyTurn(state);

  assert.equal(result.kind, 'debuff');
  assert.equal(state.player.hp, 200);
  assert.ok(hasEffect(state.player, 'weaken'));
  assert.equal(state.enemyIntent.key, 'blast');
});

test('a badly hurt caster heals itself, once', (t) => {
  t.mock.method(Math, 'random', () => 0.5);
  const state = fight({ archetype: 'caster', hp: 8 });
  assert.equal(reactToPlayer(state).key, 'mend');
  const result = resolveEnemyTurn(state);
  assert.equal(result.kind, 'heal');
  assert.equal(state.enemy.hp, 18);
  state.enemy.hp = 8;
  state.enemyIntent = planIntent(state);
  assert.notEqual(reactToPlayer(state).key, 'mend');
});

test('a caster below 40% shields itself instead when it is not yet desperate', () => {
  const state = fight({ archetype: 'caster', hp: 14 });
  assert.equal(reactToPlayer(state).key, 'ward');
});

// ─── Construct ───

test('a construct charges up, then hits twice as hard', (t) => {
  t.mock.method(Math, 'random', () => 0.5);
  const state = fight({ archetype: 'construct' });
  const charge = atTurn(state, 2);
  assert.equal(charge.style, 'charge');
  assert.equal(charge.warn, true);

  resolveEnemyTurn(state);
  assert.equal(state.enemyIntent.key, 'overcharge');
  assert.equal(state.enemyIntent.label.endsWith('⚠'), true);

  const result = resolveEnemyTurn(state);
  assert.equal(result.damage.amount, BASIC_HIT * OVERCHARGE_MULTIPLIER);
  assert.notEqual(state.enemyIntent.key, 'overcharge');
});

test('a stun drains a construct\'s charge', (t) => {
  t.mock.method(Math, 'random', () => 0.5);
  const state = fight({ archetype: 'construct' });
  atTurn(state, 2);
  resolveEnemyTurn(state); // charged
  applyEffect(state.enemy, 'stun', 1);

  const result = resolveEnemyTurn(state);

  assert.equal(result.cancelled, 'Overcharged Strike');
  assert.notEqual(state.enemyIntent.key, 'overcharge');
});

test('machines do not bleed or take poison', (t) => {
  t.mock.method(Math, 'random', () => 0.5);
  const state = fight({ archetype: 'construct' });
  const cut = resolvePlayerSkill(state, cleave);
  resolvePlayerSkill(state, poisonBlade);
  assert.equal(cut.immune, 'bleed');
  assert.equal(cut.effect, null);
  assert.deepEqual(state.enemy.status_effects, []);
});

// ─── Undead ───

test('the undead drain life, healing half the damage', (t) => {
  t.mock.method(Math, 'random', () => 0.5);
  const state = fight({ archetype: 'undead', hp: 10 });
  const drain = atTurn(state, 1);
  assert.equal(drain.key, 'drain');

  const result = executeIntent(state, drain);

  assert.equal(result.drained, Math.floor(BASIC_HIT / 2));
  assert.equal(state.enemy.hp, 10 + Math.floor(BASIC_HIT / 2));
});

test('the undead cannot be poisoned, but they can bleed', (t) => {
  t.mock.method(Math, 'random', () => 0.5);
  const state = fight({ archetype: 'undead' });
  assert.equal(resolvePlayerSkill(state, poisonBlade).immune, 'poisoned');
  assert.equal(resolvePlayerSkill(state, cleave).effect, 'bleed');
});

// ─── Horror ───

test('a horror alternates dread and rending', (t) => {
  t.mock.method(Math, 'random', () => 0.5);
  const state = fight({ archetype: 'horror' });
  assert.equal(state.enemyIntent.key, 'dread');
  resolveEnemyTurn(state);
  assert.ok(hasEffect(state.player, 'weaken'));
  assert.equal(state.enemyIntent.key, 'rend');
  resolveEnemyTurn(state);
  assert.ok(hasEffect(state.player, 'bleed'));
});

// ─── Elites and bosses ───

test('an elite rallies once at half health', (t) => {
  t.mock.method(Math, 'random', () => 0.5);
  const state = fight({ archetype: 'soldier', threat: 'elite', hp: 20 });
  assert.equal(reactToPlayer(state).key, 'rally');

  const result = resolveEnemyTurn(state);

  assert.equal(result.kind, 'heal');
  assert.equal(state.enemy.hp, 28);
  assert.ok(hasEffect(state.enemy, 'focus'));
  state.enemy.hp = 20;
  state.enemyIntent = planIntent(state);
  assert.notEqual(reactToPlayer(state).key, 'rally');
});

const bossMoves = [
  { name: 'Shadow Lash', damage_dice: '1d8+2' },
  { name: 'Hex', status_effect: 'weaken', status_duration: 2 },
  { name: 'Devastating Onslaught', damage_dice: '3d10+7' },
];

test('a boss holds its finisher back until phase two', (t) => {
  t.mock.method(Math, 'random', () => 0.5);
  const state = fight({ archetype: 'caster', threat: 'boss', abilities: bossMoves });
  for (let turn = 0; turn < 6; turn++) {
    assert.notEqual(atTurn(state, turn).name, 'Devastating Onslaught');
  }
});

test('at half health a boss enters phase two: taunt, empowered, finisher unlocked', (t) => {
  t.mock.method(Math, 'random', () => 0.5);
  const state = fight({ archetype: 'caster', threat: 'boss', abilities: bossMoves, hp: 20 });
  const phase = reactToPlayer(state);
  assert.equal(phase.key, 'phase');
  assert.equal(phase.warn, true);

  const result = resolveEnemyTurn(state);

  assert.equal(result.taunt, 'phase');
  assert.ok(hasEffect(state.enemy, 'empowered'));
  assert.equal(state.enemy.ai.phase, 2);
  const finisher = atTurn(state, 3);
  assert.equal(finisher.name, 'Devastating Onslaught');
  assert.equal(finisher.label, 'Devastating Onslaught ⚠');
  assert.equal(reactToPlayer(state).key, 'finisher'); // phase two only happens once
});
