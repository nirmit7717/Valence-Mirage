import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import * as api from '../api';
import { useAuth } from '../AppRouter';
import PageLoader from '../components/PageLoader';
import './auth.css';

export default function DashboardPage() {
  const navigate = useNavigate();
  const { username, logout: authLogout } = useAuth();
  const [user, setUser] = useState(null);
  const [campaigns, setCampaigns] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getUserDashboard().then(data => {
      setUser(data.user);
      setCampaigns(data.campaigns || []);
      setStats(data.stats);
      setLoading(false);
    }).catch(() => {
      authLogout();
      navigate('/login');
    });
  }, []);

  const handleLogout = () => {
    authLogout();
    navigate('/login');
  };

  if (loading) return <div className="vm-page-center"><PageLoader text="Loading dashboard..." /></div>;

  const winRate = stats?.total_campaigns > 0
    ? Math.round((stats.wins / stats.total_campaigns) * 100) : 0;

  return (
    <div className="vm-page">
      <div className="vm-page-header">
        <div>
          <h1 className="vm-page-title">Dashboard</h1>
          <p className="vm-page-subtitle">Welcome back, {user?.username || username}</p>
        </div>
        <button className="auth-btn" onClick={() => navigate('/new')}>+ New Campaign</button>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{stats?.total_campaigns || 0}</div>
          <div className="stat-label">Campaigns</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{winRate}%</div>
          <div className="stat-label">Win Rate</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats?.avg_turns || 0}</div>
          <div className="stat-label">Avg Turns</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats?.favorite_class || '—'}</div>
          <div className="stat-label">Favorite Class</div>
        </div>
      </div>

      <div className="vm-section">
        <div className="vm-section-header">
          <h2>Campaign History</h2>
          {campaigns.length > 0 && (
            <button className="vm-link" onClick={() => navigate('/campaigns')}>View All →</button>
          )}
        </div>
        {campaigns.length === 0 ? (
          <div className="vm-empty-state">
            <p>No campaigns yet. Your legend awaits.</p>
            <button className="auth-btn" onClick={() => navigate('/new')}>Begin Your First Adventure</button>
          </div>
        ) : (
          <div className="vm-card-list">
            {campaigns.slice(0, 5).map(c => (
              <div key={c.id} className="vm-card" onClick={() => navigate(`/campaign/${c.session_id}/history`)}>
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
    </div>
  );
}
