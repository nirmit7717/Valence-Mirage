import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import * as api from '../api';
import { useAuth } from '../AppRouter';

export default function CampaignDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { username } = useAuth();
  const [turns, setTurns] = useState([]);
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!username) { navigate('/login'); return; }

    Promise.all([
      api.getSession(id).catch(() => null),
      api.getSessionHistory(id).catch(() => []),
    ]).then(([sessionData, historyData]) => {
      if (!sessionData) {
        setError('Campaign not found.');
      } else {
        setSession(sessionData);
        setTurns(historyData.turns || historyData || []);
      }
      setLoading(false);
    });
  }, [id, username]);

  if (loading) return <div className="auth-page"><p className="loading-text">Loading campaign...</p></div>;
  if (error) return (
    <div className="auth-page">
      <div style={{ textAlign: 'center', marginTop: '3rem' }}>
        <h2 style={{ color: '#c9a04e' }}>⚠ {error}</h2>
        <button className="auth-btn" onClick={() => navigate('/campaigns')} style={{ marginTop: '1rem' }}>Back to Campaigns</button>
      </div>
    </div>
  );

  return (
    <div className="auth-page">
      <div style={{ maxWidth: 800, margin: '0 auto', padding: '2rem' }}>
        <button className="auth-btn secondary" onClick={() => navigate('/campaigns')} style={{ marginBottom: '1rem' }}>← Back</button>
        <h1 style={{ color: '#c9a04e' }}>{session?.world_state?.campaign?.title || 'Campaign Detail'}</h1>
        <div style={{ color: '#666', marginTop: '0.5rem' }}>
          {session?.player?.character_class} · {session?.turn_number || turns.length} turns · Session {id?.slice(0, 8)}...
        </div>

        {turns.length > 0 ? (
          <div style={{ marginTop: '2rem' }}>
            <h2 style={{ color: '#c9a04e' }}>Turn History</h2>
            {turns.map((t, i) => (
              <div key={i} style={{ background: '#1a1a2e', borderRadius: 8, padding: '1rem', marginTop: '0.75rem', borderLeft: '3px solid #c9a04e' }}>
                <div style={{ color: '#c9a04e', fontSize: '0.85rem' }}>Turn {t.turn_number || i + 1}</div>
                {t.player_input && <div style={{ color: '#e0e0e0', marginTop: '0.25rem' }}><strong>You:</strong> {t.player_input}</div>}
                {t.intent?.description && <div style={{ color: '#a0a0a0', fontSize: '0.85rem', marginTop: '0.25rem' }}>{t.intent.description}</div>}
                {t.roll && <div style={{ color: '#888', fontSize: '0.8rem', marginTop: '0.25rem' }}>Roll: {t.roll} → {t.outcome}</div>}
              </div>
            ))}
          </div>
        ) : (
          <p style={{ color: '#666', marginTop: '2rem' }}>No turn history available.</p>
        )}

        {session?.world_state?.campaign_ended ? (
          <div style={{ marginTop: '1rem' }}>
            <span className="result-loss" style={{ padding: '0.5rem 1rem', borderRadius: 6 }}>Campaign Ended</span>
          </div>
        ) : session ? (
          <button className="auth-btn" onClick={() => navigate(`/campaign/${id}`)} style={{ marginTop: '1rem' }}>
            Resume Campaign
          </button>
        ) : null}
      </div>
    </div>
  );
}
