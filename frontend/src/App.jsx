import { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGame } from './hooks/useGame';
import { THEMES, injectAmbienceCSS } from './utils/theme';
import ConnectOverlay from './components/ConnectOverlay';
import NarrativeCard from './components/NarrativeCard';
import FloatingHUD from './components/FloatingHUD';
import CombatOverlay from './components/CombatOverlay';
import LoadingOverlay from './components/LoadingOverlay';
import CampaignEndOverlay from './components/CampaignEndOverlay';
import DiceRoll from './components/DiceRoll';
import SettingsPanel from './components/SettingsPanel';

injectAmbienceCSS();

export default function GameApp({ campaignId }) {
  const game = useGame();
  const navigate = useNavigate();
  const [connected, setConnected] = useState(false);
  const [animationsEnabled, setAnimationsEnabled] = useState(true);
  const [textSpeed, setTextSpeed] = useState(20);
  const [restoreError, setRestoreError] = useState(null);

  const themeData = THEMES[game.theme] || THEMES.default;

  // Hydrate from campaign ID on mount
  useEffect(() => {
    if (campaignId && !game.sessionId) {
      game.restoreSession(campaignId).then(data => {
        if (data) {
          setConnected(true);
        } else {
          setRestoreError('Campaign not found or expired.');
        }
      });
    }
  }, [campaignId]);

  useEffect(() => {
    document.body.style.background = themeData.gradient;
    document.body.style.backgroundAttachment = 'fixed';
    document.body.style.minHeight = '100vh';
    document.body.style.transition = 'background 1.2s ease-in-out';
    document.body.className = document.body.className.replace(/amb-\S+/g, '').trim();
    if (themeData.animClass) document.body.classList.add(themeData.animClass);
  }, [themeData]);

  const handleStart = useCallback(async (params) => {
    const data = await game.startSession(params);
    setConnected(true);
    if (data?.session_id) {
      navigate(`/campaign/${data.session_id}`, { replace: true });
    }
  }, [game, navigate]);

  const handleChoice = useCallback((choice) => {
    if (game.gameOver) return;
    game.submitAction(choice);
  }, [game]);

  if (restoreError) {
    return (
      <div className="game-root">
        <div className="stage-waiting">
          <div className="stage-waiting-text">
            <strong>⚠ {restoreError}</strong>
            <br /><br />
            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
              <button className="auth-btn" onClick={() => navigate('/new')}>New Campaign</button>
              <button className="auth-btn secondary" onClick={() => navigate('/campaigns')}>Campaign History</button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="game-root">
      {/* Minimal game header — only when connected */}
      {connected && (
        <div className="game-mini-bar">
          <button className="back-btn" onClick={() => navigate('/dashboard')}>← Leave</button>
          <span className="game-top-title">
            🎲 {game.sessionInfo?.title || 'Valence Mirage'}
            {game.sessionInfo ? ` · Turn ${game.sessionInfo.turn}` : ''}
          </span>
          <span />
        </div>
      )}

      {!connected ? (
        <>
          <ConnectOverlay onStart={handleStart} onCancel={() => navigate('/dashboard')} />
          <LoadingOverlay show={game.loading} hasRoll={false} />
        </>
      ) : (
        <>
          <FloatingHUD data={game.sidebar} />
          <div className="game-stage">
            {!game.combat && !game.narration && !game.diceResult && (
              <div className="stage-waiting">
                <div className="stage-waiting-text">
                  {game.gameOver ? 'Your journey has ended...' : 'Awaiting your next move...'}
                </div>
              </div>
            )}
          </div>

          <DiceRoll diceResult={game.diceResult} onComplete={game.onDiceAnimationComplete} />

          <NarrativeCard
            narration={game.narration}
            onChoice={handleChoice}
            onDismiss={game.dismissNarration}
            animationsEnabled={animationsEnabled}
            textSpeed={textSpeed}
            inputDisabled={game.gameOver}
          />
          <CombatOverlay combat={game.combat} onResolve={game.resolveCombat} animationsEnabled={animationsEnabled} />
          <CampaignEndOverlay show={game.campaignEnded} victory={game.victory} gameOver={game.gameOver} />
          <LoadingOverlay show={game.loading} hasRoll={false} />
        </>
      )}
      <SettingsPanel
        animationsEnabled={animationsEnabled}
        setAnimationsEnabled={setAnimationsEnabled}
        textSpeed={textSpeed}
        setTextSpeed={setTextSpeed}
      />
    </div>
  );
}
