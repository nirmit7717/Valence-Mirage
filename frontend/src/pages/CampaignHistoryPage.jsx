import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import * as api from '../api';
import PageLoader from '../components/PageLoader';

export default function CampaignHistoryPage() {
  const navigate = useNavigate();
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getUserDashboard().then(data => {
      setCampaigns(data.campaigns || []);
      setLoading(false);
    }).catch(() => {
      setError('Failed to load campaigns.');
      setLoading(false);
    });
  }, []);

  if (loading) return <div className="vm-page-center"><PageLoader text="Loading campaigns..." /></div>;

  if (error) return (
    <div className="vm-page">
      <div className="vm-empty-state">
        <p>{error}</p>
        <button className="auth-btn" onClick={() => navigate('/dashboard')}>Back to Dashboard</button>
      </div>
    </div>
  );

  return (
    <div className="vm-page">
      <div className="vm-page-header">
        <h1 className="vm-page-title">Campaign History</h1>
        <button className="auth-btn" onClick={() => navigate('/new')}>+ New Campaign</button>
      </div>

      {campaigns.length === 0 ? (
        <div className="vm-empty-state">
          <p>No campaigns yet. Your legend awaits.</p>
          <button className="auth-btn" onClick={() => navigate('/new')}>Begin Your First Adventure</button>
        </div>
      ) : (
        <div className="vm-card-list">
          {campaigns.map(c => (
            <div key={c.id} className="vm-card vm-card-clickable" onClick={() => navigate(`/campaign/${c.session_id}/history`)}>
              <div className="vm-card-main">
                <div className="vm-card-title">{c.campaign_title || 'Untitled Campaign'}</div>
                <div className="vm-card-meta">{c.character_class} · {c.turns} turns · {new Date(c.created_at).toLocaleDateString()}</div>
              </div>
              <span className={`vm-badge ${c.result === 'victory' ? 'vm-badge-success' : 'vm-badge-danger'}`}>
                {c.result || '—'}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
