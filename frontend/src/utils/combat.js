// ═══════════════════════════════════════════════
//  Combat — Pure combat resolution functions
//  Ported from the original client-side engine
//  Dice and status effects live in combatRules.js; enemy behavior in enemyAI.js.
// ═══════════════════════════════════════════════

import {
  applyEffect,
  getArmorModifier,
  getDamageModifier,
  getRollModifier,
  getStatusIcon,
  rollD20,
  rollDice,
} from './combatRules.js';
import { planIntent, reactToPlayer } from './enemyAI.js';

export {
  applyEffect,
  canAct,
  getArmorModifier,
  getDamageModifier,
  getDodgeChance,
  getRollModifier,
  getStatusIcon,
  hasEffect,
  isImmune,
  rollD20,
  rollDice,
  tickEffects,
} from './combatRules.js';
export { executeIntent, planIntent, reactToPlayer, resolveEnemyTurn } from './enemyAI.js';

export function getWeaponDice(weaponName) {
  const w = weaponName.toLowerCase();
  if (w.includes('greatsword') || w.includes('dark steel')) return '2d6+3';
  if (w.includes('longsword') || (w.includes('sword') && !w.includes('dark'))) return '1d8+2';
  if (w.includes('dagger') || w.includes('twin')) return '1d6+1';
  if (w.includes('rapier')) return '1d8+1';
  if (w.includes('mace') || w.includes('hammer') || w.includes('war hammer')) return '1d8+2';
  if (w.includes('staff') || w.includes('oak')) return '1d6+1';
  if (w.includes('lute')) return '1d4';
  return '1d6+1';
}

// Deep copy of a combat state. Turns are resolved on a copy and only committed to
// React state after their dice animation lands, so HP never changes mid-roll.
export function cloneCombatState(state) {
  return structuredClone(state);
}

export function enemyIntro(name) {
  return `⚔️ ${(name || 'An enemy').trim()} appears!`;
}

// Body for POST /session/:id/combat/resolve. The server checks it against the stored fight.
export function buildResolvePayload(result, state) {
  return {
    combat_id: state.combat_id || '',
    result,
    player_hp: result === 'defeat' ? 0 : Math.max(0, Math.round(state.player.hp)),
    player_mana: Math.max(0, Math.round(state.player.mana)),
    enemy_name: state.enemy.name,
    items_used: [...(state.items_used || [])],
    // Story lines only (the small numbers shown next to them stay in the browser).
    combat_log: (state.logEntries || []).slice(-12).map(entry => {
      const message = typeof entry === 'string' ? entry : entry.text || '';
      const actor = typeof entry === 'string' || !['player', 'enemy'].includes(entry.type)
        ? (/\byou\b/i.test(message) ? 'player' : 'enemy')
        : entry.type;
      return { actor, message: message.replace(/^(?:⚔️|🧪|⚡|🏆|💀|💫|💨)+\s*/u, '') };
    }),
    turns_taken: Math.max(1, state.turn || 1),
  };
}

export function createCombatState(combatData) {
  const state = {
    enemy: { ...combatData.enemy, status_effects: [] },
    player: {
      ...combatData.player,
      status_effects: [],
      armor: combatData.player.armor || 0,
      attack_bonus: combatData.player.attack_bonus || 0,
    },
    abilities: combatData.abilities || [],
    inventory: combatData.inventory || [],
    turn: 1,
    resolved: false,
    enemy_tier: combatData.enemy_tier || 1,
    // Story context for flavor text (utils/combatFlavor.js).
    genre: combatData.genre || 'fantasy',
    scene: combatData.scene || '',
    // Sent back to the server, which checks the result against the stored encounter.
    combat_id: combatData.combat_id || '',
    items_used: [],
  };
  // The enemy's first move, shown on its card from the start.
  state.enemyIntent = planIntent(state);
  return state;
}

// After every player action the enemy may change its planned move in response
// (a soldier answering a buff, a boss entering phase 2...), so the card stays true.
function withReaction(state, result) {
  reactToPlayer(state);
  return result;
}

function playerAttack(state, weaponName, dice) {
  const roll = rollD20();
  const atkBonus = state.player.attack_bonus;
  const rollMod = getRollModifier(state.player);
  const total = roll + atkBonus + rollMod;
  const enemyArmor = state.enemy.armor + getArmorModifier(state.enemy);
  const threshold = 8 + enemyArmor;
  const isCrit = roll === 20;
  const isMiss = roll === 1;
  const hit = isCrit || total >= threshold;

  const diceInfo = { roll, target: threshold, success: hit, crit: isCrit || isMiss };

  if (isMiss) {
    return { log: `You swing ${weaponName}... MISS! (rolled 1)`, kind: 'miss', type: 'player', flash: 'player', diceInfo };
  }
  if (!hit) {
    return { log: `Your ${weaponName} glances off their armor. (${roll}+${(atkBonus + rollMod).toFixed(1)} vs AC ${threshold})`, kind: 'glance', type: 'player', flash: 'player', diceInfo };
  }

  let dmg = rollDice(dice);
  dmg = Math.max(1, Math.floor(dmg * getDamageModifier(state.player)));
  if (isCrit) dmg = Math.floor(dmg * 1.5);
  state.enemy.hp -= dmg;

  const critTxt = isCrit ? '⚡ CRITICAL! ' : '';
  return {
    log: `${critTxt}You strike with ${weaponName} for ${dmg} damage! (${roll}+${(atkBonus + rollMod).toFixed(1)})`,
    kind: isCrit ? 'crit' : 'hit',
    type: isCrit ? 'crit' : 'player',
    damage: { target: 'enemy', amount: dmg, crit: isCrit },
    flash: 'enemy',
    diceInfo,
  };
}

