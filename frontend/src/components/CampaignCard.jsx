export default function CampaignCard({ campaign, onClick }) {
  const isVictory = campaign.result === 'victory';
  return (
    <div className="vm-card vm-card-clickable vm-card-interactive" onClick={onClick}>
      <div className="vm-card-accent" style={{ background: isVictory ? 'linear-gradient(135deg, #2a6, #4c8)' : 'linear-gradient(135deg, #a33, #c55)' }} />
      <div className="vm-card-main">
        <div className="vm-card-title">{campaign.campaign_title || 'Untitled Campaign'}</div>
        <div className="vm-card-meta">
          <span className="vm-card-tag">{campaign.character_class}</span>
          <span>{campaign.turns} turns</span>
          <span>{new Date(campaign.created_at).toLocaleDateString()}</span>
        </div>
      </div>
      <span className={`vm-badge ${isVictory ? 'vm-badge-success' : 'vm-badge-danger'}`}>
        {isVictory ? '🏆 Victory' : '💀 Defeat'}
      </span>
    </div>
  );
}
