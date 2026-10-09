import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import * as api from '../api';
import { CLASS_DATA } from '../data/classes';
import PageLoader from '../components/PageLoader';

// Turn records come straight from the backend Turn model:
//   { turn_number, player_input, roll, outcome: { result, roll, threshold, narration, ... } }
// `outcome` is an object — reading it as a string is what used to crash this page.
function describeTurn(turn) {
  const outcome = turn.outcome && typeof turn.outcome === 'object' ? turn.outcome : {};
  const result = outcome.result || '';
  const roll = outcome.roll || turn.roll || 0;
  const actionType = turn.intent?.action_type || '';
  // A fight is recorded as its own turn: action_type "combat", result combat_victory / combat_defeat.
  const fight = actionType === 'combat' || result === 'combat_victory' || result === 'combat_defeat';
  return {
    number: turn.turn_number,
    input: turn.player_input || '',
    result,
    rolled: roll > 0,
    roll,
    threshold: outcome.threshold || 0,
    narration: stripChoices(outcome.narration || ''),
    success: result.includes('success'),
    fight,
    combat: fight || actionType === 'attack' || result === 'player_death',
  };
}

function fightLabel(result) {
  return result === 'combat_defeat' ? '⚔️ Fight lost' : '⚔️ Fight won';
}

function stripChoices(text) {
  return text.replace(/^\s*(?:→|->).*$/gm, '').trim();
}

function resultLabel(result) {
  return result ? result.replace(/_/g, ' ') : '—';
}

const ENDINGS = {
  victory: { label: '🏆 Victory', className: 'vm-badge-success' },
  defeat: { label: '💀 Defeat', className: 'vm-badge-danger' },
  lost_focus: { label: '🌫️ Lost Focus', className: 'vm-badge-danger' },
};

