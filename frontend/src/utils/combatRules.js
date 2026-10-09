// ═══════════════════════════════════════════════
//  Combat rules — dice and status effects
//  Shared by combat.js (player actions) and enemyAI.js (enemy behavior).
//  STATUS_RULES mirrors the backend registry (backend/models/combat.py);
//  backend/tests/test_status_effects.py checks they list the same effects.
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

// ─── Status Effect Rules (mirrors backend registry) ───
const STATUS_RULES = {
  bleed:    { dot: [2, 4], skipTurn: false, damageModifier: 1.0, rollModifier: 0, armorModifier: 0, maxDuration: 3, dodgeChance: 0 },
  stun:     { dot: [0, 0], skipTurn: true,  damageModifier: 1.0, rollModifier: 0, armorModifier: 0, maxDuration: 1, dodgeChance: 0 },
  weaken:   { dot: [0, 0], skipTurn: false, damageModifier: 0.5, rollModifier: 0, armorModifier: 0, maxDuration: 2, dodgeChance: 0 },
  focus:    { dot: [0, 0], skipTurn: false, damageModifier: 1.0, rollModifier: 5, armorModifier: 0, maxDuration: 1, dodgeChance: 0 },
  empowered: { dot: [0, 0], skipTurn: false, damageModifier: 1.5, rollModifier: 0, armorModifier: 0, maxDuration: 2, dodgeChance: 0 },
  poisoned: { dot: [1, 4], skipTurn: false, damageModifier: 1.0, rollModifier: 0, armorModifier: 0, maxDuration: 5, dodgeChance: 0 },
  burning:  { dot: [1, 3], skipTurn: false, damageModifier: 1.0, rollModifier: 0, armorModifier: 0, maxDuration: 3, dodgeChance: 0 },
  blocking: { dot: [0, 0], skipTurn: false, damageModifier: 1.0, rollModifier: 0, armorModifier: 3, maxDuration: 1, dodgeChance: 0 },
  healing:  { dot: [-6, -2], skipTurn: false, damageModifier: 1.0, rollModifier: 0, armorModifier: 0, maxDuration: 3, dodgeChance: 0 },
  dodging:  { dot: [0, 0], skipTurn: false, damageModifier: 1.0, rollModifier: 0, armorModifier: 0, maxDuration: 1, dodgeChance: 0.5 },
  hidden:   { dot: [0, 0], skipTurn: false, damageModifier: 1.0, rollModifier: 3, armorModifier: 0, maxDuration: 2, dodgeChance: 0 },
};

const STATUS_ICONS = {
  bleed: '🩸', stun: '💫', weaken: '📉', focus: '🎯', empowered: '💢',
  poisoned: '☠️', burning: '🔥', blocking: '🛡️', healing: '💚',
  dodging: '💨', hidden: '👤',
};

// Enemy kinds that some effects can't touch: machines don't bleed, the dead can't be poisoned.
const IMMUNITIES = {
  construct: ['bleed', 'poisoned'],
  undead: ['poisoned'],
};

function getRule(name) {
  return STATUS_RULES[name.toLowerCase()] ||
    { dot: [0, 0], skipTurn: false, damageModifier: 1.0, rollModifier: 0, armorModifier: 0, maxDuration: 5, dodgeChance: 0 };
}

export function getStatusIcon(name) {
  return STATUS_ICONS[name.toLowerCase()] || '✦';
}

export function isImmune(combatant, effectName) {
  return (IMMUNITIES[(combatant.archetype || '').toLowerCase()] || []).includes((effectName || '').toLowerCase());
}

export function hasEffect(combatant, effectName) {
  return (combatant.status_effects || []).some(e => e.name.toLowerCase() === effectName.toLowerCase());
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

/** Apply (or refresh) an effect. Returns false when the combatant is immune to it. */
export function applyEffect(combatant, effectName, duration) {
  if (isImmune(combatant, effectName)) return false;
  const rule = getRule(effectName);
  const capped = Math.min(duration, rule.maxDuration);
  const existing = (combatant.status_effects || []).find(e => e.name.toLowerCase() === effectName.toLowerCase());
  if (existing) {
    existing.duration = Math.max(existing.duration, capped);
  } else {
    combatant.status_effects = [...(combatant.status_effects || []), { name: effectName, duration: capped }];
  }
  return true;
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
