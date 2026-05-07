import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import * as api from '../api';
import PageLoader from '../components/PageLoader';

export default function CampaignDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [turns, setTurns] = useState([]);
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
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
  }, [id]);

  if (loading) return <div className="vm-page-center"><PageLoader text="Loading campaign..." /></div>;

  if (error) return (
    <div className="vm-page">
      <div className="vm-empty-state">
        <h2 className="vm-page-title">⚠ {error}</h2>
        <button className="auth-btn" onClick={() => navigate('/campaigns')}>Back to Campaigns</button>
      </div>
    </div>
  );

  const campaignTitle = session?.world_state?.campaign?.title || 'Campaign Detail';
  const cls = session?.player?.character_class || '—';
  const turnCount = session?.turn_number || turns.length;
  const ended = session?.world_state?.campaign_ended;

  return (
    <div className="vm-page">
      <div className="vm-page-header">
        <div>
          <button className="vm-link" onClick={() => navigate('/campaigns')}>← Campaigns</button>
          <h1 className="vm-page-title">{campaignTitle}</h1>
          <p className="vm-page-subtitle">{cls} · {turnCount} turns · {id?.slice(0, 8)}...</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          {ended ? (
            <span className="vm-badge vm-badge-danger">Ended</span>
          ) : (
            <button className="auth-btn" onClick={() => navigate(`/campaign/${id}`)}>Resume Campaign</button>
          )}
        </div>
      </div>

      {turns.length > 0 ? (
        <div className="vm-card-list">
          {turns.map((t, i) => (
            <div key={i} className="vm-card">
              <div className="vm-card-main">
                <div className="vm-card-title">Turn {t.turn_number || i + 1}</div>
                {t.player_input && <div className="vm-card-meta"><strong>You:</strong> {t.player_input}</div>}
                {t.intent?.description && <div className="vm-card-meta">{t.intent.description}</div>}
              </div>
              {t.roll && <span className="vm-badge">🎲 {t.roll} → {t.outcome}</span>}
            </div>
          ))}
        </div>
      ) : (
        <div className="vm-empty-state">
          <p>No turn history available for this campaign.</p>
        </div>
      )}
    </div>
  );
}
