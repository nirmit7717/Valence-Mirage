export default function AboutPage() {
  return (
    <div className="auth-page">
      <div className="about-content" style={{ maxWidth: 700, margin: '0 auto', padding: '2rem' }}>
        <h1 style={{ color: '#c9a04e' }}>🎲 Valence Mirage</h1>
        <p style={{ color: '#a0a0a0', lineHeight: 1.8 }}>
          An AI-powered dark fantasy RPG with structured campaigns, turn-based combat,
          and probabilistic mechanics. Players describe actions in natural language and
          an AI Game Master adjudicates outcomes through explicit probabilistic mechanics —
          combining the creative freedom of LLMs with the fairness and tension of tabletop dice systems.
        </p>
        <h2 style={{ color: '#c9a04e', marginTop: '2rem' }}>How It Works</h2>
        <ol style={{ color: '#a0a0a0', lineHeight: 2 }}>
          <li>Choose a class and campaign size</li>
          <li>The AI generates a structured campaign blueprint</li>
          <li>Describe your actions in natural language</li>
          <li>The system evaluates probability and rolls dice</li>
          <li>The narrator generates immersive story progression</li>
        </ol>
        <h2 style={{ color: '#c9a04e', marginTop: '2rem' }}>Character Classes</h2>
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginTop: '1rem' }}>
          {['⚔️ Warrior', '🗡️ Rogue', '🔮 Wizard', '✨ Cleric', '🎵 Bard'].map(cls => (
            <span key={cls} style={{ background: '#1a1a2e', padding: '0.5rem 1rem', borderRadius: 6, color: '#c9a04e' }}>{cls}</span>
          ))}
        </div>
        <p style={{ color: '#666', marginTop: '3rem', fontSize: '0.9rem' }}>
          <em>Valence Mirage — Freedom is allowed but probability decides its cost.</em>
        </p>
      </div>
    </div>
  );
}
