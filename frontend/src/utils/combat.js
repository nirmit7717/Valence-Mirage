// ═══════════════════════════════════════════════
//  Combat — Pure combat resolution functions
//  Ported from the original client-side engine
// ═══════════════════════════════════════════════

export function rollD20() {
  return Math.floor(Math.random() * 20) + 1;
}

export function rollDice(str) {
  if (!str) return 0;
  const m = str.match(/(\d+)d(\d+)([+-]\d+)?/);
  if (!m) return 0;
  const count = parseInt(m[1]), sides = parseInt(m[2]), mod = parseInt(m[3] || 0);
  let total = 0;
  for (let i = 0; i < count; i++) total += Math.floor(Math.random() * sides) + 1;
  return total + mod;
}

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

// ─── Status Effect Rules (mirrors backend registry) ───
const STATUS_RULES = {
  bleed:    { dot: [2, 4], skipTurn: false, damageModifier: 1.0, rollModifier: 0, armorModifier: 0, maxDuration: 3, dodgeChance: 0 },
  stun:     { dot: [0, 0], skipTurn: true,  damageModifier: 1.0, rollModifier: 0, armorModifier: 0, maxDuration: 1, dodgeChance: 0 },
  weaken:   { dot: [0, 0], skipTurn: false, damageModifier: 0.5, rollModifier: 0, armorModifier: 0, maxDuration: 2, dodgeChance: 0 },
  focus:    { dot: [0, 0], skipTurn: false, damageModifier: 1.0, rollModifier: 5, armorModifier: 0, maxDuration: 1, dodgeChance: 0 },
  poisoned: { dot: [1, 4], skipTurn: false, damageModifier: 1.0, rollModifier: 0, armorModifier: 0, maxDuration: 5, dodgeChance: 0 },
  burning:  { dot: [1, 3], skipTurn: false, damageModifier: 1.0, rollModifier: 0, armorModifier: 0, maxDuration: 3, dodgeChance: 0 },
  blocking: { dot: [0, 0], skipTurn: false, damageModifier: 1.0, rollModifier: 0, armorModifier: 3, maxDuration: 1, dodgeChance: 0 },
  healing:  { dot: [-6, -2], skipTurn: false, damageModifier: 1.0, rollModifier: 0, armorModifier: 0, maxDuration: 3, dodgeChance: 0 },
  dodging:  { dot: [0, 0], skipTurn: false, damageModifier: 1.0, rollModifier: 0, armorModifier: 0, maxDuration: 1, dodgeChance: 0.5 },
  hidden:   { dot: [0, 0], skipTurn: false, damageModifier: 1.0, rollModifier: 3, armorModifier: 0, maxDuration: 2, dodgeChance: 0 },
};

function getRule(name) {
  return STATUS_RULES[name.toLowerCase()] ||
    { dot: [0, 0], skipTurn: false, damageModifier: 1.0, rollModifier: 0, armorModifier: 0, maxDuration: 5, dodgeChance: 0 };
}

export function getStatusIcon(name) {
  const icons = {
    bleed: '🩸', stun: '💫', weaken: '📉', focus: '🎯',
    poisoned: '☠️', burning: '🔥', blocking: '🛡️', healing: '💚',
    dodging: '💨', hidden: '👤',
  };
  return icons[name.toLowerCase()] || '✦';
}

export function getDamageModifier(combatant) {
  let mod = 1.0;
  for (const eff of (combatant.status_effects || [])) {
    mod *= getRule(eff.name).damageModifier;
  }
  return mod;
}

export function getRollModifier(combatant) {
  let mod = 0;
  for (const eff of (combatant.status_effects || [])) {
    mod += getRule(eff.name).rollModifier;
  }
  return mod;
}

export function getArmorModifier(combatant) {
  let mod = 0;
  for (const eff of (combatant.status_effects || [])) {
    mod += getRule(eff.name).armorModifier;
  }
  return mod;
}

export function getDodgeChance(combatant) {
  let chance = 0;
  for (const eff of (combatant.status_effects || [])) {
    chance = Math.max(chance, getRule(eff.name).dodgeChance);
  }
  return chance;
}

export function canAct(combatant) {
  for (const eff of (combatant.status_effects || [])) {
    if (getRule(eff.name).skipTurn) return false;
  }
  return true;
}

export function applyEffect(combatant, effectName, duration) {
  const rule = getRule(effectName);
  const capped = Math.min(duration, rule.maxDuration);
  const existing = (combatant.status_effects || []).find(e => e.name.toLowerCase() === effectName.toLowerCase());
  if (existing) {
    existing.duration = Math.max(existing.duration, capped);
  } else {
    combatant.status_effects = [...(combatant.status_effects || []), { name: effectName, duration: capped }];
  }
}

