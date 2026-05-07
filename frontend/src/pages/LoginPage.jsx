import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import * as api from '../api';
import { useAuth } from '../AppRouter';
import './auth.css';

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showTester, setShowTester] = useState(false);
  const [testerEmail, setTesterEmail] = useState('');
  const [testerMsg, setTesterMsg] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await api.login(username, password);
      login(data.access_token, username);
      navigate('/dashboard');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleTester = async (e) => {
    e.preventDefault();
    setTesterMsg('');
    try {
      await api.testerRequest(testerEmail);
      setTesterMsg('Request submitted! We\'ll be in touch.');
      setTesterEmail('');
    } catch (err) {
      setTesterMsg(err.message);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-left">
        <h1 className="auth-title">Valence Mirage</h1>
        <p className="auth-subtitle">AI-Driven Narrative RPG</p>
        <p className="auth-desc">
          Embark on adventures shaped by your choices. Dynamic storytelling,
          probabilistic dice mechanics, and AI-crafted narratives await.
          Every decision carves a unique path through the darkness.
        </p>
        <div className="auth-features">
          <span>⚔️ Tactical Combat</span>
          <span>🎭 Dynamic Story</span>
          <span>🎲 Dice Mechanics</span>
        </div>
      </div>
      <div className="auth-right">
        <form className="auth-form" onSubmit={handleLogin}>
          <h2>Sign In</h2>
          {error && <div className="auth-error">{error}</div>}
          <input type="text" placeholder="Username" value={username}
            onChange={e => setUsername(e.target.value)} required disabled={loading} />
          <input type="password" placeholder="Password" value={password}
            onChange={e => setPassword(e.target.value)} required disabled={loading} />
          <button type="submit" className="auth-btn" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
        <div className="tester-section">
          <button className="tester-toggle" onClick={() => setShowTester(!showTester)}>
            Want to be a tester? ▾
          </button>
          {showTester && (
            <form className="tester-form" onSubmit={handleTester}>
              <input type="email" placeholder="your@email.com" value={testerEmail}
                onChange={e => setTesterEmail(e.target.value)} required />
              <button type="submit" className="auth-btn secondary">Submit</button>
              {testerMsg && <p className="tester-msg">{testerMsg}</p>}
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
