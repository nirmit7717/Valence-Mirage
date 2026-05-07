import { useNavigate } from 'react-router-dom';

export default function AboutPage() {
  const navigate = useNavigate();

  return (
    <div className="vm-page">
      <div className="vm-page-header">
        <h1 className="vm-page-title">About Valence Mirage</h1>
      </div>

      <div className="vm-section">
        <p className="vm-text-lg">
          An AI-powered dark fantasy RPG with structured campaigns, turn-based combat,
          and probabilistic mechanics. Players describe actions in natural language and
          an AI Game Master adjudicates outcomes through explicit probabilistic mechanics —
          combining the creative freedom of LLMs with the fairness and tension of tabletop dice systems.
        </p>
      </div>

      <div className="vm-section">
        <h2 className="vm-section-title">How It Works</h2>
        <ol className="vm-list">
          <li>Choose a class and campaign size</li>
          <li>The AI generates a structured campaign blueprint</li>
          <li>Describe your actions in natural language</li>
          <li>The system evaluates probability and rolls dice</li>
          <li>The narrator generates immersive story progression</li>
        </ol>
      </div>

      <div className="vm-section">
        <h2 className="vm-section-title">Character Classes</h2>
        <div className="vm-class-grid">
          {[
            { emoji: '⚔️', name: 'Warrior', desc: 'Brute force, high HP, melee mastery' },
            { emoji: '🗡️', name: 'Rogue', desc: 'Stealth, poison, critical strikes' },
            { emoji: '🔮', name: 'Wizard', desc: 'Arcane magic, area damage, high mana' },
            { emoji: '✨', name: 'Cleric', desc: 'Healing, holy damage, support' },
            { emoji: '🎵', name: 'Bard', desc: 'Inspiration, mockery, crowd control' },
          ].map(cls => (
            <div key={cls.name} className="vm-class-card">
              <span className="vm-class-emoji">{cls.emoji}</span>
              <div className="vm-class-name">{cls.name}</div>
              <div className="vm-class-desc">{cls.desc}</div>
            </div>
          ))}
        </div>
      </div>

      <p className="vm-tagline"><em>Freedom is allowed but probability decides its cost.</em></p>
    </div>
  );
}
