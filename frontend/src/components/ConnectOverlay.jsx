import { useState } from 'react';
import { CLASS_DATA } from '../data/classes';
import { keywordsToText } from '../utils/keywords';
import KeywordInput from './KeywordInput';

const SIZES = [
  { value: 'small', emoji: '⚡', label: 'Short', desc: '8-10 turns · 3 fights' },
  { value: 'medium', emoji: '🗺️', label: 'Standard', desc: '13-15 turns · 5 fights' },
  { value: 'large', emoji: '📖', label: 'Grand Saga', desc: '20-25 turns · 7 fights' },
];

export default function ConnectOverlay({ onStart, onCancel }) {
  const [name, setName] = useState('Adventurer');
  const [cls, setCls] = useState('warrior');
  const [size, setSize] = useState('medium');
  const [keywords, setKeywords] = useState([]);
  const [loading, setLoading] = useState(false);

  const selected = CLASS_DATA[cls];

  const handleStart = async () => {
    setLoading(true);
    try {
      await onStart({ player_name: name || 'Adventurer', keywords: keywordsToText(keywords), character_class: cls, campaign_size: size });
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
        <div className="class-grid" role="radiogroup" aria-label="Character class">
          {Object.entries(CLASS_DATA).map(([key, data]) => (
            <div
              key={key}
              role="radio"
              aria-checked={cls === key}
              tabIndex={0}
              className={`class-card ${cls === key ? 'class-card-active' : ''}`}
              style={{ '--class-accent': data.accent }}
              onClick={() => setCls(key)}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setCls(key); } }}
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
            onChange={e => setName(e.target.value)} className="connect-input" aria-label="Character name" />

          {/* Campaign size */}
          <div className="size-selector" role="radiogroup" aria-label="Campaign length">
            {SIZES.map(s => {
              const active = size === s.value;
              return (
                <button key={s.value} type="button" role="radio" aria-checked={active}
                  className={`size-btn ${active ? 'size-btn-active' : ''}`}
                  onClick={() => setSize(s.value)}>
                  {active && <span className="size-check" aria-hidden="true">✓</span>}
                  <span className="size-emoji">{s.emoji}</span>
                  <span className="size-label">{s.label}</span>
                  <span className="size-desc">{s.desc}</span>
                </button>
              );
            })}
          </div>

          <KeywordInput keywords={keywords} onChange={setKeywords} />
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
