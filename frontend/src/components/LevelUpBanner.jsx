import { useEffect } from 'react';
import { describeLevelUps } from '../utils/progression';

const AUTO_HIDE_MS = 6000;

// Announces level-ups from the last response. `levelUps` is the server's `level_up` list.
export default function LevelUpBanner({ levelUps, onDismiss }) {
  const summary = describeLevelUps(levelUps);
  const active = summary !== null;

  useEffect(() => {
    if (!active) return undefined;
    const timer = setTimeout(onDismiss, AUTO_HIDE_MS);
    return () => clearTimeout(timer);
  }, [levelUps, onDismiss, active]);

  // The live region stays mounted so screen readers announce new content.
  return (
    <div className="level-up-region" role="status" aria-live="polite">
      {summary && (
        <div className="level-up-banner">
          <span className="level-up-title">
            ⬆️ Level {summary.level}!{summary.levelsGained > 1 ? ` (+${summary.levelsGained} levels)` : ''}
          </span>
          {summary.gains.length > 0 && <span className="level-up-gains">{summary.gains.join(' · ')}</span>}
          <button type="button" className="level-up-close" onClick={onDismiss} aria-label="Dismiss level-up">
            ✕
          </button>
        </div>
      )}
    </div>
  );
}
