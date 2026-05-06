import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import * as api from '../api';
import { useAuth } from '../AppRouter';

export default function CampaignHistoryPage() {
  const navigate = useNavigate();
  const { username } = useAuth();
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!username) { navigate('/login'); return; }
    api.getUserDashboard().then(data => {
      setCampaigns(data.campaigns || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [username]);

  if (loading) return <div className="auth-page"><p className="loading-text">Loading campaigns...</p></div>;

  return (
    <div className="auth-page">
      <div style={{ maxWidth: 800, margin: '0 auto', padding: '2rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h1 style={{ color: '#c9a04e' }}>Campaign History</h1>
          <button className="auth-btn" onClick={() => navigate('/new')}>New Campaign</button>
        </div>

        {campaigns.length === 0 ? (
          <div style={{ textAlign: 'center', marginTop: '3rem' }}>
            <p style={{ color: '#666' }}>No campaigns yet. Start your first adventure!</p>
            <button className="auth-btn" onClick={() => navigate('/new')} style={{ marginTop: '1rem' }}>Begin</button>
          </div>
        ) : (
          <div style={{ marginTop: '1.5rem' }}>
            {campaigns.map(c => (
              <div
                key={c.id}
                className="campaign-card"
                onClick={() => navigate(`/campaign/${c.session_id}/history`)}
                style={{
                  background: '#1a1a2e',
                  borderRadius: 8,
                  padding: '1rem 1.5rem',
                  marginBottom: '0.75rem',
                  cursor: 'pointer',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  border: '1px solid #2a2a3e',
                }}
              >
                <div>
                  <div style={{ color: '#c9a04e', fontWeight: 600 }}>{c.campaign_title || 'Untitled Campaign'}</div>
                  <div style={{ color: '#666', fontSize: '0.85rem' }}>
                    {c.character_class} · {c.turns} turns · {new Date(c.created_at).toLocaleDateString()}
                  </div>
                </div>
                <span className={c.result === 'victory' ? 'result-win' : 'result-loss'}
                  style={{ padding: '0.25rem 0.75rem', borderRadius: 4, fontSize: '0.85rem' }}>
                  {c.result || '—'}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
