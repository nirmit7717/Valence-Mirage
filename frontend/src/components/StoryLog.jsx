import { useEffect, useRef, useState } from 'react';

// Read-only reader for earlier scenes. Opens on the scene before the current one;
// "Back to present" closes it so the player continues where they left off.
// Mounted only while open (see wrapper below), so each opening starts fresh.
export default function StoryLog({ open, entries, onClose }) {
  if (!open || entries.length === 0) return null;
  return <StoryReader entries={entries} onClose={onClose} />;
}

function StoryReader({ entries, onClose }) {
  // Start one scene back — the current scene is already on the card behind.
  const [index, setIndex] = useState(() => Math.max(0, entries.length - 2));
  const closeRef = useRef(null);

  useEffect(() => { closeRef.current?.focus(); }, []);

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') onClose();
      else if (e.key === 'ArrowLeft') setIndex(i => Math.max(0, i - 1));
      else if (e.key === 'ArrowRight') setIndex(i => Math.min(entries.length - 1, i + 1));
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [entries.length, onClose]);

  const safeIndex = Math.min(index, entries.length - 1);
  const entry = entries[safeIndex];
  const isLatest = safeIndex === entries.length - 1;
  const heading = entry.turn ? `Turn ${entry.turn}` : entry.turn === 0 ? 'The Beginning' : 'Scene';

  return (
    <div className="story-log-overlay" role="dialog" aria-modal="true" aria-label="Story so far" onClick={onClose}>
      <div className="story-log-card" onClick={(e) => e.stopPropagation()}>
        <div className="story-log-header">
          <span className="story-log-title">📖 Story So Far</span>
          <span className="story-log-count">{safeIndex + 1} / {entries.length}</span>
        </div>

        <div className="story-log-body" key={safeIndex}>
          <div className="story-log-turn">{heading}{isLatest ? ' · current' : ''}</div>
          {entry.playerInput && <div className="story-log-input">“{entry.playerInput}”</div>}
          <div className="story-log-text" dangerouslySetInnerHTML={{ __html: entry.html }} />
        </div>

        <div className="story-log-nav">
          <button className="nc-nav-btn" onClick={() => setIndex(Math.max(0, safeIndex - 1))} disabled={safeIndex === 0}>
            ‹ Previous
          </button>
          <button className="nc-nav-btn" onClick={() => setIndex(Math.min(entries.length - 1, safeIndex + 1))} disabled={isLatest}>
            Next ›
          </button>
        </div>
        <button ref={closeRef} className="nc-continue-btn story-log-close" onClick={onClose}>Back to present ▸</button>
      </div>
    </div>
  );
}
