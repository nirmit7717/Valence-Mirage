# 🎲 Valence Mirage

**A probabilistic narrative simulation engine — where LLM-driven storytelling meets dice-governed fairness and RL-powered adaptation.**

---

## The Vision

Valence Mirage is an AI Game Master system that transforms interactive storytelling into a **probabilistic, stateful, and adaptive simulation**. Players speak in natural language, attempt anything they can imagine — and face quantified probability and consequence.

> **"Freedom is allowed. Probability decides its cost."**

### What makes this different?

Existing AI storytelling systems fall into two camps:
- **Rules-light** (AI Dungeon) — pure LLM generation, no structure, easily exploitable
- **Rules-heavy** (traditional CRPGs) — rigid, no creative freedom

**Valence Mirage bridges both worlds:**

- **Free-form input** — Players describe actions in natural language, no restricted command set
- **Probabilistic enforcement** — Every action is evaluated, scored, and resolved through explicit dice mechanics
- **RAG-guided coherence** — Narrative trajectories are grounded in retrieved story patterns, preventing incoherence
- **RL-driven adaptation** — The system learns player behavior and adapts encounters, difficulty, and pacing over time
- **Anti-exploitation** — Repetition penalties, novelty bonuses, and narrative break risk prevent "god mode" spam

| Feature | AI Dungeon | Daicer | Claude-DnD | **Valence Mirage** |
|---------|-----------|--------|------------|---------------------|
| Free-form Input | ✅ | ✅ | ✅ | ✅ |
| D&D 5e Rules | ❌ | ✅ | ✅ | ✅ |
| LLM Narration | ✅ | ✅ | ✅ | ✅ |
| Probabilistic Resolution | ❌ | ✅ (dice) | ✅ (dice) | **✅ (formula + dice)** |
| RAG Memory | ❌ | ✅ | ❌ | **✅ (multi-layer)** |
| RL Adaptation | ❌ | ❌ | ❌ | **✅** |
| Player Behavior Learning | ❌ | ❌ | ❌ | **✅** |
| Anti-Exploitation | ❌ | ❌ | ❌ | **✅** |
| Multiplayer | ❌ | ✅ | ❌ | ✅ (post-MVP) |

---

## Core Mechanics

### 1. Player Intent → Structured Action

Players type anything. The system parses it into structured data:

```
Input: "I rewrite reality to dominate everything"

Output:
{
  "action_type": "domination",
  "scale": "large",
  "risk": "extreme",
  "embedding": [...]
}
```

### 2. RAG-Based Narrative Retrieval

The action embedding is compared against a vector database of narrative trajectories, each tagged with difficulty scores, coherence ratings, risk profiles, and historical outcomes.

**Distributed RAG layers:**
- ⚔️ Combat DB — tactical actions, engagement patterns
- 🗣️ Social/Political DB — diplomacy, deception, persuasion
- ✨ Cosmic/Abstract DB — reality manipulation, high-tier magic
- 📖 Character Arc DB — personal growth, story beats

### 3. Probability Assignment Engine

Action feasibility is computed through a weighted scoring model:

```
Score = w₁·similarity 
      + w₂·player_power 
      + w₃·stat_bonus
      + w₈·novelty_bonus
      - w₃·difficulty 
      - w₄·narrative_break_risk
      - w₅·stat_mismatch
      - w₆·inventory_gap
      - w₇·saturation_penalty
```

**Probability conversion:** `P(success) = σ(Score)`

### 4. Dice Mapping

Probability is mapped to a d20 threshold — preserving the tactile feel of tabletop RPGs:

| Probability | Required Roll (d20) |
|-------------|-------------------|
| 0.9 | 2+ |
| 0.7 | 6+ |
| 0.5 | 10+ |
| 0.3 | 14+ |
| 0.1 | 18+ |

### 5. Outcome Spectrum

| Roll Result | Outcome |
|-------------|---------|
| Critical Success | Perfect execution, bonus effects |
| Success | Goal achieved cleanly |
| Partial Success | Goal achieved with consequences |
| Failure | Action fails |
| Critical Failure | Backfire / severe consequence |

### 6. Anti-Exploitation System

- **Saturation Penalty** — Repeated actions reduce success probability: `Penalty ∝ frequency(action_type)`
- **Novelty Bonus** — Creative, diverse actions get probability boosts: `Bonus ∝ distance(previous_actions)`
- **Narrative Break Risk** — Actions that destabilize story coherence are penalized

---

## Gameplay Loop

```
Player Input (free-form text)
       ↓
Intent Parsing (LLM → structured action + embedding)
       ↓
RAG Retrieval (top-k similar narrative trajectories)
       ↓
Probability Calculation (stats + inventory + constraints + RAG)
       ↓
Dice Prompt ("You need 14+ to succeed")
       ↓
Dice Roll (player or system)
       ↓
Outcome Determination (success / partial / failure)
       ↓
State Update (stats, inventory, world)
       ↓
Narrative Generation (LLM generates story progression)
       ↓
RL Adaptation (player profile updated, difficulty tuned)
       ↓
Loop Continues
```

