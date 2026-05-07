import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import * as api from '../api';
import PageLoader from '../components/PageLoader';
import CampaignCard from '../components/CampaignCard';

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
            <CampaignCard key={c.id} campaign={c} onClick={() => navigate(`/campaign/${c.session_id}/history`)} />
          ))}
        </div>
      )}
    </div>
  );
}
