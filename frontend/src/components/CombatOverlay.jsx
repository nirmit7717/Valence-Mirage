import { useState, useCallback, useEffect, useRef } from 'react';
import { canAct, getWeaponDice, resolvePlayerAttack, resolvePlayerSkill, resolvePlayerItem, resolveEnemyTurn, getStatusIcon, cloneCombatState, enemyIntro } from '../utils/combat';
import { classIcon, createFlavor, enemyIcon, resultDetail } from '../utils/combatFlavor';

const THREAT_LABELS = { minion: 'Minion', elite: 'Elite', boss: 'Boss' };
const LOG_CLASSES = { player: 'player-log', enemy: 'enemy-log', crit: 'crit-log', scene: 'scene-log', system: 'system-log' };

// Story line + small numbers for one combat.js result (see utils/combatFlavor.js).
function storyLine(flavor, result, source) {
  if (source.kind === 'attack') return flavor.attackLine(source.weapon, result.kind);
  if (source.kind === 'skill') return flavor.skillLine(source.ability.name, result.kind, result.effect || '');
  if (source.kind === 'item') return flavor.itemLine(source.item);
  return flavor.enemyMoveLine(result.move, result.kind, result.effect || '');
}

function describeResult(flavor, result, source) {
  return { text: storyLine(flavor, result, source) || result.log, detail: resultDetail(result, getStatusIcon) };
}

// ─── Inline Combat Dice Animation ───
function CombatDice({ roll, target, success, crit, onDone }) {
  const [phase, setPhase] = useState('spin');
  const [display, setDisplay] = useState('?');

  useEffect(() => {
    let count = 0;
    const max = 8;
    const iv = setInterval(() => {
      count++;
      if (count >= max) {
        setDisplay(roll);
        clearInterval(iv);
        setTimeout(() => { setPhase('show'); setTimeout(() => onDone?.(), 400); }, 150);
      } else {
        setDisplay(Math.floor(Math.random() * 20) + 1);
      }
    }, 60);
    return () => clearInterval(iv);
  }, [roll, target, onDone]);

  return (
    <div className={`combat-dice ${success ? 'cd-success' : 'cd-fail'} ${crit ? 'cd-crit' : ''}`}>
      {phase === 'spin' ? (
        <span className="cd-num cd-spinning">🎲 {display}</span>
      ) : (
        <>
          <span className={`cd-num ${success ? 'cd-green' : 'cd-red'}`}>{roll}</span>
          <span className="cd-vs">vs {target}</span>
          <span className={`cd-label ${success ? 'cd-green' : 'cd-red'}`}>{crit ? (success ? 'CRIT!' : 'CRIT FAIL!') : success ? 'HIT' : 'MISS'}</span>
        </>
      )}
    </div>
  );
}

