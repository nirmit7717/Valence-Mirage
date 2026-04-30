import { useState, useEffect } from 'react';

export default function DiceRoll({ diceResult, onComplete }) {
  const [phase, setPhase] = useState('rolling'); // rolling | result | done
  const [displayNumber, setDisplayNumber] = useState('?');
  const [rollCount, setRollCount] = useState(0);

  useEffect(() => {
    if (!diceResult) return; // Wait for actual dice data, don't fire onComplete

    // Phase 1: Rolling animation (numbers cycling)
    const finalRoll = diceResult.rolled;
    const maxCycles = 12;
    let count = 0;

    const interval = setInterval(() => {
      count++;
      setRollCount(count);
      // Random number, but gradually approach the final value
      if (count >= maxCycles) {
        setDisplayNumber(finalRoll);
        clearInterval(interval);
        // Phase 2: Show result for a moment
        setTimeout(() => {
          setPhase('result');
          // Phase 3: Let parent know we're done
          setTimeout(() => {
            setPhase('done');
            onComplete?.();
          }, 800);
        }, 200);
      } else {
        // Weighted random: gets closer to actual value as cycles progress
        const weight = count / maxCycles;
        const range = Math.max(2, Math.floor(20 * (1 - weight)));
        let num = finalRoll + Math.floor(Math.random() * range * 2) - range;
        num = Math.max(1, Math.min(20, num));
        setDisplayNumber(num);
      }
    }, 80);

    return () => clearInterval(interval);
  }, [diceResult]); // removed onComplete from deps to avoid re-triggering

  if (!diceResult || phase === 'done') return null;

  const isSuccess = diceResult.success;
  const isCrit = diceResult.critical;
  const typeLabel = { attack: '⚔️ Attack', skill: '✦ Skill', check: '🔍 Check' }[diceResult.type] || '🎲 Roll';

  return (
    <div className="dice-overlay">
      <div className={`dice-card ${phase === 'result' ? (isSuccess ? 'dice-success' : 'dice-failure') : ''} ${isCrit ? 'dice-crit' : ''}`}>
        {phase === 'rolling' && (
          <>
            <div className="dice-type">{typeLabel}</div>
            <div className="dice-number rolling">{displayNumber}</div>
            <div className="dice-target">vs {diceResult.target}+</div>
          </>
        )}
        {phase === 'result' && (
          <>
            <div className="dice-type">{typeLabel}</div>
            <div className={`dice-number result ${isSuccess ? 'dice-num-success' : 'dice-num-failure'}`}>
              {diceResult.rolled}
            </div>
            <div className="dice-target">vs {diceResult.target}+</div>
            <div className={`dice-outcome ${isSuccess ? 'dice-out-success' : 'dice-out-failure'}`}>
              {isCrit ? (isSuccess ? '✦ CRITICAL SUCCESS ✦' : '✦ CRITICAL FAILURE ✦') : (isSuccess ? 'SUCCESS' : 'FAILURE')}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