---

## Player Constraints

### Stats System
Stats directly influence probability:
- **Intelligence** → spell precision, knowledge checks
- **Strength** → physical success, combat effectiveness
- **Control** → stability of complex/scale actions
- **Mana** → resource for abilities (consumed per action)

### Inventory System
Items modify probability — tools enable actions, missing items increase difficulty.

### Resource Constraints
Mana consumption, cooldowns, and fatigue prevent infinite resource loops.

---

## RL Integration

### Player Modeling
Every player builds a behavioral profile over time:
```
PlayerProfile = Embedding(action_history, decision_patterns, risk_tolerance, strategy_style)
```

### Adaptive Environment
- World reacts to player behavior patterns
- Enemies adapt to repeated strategies
- Stakes scale dynamically with player skill
- RL agent (PPO) learns optimal difficulty and pacing per player

### Reward Signal
- Session engagement (duration, return rate)
- Action diversity (are they exploring?)
- Combat satisfaction (fair challenge perception)
- Narrative quality ratings

---

## Architecture

```
┌─────────────────────────────────────────────┐
│           Frontend (React / Web UI)          │
│     Dice visualization, feedback, chat       │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│           API Gateway (FastAPI)              │
└──────────────────────┬──────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
┌──────────────┐ ┌───────────┐ ┌──────────────┐
│ Intent Engine│ │Probability│ │   Narrative   │
│    (LLM)     │ │  Engine   │ │  Generator   │
│ Parse + Embed│ │(RAG+Logic)│ │    (LLM)     │
└──────────────┘ └───────────┘ └──────────────┘
                       │
                       ▼
              ┌──────────────┐
              │ Dice Engine  │
              │  State Mgr   │
              │ RL Adaptation│
              └──────┬───────┘
                     │
           ┌─────────┼─────────┐
           ▼                   ▼
    ┌─────────────┐    ┌──────────────┐
    │  Vector DB  │    │   Game DB    │
    │ (FAISS/     │    │ (SQLite →    │
    │  ChromaDB)  │    │  PostgreSQL) │
    └─────────────┘    └──────────────┘
```

---

## MVP Roadmap

The MVP is deliberately scoped to **single-player, no RL, no microservices** — get the core loop playable first.

### Phase 1 — Core Loop ⚡
- Text input → intent parsing → simplified probability → dice → narrative output
- **Deliverable:** Playable text-based game loop

### Phase 2 — State & Constraints 📊
- Player stats, inventory system, resource consumption, state persistence (SQLite)
- **Deliverable:** Player progression with meaningful constraints

### Phase 3 — RAG Integration 🔍
- FAISS vector DB, action embeddings, similarity-based probability scoring
- **Deliverable:** Smarter, context-aware probability assignment

### Phase 4 — UX Layer 🎨
- Dice visualization, risk feedback ("This is high-risk. You need 15+."), outcome explanations, alternative action suggestions
- **Deliverable:** Engaging, intuitive user experience

### Phase 5 — Anti-Exploitation 🛡️
- Repetition penalty, novelty bonus, narrative break risk detection
- **Deliverable:** Balanced, non-exploitable gameplay

### Post-MVP 🚀
- Multiplayer support
- RL-based difficulty tuning
- Persistent worlds
- AI Dungeon Master personality modes

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python (FastAPI) |
| LLM | Fine-tuned open-source model (TBD) |
| Embeddings | Sentence Transformers |
| Vector DB | FAISS → ChromaDB/Qdrant |
| Game DB | SQLite → PostgreSQL |
| Frontend | React |
| RL | PPO (post-MVP) |
| D&D Rules | D&D 5e SRD / Open5e API |

---

## Datasets & Training Strategy

See [`RESEARCH.md`](./RESEARCH.md) for the full dataset landscape analysis.

**Three-phase training approach:**
1. **Base DM Model** — Fine-tune on combined RP + NPC + adventure datasets
2. **DPO Alignment** — Preference-tune for better DM behavior (fairness, pacing, engagement)
3. **RL Custom Data** — Self-generated through playtest sessions and combat simulations

---

## Project Status

- [x] Research & landscape analysis
- [x] Core mechanics design
- [x] Architecture design
- [x] MVP roadmap
- [ ] Phase 1: Core loop implementation
- [ ] Phase 2: State & constraints
- [ ] Phase 3: RAG integration
- [ ] Phase 4: UX layer
- [ ] Phase 5: Anti-exploitation
- [ ] Post-MVP: Multiplayer + RL

---

## License

TBD

---

*Valence Mirage — Built by Nirmit*
