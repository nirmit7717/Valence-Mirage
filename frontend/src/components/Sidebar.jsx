export default function Sidebar({ data }) {
  if (!data) return null;

  const hpPct = Math.max(0, (data.hp / data.maxHp) * 100);
  const manaPct = Math.max(0, (data.mana / data.maxMana) * 100);
  const xpPct = data.xpToNext ? (data.xp / data.xpToNext) * 100 : 0;

  return (
    <div className="sidebar">
      <h3>Character</h3>
      <StatRow label="Name" value={data.name} />
      <StatRow label="Level" value={data.level} />
      <StatRow label="XP" value={`${data.xp} / ${data.xpToNext}`} />
      <div className="xp-bar"><div className="fill" style={{ width: `${xpPct}%` }} /></div>

      <h3>HP</h3>
      <div className="stat-row"><span className="stat-val">{data.hp} / {data.maxHp}</span></div>
      <div className="hp-bar"><div className="fill" style={{ width: `${hpPct}%` }} /></div>

      <h3>Mana</h3>
      <div className="stat-row"><span className="stat-val">{data.mana} / {data.maxMana}</span></div>
      <div className="mana-bar"><div className="fill" style={{ width: `${manaPct}%` }} /></div>

      <h3>Stats</h3>
      <StatRow label="STR" value={data.stats?.strength} />
      <StatRow label="INT" value={data.stats?.intelligence} />
      <StatRow label="DEX" value={data.stats?.dexterity} />
      <StatRow label="CON" value={data.stats?.control} />
      <StatRow label="CHA" value={data.stats?.charisma} />
      <StatRow label="WIS" value={data.stats?.wisdom} />

      {data.lastRoll && (
        <>
          <h3>Last Action</h3>
          <div className="score-box">
            {data.lastRoll.type === 'rolled' ? (
              <>
                <StatRow label="Type" value="🎲 Rolled" />
                <StatRow label="Probability" value={data.lastRoll.probability ? (data.lastRoll.probability * 100).toFixed(1) + '%' : '—'} />
                <StatRow label="Threshold" value={`${data.lastRoll.threshold}+`} />
                <StatRow label="Roll" value={data.lastRoll.roll} />
              </>
            ) : (
              <StatRow label="Type" value="📖 Choice" />
            )}
            <StatRow label="Result" value={data.lastRoll.outcome?.replace(/_/g, ' ')} />
          </div>
        </>
      )}

      <h3>Story Beat</h3>
      <div style={{ color: '#c8a', fontSize: 12 }}>{data.beat}</div>

      <h3>Effects</h3>
      <div style={{ color: '#888', fontSize: 12 }}>{data.effects?.length ? data.effects.join(', ') : 'None'}</div>

      <h3>Inventory</h3>
      <div style={{ color: '#888', fontSize: 12 }}>
        {data.inventory?.length ? data.inventory.map((i, idx) => (
          <div key={idx} className="inventory-item">{i.name} <span className="item-type">[{i.type || i.item_type}]</span></div>
        )) : 'Empty'}
      </div>

      <h3>NPCs</h3>
      <div style={{ color: '#888', fontSize: 12 }}>
        {data.npcs?.length ? data.npcs.map((n, idx) => (
          <div key={idx} style={{ padding: '2px 0', color: '#c8a' }}>
            {n.name} <span style={{ color: '#666', fontSize: 10 }}>[{n.role}]</span>
          </div>
        )) : 'None'}
      </div>
    </div>
  );
}

function StatRow({ label, value }) {
  return (
    <div className="stat-row">
      <span className="stat-label">{label}</span>
      <span className="stat-val">{value ?? '—'}</span>
    </div>
  );
}
