// ═══════════════════════════════════════════════
//  Enemy AI — behavior by enemy type
//  Every enemy plans its next move one turn ahead (shown on its card as
//  "Next: …", with ⚠ for a big hit), may react to what the player just did,
//  then carries the move out on its turn.
//
//  brute       winds up a ×1.75 blow every third turn; a stun cancels it,
//              blocking or dodging blunts it (half damage)
//  soldier     steady attacks; answers a player buff by weakening them;
//              raises a guard when hurt
//  skirmisher  a flurry of two quick hits (60% each), bleeding cuts
//  beast       pounces to stun; frenzies (empowered) once below half HP
//  caster      hex (weaken) and blast; heals or shields itself once at ≤40% HP
//  construct   charges up, then an overcharged ×2 strike; immune to bleed and poison
//  undead      drains life (heals half the damage dealt); immune to poison
//  horror      dread (weaken) and rend (bleed)
//  elites      rally once at half HP (heal 20% and focus)
//  bosses      enter phase 2 once at half HP (taunt, empowered), then unleash
//              their finisher every third turn
//
//  Enemies without an archetype keep the original simple behavior.
// ═══════════════════════════════════════════════

import {
  applyEffect,
  canAct,
  getArmorModifier,
  getDamageModifier,
  getDodgeChance,
  getRollModifier,
  getStatusIcon,
  hasEffect,
  rollD20,
  rollDice,
  tickEffects,
} from './combatRules.js';

export const HEAVY_MULTIPLIER = 1.75;
export const OVERCHARGE_MULTIPLIER = 2;
export const FLURRY_MULTIPLIER = 0.6;

const PLAYER_BUFFS = ['focus', 'hidden', 'blocking', 'dodging', 'empowered'];

// ─── Memory and move helpers ───

function memory(enemy) {
  if (!enemy.ai) {
    enemy.ai = { turn: 0, last: null, charged: false, frenzied: false, mended: false, rallied: false, selfBuffed: false, phase: 1 };
  }
  return enemy.ai;
}

function move(fields) {
  const planned = {
    key: 'attack',
    name: 'Attack',
    style: 'attack', // attack | heavy | flurry | debuff | buff | heal | rally | charge | phase
    dice: '',        // '' = the enemy's basic attack damage
    multiplier: 1,
    hits: 1,
    effect: null,
    duration: 2,
    target: 'player',
    drain: false,
    warn: false,
    reaction: false,
    ...fields,
  };
  planned.label = `${planned.name}${planned.warn ? ' ⚠' : ''}`;
  return planned;
}

const attack = () => move({});

// A move built from one of the enemy's own abilities.
function strike(ability, key, extra = {}) {
  const self = ability.target === 'self';
  let style = 'attack';
  if (self) style = 'buff';
  else if (!ability.damage_dice && ability.heal_self) style = 'heal';
  else if (!ability.damage_dice && ability.status_effect) style = 'debuff';
  return move({
    key,
    name: ability.name,
    style,
    dice: ability.damage_dice || '',
    effect: ability.status_effect || null,
    duration: ability.status_duration || 2,
    target: self ? 'self' : 'player',
    drain: Boolean(ability.heal_self && ability.damage_dice),
    ...extra,
  });
}

const maxRoll = (dice) => {
  const m = (dice || '').match(/(\d+)d(\d+)([+-]\d+)?/);
  return m ? parseInt(m[1]) * parseInt(m[2]) + parseInt(m[3] || 0) : 0;
};
const find = (enemy, test) => (enemy.abilities || []).find(test) || null;
const withEffect = (effect) => (a) => a.status_effect === effect && a.target !== 'self';
const pureDamage = (a) => Boolean(a.damage_dice) && !a.status_effect && !a.heal_self && a.target !== 'self';
const anyDamage = (a) => Boolean(a.damage_dice) && a.target !== 'self';

// A boss's last ability is its finisher, held back until phase 2.
function usableAbilities(enemy, ai) {
  const list = enemy.abilities || [];
  return enemy.threat === 'boss' && ai.phase < 2 && list.length > 2 ? list.slice(0, -1) : list;
}

