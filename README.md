# 🎲 Valence Mirage

**An AI-powered dark fantasy RPG with structured campaigns, turn-based combat, and probabilistic mechanics.**

---

## What Is It?

Valence Mirage is an interactive storytelling engine where players describe actions in natural language and an AI Game Master adjudicates outcomes through explicit probabilistic mechanics — combining the creative freedom of LLMs with the fairness and tension of tabletop dice systems.

Players can attempt anything. Probability decides the cost.

### Core Experience

- **Free-form input** — No restricted command set. Describe what you want to do naturally.
- **Fair outcomes** — Actions are evaluated through probability and resolved with dice, not arbitrary LLM decisions.
- **Rich narration** — An AI Game Master (70B model) generates immersive story progression, NPC dialogue, and world-building.
- **Character classes** — Warrior, Rogue, Wizard, Cleric, Bard — each with unique stats, abilities, and combat style.
- **Structured campaigns** — Choose Short, Standard, or Grand saga — each with defined narrative arcs and pacing.
- **Turn-based combat** — Class abilities, dice-based damage, status effects, and tactical decision-making.
- **Dynamic NPCs** — AI-generated characters with personality, disposition, trust, and context-aware dialogue.

---

## How It Works

```
1. Player chooses a class and campaign size
2. AI generates a structured campaign blueprint (acts, beats, NPCs)
3. Each turn:
   ├── Player describes an action in natural language
   ├── Intent Parser (8B model) classifies the action
   ├── Probability Engine scores the action (stats + difficulty + context)
   ├── d20 dice roll resolves the outcome
   └── Narrator (70B model) generates story progression
4. Combat encounters: class abilities + dice damage + status effects
5. Campaign advances through beats → acts → climax
```

### Architecture

```
backend/
├── main.py                    # FastAPI server, API endpoints
├── config.py                  # NVIDIA NIM API, model config
├── database.py                # SQLite persistence (aiosqlite)
├── engines/
│   ├── campaign_planner.py    # Template-driven campaign generation
│   ├── intent_parser.py       # Action classification (8B)
│   ├── narrator.py            # Story narration (70B) + combat narration
│   ├── combat_engine.py       # Turn-based combat resolution
│   ├── npc_engine.py          # Dynamic NPC generation + dialogue
│   ├── probability.py         # Weighted scoring + sigmoid normalization
│   ├── dice.py                # d20 resolution, 5 outcome tiers
│   └── state_manager.py       # Player/session state tracking
├── models/
│   ├── character.py           # Classes, abilities, starting gear
│   ├── game_state.py          # Player, session, turn models
│   ├── action.py              # ActionIntent model
│   └── outcome.py             # Outcome types
├── data/
│   ├── campaign_templates.py  # Small/Medium/Large campaign skeletons
│   ├── enemies.py             # Enemy templates + deterministic loot tables
│   ├── trajectories.json      # Seed narrative trajectories for RAG
│   └── rules/                 # Combat, exploration, progression rules
├── rag/
│   ├── vector_store.py        # ChromaDB vector storage
│   ├── embeddings.py          # NVIDIA NIM embeddings
│   └── retriever.py           # Similarity search + rule retrieval
├── prompts/
│   ├── campaign_plan.txt      # Campaign generation prompt
│   ├── intent_parse.txt       # Action classification prompt
│   ├── narrator.txt           # Exploration narration prompt
│   └── combat_narrator.txt    # Combat narration prompt
└── static/
    └── index.html             # Dark fantasy web UI
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3, FastAPI, Uvicorn |
| Frontend | Vanilla HTML/CSS/JS (dark fantasy theme) |
| AI — Intent Parsing | Llama 3.1 8B (NVIDIA NIM) |
| AI — Narration | Llama 3.3 70B (NVIDIA NIM) |
| AI — Embeddings | NV-EmbedQA-E5 (NVIDIA NIM) |
| Vector Search | ChromaDB |
| Storage | SQLite (aiosqlite) |

---

## Project Status

**v0.4.0 — Active Development**

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Core Loop (intent → dice → narration) | ✅ Complete |
| 2 | State & Constraints (persistence, RAG, rules) | ✅ Complete |
| 3 | Intelligence (vector search, NPCs, trajectories) | ✅ Complete |
| 3.5 | Character Classes + Campaign Templates | ✅ Complete |
| 3.6 | Turn-Based Combat System | 🔧 In Progress |
| 4 | RL Engagement Tracker (personalization) | 📋 Planned |

---

## Quick Start

### Prerequisites
- Python 3.10+
- An API key from **NVIDIA NIM** or **OpenRouter**

### Setup

```bash
# Clone
git clone https://github.com/nirmit7717/Valence-Mirage.git
cd Valence-Mirage/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set your API key (use one of the following)
export NVIDIA_API_KEY="your-nvidia-nim-key-here"
# OR
export OPENROUTER_API_KEY="your-openrouter-key-here"

