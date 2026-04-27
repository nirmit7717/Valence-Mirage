import { useState } from 'react';

const CLASSES = [
  { value: 'warrior', emoji: '⚔️', label: 'Warrior — Battle-hardened fighter' },
  { value: 'rogue', emoji: '🗡️', label: 'Rogue — Cunning shadow-dancer' },
  { value: 'wizard', emoji: '🔮', label: 'Wizard — Master of the arcane' },
  { value: 'cleric', emoji: '✨', label: 'Cleric — Divine warrior-healer' },
  { value: 'bard', emoji: '🎵', label: 'Bard — Charismatic performer' },
];

const SIZES = [
  { value: 'small', emoji: '⚡', label: 'Short Adventure (12-15 turns)' },
  { value: 'medium', emoji: '🗺️', label: 'Standard Quest (20-25 turns)' },
  { value: 'large', emoji: '📖', label: 'Grand Saga (30-35 turns)' },
];

export default function ConnectOverlay({ onStart }) {
  const [name, setName] = useState('Adventurer');
  const [cls, setCls] = useState('warrior');
  const [size, setSize] = useState('medium');
  const [keywords, setKeywords] = useState('');
  const [loading, setLoading] = useState(false);

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
      <div className="connect-box">
        <h2>🎲 Valence Mirage</h2>
        <p style={{ color: '#888', marginBottom: 16, fontSize: 13 }}>Choose your class and begin your adventure</p>
        <input type="text" placeholder="Character name..." maxLength={50} value={name}
          onChange={e => setName(e.target.value)} />
        <select value={cls} onChange={e => setCls(e.target.value)}>
          {CLASSES.map(c => <option key={c.value} value={c.value}>{c.emoji} {c.label}</option>)}
        </select>
        <select value={size} onChange={e => setSize(e.target.value)}>
          {SIZES.map(s => <option key={s.value} value={s.value}>{s.emoji} {s.label}</option>)}
        </select>
        <input type="text" placeholder="Adventure keywords... (e.g. haunted castle undead siege)"
          maxLength={200} value={keywords} onChange={e => setKeywords(e.target.value)}
          style={{ fontSize: 12, color: '#999' }} />
        <button onClick={handleStart} disabled={loading}>
          {loading ? 'Creating...' : 'Enter the World'}
        </button>
      </div>
    </div>
  );
}
