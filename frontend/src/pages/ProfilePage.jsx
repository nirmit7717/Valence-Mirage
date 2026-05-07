import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import * as api from '../api';
import { useAuth } from '../AppRouter';
import PageLoader from '../components/PageLoader';
import StatBar from '../components/StatBar';

export default function ProfilePage() {
  const navigate = useNavigate();
  const { username } = useAuth();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getUserMe().then(data => {
      setProfile(data);
      setLoading(false);
    }).catch(() => {
      setError('Failed to load profile.');
      setLoading(false);
    });
  }, []);

  if (loading) return <div className="vm-page-center"><PageLoader text="Loading profile..." /></div>;

  if (error) return (
    <div className="vm-page">
      <div className="vm-empty-state">
        <p>{error}</p>
        <button className="auth-btn" onClick={() => navigate('/dashboard')}>Back to Dashboard</button>
      </div>
    </div>
  );

  const dimensions = profile?.profile_dimensions || null;

  const dimMeta = {
    combat_affinity: { label: 'Combat Affinity', icon: '⚔️', color: '#c44' },
    exploration_tendency: { label: 'Exploration', icon: '🗺️', color: '#6b5' },
    social_engagement: { label: 'Social', icon: '💬', color: '#59d' },
    risk_tolerance: { label: 'Risk Tolerance', icon: '🎲', color: '#c9a04e' },
    narrative_depth: { label: 'Narrative Depth', icon: '📖', color: '#85f' },
    strategic_planning: { label: 'Strategy', icon: '🧠', color: '#fb5' },
  };

  return (
    <div className="vm-page">
      <div className="vm-page-header">
        <h1 className="vm-page-title">Player Profile</h1>
      </div>

      {/* User info card */}
      <div className="vm-card vm-card-glass" style={{ maxWidth: 500 }}>
        <div className="vm-profile-row">
          <span>Username</span>
          <span className="vm-profile-val">{profile?.username || username}</span>
        </div>
        <div className="vm-profile-row">
          <span>Role</span>
          <span className="vm-profile-val">{profile?.role || 'player'}</span>
        </div>
        <div className="vm-profile-row">
          <span>Joined</span>
          <span className="vm-profile-val">{profile?.created_at ? new Date(profile.created_at).toLocaleDateString() : '—'}</span>
        </div>
      </div>

      {/* Engagement dimensions */}
      <div className="vm-section">
        <h2 className="vm-section-title">Engagement Profile</h2>
        <p className="vm-text-sm">Your play style is analyzed across sessions to personalize future campaigns. Profile emerges after 2-3 completed campaigns.</p>
        <div className="vm-card vm-card-glass" style={{ maxWidth: 500, padding: '1.25rem' }}>
          {dimensions ? (
            <div className="profile-dims">
              {Object.entries(dimensions).map(([key, value]) => {
                const meta = dimMeta[key] || { label: key, icon: '•', color: '#888' };
                const pct = ((value + 1) / 2) * 100; // -1..1 → 0..100
                return (
                  <div key={key} className="profile-dim">
                    <div className="profile-dim-header">
                      <span>{meta.icon} {meta.label}</span>
                      <span className="profile-dim-val" style={{ color: meta.color }}>{value.toFixed(2)}</span>
                    </div>
                    <div className="profile-dim-track">
                      <div className="profile-dim-fill" style={{ width: `${pct}%`, background: meta.color }} />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="vm-empty-state" style={{ padding: '1.5rem' }}>
              <p>No profile data yet. Complete campaigns to build your engagement profile.</p>
              <button className="auth-btn" onClick={() => navigate('/new')}>Start a Campaign</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