export default function CampaignDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [turns, setTurns] = useState([]);
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState({});

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.getSession(id), api.getSessionHistory(id).catch(() => [])])
      .then(([sessionData, historyData]) => {
        if (cancelled) return;
        setSession(sessionData);
        setTurns(Array.isArray(historyData) ? historyData.map(describeTurn) : []);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e.status === 404 ? 'Campaign not found, or it belongs to another account.' : `Couldn't load this campaign: ${e.message}`);
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [id]);

  if (loading) return <div className="vm-page-center"><PageLoader text="Loading campaign..." /></div>;
  if (error) return (
    <div className="vm-page">
      <div className="vm-empty-state">
        <h2 className="vm-page-title">⚠ {error}</h2>
        <button className="auth-btn" onClick={() => navigate('/campaigns')}>Back to Campaigns</button>
      </div>
    </div>
  );

  const ws = session?.world_state || {};
  const campaign = ws.campaign || {};
  const player = session?.player || {};
  const cls = player.character_class || '—';
  const clsData = CLASS_DATA[cls];
  const turnCount = session?.turn_number || turns.length;
  const ended = Boolean(ws.campaign_ended);
  const outcome = ws.campaign_result || (ws.status === 'failed' ? 'defeat' : ws.warning_count >= 3 ? 'lost_focus' : 'victory');
  const ending = ENDINGS[outcome] || ENDINGS.victory;
  const opening = stripChoices(ws.opening_narration || '');

  const totalRolls = turns.filter(t => t.rolled).length;
  const successes = turns.filter(t => t.rolled && t.success).length;

  const toggle = (key) => setExpanded(prev => ({ ...prev, [key]: !prev[key] }));

  return (
    <div className="vm-page">
      {/* Breadcrumb */}
      <div className="vm-breadcrumb">
        <button className="vm-link" onClick={() => navigate('/campaigns')}>Campaigns</button>
        <span className="vm-breadcrumb-sep">/</span>
        <span className="vm-breadcrumb-current">{campaign.title || 'Campaign Detail'}</span>
      </div>

      {/* Hero header */}
      <div className="campaign-detail-hero" style={{ '--class-accent': clsData?.accent || '#c9a04e' }}>
        <div className="campaign-detail-info">
          <h1 className="campaign-detail-title">{campaign.title || 'Untitled Campaign'}</h1>
          <div className="campaign-detail-meta">
            <span className="campaign-detail-class">{clsData?.emoji || ''} {cls}</span>
            <span>{turnCount} turns</span>
            <span>{session?.created_at ? new Date(session.created_at).toLocaleDateString() : ''}</span>
          </div>
          {campaign.premise && <p className="campaign-detail-premise">{campaign.premise}</p>}
        </div>
        <div className="campaign-detail-actions">
          {ended ? (
            <span className={`vm-badge vm-badge-lg ${ending.className}`}>{ending.label}</span>
          ) : (
            <button className="auth-btn" onClick={() => navigate(`/campaign/${id}`)}>Resume Campaign</button>
          )}
        </div>
      </div>

      {/* Summary stats */}
      <div className="campaign-summary-grid">
        <div className="campaign-summary-stat">
          <span className="campaign-summary-val">{turnCount}</span>
          <span className="campaign-summary-label">Turns</span>
        </div>
        <div className="campaign-summary-stat">
          <span className="campaign-summary-val">{totalRolls}</span>
          <span className="campaign-summary-label">Dice Rolls</span>
        </div>
        <div className="campaign-summary-stat">
          <span className="campaign-summary-val">{successes}</span>
          <span className="campaign-summary-label">Successes</span>
        </div>
        <div className="campaign-summary-stat">
          <span className="campaign-summary-val">{player.level || 1}</span>
          <span className="campaign-summary-label">Final Level</span>
        </div>
      </div>

      {/* Turn timeline */}
      <div className="vm-section">
        <h2 className="vm-section-title">Journey Timeline</h2>
        {opening && (
          <div className="timeline">
            <div className="timeline-item">
              <div className="timeline-marker"><span className="timeline-dot">📜</span></div>
              <div className="timeline-content">
                <div className="timeline-header"><span className="timeline-turn">The Beginning</span></div>
                <div className="timeline-narration">
                  {expanded.opening || opening.length <= 280 ? opening : `${opening.slice(0, 280)}…`}
                </div>
                {opening.length > 280 && (
                  <button className="vm-link timeline-toggle" onClick={() => toggle('opening')}>
                    {expanded.opening ? 'Show less' : 'Read more'}
                  </button>
                )}
              </div>
            </div>
          </div>
        )}
        {turns.length > 0 ? (
          <div className="timeline">
            {turns.map((t, i) => {
              const key = `t${t.number}-${i}`;
              const long = t.narration.length > 280;
              return (
                <div key={key} className={`timeline-item ${t.combat ? 'timeline-combat' : ''}`}>
                  <div className="timeline-marker">
                    <span className="timeline-dot">{t.combat ? '⚔️' : `T${t.number || i + 1}`}</span>
                    {i < turns.length - 1 && <div className="timeline-line" />}
                  </div>
                  <div className="timeline-content">
                    <div className="timeline-header">
                      <span className="timeline-turn">Turn {t.number || i + 1}</span>
                      {t.fight ? (
                        <span className={`timeline-badge ${t.result === 'combat_victory' ? 'vm-badge-success' : ''}`}>
                          {fightLabel(t.result)}
                        </span>
                      ) : t.rolled ? (
                        <span className={`timeline-badge ${t.success ? 'vm-badge-success' : ''}`}>
                          🎲 {t.roll} vs {t.threshold}+ → {resultLabel(t.result)}
                        </span>
                      ) : (
                        <span className="timeline-badge">📖 {resultLabel(t.result)}</span>
                      )}
                    </div>
                    {t.input && <div className="timeline-input">"{t.input}"</div>}
                    {t.narration && (
                      <>
                        <div className="timeline-narration">
                          {expanded[key] || !long ? t.narration : `${t.narration.slice(0, 280)}…`}
                        </div>
                        {long && (
                          <button className="vm-link timeline-toggle" onClick={() => toggle(key)}>
                            {expanded[key] ? 'Show less' : 'Read more'}
                          </button>
                        )}
                      </>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : !opening && (
          <div className="vm-empty-state">
            <p>No turn history available for this campaign.</p>
          </div>
        )}
      </div>
    </div>
  );
}
