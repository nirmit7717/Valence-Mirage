import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import App from '../App';

export default function GamePage() {
  const navigate = useNavigate();

  useEffect(() => {
    // Auth is optional for game — but redirect if we want enforcement
    // For now, game works with or without token
  }, []);

  return (
    <div className="game-page">
      <header className="game-top-bar">
        <button className="back-btn" onClick={() => navigate('/dashboard')}>← Dashboard</button>
        <span className="game-top-title">Valence Mirage</span>
        <span />
      </header>
      <App />
    </div>
  );
}
