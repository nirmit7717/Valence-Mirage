// Run with: npm test   (Node's built-in test runner, no extra dependencies)
import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  cloneCombatState,
  createCombatState,
  enemyIntro,
  resolveEnemyTurn,
  resolvePlayerAttack,
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
