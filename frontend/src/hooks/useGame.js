// ═══════════════════════════════════════════════
//  useGame — Core game state management hook
// ═══════════════════════════════════════════════

import { useState, useCallback, useRef } from 'react';
import * as api from '../api';
import { createCombatState } from '../utils/combat';
import { getThemeFromCampaign } from '../utils/theme';

export function useGame() {
  const [sessionId, setSessionId] = useState(null);
  const [sessionInfo, setSessionInfo] = useState(null);
  const [messages, setMessages] = useState([]);
  const [sidebar, setSidebar] = useState(null);
  const [loading, setLoading] = useState(false);
  const [narration, setNarration] = useState(null);
  const [combat, setCombat] = useState(null);
  const [campaignEnded, setCampaignEnded] = useState(false);
  const [gameOver, setGameOver] = useState(false);
  const [victory, setVictory] = useState(false);
  const [theme, setTheme] = useState('default');
  const [busy, setBusy] = useState(false);
  const [diceResult, setDiceResult] = useState(null);     // triggers dice animation
  const [pendingResponse, setPendingResponse] = useState(null); // queued until dice animation completes
  const msgIdRef = useRef(0);

  const addMessage = useCallback((type, content) => {
    const id = ++msgIdRef.current;
    setMessages(prev => [...prev, { id, type, content }]);
    return id;
  }, []);

  const removeMessage = useCallback((id) => {
    setMessages(prev => prev.filter(m => m.id !== id));
  }, []);

  const startSession = useCallback(async ({ player_name, keywords, character_class, campaign_size }) => {
    setLoading(true);
    try {
      const data = await api.createSession({ player_name, keywords, character_class, campaign_size });
      setSessionId(data.session_id);
      setSessionInfo({ turn: 0, title: data.campaign?.title });

      const detectedTheme = getThemeFromCampaign(data.campaign);
      setTheme(detectedTheme);

      const classEmoji = { warrior: '⚔️', rogue: '🗡️', wizard: '🔮', cleric: '✨', bard: '🎵' };
      const className = data.character_class ? data.character_class.charAt(0).toUpperCase() + data.character_class.slice(1) : character_class;
      addMessage('system', `${classEmoji[data.character_class] || '⚔️'} <strong>${className}</strong> — ${data.class_description || ''}`);

      if (data.opening_narration) {
        setNarration({
          html: `<strong>📜 ${data.campaign.title}</strong><br/><br/>${data.opening_narration}`,
          meta: null,
          choices: data.choices || null,
          combatData: null,
        });
        addMessage('system', `<strong>📜 ${data.campaign.title}</strong><br/><br/>${data.opening_narration}`);
      } else {
        addMessage('system', `<strong>📜 ${data.campaign.title}</strong><br/><br/>${data.campaign.premise}<br/><br/><em>Setting: ${data.campaign.setting}</em>`);
      }

      if (data.npcs?.length) {
        let npcMsg = '<strong>👥 People You Meet:</strong><br/>';
        data.npcs.forEach(n => { npcMsg += `• <strong>${n.name}</strong> (${n.role}) — disposition: ${(n.disposition || 0).toFixed(1)}<br/>`; });
        addMessage('system', npcMsg);
      }

      if (data.player) {
        setSidebar({
          name: player_name,
          level: 1,
          xp: 0, xpToNext: 100,
          hp: data.player.hp, maxHp: data.player.max_hp,
          mana: data.player.mana, maxMana: data.player.max_mana,
          stats: data.player.stats,
          beat: data.campaign?.acts?.[0]?.beats?.[0]?.title || '—',
          inventory: data.player.inventory || [],
          npcs: data.npcs || [],
          effects: [],
          lastRoll: null,
          objective: data.world_state?.campaign_objective || data.campaign?.possible_endings?.[0] || '',
        });
      }

      return data;
    } finally {
      setLoading(false);
    }
  }, [addMessage]);

  // Called by DiceRoll when animation finishes — processes the queued response
  const onDiceAnimationComplete = useCallback(() => {
    setDiceResult(null);
    const data = pendingResponse;
    if (!data) return;
    setPendingResponse(null);
    _processResponse(data);
  }, [pendingResponse]);

  // Shared response processing (called either directly or after dice animation)
  const _processResponse = useCallback((data) => {
    // Extract arrow choices
    let cleanNarration = data.narration || '';
    const arrowChoices = [];
    cleanNarration = cleanNarration.replace(/^(?:→|->)\s*(.+)$/gm, (_, choice) => { arrowChoices.push(choice.trim()); return ''; }).trim();
    data.narration = cleanNarration;
    if (arrowChoices.length > 0 && (!data.choices || data.choices.length === 0)) {
      data.choices = arrowChoices;
    }

    // Build meta HTML
    let metaHtml = '';
    if (data.requires_roll) {
      const badgeClass = data.outcome.includes('critical')
        ? (data.outcome.includes('success') ? 'crit-success' : 'crit-failure')
        : (data.outcome === 'success' ? 'success' : data.outcome === 'partial_success' ? 'partial' : 'failure');
      const outcomeLabel = data.outcome.replace(/_/g, ' ').toUpperCase();
      metaHtml += `<span class="dice-badge ${badgeClass}">🎲 ${data.roll} vs ${data.dice_threshold}+</span>`;
      metaHtml += `<span class="dice-badge ${badgeClass}">${outcomeLabel}</span>`;
      if (data.probability) metaHtml += `<span class="dice-badge">P: ${(data.probability * 100).toFixed(1)}%</span>`;
    } else {
      metaHtml += `<span class="dice-badge choice">📖 Narrative Choice</span>`;
    }
    if (data.current_beat) metaHtml += `<span class="beat-tag">📍 ${data.current_beat}</span>`;
    if (data.state_changes?.items_gained?.length) {
      data.state_changes.items_gained.forEach(item => metaHtml += `<span class="dice-badge choice">🎁 Loot: ${item}</span>`);
    }
    if (data.level_up?.new_level) metaHtml += `<span class="dice-badge crit-success">⬆️ Level ${data.level_up.new_level}!</span>`;

    // NPC dialogue
    let npcHtml = '';
    if (data.npc_dialogue?.dialogue) {
      const npcName = data.npc_dialogue.name || 'NPC';
      const npcEmotion = data.npc_dialogue.emotion || '';
      npcHtml = `<div class="npc-dialogue-box">
        <div class="npc-name">💬 ${npcName}${npcEmotion ? ` (${npcEmotion})` : ''}</div>
        <div class="npc-text">${data.npc_dialogue.dialogue}</div>
        ${data.npc_dialogue.disposition_change ? `<div class="npc-disp">Disposition ${data.npc_dialogue.disposition_change > 0 ? '+' : ''}${data.npc_dialogue.disposition_change.toFixed(2)}</div>` : ''}
      </div>`;
    }

    // Chat log
    const fullContent = data.narration +
      (metaHtml ? `<div class="meta">${metaHtml}</div>` : '') +
      npcHtml +
      (data.choices?.length ? `<div class="choices-box">${data.choices.map(c => `<button class="choice-btn" data-choice="${c.replace(/"/g, '&quot;')}">${c}</button>`).join('')}</div>` : '');
    addMessage('system', fullContent);

    // Combat data
    const combatData = (data.combat_started && data.combat_data) ? data.combat_data : null;

    setNarration({
      html: data.narration + npcHtml,
      meta: metaHtml,
      choices: data.choices || null,
      combatData: combatData,
    });

    // Update sidebar
    setSidebar(prev => prev ? {
      ...prev,
      level: data.player_level || prev.level,
      xp: data.player_xp || 0,
      xpToNext: data.player_xp_to_next || 100,
      hp: data.player_hp,
      maxHp: data.max_hp || prev.maxHp,
      mana: data.player_mana,
      maxMana: data.max_mana || prev.maxMana,
      beat: data.current_beat || prev.beat,
      inventory: data.inventory || prev.inventory,
      npcs: data.npcs || prev.npcs,
      lastRoll: data.requires_roll ? {
        type: 'rolled',
        probability: data.probability,
        threshold: data.dice_threshold,
        roll: data.roll,
        outcome: data.outcome,
      } : { type: 'choice', outcome: data.outcome },
      objective: data.campaign_objective || prev.objective,
    } : prev);

    setSessionInfo(prev => prev ? { ...prev, turn: data.turn_number } : prev);

    // Game over states
    if (data.game_over) {
      setTimeout(() => { setGameOver(true); setCampaignEnded(true); }, 1500);
    } else if (data.victory) {
      setTimeout(() => { setVictory(true); setCampaignEnded(true); }, 1500);
    } else if (data.campaign_ended && !combatData) {
      setTimeout(() => setCampaignEnded(true), 1500);
    }
  }, [addMessage]);

  const submitAction = useCallback(async (actionText) => {
    if (!sessionId || busy || combat || gameOver) return;
    setBusy(true);
    setLoading(true);

    addMessage('player', actionText);
    const loadingId = addMessage('system', '⟳ Resolving your fate...');

    try {
      const data = await api.submitAction(sessionId, actionText);
      removeMessage(loadingId);

      // If there's a dice_result, show dice animation FIRST, then process
      if (data.dice_result) {
        setDiceResult(data.dice_result);
        setPendingResponse(data);
        // Response will be processed in onDiceAnimationComplete
      } else {
        // No dice roll — process immediately
        _processResponse(data);
      }

    } catch (e) {
      removeMessage(loadingId);
      addMessage('system', '⚠ Something went wrong: ' + e.message);
    } finally {
      setLoading(false);
      setBusy(false);
    }
  }, [sessionId, busy, combat, gameOver, addMessage, removeMessage, _processResponse]);

  const resolveCombat = useCallback(async (result, combatState) => {
    if (!sessionId) return;
    try {
      const data = await api.resolveCombat(sessionId, {
        result,
        player_hp: Math.max(0, combatState.player.hp),
        player_mana: Math.max(0, combatState.player.mana),
        enemy_name: combatState.enemy.name,
        combat_log: (combatState.logEntries || []).map(msg => ({
          actor: msg.includes('You') ? 'player' : 'enemy',
          message: msg.replace(/^[⚔️🧪⚡🏆💀]+ /, ''),
        })),
        turns_taken: combatState.turn,
      });

      setCombat(null);

      if (data.game_over) {
        // Player died in combat
        addMessage('system', `<strong>💀 Fallen...</strong><br/>${data.narration || 'The darkness claims you.'}`);
        setTimeout(() => { setGameOver(true); setCampaignEnded(true); }, 1000);
      } else if (result === 'victory') {
        let msg = '<strong>🏆 Victory!</strong>';
        if (data.rewards?.xp) msg += `<br/>+${data.rewards.xp} XP`;
        if (data.rewards?.loot_descriptions) data.rewards.loot_descriptions.forEach(l => msg += `<br/>${l}`);
        msg += `<br/><br/><em>The battle is won.</em>`;
        addMessage('system', msg);

        if (data.narration) {
          addMessage('system', data.narration);
          setNarration({ html: data.narration, meta: null, choices: data.choices || null, combatData: null });
        }

        if (data.victory) {
          setTimeout(() => { setVictory(true); setCampaignEnded(true); }, 1500);
        }
      } else {
        addMessage('system', '<strong>💀 Defeat...</strong><br/>The darkness claims you.');
        if (data.narration) {
          addMessage('system', data.narration);
          setNarration({ html: data.narration, meta: null, choices: null, combatData: null });
        }
      }

      setSidebar(prev => prev ? {
        ...prev,
        hp: data.player_hp,
        maxHp: data.max_hp || prev.maxHp,
        mana: data.player_mana,
        maxMana: data.max_mana || prev.maxMana,
        level: data.player_level || prev.level,
        xp: data.player_xp ?? prev.xp,
        xpToNext: data.player_xp_to_next || prev.xpToNext,
        inventory: data.inventory || prev.inventory,
        objective: data.campaign_objective || prev.objective,
      } : prev);

      if (data.campaign_ended && !data.game_over && !data.victory) {
        setTimeout(() => setCampaignEnded(true), 1500);
      }

    } catch (e) {
      setCombat(null);
      addMessage('system', '⚠ Combat resolution failed: ' + e.message);
    }
  }, [sessionId, addMessage]);

  const dismissNarration = useCallback(() => {
    setNarration(prev => {
      if (prev?.combatData) {
        const cd = prev.combatData;
        setTimeout(() => {
          const cs = createCombatState(cd);
          setCombat(cs);
        }, 600);
      }
      return null;
    });
  }, []);

  return {
    sessionId, sessionInfo, messages, sidebar, loading, narration,
    combat, campaignEnded, gameOver, victory, theme, busy,
    diceResult, pendingResponse,
    startSession, submitAction, resolveCombat,
    dismissNarration,
    onDiceAnimationComplete,
    setCombat, addMessage,
  };
}
