import { useState, useCallback, useEffect, useRef } from 'react';
import { rollD20, rollDice, getWeaponDice, tickEffects, resolvePlayerAttack, resolvePlayerSkill, resolvePlayerItem, resolveEnemyTurn } from '../utils/combat';

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
  const actionLockRef = useRef(false);

  // Initialize combat
  useEffect(() => {
    if (!combat) return;
    setState({ ...combat });
    setLogs([{ text: `⚔️ A ${combat.enemy.name} appears!`, type: 'system' }]);
    setMenu('main');
    setTurnPhase('player');
    setEntering(true);
    setEnding(false);
    setActiveDice(null);
    actionLockRef.current = false;
    setTimeout(() => setEntering(false), 500);
  }, [combat]);

  const addLog = useCallback((text, type = 'system') => {
    setLogs(prev => [{ text, type }, ...prev].slice(0, 25));
  }, []);

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

  const checkDeath = useCallback((s) => {
    if (s.enemy.hp <= 0) {
      s.enemy.hp = 0;
      addLog(`🏆 ${s.enemy.name} is defeated!`, 'crit');
      setEnding(true);
      setTimeout(() => onResolve('victory', s), 1200);
      return true;
    }
    if (s.player.hp <= 0) {
      s.player.hp = 0;
      addLog('💀 You have been defeated...', 'crit');
      setEnding(true);
      setTimeout(() => onResolve('defeat', s), 1200);
      return true;
    }
    return false;
  }, [addLog, onResolve]);

  const showDiceThen = useCallback((diceInfo, callback) => {
    if (!diceInfo) { callback(); return; }
    setActiveDice(diceInfo);
    // Callback fires after CombatDice's onDone (~1.1s)
    // We delay slightly to let the dice land visually
    setTimeout(callback, 1100);
  }, []);

  // Player actions
  const doAttack = useCallback((weaponName, dice) => {
    if (!state || state.resolved || actionLockRef.current) return;
    actionLockRef.current = true;
    const s = { ...state, enemy: { ...state.enemy }, player: { ...state.player } };
    const result = resolvePlayerAttack(s, weaponName, dice);
    showDiceThen(result.diceInfo, () => {
      addLog(result.log, result.type === 'crit' ? 'crit' : 'player');
      if (result.damage) showDmg(result.damage.target, result.damage.amount, result.damage.crit ? 'crit' : result.damage.heal ? 'heal' : 'damage');
      if (result.flash) flashCard(result.flash);
      setState(s);
      actionLockRef.current = false;
      if (checkDeath(s)) return;
      setTimeout(() => doEnemy(s), 600);
    });
  }, [state, addLog, showDmg, flashCard, checkDeath, showDiceThen]);

  const doSkill = useCallback((ability) => {
    if (!state || state.resolved || actionLockRef.current) return;
    if (ability.mana_cost > state.player.mana) { addLog(`Not enough mana for ${ability.name}!`, 'system'); return; }
    actionLockRef.current = true;
    const s = { ...state, enemy: { ...state.enemy }, player: { ...state.player, status_effects: [...state.player.status_effects], mana: state.player.mana - ability.mana_cost }, enemy: { ...state.enemy, status_effects: [...state.enemy.status_effects] } };
    const result = resolvePlayerSkill(s, ability);
    showDiceThen(result.diceInfo, () => {
      addLog(result.log, result.type === 'crit' ? 'crit' : 'player');
      if (result.damage) showDmg(result.damage.target, result.damage.amount, result.damage.crit ? 'crit' : result.damage.heal ? 'heal' : 'damage');
      if (result.flash) flashCard(result.flash);
      setState(s);
      actionLockRef.current = false;
      if (checkDeath(s)) return;
      setTimeout(() => doEnemy(s), 600);
    });
  }, [state, addLog, showDmg, flashCard, checkDeath, showDiceThen]);

  const doItem = useCallback((itemName, hpRestore, manaRestore) => {
    if (!state || state.resolved || actionLockRef.current) return;
    actionLockRef.current = true;
    const s = { ...state, player: { ...state.player }, inventory: [...state.inventory] };
    const results = resolvePlayerItem(s, itemName, hpRestore, manaRestore);
    results.forEach(r => {
      addLog(r.log, 'player');
      if (r.damage) showDmg(r.damage.target, r.damage.amount, 'heal');
    });
    setState(s);
    actionLockRef.current = false;
    setTimeout(() => doEnemy(s), 600);
  }, [state, addLog, showDmg]);

  const doEnemy = useCallback((s) => {
    if (s.resolved) return;
    setTurnPhase('enemy');

    const result = resolveEnemyTurn(s);
    if (result.ended) {
      if (result.victory) { s.resolved = true; addLog(`🏆 ${s.enemy.name} is defeated!`, 'crit'); setEnding(true); setTimeout(() => onResolve('victory', s), 800); }
      return;
    }
    showDiceThen(result.diceInfo, () => {
      addLog(result.log, result.type === 'crit' ? 'crit' : 'enemy');
      if (result.damage) showDmg(result.damage.target, result.damage.amount, result.damage.crit ? 'crit' : 'damage');
      if (result.flash) flashCard(result.flash);
      setState({ ...s });
      if (checkDeath(s)) return;
      setTimeout(() => {
        setTurnPhase('player');
        setMenu('main');
      }, 300);
    });
  }, [addLog, showDmg, flashCard, checkDeath, onResolve, showDiceThen]);

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
            <span className="entity-icon">👹</span>
            <h3>{state.enemy.name}</h3>
            <div className="hp-bar-bg"><div className="hp-bar-fill" style={{ width: `${ePct}%` }} /></div>
            <div className="hp-text">HP: {Math.max(0, state.enemy.hp)}/{state.enemy.max_hp} | Armor: {state.enemy.armor}</div>
            {state.enemy.status_effects.length > 0 && (
              <div className="status-effects-row">
                {state.enemy.status_effects.map((se, i) => <span key={i} className="status-pill">{se.name}{se.duration > 0 ? ` (${se.duration})` : ''}</span>)}
              </div>
            )}
            {/* Damage floats */}
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
            <span className="entity-icon">🥷</span>
            <h3>{state.player.name}</h3>
            <div className="hp-bar-bg"><div className="hp-bar-fill" style={{ width: `${pPct}%` }} /></div>
            <div className="hp-text">HP: {Math.max(0, state.player.hp)}/{state.player.max_hp} | MP: {state.player.mana}/{state.player.max_mana}</div>
            {state.player.status_effects.length > 0 && (
              <div className="status-effects-row">
                {state.player.status_effects.map((se, i) => <span key={i} className="status-pill">{se.name}{se.duration > 0 ? ` (${se.duration})` : ''}</span>)}
              </div>
            )}
            {dmgFloats.filter(f => f.target === 'player').map(f => (
              <div key={f.id} className={`dmg-float ${f.type === 'crit' ? 'crit-float' : f.type === 'heal' ? 'heal-float' : 'dmg-taken'}`}>
                {f.type === 'heal' ? '+' : '-'}{f.amount}
              </div>
            ))}
          </div>
        </div>

        {/* Log */}
        <div className="combat-log-area">
          {logs.map((l, i) => (
            <div key={i} className={`combat-log-entry ${l.type === 'player' ? 'player-log' : l.type === 'enemy' ? 'enemy-log' : l.type === 'crit' ? 'crit-log' : 'system-log'}`}>
              {l.text}
            </div>
          ))}
        </div>

        {/* Combat Dice Animation */}
        {activeDice && (
          <CombatDice
            roll={activeDice.roll}
            target={activeDice.target}
            success={activeDice.success}
            crit={activeDice.crit}
            onDone={() => setActiveDice(null)}
          />
        )}

        {/* Controls */}
        <div className="combat-controls">
          <div className={`turn-indicator ${turnPhase === 'player' ? 'your-turn' : 'enemy-turn'}`}>
            {turnPhase === 'player' ? 'YOUR TURN' : 'ENEMY TURN'}
          </div>
          <div className="menu-tier">
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

    const text = latest.text.toLowerCase();
    if (text.includes('critical') || text.includes('⚡')) {
      setFlash('crit');
      setTimeout(() => setFlash(null), 300);
    } else if (text.includes('miss')) {
      setFlash('miss');
      setTimeout(() => setFlash(null), 200);
    } else if (latest.type === 'enemy' || latest.type === 'player') {
      if (text.includes('damage') || text.includes('strike') || text.includes('uses')) {
        setFlash('hit');
        setTimeout(() => setFlash(null), 150);
      }
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
