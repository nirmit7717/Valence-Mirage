// ═══════════════════════════════════════════════
//  Combat flavor — story lines for the fight screen
//  The log reads like the story ("Sparks burst from the drone's chassis") and the
//  numbers go in a small detail next to it ("−7"). Lines depend on the weapon, the
//  enemy's archetype and the campaign's genre, and never repeat back to back.
// ═══════════════════════════════════════════════

const MINUS = '\u2212';

// ─── Icons ───

const ENEMY_ICONS = {
  brute: '👹', soldier: '🛡️', skirmisher: '🗡️', beast: '🐺',
  caster: '🔮', construct: '🤖', undead: '💀', horror: '👁️',
};
const CLASS_ICONS = { warrior: '⚔️', rogue: '🗡️', wizard: '🔮', cleric: '✨', bard: '🎵' };

export function enemyIcon(archetype) {
  return ENEMY_ICONS[(archetype || '').toLowerCase()] || '👹';
}

export function classIcon(characterClass) {
  return CLASS_ICONS[(characterClass || '').toLowerCase()] || '🧭';
}

// ─── Weapons ───

const WEAPON_CATEGORIES = [
  ['unarmed', /\b(unarmed|fist|fists|punch|bare)\b/],
  ['ranged', /\b(bow|crossbow|sling|gun|pistol|rifle|blaster|revolver|shotgun|carbine)\b/],
  ['music', /\b(lute|lyre|harp|flute|drum|fiddle|horn)\b/],
  ['arcane', /\b(staff|wand|rod|orb|tome)\b/],
  ['blunt', /\b(mace|hammer|club|maul|flail|morningstar|cudgel|bat|pipe)\b/],
  ['blade', /\b(sword|longsword|greatsword|blade|blades|dagger|daggers|knife|knives|katana|sabre|saber|rapier|axe|sickle|scimitar|cleaver|machete)\b/],
];

/** blade | blunt | arcane | ranged | music | unarmed */
export function weaponCategory(name) {
  const lowered = (name || '').toLowerCase();
  const match = WEAPON_CATEGORIES.find(([, pattern]) => pattern.test(lowered));
  return match ? match[0] : 'blade';
}

// What a blow lands on, by enemy kind and setting.
function bodyWord(archetype, genre) {
  if (archetype === 'construct') return 'chassis';
  if (archetype === 'beast') return 'hide';
  if (archetype === 'undead') return 'brittle frame';
  if (archetype === 'horror') return 'writhing flesh';
  if (genre === 'scifi') return 'armor plating';
  if (genre === 'postapoc') return 'scrap armor';
  return 'armor';
}

// ─── Line pools ({weapon}, {enemy}, {body}, {move}, {effect}, {ability}, {item}) ───

const ATTACK_HITS = {
  blade: [
    'Your {weapon} bites into {enemy}',
    'You slash across {enemy}, steel flashing',
    'Your {weapon} finds a gap in the {body}',
  ],
  blunt: [
    'Your {weapon} crashes into {enemy}',
    'A heavy blow from your {weapon} staggers {enemy}',
    'You hammer {enemy} back a step',
  ],
  arcane: [
    'Power crackles from your {weapon} into {enemy}',
    'You drive the {weapon} into {enemy} with a burst of force',
    'Your {weapon} flares and {enemy} recoils',
  ],
  ranged: [
    'Your shot strikes {enemy}',
    'You fire and {enemy} jerks as it lands',
    'A clean shot punches into the {body}',
  ],
  music: [
    'A jarring chord from your {weapon} rattles {enemy}',
    'You swing the {weapon} and it rings off {enemy}',
    'Your {weapon} sings, and {enemy} flinches from the sound',
  ],
  unarmed: [
    'Your fist connects with {enemy}',
    'You drive an elbow into {enemy}',
    'A hard kick sends {enemy} reeling',
  ],
};

const ATTACK_CRITS = {
  blade: ['Your {weapon} carves deep into {enemy}', 'A perfect cut opens the {body} wide'],
  blunt: ['Your {weapon} lands with bone-shaking force', '{enemy} buckles under a crushing blow'],
  arcane: ['Your {weapon} erupts, engulfing {enemy}', 'Raw power tears through {enemy}'],
  ranged: ['A perfect shot finds {enemy}\'s weak point', 'Your shot tears straight through the {body}'],
  music: ['Your {weapon} hits a note that sends {enemy} sprawling', 'A thunderous chord knocks {enemy} flat'],
  unarmed: ['A devastating strike folds {enemy} in half', 'You land a blow {enemy} will remember'],
};

