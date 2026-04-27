const MESSAGES = [
  'Generating...',
  'The dice are rolling...',
  'The story unfolds...',
  'Fate stirs...',
  'The world takes shape...',
];

export default function LoadingOverlay({ show }) {
  if (!show) return null;
  return (
    <div className="loading-overlay">
      <div className="loading-content">
        <div className="loading-spinner" />
        <div className="loading-text">{MESSAGES[Math.floor(Math.random() * MESSAGES.length)]}</div>
      </div>
    </div>
  );
}
