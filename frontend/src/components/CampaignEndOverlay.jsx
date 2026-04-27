export default function CampaignEndOverlay({ show, victory, gameOver }) {
  if (!show) return null;

  const isVictory = victory && !gameOver;
  const isDefeat = gameOver;

  return (
    <div className="connect-overlay" style={{ zIndex: 600 }}>
      <div className="connect-box" style={{ maxWidth: 450 }}>
        {isVictory ? (
          <>
            <h2>🏆 Victory</h2>
            <p style={{ color: '#c9a84c', marginBottom: 16, fontSize: 15 }}>
              The campaign is complete. Your deeds will echo through the ages.
            </p>
            <p style={{ color: '#888', fontSize: 13, marginBottom: 24 }}>
              The tale is told. The legend is yours.
            </p>
          </>
        ) : isDefeat ? (
          <>
            <h2>💀 Fallen</h2>
            <p style={{ color: '#c66', marginBottom: 16, fontSize: 15 }}>
              Your wounds were too grave. The darkness claims another soul.
            </p>
            <p style={{ color: '#666', fontSize: 13, marginBottom: 24 }}>
              The journey ends here. But every ending seeds a new beginning.
            </p>
          </>
        ) : (
          <>
            <h2>📜 Journey's End</h2>
            <p style={{ color: '#c8a', marginBottom: 16, fontSize: 15 }}>
              You have survived the trial and reached the end of this tale.
            </p>
            <p style={{ color: '#888', fontSize: 13, marginBottom: 24 }}>
              Your journey is now a legend.
            </p>
          </>
        )}
        <button onClick={() => window.location.reload()}>Begin a New Adventure</button>
      </div>
    </div>
  );
}