const ATTACK_MISSES = [
  '{enemy} twists away from your {weapon}',
  'Your {weapon} cuts only air',
  '{enemy} sidesteps at the last moment',
];

const ATTACK_GLANCES = [
  'Your {weapon} skids off the {body}',
  '{enemy} takes the blow on its {body}',
  'Your {weapon} glances away harmlessly',
];

// Damage from a basic attack, by enemy kind.
const ENEMY_HITS = {
  brute: ['{enemy} slams into you like a falling wall', '{enemy} swings a massive fist into your side', '{enemy} batters you off your feet'],
  soldier: ['{enemy} strikes with practiced precision', '{enemy} drives a disciplined blow past your guard', '{enemy} presses the attack, steady and sure'],
  skirmisher: ['{enemy} darts in and cuts you', '{enemy} slips past your guard with a quick strike', '{enemy} strikes from your blind side'],
  beast: ['{enemy} sinks its fangs into you', '{enemy} rakes you with its claws', '{enemy} lunges and bowls you over'],
  caster: ['{enemy} hurls crackling energy at you', '{enemy} lashes out with a burst of power', 'A bolt from {enemy} sears your skin'],
  construct: ['{enemy}\'s servos whine as it strikes', '{enemy} hammers you with mechanical force', '{enemy} fires a burst that rattles your bones'],
  undead: ['{enemy}\'s cold grip tears at you', '{enemy} claws at you with grave-cold fingers', '{enemy} strikes, and a chill spreads through you'],
  horror: ['{enemy}\'s limbs lash out from impossible angles', 'Something in {enemy} tears at your mind and body', '{enemy} engulfs you in a nightmare of teeth'],
};

const ENEMY_CRITS = [
  '{enemy} lands a brutal, perfect blow',
  '{enemy} finds the opening it was waiting for',
];

const ENEMY_MOVES = [
  '{enemy} unleashes {move}',
  '{enemy}\'s {move} catches you',
  '{enemy} strikes with {move}',
];

const ENEMY_MISSES = [
  '{enemy} overreaches and misses',
  '{enemy}\'s attack goes wide',
  'You read {enemy}\'s move and it finds nothing',
];

const ENEMY_GLANCES = [
  'You catch {enemy}\'s blow on your guard',
  '{enemy}\'s attack scrapes harmlessly off your armor',
  'You turn {enemy}\'s strike aside',
];

const ENEMY_DODGED = [
  'You slip out of reach of {enemy}',
  'You twist away just in time',
];

const ENEMY_DEBUFFS = [
  '{enemy}\'s {move} leaves you {effect}',
  '{move} washes over you and you feel {effect}',
];

const ENEMY_BUFFS = [
  '{enemy} uses {move} and grows {effect}',
  '{enemy} gathers itself with {move}',
];

const ENEMY_STUNNED = [
  '{enemy} reels, unable to act',
  '{enemy} staggers, senses scrambled',
];

const ENEMY_HEALS = [
  '{enemy} uses {move}, its wounds closing',
  '{enemy} draws on hidden strength with {move}',
];

const ENEMY_CHARGES = [
  '{enemy} gathers power for something terrible',
  'Energy builds around {enemy}. Something big is coming',
];

const SKILL_HITS = [
  'Your {ability} slams into {enemy}',
  'You unleash {ability} on {enemy}',
  '{ability} strikes {enemy} squarely',
];
const SKILL_CRITS = ['Your {ability} lands with devastating force', '{ability} tears into {enemy} at the perfect moment'];
const SKILL_MISSES = ['{enemy} evades your {ability}', 'Your {ability} goes astray'];
const SKILL_GLANCES = ['Your {ability} barely scratches the {body}', '{enemy} weathers your {ability}'];
const SKILL_BUFFS = ['You use {ability}', 'You call on {ability}'];
const SKILL_DEBUFFS = ['Your {ability} leaves {enemy} {effect}', 'You turn {ability} on {enemy}'];
const SKILL_HEALS = ['Warmth floods through you as {ability} takes hold', 'You steady yourself with {ability}'];

const ITEM_LINES = ['You use the {item}', 'You quickly use your {item}'];

