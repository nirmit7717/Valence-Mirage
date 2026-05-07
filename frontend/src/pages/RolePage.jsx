import { useParams, useNavigate } from 'react-router-dom';
import { CLASS_DATA } from '../data/classes';
import StatBar from '../components/StatBar';

export default function RolePage() {
  const { role } = useParams();
  const navigate = useNavigate();
  const data = CLASS_DATA[role];

  if (!data) {
    return (
      <div className="vm-page">
        <div className="vm-empty-state">
          <h2 className="vm-page-title">Unknown Class</h2>
          <p>That class doesn't exist. Choose from the available roles.</p>
          <button className="auth-btn" onClick={() => navigate('/new')}>Choose a Class</button>
        </div>
      </div>
    );
  }

  const typeColors = { attack: '#c44', spell: '#85f', defend: '#59d', support: '#6b5' };

  return (
    <div className="vm-page">
      {/* Hero banner */}
      <div className="role-hero" style={{ '--role-accent': data.accent }}>
        <div className="role-hero-emoji">{data.emoji}</div>
        <div className="role-hero-info">
          <h1 className="role-hero-name">{data.name}</h1>
          <p className="role-hero-tagline">{data.tagline}</p>
        </div>
        <button className="auth-btn" onClick={() => navigate('/new')} style={{ marginLeft: 'auto' }}>Play as {data.name}</button>
      </div>

      {/* Lore */}
      <div className="vm-section">
        <div className="role-lore">{data.lore}</div>
      </div>

      {/* Stats */}
      <div className="vm-section">
        <h2 className="vm-section-title">Attributes</h2>
        <div className="role-stats-grid">
          <StatBar label="HP" value={data.hp} max={70} color="#c44" icon="❤️" />
          <StatBar label="Mana" value={data.mana} max={70} color="#59d" icon="💎" />
        </div>
        <div className="role-attr-grid">
          {Object.entries(data.stats).map(([stat, val]) => (
            <div key={stat} className="role-attr-item">
              <div className="role-attr-val" style={{ color: val >= 14 ? data.accent : val <= 8 ? '#666' : '#aaa' }}>{val}</div>
              <div className="role-attr-name">{stat}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Playstyle */}
      <div className="vm-section">
        <h2 className="vm-section-title">Playstyle</h2>
        <p className="vm-text-lg">{data.playstyle}</p>
      </div>

      {/* Abilities */}
      <div className="vm-section">
        <h2 className="vm-section-title">Abilities</h2>
        <div className="role-abilities">
          {data.abilities.map(ab => (
            <div key={ab.name} className="role-ability-card" style={{ borderLeftColor: typeColors[ab.type] || '#666' }}>
              <div className="role-ability-header">
                <span className="role-ability-name">{ab.name}</span>
                <span className="role-ability-cost">{ab.cost > 0 ? `${ab.cost} MP` : 'Free'}</span>
              </div>
              <p className="role-ability-desc">{ab.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Strengths & Weaknesses */}
      <div className="role-sw-grid">
        <div className="vm-section">
          <h2 className="vm-section-title">💪 Strengths</h2>
          <ul className="vm-list">
            {data.strengths.map((s, i) => <li key={i}>{s}</li>)}
          </ul>
        </div>
        <div className="vm-section">
          <h2 className="vm-section-title">⚠️ Weaknesses</h2>
          <ul className="vm-list">
            {data.weaknesses.map((w, i) => <li key={i}>{w}</li>)}
          </ul>
        </div>
      </div>

      {/* Starting Gear */}
      <div className="vm-section">
        <h2 className="vm-section-title">Starting Equipment</h2>
        <div className="role-gear">
          {data.gear.map(g => (
            <span key={g} className="role-gear-tag">{g}</span>
          ))}
        </div>
      </div>

      {/* Tips */}
      <div className="vm-section">
        <h2 className="vm-section-title">💡 Tips</h2>
        <p className="vm-text-lg">{data.tips}</p>
      </div>
    </div>
  );
}
