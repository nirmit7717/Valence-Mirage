const NO_ROLL_MESSAGES = [
  'Generating...',
  'The story unfolds...',
  'Fate stirs...',
  'The world takes shape...',
  'The realm awaits...',
];

const ROLL_MESSAGES = [
  'The dice are rolling...',
  'Fate hangs in the balance...',
  'The dice tumble through the air...',
  'Fortune decides...',
];

export default function LoadingOverlay({ show, hasRoll }) {
  if (!show) return null;
  const messages = hasRoll ? ROLL_MESSAGES : NO_ROLL_MESSAGES;
  return (
    <div className="loading-overlay">
      <div className="loading-content">
        <div className="loading-spinner" />
        <div className="loading-text">{messages[Math.floor(Math.random() * messages.length)]}</div>
      </div>
    </div>
  );
}
