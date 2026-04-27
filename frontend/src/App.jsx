import { useState, useCallback, useEffect } from 'react';
import { useGame } from './hooks/useGame';
import { THEMES, injectAmbienceCSS } from './utils/theme';
import ConnectOverlay from './components/ConnectOverlay';
import NarrativeCard from './components/NarrativeCard';
import FloatingHUD from './components/FloatingHUD';
import CombatOverlay from './components/CombatOverlay';
import LoadingOverlay from './components/LoadingOverlay';
import CampaignEndOverlay from './components/CampaignEndOverlay';
import SettingsPanel from './components/SettingsPanel';

injectAmbienceCSS();

export default function App() {
  const game = useGame();
  const [connected, setConnected] = useState(false);
  const [animationsEnabled, setAnimationsEnabled] = useState(true);
  const [textSpeed, setTextSpeed] = useState(20);

  const themeData = THEMES[game.theme] || THEMES.default;

  useEffect(() => {
    document.body.style.background = themeData.gradient;
    document.body.style.backgroundAttachment = 'fixed';
    document.body.style.minHeight = '100vh';
    document.body.style.transition = 'background 1.2s ease-in-out';
    document.body.className = document.body.className.replace(/amb-\S+/g, '').trim();
    if (themeData.animClass) document.body.classList.add(themeData.animClass);
  }, [themeData]);

  const handleStart = useCallback(async (params) => {
    await game.startSession(params);
    setConnected(true);
  }, [game]);

  const handleChoice = useCallback((choice) => {
    game.submitAction(choice);
  }, [game]);

  return (
    <div className="game-root">
      {!connected ? (
        <>
          <ConnectOverlay onStart={handleStart} />
          <LoadingOverlay show={game.loading} />
        </>
      ) : (
        <>
          <FloatingHUD data={game.sidebar} />
          <div className="game-stage">
            <div className="stage-header">
              <span className="stage-title">🎲 Valence Mirage</span>
              <span className="stage-info">
                {game.sessionInfo ? `Turn ${game.sessionInfo.turn} | ${game.sessionInfo.title}` : ''}
              </span>
            </div>
            {!game.combat && !game.narration && (
              <div className="stage-waiting">
                <div className="stage-waiting-text">Awaiting your next move...</div>
              </div>
            )}
          </div>
          <NarrativeCard
            narration={game.narration}
            onChoice={handleChoice}
            onDismiss={game.dismissNarration}
            animationsEnabled={animationsEnabled}
            textSpeed={textSpeed}
          />
          <CombatOverlay combat={game.combat} onResolve={game.resolveCombat} animationsEnabled={animationsEnabled} />
          <CampaignEndOverlay show={game.campaignEnded} />
          <LoadingOverlay show={game.loading} />
        </>
      )}
      {/* Settings always visible */}
      <SettingsPanel
        animationsEnabled={animationsEnabled}
        setAnimationsEnabled={setAnimationsEnabled}
        textSpeed={textSpeed}
        setTextSpeed={setTextSpeed}
      />
    </div>
  );
}