export function resolvePlayerAttack(state, weaponName, dice) {
  return withReaction(state, playerAttack(state, weaponName, dice));
}

// Who a support/defend ability's status effect lands on. Older payloads have no
// `target`; debuffs (weaken/stun) on a support ability are meant for the enemy.
function abilityTargetsEnemy(ability) {
  if (ability.target) return ability.target === 'enemy';
  return ['weaken', 'stun'].includes((ability.status_effect || '').toLowerCase());
}

function playerSkill(state, ability) {
  // The only place a skill's mana cost is paid.
  state.player.mana = Math.max(0, state.player.mana - ability.mana_cost);

  // Support / defend
  if (ability.ability_type === 'support' || ability.ability_type === 'defend') {
    if (ability.name.toLowerCase() === 'heal') {
      const heal = Math.floor(Math.random() * 11) + 15;
      state.player.hp = Math.min(state.player.max_hp, state.player.hp + heal);
      return { log: `You cast ${ability.name} and restore ${heal} HP!`, kind: 'heal', type: 'player', damage: { target: 'player', amount: heal, heal: true } };
    }
    if (ability.status_effect) {
      const icon = getStatusIcon(ability.status_effect);
      const effect = ability.status_effect;
      if (abilityTargetsEnemy(ability)) {
        if (!applyEffect(state.enemy, effect, ability.status_duration || 2)) {
          return { log: `${state.enemy.name} is immune to ${effect}!`, kind: 'debuff', effect: null, immune: effect, type: 'player' };
        }
        return { log: `${icon} You use ${ability.name}! ${state.enemy.name} is afflicted with ${effect}.`, kind: 'debuff', effect, type: 'player', flash: 'enemy' };
      }
      applyEffect(state.player, effect, ability.status_duration || 2);
      return { log: `${icon} You use ${ability.name}! Gained ${effect}.`, kind: 'buff', effect, type: 'player' };
    }
    return { log: `You use ${ability.name}!`, kind: 'buff', type: 'player' };
  }

  // Attack / Spell
  const roll = rollD20();
  const atkBonus = state.player.attack_bonus;
  const rollMod = getRollModifier(state.player);
  const total = roll + atkBonus + rollMod;
  const enemyArmor = state.enemy.armor + getArmorModifier(state.enemy);
  const threshold = 8 + enemyArmor;
  const isCrit = roll === 20;
  const isMiss = roll === 1;

  if (isMiss) return { log: `${ability.name} misses! (rolled 1)`, kind: 'miss', type: 'player', flash: 'player', diceInfo: { roll: 1, target: threshold, success: false, crit: true } };
  if (total < threshold && !isCrit) return { log: `${ability.name} glances off armor. (${roll}+${(atkBonus + rollMod).toFixed(1)} vs AC ${threshold})`, kind: 'glance', type: 'player', flash: 'player', diceInfo: { roll, target: threshold, success: false, crit: false } };

  const dice = ability.damage_dice || '1d6';
  let dmg = rollDice(dice);
  dmg = Math.max(1, Math.floor(dmg * getDamageModifier(state.player)));
  if (isCrit) dmg = Math.floor(dmg * 1.5);
  state.enemy.hp -= dmg;

  // Machines don't bleed and the dead can't be poisoned (combatRules.js).
  let effect = ability.status_effect || null;
  let immune = null;
  if (effect && !applyEffect(state.enemy, effect, ability.status_duration || 2)) {
    immune = effect;
    effect = null;
  }

  const critTxt = isCrit ? '⚡ CRITICAL! ' : '';
  const effectTxt = effect ? ` ${getStatusIcon(effect)} Applied ${effect}!` : immune ? ` It is immune to ${immune}.` : '';
  return {
    log: `${critTxt}${ability.name} deals ${dmg} damage!${effectTxt}`,
    kind: isCrit ? 'crit' : 'hit',
    effect,
    immune,
    type: isCrit ? 'crit' : 'player',
    damage: { target: 'enemy', amount: dmg, crit: isCrit },
    flash: 'enemy',
    diceInfo: { roll, target: threshold, success: true, crit: isCrit },
  };
}

export function resolvePlayerSkill(state, ability) {
  return withReaction(state, playerSkill(state, ability));
}

export function resolvePlayerItem(state, itemName, hpRestore, manaRestore) {
  const results = [];
  if (hpRestore > 0) {
    const heal = Math.max(hpRestore, Math.floor(hpRestore * (0.8 + Math.random() * 0.4)));
    state.player.hp = Math.min(state.player.max_hp, state.player.hp + heal);
    results.push({ log: `You use ${itemName} and restore ${heal} HP!`, kind: 'item', type: 'player', damage: { target: 'player', amount: heal, heal: true } });
  }
  if (manaRestore > 0) {
    state.player.mana = Math.min(state.player.max_mana, state.player.mana + manaRestore);
    results.push({ log: `You use ${itemName} and restore ${manaRestore} mana!`, kind: 'item', manaRestored: manaRestore, type: 'player' });
  }
  // Remove item, and record it so the server removes it from the saved inventory too
  const idx = state.inventory.findIndex(i => i.name === itemName && i.type === 'consumable');
  if (idx !== -1) {
    state.inventory.splice(idx, 1);
    state.items_used = [...(state.items_used || []), itemName];
  }
  return withReaction(state, results);
}
