import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import * as api from '../api';
import { useAuth } from '../AppRouter';
import PageLoader from '../components/PageLoader';

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

  return (
    <div className="vm-page">
      <div className="vm-page-header">
        <h1 className="vm-page-title">Player Profile</h1>
      </div>

      <div className="vm-card" style={{ maxWidth: 500 }}>
        <div className="vm-profile-row"><span>Username</span><span className="vm-profile-val">{profile?.username || username}</span></div>
        <div className="vm-profile-row"><span>Role</span><span className="vm-profile-val">{profile?.role || 'player'}</span></div>
        <div className="vm-profile-row"><span>Joined</span><span className="vm-profile-val">{profile?.created_at ? new Date(profile.created_at).toLocaleDateString() : '—'}</span></div>
      </div>

      <div className="vm-section">
        <h2 className="vm-section-title">Engagement Profile</h2>
        <p className="vm-text-sm">Your play style is analyzed across sessions to personalize future campaigns. Profile emerges after 2-3 completed campaigns.</p>
        <div className="vm-card" style={{ maxWidth: 500 }}>
          {dimensions ? (
            Object.entries(dimensions).map(([key, value]) => (
              <div key={key} className="vm-profile-row">
                <span>{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
                <div className="vm-profile-bar-wrap">
                  <div className="vm-profile-bar" style={{ width: `${((value + 1) / 2) * 100}%` }} />
                  <span className="vm-profile-val">{value.toFixed(2)}</span>
                </div>
              </div>
            ))
          ) : (
            <div className="vm-empty-state">
              <p>No profile data yet. Complete campaigns to build your engagement profile.</p>
              <button className="auth-btn" onClick={() => navigate('/new')}>Start a Campaign</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