function finisherOf(enemy) {
  const list = (enemy.abilities || []).filter(anyDamage);
  return list.length ? [...list].sort((a, b) => maxRoll(b.damage_dice) - maxRoll(a.damage_dice))[0] : null;
}

// ─── Behavior by archetype ───

const PLANNERS = {
  brute(e, p, ai) {
    if (ai.turn % 3 === 2) {
      const heavy = find(e, pureDamage) || find(e, anyDamage);
      return move({ key: 'heavy', name: heavy?.name || 'Crushing Blow', style: 'heavy', multiplier: HEAVY_MULTIPLIER, warn: true });
    }
    const stunner = find(e, withEffect('stun'));
    if (stunner && ai.last !== 'stun' && !hasEffect(p, 'stun') && ai.turn % 3 === 1) return strike(stunner, 'stun');
    return attack();
  },

  soldier(e, p, ai) {
    if (e.hp <= e.max_hp * 0.6 && ai.last !== 'guard' && !hasEffect(e, 'blocking') && ai.turn % 3 === 1) {
      return move({ key: 'guard', name: 'Raise Guard', style: 'buff', target: 'self', effect: 'blocking', duration: 1 });
    }
    const precise = find(e, pureDamage);
    if (precise && ai.turn % 2 === 1) return strike(precise, 'precise');
    return attack();
  },

  skirmisher(e, p, ai) {
    const step = ai.turn % 3;
    if (step === 0) {
      const flurry = find(e, pureDamage);
      return move({ key: 'flurry', name: flurry?.name || 'Flurry of Blows', style: 'flurry', hits: 2, multiplier: FLURRY_MULTIPLIER });
    }
    if (step === 1 && !hasEffect(p, 'bleed')) {
      const cut = find(e, withEffect('bleed'));
      return cut ? strike(cut, 'cut') : move({ key: 'cut', name: 'Vicious Cut', effect: 'bleed', duration: 2 });
    }
    return attack();
  },

  beast(e, p, ai) {
    if (ai.turn % 3 === 1 && ai.last !== 'pounce' && !hasEffect(p, 'stun')) {
      const pounce = find(e, withEffect('stun'));
      return pounce ? strike(pounce, 'pounce') : move({ key: 'pounce', name: 'Pounce', effect: 'stun', duration: 1 });
    }
    const bite = find(e, withEffect('bleed'));
    if (bite && ai.turn % 3 === 2 && !hasEffect(p, 'bleed')) return strike(bite, 'bite');
    return attack();
  },

  caster(e, p, ai) {
    if (!hasEffect(p, 'weaken') && ai.last !== 'hex') {
      const hex = find(e, withEffect('weaken'));
      return hex ? strike(hex, 'hex') : move({ key: 'hex', name: 'Hex', style: 'debuff', effect: 'weaken', duration: 2 });
    }
    const blast = find(e, anyDamage);
    return blast ? strike(blast, 'blast') : move({ key: 'blast', name: 'Arcane Blast', multiplier: 1.25 });
  },

  construct(e, p, ai) {
    if (ai.charged) {
      const big = find(e, pureDamage);
      return move({ key: 'overcharge', name: big?.name || 'Overcharged Strike', style: 'heavy', multiplier: OVERCHARGE_MULTIPLIER, warn: true });
    }
    if (ai.turn % 3 === 2) return move({ key: 'charge', name: 'Charging Up', style: 'charge', warn: true });
    const pulse = find(e, withEffect('stun'));
    if (pulse && ai.turn % 3 === 1 && ai.last !== 'pulse' && !hasEffect(p, 'stun')) return strike(pulse, 'pulse');
    return attack();
  },

  undead(e, p, ai) {
    if (ai.turn % 2 === 1) {
      const drain = find(e, a => a.heal_self && a.damage_dice);
      return move({ key: 'drain', name: drain?.name || 'Draining Touch', dice: drain?.damage_dice || '', drain: true });
    }
    const rot = find(e, withEffect('poisoned'));
    if (rot && !hasEffect(p, 'poisoned')) return strike(rot, 'rot');
    return attack();
  },

  horror(e, p, ai) {
    if (ai.turn % 2 === 0 && ai.last !== 'dread' && !hasEffect(p, 'weaken')) {
      const dread = find(e, withEffect('weaken'));
      return dread ? strike(dread, 'dread') : move({ key: 'dread', name: 'Dread Gaze', style: 'debuff', effect: 'weaken', duration: 2 });
    }
    if (!hasEffect(p, 'bleed')) {
      const rend = find(e, withEffect('bleed'));
      return rend ? strike(rend, 'rend') : move({ key: 'rend', name: 'Rend', effect: 'bleed', duration: 2 });
    }
    return attack();
  },
};

