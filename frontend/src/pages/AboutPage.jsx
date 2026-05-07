import { useNavigate } from 'react-router-dom';
import { CLASS_DATA } from '../data/classes';

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
        <div className="about-class-grid">
          {Object.entries(CLASS_DATA).map(([key, cls]) => (
            <div key={key} className="about-class-card" style={{ '--class-accent': cls.accent }}
              onClick={() => navigate(`/roles/${key}`)}>
              <div className="about-class-emoji">{cls.emoji}</div>
              <div className="about-class-name">{cls.name}</div>
              <div className="about-class-tagline">{cls.tagline.split('.')[0]}.</div>
              <div className="about-class-link">View Details →</div>
            </div>
          ))}
        </div>
      </div>

      <p className="vm-tagline"><em>Freedom is allowed but probability decides its cost.</em></p>
    </div>
  );
}
