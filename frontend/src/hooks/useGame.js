// ═══════════════════════════════════════════════
//  useGame — Core game state management hook
// ═══════════════════════════════════════════════

import { useState, useCallback, useEffect, useRef } from 'react';
import * as api from '../api';
import { buildResolvePayload, createCombatState } from '../utils/combat';
import { xpBadgeText } from '../utils/progression';
import { getThemeFromCampaign } from '../utils/theme';

const STORY_LOG_LIMIT = 50;

// Pull "→ choice" lines out of narration text.
function splitChoices(narration) {
  const choices = [];
  const text = (narration || '')
    .replace(/^\s*(?:→|->)\s*(.+)$/gm, (_, choice) => { choices.push(choice.trim()); return ''; })
    .trim();
  return { text, choices };
}

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
  // Every scene shown so far ({ turn, playerInput, html }), so the player can page back.
  const [storyLog, setStoryLog] = useState([]);
  // Level-ups from the last response (server `level_up` list), shown in a banner.
  const [levelUps, setLevelUps] = useState(null);
  const dismissLevelUp = useCallback(() => setLevelUps(null), []);
  const announceLevelUps = useCallback((list) => {
    if (Array.isArray(list) && list.length) setLevelUps(list);
  }, []);
  const msgIdRef = useRef(0);
  const restoreSessionRef = useRef(null);

  const recordScene = useCallback((html, turn, playerInput = null) => {
    if (!html) return;
    setStoryLog(prev => [...prev, { turn, playerInput, html }].slice(-STORY_LOG_LIMIT));
  }, []);

  const addMessage = useCallback((type, content) => {
    const id = ++msgIdRef.current;
    setMessages(prev => [...prev, { id, type, content }]);
    return id;
  }, []);

  const removeMessage = useCallback((id) => {
    setMessages(prev => prev.filter(m => m.id !== id));
  }, []);

  // Show a notice in the narrative card (the chat log isn't rendered in the game view),
  // keeping the previous choices so the player can try something else.
  const showNotice = useCallback((text) => {
    const safe = String(text || '').replace(/[<>&]/g, ch => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;' }[ch]));
    setNarration(prev => ({
      html: `<p class="nc-warning"><em>⚠ ${safe}</em></p>`,
      meta: null,
      choices: prev?.choices?.length ? prev.choices : null,
      combatData: null,
      pendingOutcome: null,
    }));
  }, []);

  // Map a finished campaign's result onto the end-screen flags.
  const applyCampaignEnd = useCallback((result) => {
    if (result === 'victory') setVictory(true);
    else if (result === 'defeat' || result === 'lost_focus') setGameOver(true);
    setCampaignEnded(true);
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
        const openingHtml = `<strong>📜 ${data.campaign.title}</strong><br/><br/>${data.opening_narration}`;
        setNarration({
          html: openingHtml,
          meta: null,
          choices: data.choices || null,
          combatData: null,
        });
        setStoryLog([{ turn: 0, playerInput: null, html: openingHtml }]);
        addMessage('system', openingHtml);
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
          characterClass: character_class,
          level: 1,
          turn: 1,
          xp: 0, xpToNext: 100,
          hp: data.player.hp, maxHp: data.player.max_hp,
          mana: data.player.mana, maxMana: data.player.max_mana,
          stats: data.player.stats,
          beat: data.campaign?.acts?.[0]?.beats?.[0]?.title || '—',
          progress: data.story_progress || null,
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

  // Restore session from backend (page refresh / direct URL)
  const restoreSession = useCallback(async (sessionIdFromRoute) => {
    setLoading(true);
    try {
      const data = await api.hydrateSession(sessionIdFromRoute);
      setSessionId(data.session_id);
      setSessionInfo({ turn: data.turn_number, title: data.campaign?.title });

      const detectedTheme = getThemeFromCampaign(data.campaign);
      setTheme(detectedTheme);

      // A finished campaign goes straight to its end screen (no story card to replay).
      if (data.campaign_ended) {
        applyCampaignEnd(data.campaign_result);
      }

      const title = data.campaign?.title || 'Campaign';
      const log = (data.story_log || []).map(entry => ({
        turn: entry.turn,
        playerInput: entry.player_input,
        html: entry.turn === 0 ? `<strong>📜 ${title}</strong><br/><br/>${entry.narration}` : entry.narration,
      }));
      setStoryLog(log);

      if (data.combat_data && !data.campaign_ended) {
        // Refreshed mid-fight: go straight back into the same encounter.
        setNarration(null);
        setCombat(createCombatState(data.combat_data));
      } else if (!data.campaign_ended) {
        // Resume at the latest scene (not the opening) with the options it offered.
        const latest = log[log.length - 1];
        const situation = splitChoices(data.situation || '');
        const html = latest?.html
          || `<strong>📜 ${title}</strong><br/><br/>${situation.text || data.campaign?.premise || ''}`;
        const choices = log.length > 1
          ? situation.choices
          : (Array.isArray(data.choices) && data.choices.length ? data.choices : situation.choices);
        if (html) {
          setNarration({
            html,
            meta: null,
            choices: choices.length ? choices : null,
            combatData: null,
            pendingOutcome: null,
          });
        }
      }

      // Restore sidebar
      setSidebar({
        name: data.player?.name || 'Adventurer',
        characterClass: data.character_class,
        level: data.player?.level || 1,
        turn: data.turn_number || 1,
        xp: data.player?.xp || 0,
        xpToNext: data.player?.xp_to_next || 100,
        hp: data.player?.hp || 50,
        maxHp: data.player?.max_hp || 50,
        mana: data.player?.mana || 50,
        maxMana: data.player?.max_mana || 50,
        stats: data.player?.stats,
        beat: data.current_beat || data.campaign?.acts?.[0]?.beats?.[0]?.title || '—',
        progress: data.story_progress || null,
        inventory: data.inventory || [],
        npcs: Object.values(data.npcs || {}),
        effects: [],
        lastRoll: null,
        objective: data.campaign_objective || '',
      });

      addMessage('system', `<strong>📜 ${data.campaign?.title || 'Campaign'}</strong> — Session restored.`);

      return data;
    } catch (e) {
      addMessage('system', '⚠ Failed to restore session: ' + e.message);
      return null;
    } finally {
      setLoading(false);
    }
  }, [addMessage, applyCampaignEnd]);

  useEffect(() => { restoreSessionRef.current = restoreSession; }, [restoreSession]);

  // Shared response processing (called either directly or after dice animation)
  const _processResponse = useCallback((data, playerInput = null) => {
    // Combat guard: server says combat is active but frontend hasn't entered combat mode
    // Directly activate combat without narration
    if (data.outcome === 'combat_active' && data.combat_data) {
      const cs = createCombatState(data.combat_data);
      setCombat(cs);
      setBusy(false);
      return;
    }

    // Input validation: irrelevant action — don't advance the turn; show the warning
    // in the card with the previous options so the player can try again.
    if (data.redo_turn) {
      const warning = data.warning_message || data.narration || 'That action doesn\'t seem relevant.';
      addMessage('system', `<em>⚠ ${warning}</em>`);
      showNotice(warning);
      setBusy(false);
      return;
    }

    // Dynamic UI context — update theme based on environment/tone
    if (data.ui_context) {
      const env = data.ui_context.environment;
      const tone = data.ui_context.tone;
      // Map environment to theme
      const envThemeMap = {
        forest: 'forest', dungeon: 'underdark', city: 'fantasy', ruins: 'ruins',
        mountain: 'mountain', ocean: 'ocean', desert: 'desert',
        underdark: 'underdark', horror: 'horror',
      };
      const newTheme = envThemeMap[env] || 'default';
      if (newTheme !== 'default') {
        setTheme(newTheme);
      }
      // Combat overlay — switch to horror/dark theme during combat
      if (tone === 'combat') {
        setTheme(prev => (prev === 'default' ? 'dark_fantasy' : prev));
      }
    }
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
    const xpText = xpBadgeText(data.xp_gained);
    if (xpText) metaHtml += `<span class="dice-badge xp-badge">⭐ ${xpText}</span>`;
    if (Array.isArray(data.level_up) && data.level_up.length) {
      const level = data.level_up[data.level_up.length - 1].level;
      metaHtml += `<span class="dice-badge crit-success">⬆️ Level ${level}!</span>`;
      announceLevelUps(data.level_up);
    }

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
    const pendingOutcome = data.pending_outcome;  // Two-stage flow: outcome deferred until narration dismissed

    const storyOver = pendingOutcome?.type === 'victory' || pendingOutcome?.type === 'game_over';

    recordScene(data.narration + npcHtml, data.turn_number, playerInput);
    setNarration({
      html: data.narration + npcHtml,
      meta: metaHtml,
      choices: storyOver ? null : (data.choices || null),
      combatData: combatData,
      pendingOutcome: pendingOutcome,
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
      progress: data.story_progress || prev.progress,
      turn: data.turn_number ?? prev.turn,
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

    // Two-stage flow: transitions are deferred to pending_outcome
    // Narration shows first, then dismissNarration() triggers the pending outcome
    // Legacy path: if game_over/victory still sent directly (backward compat)
    if (data.game_over) {
      if (data.game_over_reason === 'lost_focus') {
        addMessage('system', `<em>⚠ ${data.narration || 'You have strayed too far from your path. The journey collapses.'}</em>`);
      }
      setTimeout(() => { setGameOver(true); setCampaignEnded(true); }, 1500);
    } else if (data.victory) {
      setTimeout(() => { setVictory(true); setCampaignEnded(true); }, 1500);
    } else if (data.campaign_ended && !combatData) {
      setTimeout(() => setCampaignEnded(true), 1500);
    }
    // If pending_outcome exists, narration handles the transition via dismissNarration

    // Show warning if present (immersive, not system-y)
    if (data.warning_message && !data.game_over) {
      addMessage('system', `<em>${data.warning_message}</em>`);
    }

    // Combat/victory/game-over activation is handled by dismissNarration()
    // which checks narration.pendingOutcome after the player reads the narration
  }, [addMessage, showNotice, recordScene, announceLevelUps]);

  // Called by DiceRoll when animation finishes — processes the queued response
  const onDiceAnimationComplete = useCallback(() => {
    setDiceResult(null);
    const queued = pendingResponse;
    if (!queued) { setBusy(false); return; }
    setPendingResponse(null);
    _processResponse(queued.data, queued.playerInput);
    setBusy(false);
  }, [pendingResponse, _processResponse]);

  const submitAction = useCallback(async (actionText) => {
    if (!sessionId || busy || combat || gameOver || campaignEnded) return;
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
        setPendingResponse({ data, playerInput: actionText });
        setLoading(false);
        // busy stays true until onDiceAnimationComplete finishes
      } else {
        // No dice roll — process immediately
        _processResponse(data, actionText);
        setLoading(false);
        setBusy(false);
      }

    } catch (e) {
      removeMessage(loadingId);
      addMessage('system', '⚠ Something went wrong: ' + e.message);
      if (e.status === 400 && /ended/i.test(e.detail || '')) {
        // The server already considers this campaign finished — show the end screen.
        try {
          const state = await api.hydrateSession(sessionId);
          applyCampaignEnd(state.campaign_result);
        } catch {
          setCampaignEnded(true);
        }
      } else {
        showNotice(`Something went wrong: ${e.detail || e.message}. Try again.`);
      }
      setLoading(false);
      setBusy(false);
    }
  }, [sessionId, busy, combat, gameOver, campaignEnded, addMessage, removeMessage, _processResponse, applyCampaignEnd, showNotice]);

  const resolveCombat = useCallback(async (result, combatState) => {
    if (!sessionId) return;
    try {
      const data = await api.resolveCombat(sessionId, buildResolvePayload(result, combatState));

      setCombat(null);

      const po = data.pending_outcome;

      announceLevelUps(data.level_up);
      if (result === 'victory') {
        let msg = '<strong>🏆 Victory!</strong>';
        // xp_gained includes the chapter's XP when the fight closed it.
        const xpText = xpBadgeText(data.xp_gained ?? data.rewards?.xp);
        if (xpText) msg += `<br/>${xpText}`;
        if (data.rewards?.loot_descriptions) data.rewards.loot_descriptions.forEach(l => msg += `<br/>${l}`);
        msg += `<br/><br/><em>The battle is won.</em>`;
        addMessage('system', msg);

        if (data.narration) {
          addMessage('system', data.narration);
          const { text: cleanNarr, choices: arrowChoices } = splitChoices(data.narration);
          // When the fight ended the campaign, the card leads to the end screen instead of choices.
          const choices = po ? null : (arrowChoices.length > 0 ? arrowChoices : (data.choices || null));
          recordScene(cleanNarr, data.turn_number ?? null, `Fought ${combatState.enemy.name}`);
          setNarration({ html: cleanNarr, meta: null, choices, combatData: null, pendingOutcome: po });
        } else if (po) {
          // No narration but pending outcome (shouldn't happen, but safety)
          setTimeout(() => {
            if (po.type === 'game_over') { setGameOver(true); setCampaignEnded(true); }
            else if (po.type === 'victory') { setVictory(true); setCampaignEnded(true); }
          }, 600);
        }
      } else {
        // Defeat / death
        addMessage('system', `<strong>💀 Fallen...</strong><br/>${data.narration || 'The darkness claims you.'}`);
        if (data.narration) {
          const { text: cleanNarr, choices: arrowChoices } = splitChoices(data.narration);
          const choices = po ? null : (arrowChoices.length > 0 ? arrowChoices : (data.choices || null));
          recordScene(cleanNarr, data.turn_number ?? null, `Fought ${combatState.enemy.name}`);
          setNarration({ html: cleanNarr, meta: null, choices, combatData: null, pendingOutcome: po });
        } else if (po) {
          setTimeout(() => {
            if (po.type === 'game_over') { setGameOver(true); setCampaignEnded(true); }
          }, 600);
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
        // A fight is a campaign turn, and winning a planned one moves the story to its next beat.
        beat: data.current_beat || prev.beat,
        progress: data.story_progress || prev.progress,
        turn: data.turn_number ?? prev.turn,
      } : prev);
      if (data.turn_number != null) {
        setSessionInfo(prev => prev ? { ...prev, turn: data.turn_number } : prev);
      }

      // Legacy fallback — shouldn't trigger with pending_outcome system

    } catch (e) {
      setCombat(null);
      addMessage('system', '⚠ Combat resolution failed: ' + e.message);
      if (e.status === 409) {
        // This fight was already settled (e.g. resolved in another tab) — reload the real state.
        showNotice('That battle has already been settled. Restoring your journey...');
        setTimeout(() => restoreSessionRef.current?.(sessionId), 1200);
      } else {
        showNotice(`Combat resolution failed: ${e.detail || e.message}`);
      }
    }
  }, [sessionId, addMessage, showNotice, recordScene, announceLevelUps]);

  const dismissNarration = useCallback(() => {
    setNarration(prev => {
      if (!prev) return null;

      const po = prev.pendingOutcome;

      // Handle pending outcomes after narration is read
      if (po) {
        if (po.type === 'game_over') {
          setTimeout(() => {
            setGameOver(true);
            setCampaignEnded(true);
          }, 600);
        } else if (po.type === 'victory') {
          setTimeout(() => {
            setVictory(true);
            setCampaignEnded(true);
          }, 600);
        } else if (po.type === 'combat_start') {
          const cd = prev.combatData || po.combat_data;
          if (cd) {
            setTimeout(() => {
              const cs = createCombatState(cd);
              setCombat(cs);
            }, 600);
          }
        }
      } else if (prev.combatData) {
        // Legacy path: combat_data without pending_outcome
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
    diceResult, pendingResponse, storyLog, levelUps, dismissLevelUp,
    startSession, restoreSession, submitAction, resolveCombat,
    dismissNarration,
    onDiceAnimationComplete,
    setCombat, addMessage,
  };
}
