// XP and level-up display, from the server's `xp_gained` and `level_up` list
// (each entry: { level, reason, hp_gain, mana_gain, stats: { strength: 1, ... }, max_hp, max_mana }).

const STAT_LABELS = {
  strength: 'STR', intelligence: 'INT', dexterity: 'DEX', control: 'CON', charisma: 'CHA', wisdom: 'WIS',
};

/** "+25 XP", or '' when nothing was earned. */
export function xpBadgeText(xpGained) {
  const xp = Math.round(Number(xpGained) || 0);
  return xp > 0 ? `+${xp} XP` : '';
}

/**
 * Summarise the level-ups from one response for the banner.
 * @returns {null | { level: number, levelsGained: number, gains: string[] }}
 */
export function describeLevelUps(levelUps) {
  const list = Array.isArray(levelUps) ? levelUps.filter(lu => lu && Number(lu.level) > 0) : [];
  if (!list.length) return null;
  let hp = 0;
  let mana = 0;
  const stats = {};
  for (const lu of list) {
    hp += Number(lu.hp_gain) || 0;
    mana += Number(lu.mana_gain) || 0;
    for (const [stat, delta] of Object.entries(lu.stats || {})) {
      stats[stat] = (stats[stat] || 0) + (Number(delta) || 0);
    }
  }
  const gains = [];
  if (hp) gains.push(`+${hp} max HP`);
  if (mana) gains.push(`+${mana} max mana`);
  for (const [stat, delta] of Object.entries(stats)) {
    if (delta) gains.push(`+${delta} ${STAT_LABELS[stat] || stat.toUpperCase()}`);
  }
  return {
    level: Math.max(...list.map(lu => Number(lu.level))),
    levelsGained: list.length,
    gains,
  };
}
