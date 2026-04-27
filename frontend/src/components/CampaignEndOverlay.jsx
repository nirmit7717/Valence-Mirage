export default function CampaignEndOverlay({ show }) {
  if (!show) return null;
  return (
    <div className="connect-overlay" style={{ zIndex: 600 }}>
      <div className="connect-box" style={{ maxWidth: 450 }}>
        <h2>🏆 Campaign Concluded</h2>
        <p style={{ color: '#c8a', marginBottom: 16, fontSize: 15 }}>You have survived the trial and reached the end of this tale.</p>
        <p style={{ color: '#888', fontSize: 13, marginBottom: 24 }}>Your journey is now a legend.</p>
        <button onClick={() => window.location.reload()}>Start a New Adventure</button>
      </div>
    </div>
  );
}