// Taunts: what the enemy says or does at the start, at half health and when it falls.
const SPEAKS = new Set(['soldier', 'skirmisher', 'caster', 'brute']);
const TAUNTS = {
  start: {
    speaks: ['"You should not have come here."', '"Turn back, or fall here."', '"Another fool to bury."'],
    beast: ['{enemy} snarls and circles you', '{enemy} bares its teeth, ready to pounce'],
    construct: ['{enemy} locks onto you with a cold whir', 'A red light sweeps over you as {enemy} targets you'],
    undead: ['{enemy} turns empty eyes toward you', 'A hollow rattle rises from {enemy}'],
    horror: ['{enemy} unfolds, far larger than it should be', 'The air curdles as {enemy} draws near'],
  },
  half: {
    speaks: ['"Is that all you have?"', '"You will pay for that."', '"Enough games."'],
    beast: ['{enemy} howls in pain and fury', 'Wounded, {enemy} grows wilder'],
    construct: ['Sparks spit from {enemy}\'s damaged frame', '{enemy} reroutes power with a shriek of metal'],
    undead: ['{enemy} keeps coming, heedless of its wounds', 'Bones grind as {enemy} pulls itself together'],
    horror: ['{enemy} shrieks, a sound that hurts to hear', '{enemy} bleeds something that is not blood'],
  },
  defeat: {
    speaks: ['{enemy} crumples with a final gasp', '{enemy} falls and does not rise'],
    beast: ['{enemy} collapses with a last whimper', '{enemy} goes still'],
    construct: ['{enemy} sparks, shudders and powers down', '{enemy}\'s lights flicker out'],
    undead: ['{enemy} collapses into dust and silence', 'The cold light in {enemy}\'s eyes dies'],
    horror: ['{enemy} unravels into nothing', '{enemy} lets out a final, fading shriek'],
  },
};
// A boss entering its second phase.
const BOSS_PHASE = [
  '"Enough! Now you face my true power!"',
  '{enemy} roars as its true power breaks loose',
];

const BOSS_START = [
  '"So you are the one who made it this far. It ends here."',
  '{enemy} rises to face you. Everything has led to this.',
];

const PERSONAL_TITLES = new Set([
  'lord', 'lady', 'king', 'queen', 'prince', 'princess', 'director', 'captain', 'commander', 'general',
  'baron', 'baroness', 'duke', 'duchess', 'count', 'countess', 'sir', 'dame', 'master', 'mistress',
  'doctor', 'dr', 'professor', 'agent', 'officer', 'warlord', 'high', 'archmage', 'father', 'mother',
]);

/** How a line refers to the enemy: "the Goblin Scavenger", but "Captain Vex" or "Malachar". */
export function enemyRef(name) {
  const clean = (name || '').trim() || 'enemy';
  const words = clean.split(/\s+/);
  const first = words[0].toLowerCase().replace(/[^a-z]/g, '');
  if (['the', 'a', 'an'].includes(first)) return clean;
  if (words.length === 1 && /^[A-Z]/.test(clean)) return clean; // a proper name
  if (PERSONAL_TITLES.has(first)) return clean;
  return `the ${clean}`;
}

// How an effect reads in a sentence ("leaves you weakened").
const EFFECT_WORDS = {
  bleed: 'bleeding', stun: 'stunned', weaken: 'weakened', focus: 'focused', empowered: 'empowered',
  poisoned: 'poisoned', burning: 'burning', blocking: 'guarded', healing: 'mending', dodging: 'evasive',
  hidden: 'hidden',
};

export function effectWord(effect) {
  return EFFECT_WORDS[(effect || '').toLowerCase()] || effect || '';
}

export function fill(template, vars) {
  return template.replace(/\{(\w+)\}/g, (_, key) => (vars[key] ?? ''));
}

function capitalize(text) {
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : text;
}

/**
 * A flavor generator for one fight. Remembers the last line of each pool so no
 * line repeats back to back.
 */
