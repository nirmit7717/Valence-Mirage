import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import * as api from '../api';
import { CLASS_DATA } from '../data/classes';
import PageLoader from '../components/PageLoader';

export default function CampaignDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [turns, setTurns] = useState([]);
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([
      api.getSession(id).catch(() => null),
      api.getSessionHistory(id).catch(() => []),
    ]).then(([sessionData, historyData]) => {
      if (!sessionData) {
        setError('Campaign not found.');
      } else {
        setSession(sessionData);
        setTurns(historyData.turns || historyData || []);
      }
      setLoading(false);
    });
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
  const ended = ws.campaign_ended;
  const isVictory = ws.victory;

  // Extract unique enemies from turn history
  const enemies = [...new Set(
    turns.map(t => t.enemy_name || t.combat_enemy).filter(Boolean)
  )];

  // Summary stats
  const totalRolls = turns.filter(t => t.roll || t.dice_result).length;
  const combats = turns.filter(t => t.combat_enemy || t.combat_started).length;

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
        </div>
        <div className="campaign-detail-actions">
          {ended ? (
            <span className={`vm-badge vm-badge-lg ${isVictory ? 'vm-badge-success' : 'vm-badge-danger'}`}>
              {isVictory ? '🏆 Victory' : '💀 Defeat'}
            </span>
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
          <span className="campaign-summary-val">{combats}</span>
          <span className="campaign-summary-label">Combats</span>
        </div>
        <div className="campaign-summary-stat">
          <span className="campaign-summary-val">{enemies.length}</span>
          <span className="campaign-summary-label">Unique Enemies</span>
        </div>
      </div>

      {/* Enemies encountered */}
      {enemies.length > 0 && (
        <div className="vm-section">
          <h2 className="vm-section-title">Enemies Encountered</h2>
          <div className="role-gear">
            {enemies.map(e => <span key={e} className="role-gear-tag">👹 {e}</span>)}
          </div>
        </div>
      )}

      {/* Turn timeline */}
      <div className="vm-section">
        <h2 className="vm-section-title">Journey Timeline</h2>
        {turns.length > 0 ? (
          <div className="timeline">
            {turns.map((t, i) => {
              const hasCombat = t.combat_enemy || t.combat_started;
              const rollVal = t.roll || t.dice_result;
              const isSuccess = t.outcome?.includes('success');
              return (
                <div key={i} className={`timeline-item ${hasCombat ? 'timeline-combat' : ''}`}>
                  <div className="timeline-marker">
                    <span className="timeline-dot">{hasCombat ? '⚔️' : `T${t.turn_number || i + 1}`}</span>
                    {i < turns.length - 1 && <div className="timeline-line" />}
                  </div>
                  <div className="timeline-content">
                    <div className="timeline-header">
                      <span className="timeline-turn">Turn {t.turn_number || i + 1}</span>
                      {rollVal && (
                        <span className={`timeline-badge ${isSuccess ? 'vm-badge-success' : ''}`}>
                          🎲 {rollVal} → {t.outcome || '—'}
                        </span>
                      )}
                    </div>
                    {t.player_input && <div className="timeline-input">"{t.player_input}"</div>}
                    {hasCombat && <div className="timeline-combat-label">Combat: {t.combat_enemy || 'Enemy'}</div>}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="vm-empty-state">
            <p>No turn history available for this campaign.</p>
          </div>
        )}
      </div>
    </div>
  );
}