// The original behavior, for enemies without an archetype.
function genericPlan(e, p) {
  const list = e.abilities || [];
  if (!list.length) return attack();
  if (e.hp < e.max_hp * 0.5) {
    const status = list.find(a => a.status_effect && !hasEffect(a.target === 'self' ? e : p, a.status_effect));
    if (status) return strike(status, 'ability');
    return strike([...list].sort((a, b) => maxRoll(b.damage_dice) - maxRoll(a.damage_dice))[0], 'ability');
  }
  if (Math.random() < 0.3) return strike(list[Math.floor(Math.random() * list.length)], 'ability');
  return attack();
}

/** Decide the enemy's next move (shown on its card until it acts). */
export function planIntent(state) {
  const e = state.enemy;
  const p = state.player;
  const ai = memory(e);
  const view = { ...e, abilities: usableAbilities(e, ai) };

  if (e.threat === 'boss' && ai.phase >= 2 && ai.last !== 'finisher' && ai.turn % 3 === 0) {
    const finisher = finisherOf(e);
    if (finisher) return strike(finisher, 'finisher', { style: 'heavy', effect: null, warn: true });
  }

  const planner = PLANNERS[(e.archetype || '').toLowerCase()];
  if (!planner) return genericPlan(view, p);

  // Rage, frenzy and other self-buffs from the enemy's own abilities, once, when hurt.
  if (e.hp < e.max_hp * 0.5 && !ai.selfBuffed) {
    const buff = find(view, a => a.target === 'self' && a.status_effect && !hasEffect(e, a.status_effect));
    if (buff) return strike(buff, 'selfbuff');
  }
  return planner(view, p, ai);
}

// ─── Reactions (to the player's last action or to falling HP) ───

function reaction(state) {
  const e = state.enemy;
  const p = state.player;
  const ai = memory(e);
  const half = e.hp <= e.max_hp * 0.5;
  const archetype = (e.archetype || '').toLowerCase();

  if (e.threat === 'boss' && half && ai.phase === 1) {
    return move({ key: 'phase', name: 'Unleashed Fury', style: 'phase', target: 'self', effect: 'empowered', duration: 2, warn: true, reaction: true });
  }
  if (e.threat === 'elite' && half && !ai.rallied) {
    return move({ key: 'rally', name: 'Rally', style: 'rally', target: 'self', effect: 'focus', duration: 1, reaction: true });
  }
  if (archetype === 'beast' && half && !ai.frenzied) {
    return move({ key: 'frenzy', name: 'Frenzy', style: 'buff', target: 'self', effect: 'empowered', duration: 2, reaction: true });
  }
  if (archetype === 'caster' && e.hp <= e.max_hp * 0.4 && !ai.mended) {
    return e.hp <= e.max_hp * 0.25
      ? move({ key: 'mend', name: 'Dark Mending', style: 'heal', target: 'self', reaction: true })
      : move({ key: 'ward', name: 'Arcane Ward', style: 'buff', target: 'self', effect: 'blocking', duration: 1, reaction: true });
  }
  if (archetype === 'soldier' && ai.last !== 'suppress' && !hasEffect(p, 'weaken')
      && PLAYER_BUFFS.some(buff => hasEffect(p, buff))) {
    const suppress = find(e, withEffect('weaken'));
    return suppress
      ? strike(suppress, 'suppress', { reaction: true })
      : move({ key: 'suppress', name: 'Suppressing Strike', effect: 'weaken', duration: 2, reaction: true });
  }
  return null;
}

