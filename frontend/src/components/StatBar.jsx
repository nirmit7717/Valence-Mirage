export default function StatBar({ label, value, max, color = '#c9a04e', icon }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className="statbar">
      <div className="statbar-header">
        {icon && <span className="statbar-icon">{icon}</span>}
        <span className="statbar-label">{label}</span>
        <span className="statbar-val">{value}/{max}</span>
      </div>
      <div className="statbar-track">
        <div className="statbar-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}