# Update config.py to match your provider if using OpenRouter

# Run the server
python main.py
```

> **Note:** You need to provide your own API key. The project uses NVIDIA NIM by default (free tier available). If using OpenRouter, update `config.py` to point to the OpenRouter endpoint and model.

Open `http://localhost:8000` in your browser.

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/session/new` | Create session (class, size, keywords) |
| `POST` | `/session/{id}/action` | Submit player action |
| `GET` | `/session/{id}/history` | Get turn history |
| `GET` | `/session/{id}` | Get session state |
| `GET` | `/sessions` | List all sessions |
| `DELETE` | `/session/{id}` | Delete a session |
| `GET` | `/health` | Server status |

### Example: Create Session

```json
POST /session/new
{
  "player_name": "Aldric",
  "character_class": "warrior",
  "campaign_size": "medium",
  "keywords": "haunted castle undead siege"
}
```

---

## Character Classes

| Class | STR | DEX | INT | CON | CHA | WIS | HP Bonus | Mana Bonus | Abilities |
|-------|-----|-----|-----|-----|-----|-----|----------|------------|----------|
| ⚔️ Warrior | 14 | 10 | 8 | 12 | 8 | 8 | +15 | +0 | Power Strike, Shield Block, Battle Cry, Cleave |
| 🗡️ Rogue | 10 | 14 | 10 | 8 | 10 | 8 | +5 | +5 | Backstab, Dodge, Poison Blade, Shadow Step |
| 🔮 Wizard | 6 | 8 | 14 | 12 | 8 | 12 | -5 | +20 | Fireball, Ice Shield, Lightning Bolt, Arcane Barrier |
| ✨ Cleric | 10 | 8 | 10 | 10 | 10 | 12 | +5 | +10 | Heal, Smite, Bless, Holy Shield |
| 🎵 Bard | 8 | 10 | 10 | 8 | 14 | 10 | +0 | +10 | Inspire, Mock, Charm, Dissonance |

Each class starts with unique equipment. Abilities have damage dice (e.g. `2d8+3`), mana costs, and status effects (stunned, burning, blessed, etc.).

---

## Campaign Templates

| Size | Beats | Est. Turns | Session Time | Best For |
|------|-------|-----------|-------------|---------|
| ⚡ Small | 6 | 12–15 | ~15 min | Quick adventures |
| 🗺️ Medium | 10 | 20–25 | ~30 min | Standard quest |
| 📖 Large | 16 | 30–35 | ~45 min | Epic saga |

Templates enforce narrative pacing (combat, social, exploration, choice beats) while the AI fills in creative content. Soft enforcement with escalation — if you avoid combat too long, the story pushes you into it.

---

## Probability System

Every action goes through:
1. **Stat bonus** — Relevant ability score (STR for attacks, CHA for persuasion, etc.)
2. **Difficulty modifier** — Context-appropriate challenge level
3. **Mana investment** — Resource spending increases success chance
4. **Repetition penalty** — Repeated actions get harder
5. **Novelty bonus** — Creative/unexpected actions get a boost
6. **RAG similarity** — Actions similar to successful trajectories get a bonus
7. **Sigmoid normalization** → d20 threshold
8. **d20 roll** → 5 outcome tiers (crit success → crit failure)

---

## Roadmap

- [x] Core gameplay loop
- [x] State management + persistence
- [x] RAG vector search + narrative trajectories
- [x] Dynamic NPCs with disposition/trust
- [x] Character class system
- [x] Structured campaign templates
- [x] Turn-based combat with dice mechanics
- [ ] RL-based player personalization
- [x] Deterministic loot tables

---

## License

MIT

---

*Valence Mirage — Freedom is allowed but probability decides its cost.*