export function tickEffects(combatant, addLog) {
  const expired = [];
  for (const eff of combatant.status_effects) {
    const rule = getRule(eff.name);
    const [lo, hi] = rule.dot;
    if (lo !== 0 || hi !== 0) {
      const [min, max] = lo < hi ? [lo, hi] : [hi, lo];
      const val = Math.floor(Math.random() * (max - min + 1)) + min;
      if (val < 0) {
        const heal = Math.abs(val);
        combatant.hp = Math.min(combatant.max_hp, combatant.hp + heal);
        addLog(`${getStatusIcon(eff.name)} ${eff.name} restores ${heal} HP on ${combatant.name || 'you'}!`, 'system');
      } else if (val > 0) {
        combatant.hp = Math.max(0, combatant.hp - val);
        addLog(`${getStatusIcon(eff.name)} ${eff.name} deals ${val} damage to ${combatant.name || 'you'}!`, 'system');
      }
    }
    eff.duration--;
    if (eff.duration <= 0) {
      expired.push(eff);
      addLog(`${eff.name} fades from ${combatant.name || 'you'}.`, 'system');
    }
  }
  for (const eff of expired) {
    const idx = combatant.status_effects.indexOf(eff);
    if (idx !== -1) combatant.status_effects.splice(idx, 1);
  }
}

export function createCombatState(combatData) {
  return {
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
  };
}

export function resolvePlayerAttack(state, weaponName, dice) {
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
    return { log: `You swing ${weaponName}... MISS! (rolled 1)`, type: 'player', flash: 'player', diceInfo };
  }
  if (!hit) {
    return { log: `Your ${weaponName} glances off their armor. (${roll}+${(atkBonus + rollMod).toFixed(1)} vs AC ${threshold})`, type: 'player', flash: 'player', diceInfo };
  }

  let dmg = rollDice(dice);
  dmg = Math.max(1, Math.floor(dmg * getDamageModifier(state.player)));
  if (isCrit) dmg = Math.floor(dmg * 1.5);
  state.enemy.hp -= dmg;

  const critTxt = isCrit ? '⚡ CRITICAL! ' : '';
  return {
    log: `${critTxt}You strike with ${weaponName} for ${dmg} damage! (${roll}+${(atkBonus + rollMod).toFixed(1)})`,
    type: isCrit ? 'crit' : 'player',
    damage: { target: 'enemy', amount: dmg, crit: isCrit },
    flash: 'enemy',
    diceInfo,
  };
}