export default function CombatOverlay({ combat, onResolve, animationsEnabled }) {
  const [state, setState] = useState(null);
  const [menu, setMenu] = useState('main'); // main | attack | skill | item
  const [logs, setLogs] = useState([]);
  const [turnPhase, setTurnPhase] = useState('player'); // player | enemy
  const [entering, setEntering] = useState(true);
  const [ending, setEnding] = useState(false);
  const [dmgFloats, setDmgFloats] = useState([]);
  const [flashes, setFlashes] = useState({});
  const [activeDice, setActiveDice] = useState(null); // { roll, target, success, crit }
  const floatsRef = useRef(0);
  const diceIdRef = useRef(0);
  // Held from the moment the player acts until the enemy's turn has fully played out.
  const actionLockRef = useRef(false);
  // Flavor lines for this fight, and whether the enemy has reacted to dropping below half HP.
  const flavorRef = useRef(createFlavor());
  const halfTauntRef = useRef(false);
  // doEnemy runs again when the player is stunned; the ref avoids a self-referencing callback.
  const doEnemyRef = useRef(null);

  // Initialize combat: the scene that led here, who the enemy is, and its opening taunt.
  useEffect(() => {
    if (!combat) return;
    const flavor = createFlavor({
      enemy: combat.enemy.name,
      archetype: combat.enemy.archetype,
      genre: combat.genre,
      threat: combat.enemy.threat,
    });
    flavorRef.current = flavor;
    halfTauntRef.current = false;
    setState(cloneCombatState(combat));
    const opening = [
      combat.scene && { text: combat.scene, type: 'scene' },
      { text: combat.enemy.description || enemyIntro(combat.enemy.name), type: 'system' },
      { text: flavor.tauntLine('start'), type: 'enemy', kind: 'taunt' },
    ].filter(Boolean);
    setLogs(opening.reverse()); // newest first
    setMenu('main');
    setTurnPhase('player');
    setEntering(true);
    setEnding(false);
    setActiveDice(null);
    actionLockRef.current = false;
    setTimeout(() => setEntering(false), 500);
  }, [combat]);

  const addLog = useCallback((text, type = 'system', detail = '', kind = '') => {
    setLogs(prev => [{ text, type, detail, kind }, ...prev].slice(0, 25));
  }, []);

  const logResult = useCallback((result, source, type) => {
    const { text, detail } = describeResult(flavorRef.current, result, source);
    addLog(text, type, detail, result.kind || '');
  }, [addLog]);

  // The enemy reacts once when it first drops to half health.
  const maybeHalfTaunt = useCallback((s) => {
    if (halfTauntRef.current || s.enemy.hp <= 0 || s.enemy.hp > s.enemy.max_hp / 2) return;
    halfTauntRef.current = true;
    addLog(flavorRef.current.tauntLine('half'), 'enemy', '', 'taunt');
  }, [addLog]);

  const showDmg = useCallback((target, amount, type) => {
    const id = ++floatsRef.current;
    setDmgFloats(prev => [...prev, { id, target, amount, type }]);
    setTimeout(() => setDmgFloats(prev => prev.filter(f => f.id !== id)), 1000);
  }, []);

  const flashCard = useCallback((target) => {
    if (!animationsEnabled) return;
    setFlashes(prev => ({ ...prev, [target]: true }));
    setTimeout(() => setFlashes(prev => ({ ...prev, [target]: false })), 400);
  }, [animationsEnabled]);

  // Recent log lines go to the server for the post-combat narration.
  const logsRef = useRef([]);
  useEffect(() => { logsRef.current = logs; }, [logs]);
  const finish = useCallback((result, s) => {
    s.resolved = true;
    // Story lines only; the scene is already known to the server.
    s.logEntries = logsRef.current
      .filter(l => l.type !== 'scene')
      .map(l => ({ text: l.text, type: l.type }))
      .reverse()
      .slice(-12);
    setTimeout(() => onResolve(result, s), 1200);
  }, [onResolve]);

  const announceVictory = useCallback(() => {
    addLog(`🏆 ${flavorRef.current.tauntLine('defeat')}`, 'crit', 'defeated', 'crit');
  }, [addLog]);

  const checkDeath = useCallback((s) => {
    if (s.enemy.hp <= 0) {
      s.enemy.hp = 0;
      announceVictory();
      setEnding(true);
      finish('victory', s);
      return true;
    }
    if (s.player.hp <= 0) {
      s.player.hp = 0;
      addLog('💀 You have been defeated...', 'crit', '', 'crit');
      setEnding(true);
      finish('defeat', s);
      return true;
    }
    return false;
  }, [addLog, finish, announceVictory]);

  const showDiceThen = useCallback((diceInfo, callback) => {
    if (!diceInfo) { callback(); return; }
    setActiveDice({ ...diceInfo, id: ++diceIdRef.current });
    // Callback fires after CombatDice's onDone (~1.1s) so the result lands with the dice.
    setTimeout(callback, 1100);
  }, []);

  const clearDice = useCallback(() => setActiveDice(null), []);

  // Enemy turn. Resolved on a copy; nothing (HP, effects, logs) is shown until the dice land.
  const doEnemy = useCallback((current) => {
    if (current.resolved) return;
    setTurnPhase('enemy');

    const next = cloneCombatState(current);
    const result = resolveEnemyTurn(next);
    if (result.ended) {
      if (result.victory) {
        next.enemy.hp = 0;
        setState(next);
        announceVictory();
        setEnding(true);
        finish('victory', next);
      }
      return;
    }
    showDiceThen(result.diceInfo, () => {
      logResult(result, { kind: 'enemy' }, result.type === 'crit' ? 'crit' : 'enemy');
      if (result.taunt) addLog(flavorRef.current.tauntLine(result.taunt), 'enemy', '', 'taunt');
      // The enemy's heal lands on its own card.
      if (result.damage) showDmg(result.damage.target, result.damage.amount, result.damage.heal ? 'heal' : result.damage.crit ? 'crit' : 'damage');
      if (result.flash) flashCard(result.flash);
      setState(next);
      if (checkDeath(next)) return;
      maybeHalfTaunt(next); // damage over time can drop it below half too
      if (!canAct(next.player)) {
        // Stunned (a pounce, a shield slam...): the player loses this turn.
        setTimeout(() => {
          addLog('💫 You are stunned and lose your turn!', 'system', 'stun', 'stunned');
          setTimeout(() => doEnemyRef.current?.(next), 900);
        }, 500);
        return;
      }
      setTimeout(() => {
        setTurnPhase('player');
        setMenu('main');
        actionLockRef.current = false;
      }, 300);
    });
  }, [addLog, logResult, showDmg, flashCard, checkDeath, finish, showDiceThen, announceVictory, maybeHalfTaunt]);
  useEffect(() => { doEnemyRef.current = doEnemy; }, [doEnemy]);

  // Player actions — same pattern: resolve on a copy, commit after the roll animation.
  const commitPlayerResult = useCallback((next, result, source) => {
    logResult(result, source, result.type === 'crit' ? 'crit' : 'player');
    if (result.damage) showDmg(result.damage.target, result.damage.amount, result.damage.crit ? 'crit' : result.damage.heal ? 'heal' : 'damage');
    if (result.flash) flashCard(result.flash);
    setState(next);
    if (checkDeath(next)) return;
    maybeHalfTaunt(next);
    setTimeout(() => doEnemy(next), 600);
  }, [logResult, showDmg, flashCard, checkDeath, maybeHalfTaunt, doEnemy]);

  const doAttack = useCallback((weaponName, dice) => {
    if (!state || state.resolved || actionLockRef.current) return;
    actionLockRef.current = true;
    const next = cloneCombatState(state);
    const result = resolvePlayerAttack(next, weaponName, dice);
    showDiceThen(result.diceInfo, () => commitPlayerResult(next, result, { kind: 'attack', weapon: weaponName }));
  }, [state, showDiceThen, commitPlayerResult]);

  const doSkill = useCallback((ability) => {
    if (!state || state.resolved || actionLockRef.current) return;
    if (ability.mana_cost > state.player.mana) { addLog(`Not enough mana for ${ability.name}!`, 'system'); return; }
    actionLockRef.current = true;
    const next = cloneCombatState(state);
    const result = resolvePlayerSkill(next, ability); // deducts the mana cost exactly once
    showDiceThen(result.diceInfo, () => commitPlayerResult(next, result, { kind: 'skill', ability }));
  }, [state, addLog, showDiceThen, commitPlayerResult]);

  const doItem = useCallback((itemName, hpRestore, manaRestore) => {
    if (!state || state.resolved || actionLockRef.current) return;
    actionLockRef.current = true;
    const next = cloneCombatState(state);
    const results = resolvePlayerItem(next, itemName, hpRestore, manaRestore);
    results.forEach(r => {
      logResult(r, { kind: 'item', item: itemName }, 'player');
      if (r.damage) showDmg(r.damage.target, r.damage.amount, 'heal');
    });
    setState(next);
    setTimeout(() => doEnemy(next), 600);
  }, [state, logResult, showDmg, doEnemy]);

  if (!combat || !state) return null;

  const ePct = Math.max(0, (state.enemy.hp / state.enemy.max_hp) * 100);
  const pPct = Math.max(0, (state.player.hp / state.player.max_hp) * 100);
  const weapons = state.inventory.filter(i => i.type === 'weapon');
  const consumables = state.inventory.filter(i => i.type === 'consumable');

  return (
    <div className="combat-overlay-glass" style={{ animation: entering ? 'combatFadeIn 0.4s ease-out' : undefined }}>
      <div className={`combat-arena ${entering ? 'combat-entering' : ''} ${ending ? 'combat-ending' : ''}`}>
        {/* Enemy */}
        <div className="arena-top">
          <div className={`combat-entity enemy-entity ${flashes.enemy ? 'hit-flash shake' : ''}`} id="enemyCard">
            <span className="entity-icon" aria-hidden="true">{enemyIcon(state.enemy.archetype)}</span>
            <h3>
              {state.enemy.name}
              {THREAT_LABELS[state.enemy.threat] && (
                <span className={`threat-badge threat-${state.enemy.threat}`}>{THREAT_LABELS[state.enemy.threat]}</span>
              )}
            </h3>
            {state.enemy.description && <div className="enemy-desc">{state.enemy.description}</div>}
            <div className="hp-bar-bg"><div className="hp-bar-fill" style={{ width: `${ePct}%` }} /></div>
            <div className="hp-text">HP: {Math.max(0, state.enemy.hp)}/{state.enemy.max_hp} | Armor: {state.enemy.armor}</div>
            {state.enemyIntent && state.enemy.hp > 0 && (
              <div
                className={`enemy-intent ${state.enemyIntent.warn ? 'enemy-intent-warn' : ''}`}
                aria-label={`Next enemy move: ${state.enemyIntent.name}${state.enemyIntent.warn ? ' (dangerous)' : ''}`}
              >
                Next: {state.enemyIntent.label}
              </div>
            )}
            {state.enemy.status_effects.length > 0 && (
              <div className="status-effects-row">
                {state.enemy.status_effects.map((se, i) => <span key={i} className="status-pill" title={se.name}>{getStatusIcon(se.name)} {se.name}{se.duration > 0 ? ` (${se.duration})` : ''}</span>)}
              </div>
            )}
            {/* Damage floats - enemy */}
            {dmgFloats.filter(f => f.target === 'enemy').map(f => (
              <div key={f.id} className={`dmg-float ${f.type === 'crit' ? 'crit-float' : f.type === 'heal' ? 'heal-float' : 'dmg-dealt'}`}>
                {f.type === 'heal' ? '+' : '-'}{f.amount}
              </div>
            ))}
          </div>
        </div>

        {/* Player */}
        <div className="arena-bottom">
          <div className={`combat-entity player-entity ${flashes.player ? 'hit-flash shake' : ''}`} id="playerCard">
            <span className="entity-icon" aria-hidden="true">{classIcon(state.player.character_class)}</span>
            <h3>{state.player.name}</h3>
            <div className="hp-bar-bg"><div className="hp-bar-fill" style={{ width: `${pPct}%` }} /></div>
            <div className="hp-text">HP: {Math.max(0, state.player.hp)}/{state.player.max_hp} | MP: {state.player.mana}/{state.player.max_mana}</div>
            {state.player.status_effects.length > 0 && (
              <div className="status-effects-row">
                {state.player.status_effects.map((se, i) => <span key={i} className="status-pill" title={se.name}>{getStatusIcon(se.name)} {se.name}{se.duration > 0 ? ` (${se.duration})` : ''}</span>)}
              </div>
            )}
            {/* Damage floats - player */}
            {dmgFloats.filter(f => f.target === 'player').map(f => (
              <div key={f.id} className={`dmg-float ${f.type === 'crit' ? 'crit-float' : f.type === 'heal' ? 'heal-float' : 'dmg-taken'}`}>
                {f.type === 'heal' ? '+' : '-'}{f.amount}
              </div>
            ))}
          </div>
        </div>

        {/* Log */}
        <div className="combat-log-area" aria-live="polite">
          {logs.map((l, i) => (
            <div key={i} className={`combat-log-entry ${LOG_CLASSES[l.type] || 'system-log'}`}>
              {l.text}
              {l.detail && <span className="combat-log-detail"> ({l.detail})</span>}
            </div>
          ))}
        </div>

        {/* Combat Dice Animation */}
        {activeDice && (
          <CombatDice
            key={activeDice.id}
            roll={activeDice.roll}
            target={activeDice.target}
            success={activeDice.success}
            crit={activeDice.crit}
            onDone={clearDice}
          />
        )}

        {/* Controls */}
        <div className="combat-controls">
          <div className={`turn-indicator ${turnPhase === 'player' ? 'your-turn' : 'enemy-turn'}`}>
            {turnPhase === 'player' ? 'YOUR TURN' : 'ENEMY TURN'}
          </div>
          <div className={`menu-tier ${turnPhase !== 'player' || ending ? 'menu-locked' : ''}`}
            aria-disabled={turnPhase !== 'player' || ending}>
            {menu === 'main' && (
              <>
                <button className="combat-btn" onClick={() => setMenu('attack')}>⚔️ Attack</button>
                <button className="combat-btn btn-skill" onClick={() => setMenu('skill')}>✨ Skill</button>
                <button className="combat-btn btn-item" onClick={() => setMenu('item')}>🎒 Items</button>
              </>
            )}
            {menu === 'attack' && (
              <>
                {weapons.length === 0 ? (
                  <button className="combat-btn" onClick={() => doAttack('Unarmed Strike', '1d6')}>👊 Unarmed Strike</button>
                ) : weapons.map((w, i) => {
                  const dice = getWeaponDice(w.name);
                  return <button key={i} className="combat-btn" onClick={() => doAttack(w.name, dice)}>⚔️ {w.name}<span className="dmg-dice">{dice}</span></button>;
                })}
                <button className="combat-btn btn-back" onClick={() => setMenu('main')}>🔙 Back</button>
              </>
            )}
            {menu === 'skill' && (
              <>
                {state.abilities.length === 0 ? (
                  <div style={{ gridColumn: 'span 3', textAlign: 'center', color: '#555' }}>No abilities available</div>
                ) : state.abilities.map((a, i) => (
                  <button key={i} className="combat-btn btn-skill" disabled={a.mana_cost > state.player.mana}
                    onClick={() => doSkill(a)}>
                    {a.name}<span className="mana-cost">{a.mana_cost}mp</span>{a.damage_dice && <span className="dmg-dice">{a.damage_dice}</span>}
                  </button>
                ))}
                <button className="combat-btn btn-back" onClick={() => setMenu('main')}>🔙 Back</button>
              </>
            )}
            {menu === 'item' && (
              <>
                {consumables.length === 0 ? (
                  <div style={{ gridColumn: 'span 3', textAlign: 'center', color: '#555' }}>Backpack is empty...</div>
                ) : consumables.map((item, i) => {
                  const effect = item.hp_restore ? `+${item.hp_restore}HP` : item.mana_restore ? `+${item.mana_restore}MP` : '';
                  return <button key={i} className="combat-btn btn-item" onClick={() => doItem(item.name, item.hp_restore || 0, item.mana_restore || 0)}>🧪 {item.name} <span style={{ fontSize: 10, color: '#8cf' }}>{effect}</span></button>;
                })}
                <button className="combat-btn btn-back" onClick={() => setMenu('main')}>🔙 Back</button>
              </>
            )}
          </div>
        </div>

        {/* Combat cinematic effects */}
        {animationsEnabled && <CombatCinematics logs={logs} />}
      </div>
    </div>
  );
}

