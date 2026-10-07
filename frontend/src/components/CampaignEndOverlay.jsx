import { useNavigate } from 'react-router-dom';

// Shown once a campaign is over. Every button leaves this campaign's page —
// reloading it would only hydrate the finished campaign and show this screen again.
export default function CampaignEndOverlay({ show, victory, gameOver, sessionId }) {
  const navigate = useNavigate();
  if (!show) return null;

  const isVictory = victory && !gameOver;
  const isDefeat = gameOver;

  return (
    <div className="connect-overlay" style={{ zIndex: 600 }} role="dialog" aria-modal="true" aria-labelledby="campaign-end-title">
      <div className="connect-box campaign-end-box">
        {isVictory ? (
          <>
            <h2 id="campaign-end-title">🏆 Victory</h2>
            <p style={{ color: '#c9a84c', marginBottom: 16, fontSize: 15 }}>
              The campaign is complete. Your deeds will echo through the ages.
            </p>
            <p style={{ color: '#888', fontSize: 13, marginBottom: 24 }}>
              The tale is told. The legend is yours.
            </p>
          </>
        ) : isDefeat ? (
          <>
            <h2 id="campaign-end-title">💀 Fallen</h2>
            <p style={{ color: '#c66', marginBottom: 16, fontSize: 15 }}>
              Your journey has ended. The darkness claims another soul.
            </p>
            <p style={{ color: '#666', fontSize: 13, marginBottom: 24 }}>
              Every ending seeds a new beginning.
            </p>
          </>
        ) : (
          <>
            <h2 id="campaign-end-title">📜 Journey's End</h2>
            <p style={{ color: '#c8a', marginBottom: 16, fontSize: 15 }}>
              You have reached the end of this tale.
            </p>
            <p style={{ color: '#888', fontSize: 13, marginBottom: 24 }}>
              Your journey is now a legend.
            </p>
          </>
        )}
        <div className="campaign-end-actions">
          <button autoFocus onClick={() => navigate('/new')}>Begin a New Adventure</button>
          {sessionId && (
            <button className="cancel-btn" onClick={() => navigate(`/campaign/${sessionId}/history`)}>
              Review This Journey
            </button>
          )}
          <button className="cancel-btn" onClick={() => navigate('/dashboard')}>Back to Dashboard</button>
        </div>
      </div>
    </div>
  );
}
