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
├── auth.py                     # JWT auth, bcrypt, user management
├── config.py                  # NVIDIA NIM API, model config, JWT config
├── database.py                # SQLite persistence (aiosqlite) + user tables
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
│   ├── character.py           # Classes, abilities (4/class), starting gear
│   ├── combat.py              # Combat models + StatusEffectType registry
│   ├── game_state.py          # Player, session, turn models
│   ├── action.py              # ActionIntent model
│   ├── outcome.py             # Outcome types
│   └── user.py                # User + TesterRequest models
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
    └── index.html             # Built React UI (Vite output)
frontend/
├── index.html                 # Vite entry point
├── vite.config.js             # Build config (outputs to backend/static)
├── src/
│   ├── main.jsx               # React root
│   ├── AppRouter.jsx           # React Router (/, /login, /dashboard, /game)
│   ├── App.jsx                # Layout + theme manager
│   ├── api.js                 # Backend API wrapper + auth headers
│   ├── pages/
│   │   ├── LoginPage.jsx       # Dark fantasy login
│   │   ├── DashboardPage.jsx   # User stats + campaign history
│   │   └── GamePage.jsx        # Game wrapper with auth check
│   ├── hooks/
│   │   └── useGame.js          # Core game state hook
│   ├── components/
│   │   ├── ConnectOverlay.jsx  # Session creation
│   │   ├── ChatArea.jsx        # Narrative log
│   │   ├── Sidebar.jsx         # Stats/inventory/NPCs
│   │   ├── InputArea.jsx       # Action input
│   │   ├── NarrativeCard.jsx   # Modal narration + typewriter + chunking
│   │   ├── CombatOverlay.jsx   # Full combat engine + cinematics
│   │   ├── LoadingOverlay.jsx  # Fullscreen loading spinner
│   │   ├── SettingsPanel.jsx   # TTS/animation/speed controls
│   │   └── CampaignEndOverlay.jsx
│   └── utils/
│       ├── tts.js              # Browser SpeechSynthesis
│       ├── typewriter.js        # Character-by-character reveal
│       ├── chunker.js           # Smart narration splitting
│       ├── combat.js            # Pure combat resolution
│       └── theme.js             # Dynamic theming + ambience
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3, FastAPI, Uvicorn |
| Frontend | React + Vite + React Router (dark fantasy immersive UI) |
| Auth | JWT (python-jose), bcrypt (passlib) |
| AI — Intent Parsing | Llama 3.1 8B (NVIDIA NIM) |
| AI — Narration | Llama 3.3 70B (NVIDIA NIM) |
| AI — Embeddings | NV-EmbedQA-E5 (NVIDIA NIM) |
| Vector Search | ChromaDB |
| Storage | SQLite (aiosqlite) |
| Reliability | 30-60s request timeouts, 2 retry attempts max (4s backoff) |

---

## Project Status

**v0.7.2 — Active Development**

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Core Loop (intent → dice → narration) | ✅ Complete |
| 2 | State & Constraints (persistence, RAG, rules) | ✅ Complete |
| 3 | Intelligence (vector search, NPCs, trajectories) | ✅ Complete |
| 3.5 | Character Classes + Campaign Templates | ✅ Complete |
| 3.6 | Turn-Based Combat System | ✅ Complete |
| 3.7 | Combat Depth (Status Effects + Abilities) | ✅ Complete |
| 3.8 | Auth + User Management | ✅ Complete |
| 3.9 | Combat Enforcement + UI Polish | ✅ Complete |
| 3.10 | System Coherence (background, validation, context) | ✅ Complete |
| 4 | RL Engagement Tracker (personalization) | 📋 Planned |

---

## Quick Start

### Prerequisites
- Python 3.10+
- An API key from **NVIDIA NIM** or **OpenRouter**

### Setup

#### 1. Clone the repository
```bash
git clone https://github.com/nirmit7717/Valence-Mirage.git
cd Valence-Mirage/backend
```