// ─── Cinematic Effects Component ───
function CombatCinematics({ logs }) {
  const [flash, setFlash] = useState(null);

  useEffect(() => {
    if (logs.length === 0) return;
    const latest = logs[0];
    if (!latest) return;

    // Story lines don't say "critical" or "miss", so the flash follows the entry's kind.
    if (latest.kind === 'crit') {
      setFlash('crit');
      setTimeout(() => setFlash(null), 300);
    } else if (['miss', 'glance', 'dodged'].includes(latest.kind)) {
      setFlash('miss');
      setTimeout(() => setFlash(null), 200);
    } else if (latest.kind === 'hit' && (latest.type === 'enemy' || latest.type === 'player')) {
      setFlash('hit');
      setTimeout(() => setFlash(null), 150);
    }
  }, [logs]);

  if (!flash) return null;

  return (
    <div className={`cinematic-flash ${flash}`} style={{
      position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 100, borderRadius: 16,
      background: flash === 'crit' ? 'rgba(255,255,0,0.15)' : flash === 'miss' ? 'rgba(100,100,255,0.08)' : 'rgba(255,100,100,0.1)',
      animation: flash === 'crit' ? 'critFlash 0.3s ease-out' : 'hitFlash 0.15s ease-out',
    }} />
  );
}
