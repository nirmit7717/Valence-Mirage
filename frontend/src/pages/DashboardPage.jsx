import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import * as api from '../api';
import { useAuth } from '../AppRouter';
import './auth.css';

export default function DashboardPage() {
  const navigate = useNavigate();
  const { username, logout } = useAuth();
  const [user, setUser] = useState(null);
  const [campaigns, setCampaigns] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!username) { navigate('/login'); return; }
    api.getUserDashboard().then(data => {
      setUser(data.user);
      setCampaigns(data.campaigns);
      setStats(data.stats);
      setLoading(false);
    }).catch(() => {
      logout();
      navigate('/login');
    });
  }, [username]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  if (loading) return <div className="auth-page"><p className="loading-text">Loading...</p></div>;

  const winRate = stats?.total_campaigns > 0
    ? Math.round((stats.wins / stats.total_campaigns) * 100) : 0;

  return (
    <div className="dashboard-page">
      <header className="dashboard-header">
        <h1>Valence Mirage</h1>
        <div className="header-right">
          <span>Welcome, {user?.username || username}</span>
          <button className="auth-btn secondary" onClick={handleLogout}>Logout</button>
        </div>
      </header>

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

      <div className="campaigns-section">
        <div className="section-header">
          <h2>Past Campaigns</h2>
          <button className="auth-btn" onClick={() => navigate('/new')}>New Game</button>
        </div>
        {campaigns.length === 0 ? (
          <p className="no-campaigns">No campaigns yet. Start your first adventure!</p>
        ) : (
          <table className="campaigns-table">
            <thead>
              <tr>
                <th>Title</th><th>Result</th><th>Turns</th><th>Class</th><th>Date</th>
              </tr>
            </thead>
            <tbody>
              {campaigns.map(c => (
                <tr key={c.id} onClick={() => navigate(`/campaign/${c.session_id}/history`)} style={{ cursor: 'pointer' }}>
                  <td>{c.campaign_title || '—'}</td>
                  <td className={c.result === 'victory' ? 'result-win' : 'result-loss'}>{c.result}</td>
                  <td>{c.turns}</td>
                  <td>{c.character_class}</td>
                  <td>{new Date(c.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