/** After the player acts: switch the planned move if the enemy reacts. Returns the move. */
export function reactToPlayer(state) {
  if (!state?.enemy || state.enemy.hp <= 0) return state?.enemyIntent || null;
  if (state.enemyIntent?.reaction) return state.enemyIntent;
  const reacting = reaction(state);
  if (reacting) state.enemyIntent = reacting;
  return state.enemyIntent || null;
}

// ─── Carrying a move out ───

function basicDamage(e) {
  return Math.floor(Math.random() * 6) + 1 + Math.floor(e.attack_bonus || 0);
}

function healEnemy(e, share) {
  const amount = Math.max(1, Math.round(e.max_hp * share));
  const before = e.hp;
  e.hp = Math.min(e.max_hp, e.hp + amount);
  return e.hp - before;
}

// One attack roll against the player: dodged | miss | glance | hit | crit.
function swing(e, p) {
  const roll = rollD20();
  const threshold = 8 + p.armor + getArmorModifier(p);
  const dodge = getDodgeChance(p);
  if (dodge > 0 && Math.random() < dodge) return { outcome: 'dodged', roll, threshold };
  if (roll === 1) return { outcome: 'miss', roll, threshold };
  if (roll !== 20 && roll + e.attack_bonus + getRollModifier(e) < threshold) return { outcome: 'glance', roll, threshold };
  return { outcome: roll === 20 ? 'crit' : 'hit', roll, threshold };
}

function attackWith(state, intent) {
  const e = state.enemy;
  const p = state.player;
  const guarded = hasEffect(p, 'blocking') || hasEffect(p, 'dodging');
  const swings = [];
  let total = 0;
  let crit = false;
  let blunted = false;

  for (let i = 0; i < intent.hits; i++) {
    const s = swing(e, p);
    swings.push(s);
    if (s.outcome !== 'hit' && s.outcome !== 'crit') continue;
    if (intent.style === 'debuff') continue; // effect only, no damage
    let dmg = (intent.dice ? rollDice(intent.dice) : basicDamage(e)) * intent.multiplier;
    dmg = Math.max(1, Math.floor(dmg * getDamageModifier(e)));
    if (s.outcome === 'crit') { dmg = Math.floor(dmg * 1.5); crit = true; }
    if (intent.style === 'heavy' && guarded) { dmg = Math.max(1, Math.floor(dmg / 2)); blunted = true; }
    total += dmg;
  }

  const landed = swings.filter(s => s.outcome === 'hit' || s.outcome === 'crit');
  const first = landed[0] || swings[0];
  const diceInfo = { roll: first.roll, target: first.threshold, success: landed.length > 0, crit: first.outcome === 'crit' || first.outcome === 'miss' };
  const base = { move: intent.name, diceInfo };

  if (!landed.length) {
    const outcome = swings[0].outcome;
    const text = {
      dodged: `💨 You dodge ${e.name}'s ${intent.name}!`,
      miss: `${e.name}'s ${intent.name} misses!`,
      glance: `${e.name}'s ${intent.name} glances off your armor.`,
    }[outcome];
    return { ...base, log: text, kind: outcome, type: outcome === 'dodged' ? 'player' : 'enemy' };
  }

  if (intent.style === 'debuff') {
    applyEffect(p, intent.effect, intent.duration);
    return {
      ...base,
      log: `${getStatusIcon(intent.effect)} ${e.name}'s ${intent.name} leaves you ${intent.effect}!`,
      kind: 'debuff',
      effect: intent.effect,
      type: 'enemy',
      flash: 'player',
    };
  }

  p.hp -= total;
  if (intent.effect) applyEffect(p, intent.effect, intent.duration);
  // Life drain: the enemy heals half the damage it dealt.
  let drained = 0;
  if (intent.drain) {
    const before = e.hp;
    e.hp = Math.min(e.max_hp, e.hp + Math.floor(total / 2));
    drained = e.hp - before;
  }

  const critTxt = crit ? '⚡ CRITICAL! ' : '';
  const hitsTxt = intent.hits > 1 ? ` (${landed.length} of ${intent.hits} hits)` : '';
  return {
    ...base,
    log: `${critTxt}${e.name} uses ${intent.name} for ${total} damage!${hitsTxt}${blunted ? ' You blunt the blow.' : ''}`,
    kind: crit ? 'crit' : 'hit',
    effect: intent.effect,
    type: crit ? 'crit' : 'enemy',
    damage: { target: 'player', amount: total, crit },
    flash: 'player',
    blunted,
    hits: intent.hits > 1 ? landed.length : undefined,
    drained: drained || undefined,
  };
}