export function resolvePlayerSkill(state, ability) {
  state.player.mana -= ability.mana_cost;

  // Support / defend
  if (ability.ability_type === 'support' || ability.ability_type === 'defend') {
    if (ability.name.toLowerCase() === 'heal') {
      const heal = Math.floor(Math.random() * 11) + 15;
      state.player.hp = Math.min(state.player.max_hp, state.player.hp + heal);
      return { log: `You cast ${ability.name} and restore ${heal} HP!`, type: 'player', damage: { target: 'player', amount: heal, heal: true } };
    }
    if (ability.status_effect) {
      applyEffect(state.player, ability.status_effect, ability.status_duration || 2);
      return { log: `${getStatusIcon(ability.status_effect)} You use ${ability.name}! Gained ${ability.status_effect}.`, type: 'player' };
    }
    return { log: `You use ${ability.name}!`, type: 'player' };
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

  if (isMiss) return { log: `${ability.name} misses! (rolled 1)`, type: 'player', flash: 'player', diceInfo: { roll: 1, target: threshold, success: false, crit: true } };
  if (total < threshold && !isCrit) return { log: `${ability.name} glances off armor. (${roll}+${(atkBonus + rollMod).toFixed(1)} vs AC ${threshold})`, type: 'player', flash: 'player', diceInfo: { roll, target: threshold, success: false, crit: false } };

  const dice = ability.damage_dice || '1d6';
  let dmg = rollDice(dice);
  dmg = Math.max(1, Math.floor(dmg * getDamageModifier(state.player)));
  if (isCrit) dmg = Math.floor(dmg * 1.5);
  state.enemy.hp -= dmg;

  if (ability.status_effect) {
    applyEffect(state.enemy, ability.status_effect, ability.status_duration || 2);
  }

  const critTxt = isCrit ? '⚡ CRITICAL! ' : '';
  const effectTxt = ability.status_effect ? ` ${getStatusIcon(ability.status_effect)} Applied ${ability.status_effect}!` : '';
  return {
    log: `${critTxt}${ability.name} deals ${dmg} damage!${effectTxt}`,
    type: isCrit ? 'crit' : 'player',
    damage: { target: 'enemy', amount: dmg, crit: isCrit },
    flash: 'enemy',
    diceInfo: { roll, target: threshold, success: true, crit: isCrit },
  };
}

export function resolvePlayerItem(state, itemName, hpRestore, manaRestore) {
  const results = [];
  if (hpRestore > 0) {
    const heal = Math.max(hpRestore, Math.floor(hpRestore * (0.8 + Math.random() * 0.4)));
    state.player.hp = Math.min(state.player.max_hp, state.player.hp + heal);
    results.push({ log: `You use ${itemName} and restore ${heal} HP!`, type: 'player', damage: { target: 'player', amount: heal, heal: true } });
  }
  if (manaRestore > 0) {
    state.player.mana = Math.min(state.player.max_mana, state.player.mana + manaRestore);
    results.push({ log: `You use ${itemName} and restore ${manaRestore} mana!`, type: 'player' });
  }
  // Remove item
  const idx = state.inventory.findIndex(i => i.name === itemName && i.type === 'consumable');
  if (idx !== -1) state.inventory.splice(idx, 1);
  return results;
}

export function resolveEnemyTurn(state) {
  // Phase 1: Tick effects on both
  tickEffects(state.enemy, () => {});
  tickEffects(state.player, () => {});

  if (state.enemy.hp <= 0) return { ended: true, victory: true };

  // Phase 2: Can enemy act?
  if (!canAct(state.enemy)) {
    state.turn++;
    return { log: `💫 ${state.enemy.name} is stunned and cannot act!`, type: 'system', diceInfo: null };
  }

  const e = state.enemy;
  const p = state.player;

  let actionName = 'Attack';
  let damageDice = '';
  let statusEffect = null;
  let statusDuration = 0;

  if (e.abilities && e.abilities.length > 0) {
    if (e.hp < e.max_hp * 0.5) {
      const statusAbil = e.abilities.find(a => a.status_effect && !p.status_effects.some(se => se.name === a.status_effect));
      if (statusAbil) {
        actionName = statusAbil.name;
        damageDice = statusAbil.damage_dice || '';
        statusEffect = statusAbil.status_effect;
        statusDuration = statusAbil.status_duration || 2;
      } else {
        const best = [...e.abilities].sort((a, b) => (rollDice(b.damage_dice) || 0) - (rollDice(a.damage_dice) || 0))[0];
        actionName = best.name;
        damageDice = best.damage_dice || '';
        statusEffect = best.status_effect;
        statusDuration = best.status_duration || 2;
      }
    } else if (Math.random() < 0.3) {
      const abil = e.abilities[Math.floor(Math.random() * e.abilities.length)];
      actionName = abil.name;
      damageDice = abil.damage_dice || '';
      statusEffect = abil.status_effect;
      statusDuration = abil.status_duration || 2;
    }
  }

  // Phase 3: Roll to hit
  const roll = rollD20();
  const rollMod = getRollModifier(e);
  const total = roll + e.attack_bonus + rollMod;
  const playerArmor = p.armor + getArmorModifier(p);
  const threshold = 8 + playerArmor;
  const isCrit = roll === 20;
  const isMiss = roll === 1;

  // Check dodge
  const dodgeChance = getDodgeChance(p);
  if (dodgeChance > 0 && Math.random() < dodgeChance) {
    state.turn++;
    return { log: `💨 You dodge ${e.name}'s ${actionName}!`, type: 'player', diceInfo: { roll, target: threshold, success: false, crit: false } };
  }

  if (isMiss) { state.turn++; return { log: `${e.name}'s ${actionName} misses!`, type: 'enemy', diceInfo: { roll: 1, target: threshold, success: false, crit: true } }; }
  if (total < threshold && !isCrit) { state.turn++; return { log: `${e.name}'s ${actionName} glances off your armor.`, type: 'enemy', diceInfo: { roll, target: threshold, success: false, crit: false } }; }

  // Phase 4: Calculate damage
  let dmg = damageDice ? rollDice(damageDice) : Math.floor(Math.random() * 6) + 1 + Math.floor(e.attack_bonus);
  dmg = Math.max(1, Math.floor(dmg * getDamageModifier(e)));
  if (isCrit) dmg = Math.floor(dmg * 1.5);
  p.hp -= dmg;

  // Phase 5: Apply status effect
  if (statusEffect) applyEffect(p, statusEffect, statusDuration);

  const critTxt = isCrit ? '⚡ CRITICAL! ' : '';
  state.turn++;
  return {
    log: `${critTxt}${e.name} uses ${actionName} for ${dmg} damage!`,
    type: isCrit ? 'crit' : 'enemy',
    damage: { target: 'player', amount: dmg, crit: isCrit },
    flash: 'player',
    diceInfo: { roll, target: threshold, success: true, crit: isCrit },
  };
}
