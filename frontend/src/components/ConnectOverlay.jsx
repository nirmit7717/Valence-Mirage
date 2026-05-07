import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CLASS_DATA } from '../data/classes';

const SIZES = [
  { value: 'small', emoji: '⚡', label: 'Short', desc: '12-15 turns' },
  { value: 'medium', emoji: '🗺️', label: 'Standard', desc: '20-25 turns' },
  { value: 'large', emoji: '📖', label: 'Grand Saga', desc: '30-35 turns' },
];

export default function ConnectOverlay({ onStart, onCancel }) {
  const navigate = useNavigate();
  const [name, setName] = useState('Adventurer');
  const [cls, setCls] = useState('warrior');
  const [size, setSize] = useState('medium');
  const [keywords, setKeywords] = useState('');
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(0); // 0 = class select, 1 = details

  const selected = CLASS_DATA[cls];

  const handleStart = async () => {
    setLoading(true);
    try {
      await onStart({ player_name: name || 'Adventurer', keywords, character_class: cls, campaign_size: size });
    } catch {
      alert('Failed to connect to server. Is it running?');
    }
    setLoading(false);
  };

  return (
    <div className="connect-overlay">
      <div className="connect-box connect-box-wide">
        <h2 className="connect-title">🎲 Valence Mirage</h2>
        <p className="connect-subtitle">Choose your fate, adventurer</p>

        {/* Class selection grid */}
        <div className="class-grid">
          {Object.entries(CLASS_DATA).map(([key, data]) => (
            <div
              key={key}
              className={`class-card ${cls === key ? 'class-card-active' : ''}`}
              style={{ '--class-accent': data.accent }}
              onClick={() => setCls(key)}
            >
              <div className="class-card-emoji">{data.emoji}</div>
              <div className="class-card-name">{data.name}</div>
              <div className="class-card-tagline">{data.tagline.split('.')[0]}.</div>
            </div>
          ))}
        </div>

        {/* Selected class details */}
        <div className="connect-class-detail" style={{ '--class-accent': selected.accent }}>
          <div className="connect-detail-header">
            <span>{selected.emoji} {selected.name}</span>
            <button className="vm-link" onClick={() => navigate(`/roles/${cls}`)}>Full Details →</button>
          </div>
          <p className="connect-detail-desc">{selected.playstyle}</p>
          <div className="connect-detail-stats">
            {Object.entries(selected.stats).map(([s, v]) => (
              <span key={s} className={`connect-stat ${v >= 14 ? 'connect-stat-high' : v <= 8 ? 'connect-stat-low' : ''}`}>
                {s} {v}
              </span>
            ))}
            <span className="connect-stat">❤️ {selected.hp}</span>
            <span className="connect-stat">💎 {selected.mana}</span>
          </div>
        </div>

        {/* Name + Keywords */}
        <div className="connect-fields">
          <input type="text" placeholder="Character name..." maxLength={50} value={name}
            onChange={e => setName(e.target.value)} className="connect-input" />

          {/* Campaign size */}
          <div className="size-selector">
            {SIZES.map(s => (
              <button key={s.value} className={`size-btn ${size === s.value ? 'size-btn-active' : ''}`}
                onClick={() => setSize(s.value)}>
                <span className="size-emoji">{s.emoji}</span>
                <span className="size-label">{s.label}</span>
                <span className="size-desc">{s.desc}</span>
              </button>
            ))}
          </div>

          <input type="text" placeholder="Adventure keywords (e.g. haunted castle undead siege)..."
            maxLength={200} value={keywords} onChange={e => setKeywords(e.target.value)}
            className="connect-input connect-input-sm" />
        </div>

        <button className="connect-start-btn" onClick={handleStart} disabled={loading}
          style={{ '--class-accent': selected.accent }}>
          {loading ? 'Forging your destiny...' : `Enter as ${selected.name}`}
        </button>

        {onCancel && (
          <button className="cancel-btn" onClick={onCancel} disabled={loading}>
            ← Back to Dashboard
          </button>
        )}
      </div>
    </div>
  );
}