/** Carry out a planned move. Returns a result like the player's actions do. */
export function executeIntent(state, intent) {
  const e = state.enemy;
  const ai = memory(e);
  const base = { move: intent.name, type: 'enemy', diceInfo: null };

  switch (intent.style) {
    case 'buff': {
      applyEffect(e, intent.effect, intent.duration);
      if (intent.key === 'frenzy') ai.frenzied = true;
      if (intent.key === 'ward') ai.mended = true;
      if (intent.key === 'selfbuff') ai.selfBuffed = true;
      return { ...base, log: `${getStatusIcon(intent.effect)} ${e.name} uses ${intent.name} and is ${intent.effect}!`, kind: 'buff', effect: intent.effect };
    }
    case 'phase': {
      ai.phase = 2;
      applyEffect(e, 'empowered', 2);
      return { ...base, log: `💢 ${e.name} unleashes its full power!`, kind: 'buff', effect: 'empowered', taunt: 'phase' };
    }
    case 'rally': {
      ai.rallied = true;
      const healed = healEnemy(e, 0.2);
      applyEffect(e, 'focus', 1);
      return { ...base, log: `${e.name} rallies and recovers ${healed} HP!`, kind: 'heal', effect: 'focus', damage: { target: 'enemy', amount: healed, heal: true } };
    }
    case 'heal': {
      ai.mended = true;
      const healed = healEnemy(e, 0.25);
      return { ...base, log: `${e.name} uses ${intent.name} and recovers ${healed} HP!`, kind: 'heal', damage: { target: 'enemy', amount: healed, heal: true } };
    }
    case 'charge': {
      ai.charged = true;
      return { ...base, log: `⚡ ${e.name} is charging up...`, kind: 'charge' };
    }
    default: {
      if (intent.key === 'overcharge') ai.charged = false;
      return attackWith(state, intent);
    }
  }
}

/** The enemy's turn: effects tick, then it carries out its planned move and plans the next. */
export function resolveEnemyTurn(state) {
  const e = state.enemy;
  const p = state.player;
  const ai = memory(e);
  if (!state.enemyIntent) state.enemyIntent = planIntent(state);

  // Is the enemy stunned? Checked before effects tick, otherwise a one-turn stun
  // expires during the tick and never stops a single turn.
  const stunned = !canAct(e);

  // Tick effects on both (damage over time, durations)
  tickEffects(e, () => {});
  tickEffects(p, () => {});

  if (e.hp <= 0) return { ended: true, victory: true };

  if (stunned) {
    // A stun cancels whatever the enemy was building up to.
    const lost = state.enemyIntent;
    const cancelled = lost && (lost.style === 'heavy' || lost.style === 'charge' || ai.charged) ? lost.name : null;
    ai.charged = false;
    ai.turn++;
    ai.last = 'stunned';
    state.turn++;
    state.enemyIntent = planIntent(state);
    return {
      log: `💫 ${e.name} is stunned and cannot act!${cancelled ? ` Its ${cancelled} is lost.` : ''}`,
      kind: 'stunned',
      move: 'Stunned',
      effect: 'stun',
      cancelled,
      type: 'system',
      diceInfo: null,
    };
  }

  reactToPlayer(state); // damage over time can cross an HP threshold too
  const intent = state.enemyIntent;
  const result = executeIntent(state, intent);
  ai.turn++;
  ai.last = intent.key;
  state.turn++;
  state.enemyIntent = planIntent(state);
  return result;
}
