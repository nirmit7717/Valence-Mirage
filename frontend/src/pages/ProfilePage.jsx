import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import * as api from '../api';
import { useAuth } from '../AppRouter';

export default function ProfilePage() {
  const navigate = useNavigate();
  const { username } = useAuth();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!username) { navigate('/login'); return; }
    api.getUserMe().then(data => {
      setProfile(data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [username]);

  if (loading) return <div className="auth-page"><p className="loading-text">Loading profile...</p></div>;

  return (
    <div className="auth-page">
      <div style={{ maxWidth: 600, margin: '0 auto', padding: '2rem' }}>
        <h1 style={{ color: '#c9a04e' }}>Player Profile</h1>
        <div className="profile-card" style={{ background: '#1a1a2e', borderRadius: 12, padding: '1.5rem', marginTop: '1rem' }}>
          <p style={{ color: '#a0a0a0' }}><strong>Username:</strong> {profile?.username || username}</p>
          <p style={{ color: '#a0a0a0' }}><strong>Role:</strong> {profile?.role || 'player'}</p>
          <p style={{ color: '#a0a0a0' }}><strong>Joined:</strong> {profile?.created_at ? new Date(profile.created_at).toLocaleDateString() : '—'}</p>
        </div>

        <h2 style={{ color: '#c9a04e', marginTop: '2rem' }}>Engagement Profile</h2>
        <p style={{ color: '#666', fontSize: '0.9rem' }}>
          Your play style is analyzed across sessions to personalize campaigns.
          Profile emerges after 2-3 completed campaigns.
        </p>
        <div style={{ background: '#1a1a2e', borderRadius: 12, padding: '1.5rem', marginTop: '1rem' }}>
          {profile?.profile_dimensions ? (
            Object.entries(profile.profile_dimensions).map(([key, value]) => (
              <div key={key} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 0', borderBottom: '1px solid #2a2a3e' }}>
                <span style={{ color: '#a0a0a0', textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}</span>
                <span style={{ color: '#c9a04e' }}>{value.toFixed(2)}</span>
              </div>
            ))
          ) : (
            <p style={{ color: '#666' }}>No profile data yet. Complete campaigns to build your profile.</p>
          )}
        </div>
      </div>
    </div>
  );
}
