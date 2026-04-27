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

export function tickEffects(combatant, addLog) {
  const expired = [];
  for (const eff of combatant.status_effects) {
    eff.duration--;
    const name = eff.name.toLowerCase();
    if (name === 'poisoned' || name === 'poison blade' || name === 'burning') {
      const dot = Math.floor(Math.random() * 4) + 1;
      combatant.hp = Math.max(0, combatant.hp - dot);
      addLog(`${name} ticks for ${dot} on ${combatant.name || 'you'}!`, 'system');
    }
    if (eff.duration <= 0) expired.push(eff);
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
  const total = roll + atkBonus;
  const threshold = 8 + state.enemy.armor;
  const isCrit = roll === 20;
  const isMiss = roll === 1;

  if (isMiss) {
    return { log: `You swing ${weaponName}... MISS! (rolled 1)`, type: 'player', flash: 'player' };
  }
  if (total < threshold && !isCrit) {
    return { log: `Your ${weaponName} glances off their armor. (${roll}+${atkBonus.toFixed(1)} vs AC ${threshold})`, type: 'player', flash: 'player' };
  }

  let dmg = rollDice(dice);
  if (isCrit) dmg = Math.floor(dmg * 1.5);
  state.enemy.hp -= dmg;

  const critTxt = isCrit ? '⚡ CRITICAL! ' : '';
  return {
    log: `${critTxt}You strike with ${weaponName} for ${dmg} damage! (${roll}+${atkBonus.toFixed(1)})`,
    type: isCrit ? 'crit' : 'player',
    damage: { target: 'enemy', amount: dmg, crit: isCrit },
    flash: 'enemy',
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
      state.player.status_effects.push({ name: ability.status_effect, duration: ability.status_duration || 2 });
      return { log: `You use ${ability.name}! Gained ${ability.status_effect}.`, type: 'player' };
    }
    return { log: `You use ${ability.name}!`, type: 'player' };
  }

  // Attack
  const roll = rollD20();
  const atkBonus = state.player.attack_bonus;
  const total = roll + atkBonus;
  const threshold = 8 + state.enemy.armor;
  const isCrit = roll === 20;
  const isMiss = roll === 1;

  if (isMiss) return { log: `${ability.name} misses! (rolled 1)`, type: 'player', flash: 'player' };
  if (total < threshold && !isCrit) return { log: `${ability.name} glances off armor. (${roll}+${atkBonus.toFixed(1)} vs AC ${threshold})`, type: 'player', flash: 'player' };

  const dice = ability.damage_dice || '1d6';
  let dmg = rollDice(dice);
  if (isCrit) dmg = Math.floor(dmg * 1.5);
  state.enemy.hp -= dmg;

  if (ability.status_effect) {
    state.enemy.status_effects.push({ name: ability.status_effect, duration: ability.status_duration || 2 });
  }

  const critTxt = isCrit ? '⚡ CRITICAL! ' : '';
  return {
    log: `${critTxt}${ability.name} deals ${dmg} damage!`,
    type: isCrit ? 'crit' : 'player',
    damage: { target: 'enemy', amount: dmg, crit: isCrit },
    flash: 'enemy',
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
  tickEffects(state.enemy, () => {});
  tickEffects(state.player, () => {});

  if (state.enemy.hp <= 0) return { ended: true, victory: true };

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

  const roll = rollD20();
  const total = roll + e.attack_bonus;
  const threshold = 8 + p.armor;
  const isCrit = roll === 20;
  const isMiss = roll === 1;

  if (isMiss) return { log: `${e.name}'s ${actionName} misses!`, type: 'enemy' };
  if (total < threshold && !isCrit) return { log: `${e.name}'s ${actionName} glances off your armor.`, type: 'enemy' };

  let dmg = damageDice ? rollDice(damageDice) : Math.floor(Math.random() * 6) + 1 + Math.floor(e.attack_bonus);
  if (isCrit) dmg = Math.floor(dmg * 1.5);
  p.hp -= dmg;

  if (statusEffect) p.status_effects.push({ name: statusEffect, duration: statusDuration });

  const critTxt = isCrit ? '⚡ CRITICAL! ' : '';
  state.turn++;
  return {
    log: `${critTxt}${e.name} uses ${actionName} for ${dmg} damage!`,
    type: isCrit ? 'crit' : 'enemy',
    damage: { target: 'player', amount: dmg, crit: isCrit },
    flash: 'player',
  };
}
