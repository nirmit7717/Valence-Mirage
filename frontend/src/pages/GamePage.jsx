import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import App from '../App';

export default function GamePage() {
  const { id } = useParams();
  const navigate = useNavigate();

  // id from route: if "new" or undefined, shows ConnectOverlay
  // if a real session ID, App hydrates from backend
  const campaignId = (!id || id === 'new') ? null : id;

  return (
    <div className="game-page">
      <header className="game-top-bar">
        <button className="back-btn" onClick={() => navigate('/dashboard')}>← Dashboard</button>
        <span className="game-top-title">Valence Mirage</span>
        <span />
      </header>
      <App campaignId={campaignId} />
    </div>
  );
}
