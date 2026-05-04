export default function FloatingHUD({ data }) {
  if (!data) return null;

  const hpPct = Math.max(0, (data.hp / data.maxHp) * 100);
  const manaPct = Math.max(0, (data.mana / data.maxMana) * 100);
  const xpPct = data.xpToNext ? (data.xp / data.xpToNext) * 100 : 0;

  return (
    <div className="hud-sidebar">
      <div className="hud-section hud-char">
        <div className="hud-name">{data.name}</div>
        <div className="hud-level">{data.characterClass ? data.characterClass.charAt(0).toUpperCase() + data.characterClass.slice(1) : ''} · Level {data.level} · Turn {data.turn || '—'}</div>
      </div>

      <div className="hud-divider" />

      <div className="hud-section">
        <div className="hud-bar-group">
          <div className="hud-bar-label">❤️ HP</div>
          <div className="hud-bar hud-hp-bar">
            <div className="hud-bar-fill hud-hp-fill" style={{ width: `${hpPct}%` }} />
          </div>
          <div className="hud-bar-val">{data.hp}/{data.maxHp}</div>
        </div>

        <div className="hud-bar-group">
          <div className="hud-bar-label">💎 MP</div>
          <div className="hud-bar hud-mana-bar">
            <div className="hud-bar-fill hud-mana-fill" style={{ width: `${manaPct}%` }} />
          </div>
          <div className="hud-bar-val">{data.mana}/{data.maxMana}</div>
        </div>

        <div className="hud-bar-group">
          <div className="hud-bar-label">⭐ XP</div>
          <div className="hud-bar hud-xp-bar">
            <div className="hud-bar-fill hud-xp-fill" style={{ width: `${xpPct}%` }} />
          </div>
          <div className="hud-bar-val">{data.xp}/{data.xpToNext}</div>
        </div>
      </div>

      <div className="hud-divider" />

      <div className="hud-section">
        <div className="hud-stats-title">Attributes</div>
        <div className="hud-stats-grid">
          <div className="hud-stat"><span className="hud-stat-label">STR</span><span className="hud-stat-val">{data.stats?.strength}</span></div>
          <div className="hud-stat"><span className="hud-stat-label">INT</span><span className="hud-stat-val">{data.stats?.intelligence}</span></div>
          <div className="hud-stat"><span className="hud-stat-label">DEX</span><span className="hud-stat-val">{data.stats?.dexterity}</span></div>
          <div className="hud-stat"><span className="hud-stat-label">CON</span><span className="hud-stat-val">{data.stats?.control}</span></div>
          <div className="hud-stat"><span className="hud-stat-label">CHA</span><span className="hud-stat-val">{data.stats?.charisma}</span></div>
          <div className="hud-stat"><span className="hud-stat-label">WIS</span><span className="hud-stat-val">{data.stats?.wisdom}</span></div>
        </div>
      </div>

      <div className="hud-divider" />

      <div className="hud-section">
        <div className="hud-stats-title">📍 {data.beat || '—'}</div>
      </div>

      {data.lastRoll && (
        <>
          <div className="hud-divider" />
          <div className="hud-section">
            <div className="hud-stats-title">Last Roll</div>
            {data.lastRoll.type === 'rolled' ? (
              <div className="hud-roll-info">
                <div>🎲 {data.lastRoll.roll} vs {data.lastRoll.threshold}+</div>
                <div className={`hud-roll-result ${data.lastRoll.outcome?.includes('success') ? 'hud-roll-good' : 'hud-roll-bad'}`}>
                  {data.lastRoll.outcome?.replace(/_/g, ' ')}
                </div>
              </div>
            ) : (
              <div className="hud-roll-info">📖 Choice</div>
            )}
          </div>
        </>
      )}

      {data.inventory?.length > 0 && (
        <>
          <div className="hud-divider" />
          <div className="hud-section">
            <div className="hud-stats-title">Inventory</div>
            <div className="hud-inventory">
              {data.inventory.map((item, i) => (
                <div key={i} className="hud-inv-item">
                  {item.name}
                  <span className="hud-inv-type">{item.type || item.item_type}</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {data.npcs?.length > 0 && (
        <>
          <div className="hud-divider" />
          <div className="hud-section">
            <div className="hud-stats-title">NPCs</div>
            <div className="hud-inventory">
              {data.npcs.map((n, i) => (
                <div key={i} className="hud-inv-item">
                  {n.name}
                  <span className="hud-inv-type">{n.role}</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