#### 2. Create and Activate Virtual Environment
**Windows:**
```powershell
python -m venv venv
.\venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 4. Configure Environment Variables
1. Rename `.env.example` to `.env` (or create a new `.env` file).
2. Open `.env` and add your **NVIDIA_API_KEY** or **OPENROUTER_API_KEY**.

```env
NVIDIA_API_KEY="your-key-here"
# Optional: NARRATOR_MODEL="meta/llama-3.3-70b-instruct"
```

#### 5. Run the Server
```bash
python main.py
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/session/new` | Create session (class, size, keywords) |
| `POST` | `/session/{id}/action` | Submit player action |
| `POST` | `/session/{id}/combat/init` | Initiate combat encounter |
| `POST` | `/session/{id}/combat/resolve` | Submit combat result |
| `GET` | `/session/{id}/combat` | Get combat state |
| `GET` | `/session/{id}/history` | Get turn history |
| `GET` | `/session/{id}` | Get session state |
| `GET` | `/sessions` | List all sessions |
| `DELETE` | `/session/{id}` | Delete a session |
| `POST` | `/auth/login` | Login (JWT) |
| `POST` | `/auth/create-user` | Admin: create user |
| `POST` | `/auth/tester-request` | Request tester access |
| `GET` | `/user/me` | Get current user |
| `GET` | `/user/dashboard` | User dashboard data |
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
| ⚔️ Warrior | 14 | 10 | 8 | 12 | 8 | 8 | +15 | +0 | Power Strike, Guard, Cleave, War Cry |
| 🗡️ Rogue | 10 | 14 | 10 | 8 | 10 | 8 | +5 | +5 | Backstab, Evade, Poison Blade, Shadow Step |
| 🔮 Wizard | 6 | 8 | 14 | 12 | 8 | 12 | -5 | +20 | Arcane Bolt, Focus Mind, Lightning Bolt, Arcane Shield |
| ✨ Cleric | 10 | 8 | 10 | 10 | 10 | 12 | +5 | +10 | Heal, Smite, Holy Shield, Purify |
| 🎵 Bard | 8 | 10 | 10 | 8 | 14 | 10 | +0 | +10 | Mock, Inspire, Dissonance, Lullaby |

Each class has 4 abilities using a unified status effect system. Abilities interact with dice mechanics — some apply **bleed** (DoT), **stun** (skip turn), **weaken** (halve damage), **focus** (+5 to next roll), or **blocking** (+3 armor). See [Combat Depth](#combat-depth-system) for details.

---

## Campaign Templates

| Size | Beats | Est. Turns | Session Time | Best For |
|------|-------|-----------|-------------|---------|
| ⚡ Small | 6 | 12–15 | ~15 min | Quick adventures |
| 🗺️ Medium | 10 | 20–25 | ~30 min | Standard quest |
| 📖 Large | 16 | 30–35 | ~45 min | Epic saga |

Templates enforce narrative pacing (combat, social, exploration, choice beats) while the AI fills in creative content. Soft enforcement with escalation — if you avoid combat too long, the story pushes you into it.

---

## Combat Depth System

### Status Effects

All status effects are governed by a unified registry (`STATUS_EFFECT_RULES`) that defines behavior for both backend and frontend:

| Effect | Icon | Mechanic | Duration |
|--------|------|----------|----------|
| 🩸 Bleed | DoT: 2–4 damage/turn | 2–3 turns |
| 💫 Stun | Skip next turn | 1 turn |
| 📉 Weaken | Halve outgoing damage | 2 turns |
| 🎯 Focus | +5 to next d20 roll | 1 turn |
| ☠️ Poison | DoT: 1–4 damage/turn | 3–5 turns |
| 🔥 Burning | DoT: 1–3 damage/turn | 2–3 turns |
| 🛡️ Blocking | +3 armor | 1 turn |
| 💨 Dodging | 50% chance to avoid attack | 1 turn |

### 6-Phase Turn Structure

Every combat turn follows this order:

1. **Apply status effects** — DoT ticks, HoT, narrative log messages
2. **Can act?** — Stun → skip turn
3. **Execute action** — attack/ability/flee
4. **Resolve dice roll** — d20 + roll modifiers (focus, stealth)
5. **Calculate damage** — base × damage modifier (weakened → ×0.5), apply target effects
6. **Apply damage + update state** — dodge chance checked, HP updated

### Effect Rules
- **Non-stacking**: Reapplying an effect refreshes duration instead of stacking
- **Duration cap**: Each effect has a max duration (prevents infinite effects)
- **Registry-driven**: Both backend and frontend use identical rule tables

### Narration
Status effects are described narratively — never mechanically. "Blood trickles from the wound, refusing to clot" instead of "bleed for 3 turns (-2 HP/tick)".

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
- [x] Combat depth (status effects, abilities, 6-phase turns)
- [x] Context-aware combat (narrator-driven enemy selection)
- [x] Combat tension tracker (contextual, risk-based)
- [x] Combat mode enforcement (system-driven, not narrator-dependent)
- [x] Campaign deviation tracking (immersive warnings)
- [x] Auth + user management (JWT, bcrypt, admin creation)
- [x] Campaign history persistence
- [x] Deterministic loot tables
- [x] Dynamic UI context (background theming per turn)
- [x] Enemy name consistency (single source of truth)
- [x] Input validation pipeline (redo_turn, kill switch)
- [x] Context memory for deviation evaluation (turn history)
- [x] API reliability (timeouts, retries, max_tokens reduction)
- [ ] RL-based player personalization

---

## License

MIT

---

*Valence Mirage — Freedom is allowed but probability decides its cost.*