export function createFlavor({ enemy = 'the enemy', archetype = 'soldier', genre = 'fantasy', threat = 'standard', rng = Math.random } = {}) {
  const last = new Map();
  const base = { enemy: enemyRef(enemy), body: bodyWord(archetype, genre) };

  const pick = (key, pool, vars = {}) => {
    if (!pool || !pool.length) return '';
    const fresh = pool.length > 1 ? pool.filter(line => line !== last.get(key)) : pool;
    const line = fresh[Math.floor(rng() * fresh.length) % fresh.length];
    last.set(key, line);
    return capitalize(fill(line, { ...base, ...vars }));
  };

  return {
    /** kind: hit | crit | miss | glance */
    attackLine(weapon, kind) {
      const category = weaponCategory(weapon);
      const vars = { weapon: weapon || 'weapon' };
      if (kind === 'crit') return pick(`atk-crit-${category}`, ATTACK_CRITS[category], vars);
      if (kind === 'miss') return pick('atk-miss', ATTACK_MISSES, vars);
      if (kind === 'glance') return pick('atk-glance', ATTACK_GLANCES, vars);
      return pick(`atk-hit-${category}`, ATTACK_HITS[category], vars);
    },

    /** kind: hit | crit | miss | glance | buff | debuff | heal */
    skillLine(ability, kind, effect = '') {
      const vars = { ability, effect: effectWord(effect) };
      const pools = {
        crit: SKILL_CRITS, miss: SKILL_MISSES, glance: SKILL_GLANCES,
        buff: SKILL_BUFFS, debuff: SKILL_DEBUFFS, heal: SKILL_HEALS,
      };
      return pick(`skill-${kind}`, pools[kind] || SKILL_HITS, vars);
    },

    /** kind: hit | crit | miss | glance | dodged | debuff | buff | heal | charge | stunned */
    enemyMoveLine(move, kind, effect = '') {
      const vars = { move, effect: effectWord(effect) };
      const named = move && move !== 'Attack';
      switch (kind) {
        case 'crit': return pick('enemy-crit', ENEMY_CRITS, vars);
        case 'miss': return pick('enemy-miss', ENEMY_MISSES, vars);
        case 'glance': return pick('enemy-glance', ENEMY_GLANCES, vars);
        case 'dodged': return pick('enemy-dodged', ENEMY_DODGED, vars);
        case 'debuff': return pick('enemy-debuff', ENEMY_DEBUFFS, vars);
        case 'buff': return pick('enemy-buff', ENEMY_BUFFS, vars);
        case 'heal': return pick('enemy-heal', ENEMY_HEALS, vars);
        case 'charge': return pick('enemy-charge', ENEMY_CHARGES, vars);
        case 'stunned': return pick('enemy-stunned', ENEMY_STUNNED, vars);
        default:
          return named
            ? pick('enemy-move', ENEMY_MOVES, vars)
            : pick(`enemy-hit-${archetype}`, ENEMY_HITS[archetype] || ENEMY_HITS.soldier, vars);
      }
    },

    /** moment: start | half | phase (a boss's second phase) | defeat */
    tauntLine(moment) {
      if (moment === 'start' && threat === 'boss') return pick('taunt-boss', BOSS_START);
      if (moment === 'phase') return pick('taunt-phase', BOSS_PHASE);
      const pools = TAUNTS[moment] || TAUNTS.start;
      const pool = SPEAKS.has(archetype) ? pools.speaks : (pools[archetype] || pools.speaks);
      return pick(`taunt-${moment}`, pool);
    },

    itemLine(item) {
      return pick('item', ITEM_LINES, { item });
    },
  };
}

/**
 * The small numbers shown after a story line, from a combat.js result.
 * e.g. "−7", "−11 crit", "+20 HP", "rolled 4 vs 12", "💫 stun".
 */
export function resultDetail(result, icon = () => '') {
  if (!result) return '';
  const dmg = result.damage;
  const effect = result.effect ? `${icon(result.effect)} ${result.effect}`.trim() : '';
  const extras = [
    effect,
    result.hits ? `${result.hits} hits` : '',
    result.blunted ? 'blunted' : '',
    result.drained ? `drains ${result.drained}` : '',
    result.immune ? `immune to ${result.immune}` : '',
    result.cancelled ? `${result.cancelled} lost` : '',
  ].filter(Boolean);
  if (dmg?.heal) return [`+${dmg.amount} HP`, ...extras].join(' · ');
  if (dmg) return [`${MINUS}${dmg.amount}${dmg.crit ? ' crit' : ''}`, ...extras].join(' · ');
  if (result.manaRestored) return `+${result.manaRestored} MP`;
  if (extras.length) return extras.join(' · ');
  if (result.diceInfo && !result.diceInfo.success) return `rolled ${result.diceInfo.roll} vs ${result.diceInfo.target}`;
  return '';
}
