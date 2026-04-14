# Combat Rules — Valence Mirage

## Action Types
| Type | Relevant Stat | Default Risk | Default Scale |
|------|--------------|-------------|---------------|
| attack | strength | medium | moderate |
| cast_spell | intelligence | high | major |
| defend | dexterity | low | moderate |
| flee | dexterity | high | minor |

## Dice Resolution (d20)
- **Critical Success** (roll ≥ threshold + 5): Double effect, bonus narration
- **Success** (roll ≥ threshold): Full intended effect
- **Partial Success** (roll = threshold - 1): Effect with complication
- **Failure** (roll < threshold): Action fails, consequence applied
- **Critical Failure** (roll = 1 or roll ≤ threshold - 5): Catastrophic failure

## Damage Rules
- Base damage: determined by action scale + outcome
- Critical success: +50% effectiveness or bonus effect
- Critical failure: Self-damage or status effect
- HP loss thresholds for status effects:
  - Below 25% HP: "weakened" status
  - Below 10% HP: "dying" status
  - 0 HP: Unconscious

## Magic System
- Spells consume mana (cost = scale * 5)
- Cast below 10 mana: -0.3 probability penalty
- Cast at 0 mana: impossible (action rejected)
- Critical success spell: mana refunded + enhanced effect
- Critical failure spell: mana wasted + potential backlash

## Combat Modifiers
- Advantage (flanking, high ground): +2 to dice threshold
- Disadvantage (outnumbered, wounded): -2 to dice threshold
- Status effects: per-effect modifier applied to relevant rolls
