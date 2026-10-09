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
│   ├── pacing.py              # Turn budgets: when beats finish and fights happen
│   ├── progression.py         # Milestone XP, level-ups, story-scaled enemy tier/threat
│   ├── enemy_designer.py      # Names enemies from the scene, stats from archetype presets
│   ├── intent_parser.py       # Action classification (8B)
│   ├── narrator.py            # Story narration (70B) + pacing directives + epilogue
│   ├── combat_engine.py       # Turn-based combat resolution
│   ├── npc_engine.py          # Dynamic NPC generation + dialogue
│   ├── engagement_tracker.py  # Per-turn signal + EMA profile update
│   ├── encounter_tuner.py     # Profile-aware encounter difficulty
│   ├── probability.py         # Weighted scoring + sigmoid normalization
│   ├── dice.py                # d20 resolution, 5 outcome tiers
│   └── state_manager.py       # Player/session state tracking
├── models/
│   ├── character.py           # Classes, abilities (4/class), starting gear
│   ├── combat.py              # Combat models + StatusEffectType registry
│   ├── game_state.py          # Player, session, turn models
│   ├── action.py              # ActionIntent model
│   ├── outcome.py             # Outcome types
│   ├── profile.py             # PlayerProfile + TurnSignal + SessionMetrics
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
│   ├── narrator.txt           # Exploration narration prompt (incl. STORY PACING rules)
│   ├── epilogue.txt           # The campaign's ending after the final fight
│   └── combat_narrator.txt    # Combat narration prompt
└── static/
    └── index.html             # Built React UI (Vite output)
frontend/
├── index.html                 # Vite entry point
├── vite.config.js             # Build config (outputs to backend/static)
├── src/
│   ├── main.jsx               # React root
│   ├── AppRouter.jsx           # React Router + auth context (8 routes)
│   ├── App.jsx                # Layout + theme manager + campaign hydration
│   ├── api.js                 # Backend API wrapper + auth headers
│   ├── pages/
│   │   ├── LoginPage.jsx       # Dark fantasy login
│   │   ├── DashboardPage.jsx   # User stats + campaign history
│   │   ├── GamePage.jsx        # Campaign route (/:id hydration or new session)
│   │   ├── AboutPage.jsx       # Game description
│   │   ├── ProfilePage.jsx     # Player engagement profile
│   │   ├── CampaignHistoryPage.jsx  # Campaign list
│   │   └── CampaignDetailPage.jsx   # Turn-by-turn history
│   ├── hooks/
│   │   └── useGame.js          # Core game state hook
│   ├── components/
│   │   ├── ConnectOverlay.jsx  # Session creation
│   │   ├── ChatArea.jsx        # Narrative log
│   │   ├── Sidebar.jsx         # Stats/inventory/NPCs
│   │   ├── InputArea.jsx       # Action input
│   │   ├── NarrativeCard.jsx   # Modal narration + typewriter + chunking
│   │   ├── CombatOverlay.jsx   # Full combat engine + cinematics
│   │   ├── FloatingHUD.jsx     # Stats + "Chapter X of Y" story progress
│   │   ├── LevelUpBanner.jsx   # Announces level-ups (role="status")
│   │   ├── LoadingOverlay.jsx  # Fullscreen loading spinner
│   │   ├── Navbar.jsx          # Persistent top navigation
│   │   ├── SettingsPanel.jsx   # TTS/animation/speed controls
│   │   └── CampaignEndOverlay.jsx
│   └── utils/
│       ├── tts.js              # Browser SpeechSynthesis
│       ├── typewriter.js        # Character-by-character reveal
│       ├── chunker.js           # Smart narration splitting
│       ├── combat.js            # Pure combat resolution (player actions, payloads)
│       ├── combatRules.js       # Dice + status effect registry (mirrors the backend)
│       ├── enemyAI.js           # Enemy behavior by type: planned moves + reactions
│       ├── combatFlavor.js      # Story lines for the fight log, taunts, icons
│       ├── storyProgress.js     # Chapter / act labels for the HUD
│       ├── progression.js       # XP badge + level-up summaries
│       └── theme.js             # Dynamic theming + ambience
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3, FastAPI, Uvicorn |
| Frontend | React + Vite + React Router (dark fantasy immersive UI) |
| Auth | JWT (python-jose), bcrypt (passlib) |
| AI — Intent Parsing | Llama 3.2 11B Vision Instruct (NVIDIA NIM) |
| AI — Narration | Llama 3.2 11B Vision Instruct (NVIDIA NIM) |
| AI — Embeddings | NV-EmbedQA-E5 (NVIDIA NIM) |
| Vector Search | ChromaDB |
| Storage | SQLite (aiosqlite) |
| Reliability | 30-60s request timeouts, 2 retry attempts max (4s backoff) |

---

## Project Status

**v0.6.2 — Active Development**

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
| 4 | RL Engagement Tracker (personalization) | ✅ Complete |
| 5 | Multi-page Router + Campaign Persistence | ✅ Complete |

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

#### 5. Run in Development Mode

**Start Backend Server:**
In the `backend/` directory, activate the virtual environment, install dependencies, and start the development server using `uvicorn`:
```powershell
# Windows
cd backend
.\venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```
```bash
# macOS/Linux
cd backend
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

**Start Frontend Client:**
In the `frontend/` directory, install dependencies and start the Vite development server:
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

#### 6. Run in Production Mode

Build the frontend static assets and export them directly to the backend:
```bash
cd frontend
npm run build
```
Once built, start the backend server from the `backend/` directory:
```bash
cd backend
python main.py
```
Open [http://localhost:8000/static/](http://localhost:8000/static/) in your browser.

#### 7. Run the Tests

The backend suite runs offline (language-model calls are faked, the database is a temporary SQLite file):
```powershell
cd backend
.\venv\Scripts\activate
pip install -r requirements-dev.txt
python -m pytest
```
Live checks against a running server and the real model are opt-in:
```powershell
$env:VM_LIVE_BASE_URL = "http://localhost:8000"
python -m pytest -m live
```
Frontend unit tests use Node's built-in test runner:
```bash
cd frontend
npm test
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/session/new` | Create session (class, size, keywords). Guests receive a one-time `guest_token` |
| `POST` | `/session/{id}/action` | Submit player action |
| `POST` | `/session/{id}/combat/resolve` | Submit combat result (validated against the stored encounter) |
| `GET` | `/session/{id}/combat` | Get combat state |
| `GET` | `/session/{id}/history` | Get turn history (`?limit=1-500`, default 20) |
| `GET` | `/session/{id}` | Get session state |
| `GET` | `/sessions` | List your sessions (login required; admins see all) |
| `DELETE` | `/session/{id}` | Delete a session |
| `POST` | `/auth/login` | Login (JWT) |
| `POST` | `/auth/create-user` | Admin: create user |
| `POST` | `/auth/tester-request` | Request tester access |
| `GET` | `/user/me` | Get current user |
| `GET` | `/user/dashboard` | User dashboard data |
| `GET` | `/session/{id}/hydrate` | Full state for frontend hydration |
| `GET` | `/health` | Server status |

### Session Access

Every `/session/{id}/...` route checks who is asking:

- **Logged in:** send `Authorization: Bearer <token>`. Sessions you create are yours; other accounts get `404`.
- **Guest:** `/session/new` returns a `guest_token` once. Send it back as `X-Session-Token` on every call for that session (the web app stores it per session in `localStorage`).
- **Admin:** can open every session.
- An invalid or expired Bearer token on `/session/new` returns `401` instead of silently creating a guest session.

Sessions saved before ownership existed are assigned on startup: to the user stored with the session if that account exists, otherwise to `admin`.

### Combat Resolution

Fights run in the browser; the server stores the encounter when it starts and checks the result:

```json
POST /session/{id}/combat/resolve
{
  "combat_id": "…",                  // must match the active fight (else 409)
  "result": "victory",               // "victory" | "defeat"
  "player_hp": 41,                   // ≤ max HP; a defeat must be 0
  "player_mana": 30,                 // ≤ starting mana + mana restored by items_used
  "enemy_name": "Security Drone",    // must match the stored enemy (else 400)
  "items_used": ["Health Potion"],   // consumables you carry; removed from your inventory
  "combat_log": [],
  "turns_taken": 5                   // a victory needs enough turns to deal the enemy's HP
}
```

XP and loot always come from the stored encounter, and each fight can be resolved once (a repeat gets `409`). Resolution is serialized with an in-process lock per session, so run a single server worker.

A fight counts as one campaign turn. Besides HP, mana, rewards and narration, the response carries `turn_number`, `current_beat`, `story_progress`, `xp_gained` (fight XP, plus the beat's XP when the fight finishes it) and `level_up`. Winning the final fight returns the campaign's epilogue as `narration`, `choices: []` and `pending_outcome: {"type": "victory"}`.

### Story, XP and Combat Fields

| Where | Field | Meaning |
|-------|-------|---------|
| `/session/new`, `/action`, `/combat/resolve`, `/hydrate` | `story_progress` | `{chapter, total, act_id, act_title, beat_title, beat_type, threat_hint, final, next_beat_title, next_beat_type}` (`null` without an outline) |
| `/action`, `/combat/resolve` | `xp_gained` | All XP the turn earned |
| `/action`, `/combat/resolve` | `level_up` | One entry per level gained: `{level, reason, hp_gain, mana_gain, stats, max_hp, max_mana}` |
| combat payload (`combat_data`) | `genre`, `scene` | The campaign's setting (`fantasy` / `scifi` / `postapoc`) and the narration that set up the fight (no choice lines, ≤ 400 characters) |
| combat payload | `enemy.archetype`, `enemy.threat` | How the enemy fights (brute, soldier, …) and how dangerous it is (standard, elite, boss) |
| combat payload | `enemy.abilities[].target` | `"player"` or `"self"` (rage and other self-buffs) |
| combat payload | `player.character_class` | For the class icon on the fight screen |

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

| Size | Acts | Beats | Fights | Turns | Best For |
|------|------|-------|--------|-------|---------|
| ⚡ Short | 2 | 5 | 3 | 8–10 | Quick adventures |
| 🗺️ Standard | 3 | 8 | 5 | 13–15 | Standard quest |
| 📖 Grand Saga | 4 | 13 | 7 | 20–25 | Epic saga |

The AI writes the story, but the structure always comes from the template: if the model returns too few, too many or mistyped beats, the outline is conformed to the template (keeping the model's titles and descriptions where the beat types match). Fights escalate, the second-to-last fight is against an elite lieutenant, and the last fight is always the climax against the campaign's central threat.

Every beat has a turn budget (story beats 1–2 turns, a fight beat exactly 2: the turn the enemy appears plus the fight), and the beat budgets add up to the size's turn range.

### Pacing

`engines/pacing.py` keeps every campaign inside its turn range:

- A story beat finishes when an action moves it on (a successful or narrative action that engages with the scene). It can't finish before it has had its minimum turns or before its *window* opens (the sum of the earlier beats' minimums).
- A beat that runs out of turns is wrapped up on that turn, even if the player was wandering.
- A fight beat is a lead-in turn (the narrator introduces the enemy) followed by the fight itself. Winning the fight finishes the beat; winning the final fight ends the campaign in victory.
- Combat tension can start a surprise fight only where the budget has room: never on a fight beat, never on the beat right before a planned fight, never in the final act, and at most once per act. In practice that means surprise fights are rare and only happen early in a Grand Saga.
- Sessions saved before turn budgets existed play on with their old outline; beats without budgets count as 1–2 turns (2 for fights).

The narrator gets a **STORY PACING** section on every turn: chapter N of M, the act, the current and next beat, and one instruction for this turn (develop the beat, resolve it, wrap it up now, introduce the enemy, or the final confrontation with the central threat). Winning the final fight produces an epilogue (`prompts/epilogue.txt`) with no further choices. The HUD shows "Chapter X of Y · Act N" with a progress bar.

---

## Leveling

XP comes from playing the story, not from dice luck (`engines/progression.py`):

| Source | XP |
|--------|----|
| Every story turn (any roll result) | 5 |
| Finishing a beat | 20, +5 for each act after the first |
| Winning a fight | tier base (25 / 35 / 45 / 60 / 80 for tiers 1–5) × threat (minion 0.5, standard 1, elite 1.5, boss 2.5) |

| Level | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|-------|---|---|---|---|---|---|---|
| Total XP | 100 | 230 | 400 | 600 | 800 | 1050 | 1350 |

Each level-up adds +1 to the class's primary stat (and +1 to its secondary stat on even levels), raises max HP (Warrior +8, Cleric +7, Rogue +6, Bard +6, Wizard +5) and max mana (Wizard +8, Cleric +7, Bard +7, Rogue +5, Warrior +3), and restores 30% of both. Sessions saved under the old XP curve are moved onto this one when they load.

Enemy strength follows the story rather than the player's level: the tier rises from 1 to 2 (Short), 3 (Standard) or 4 (Grand Saga) as the campaign progresses, the final fight is always the boss, hinted beats are elite, and everything else (including surprise fights) is standard. A Short campaign ends around level 3, a Standard one around level 4 and a Grand Saga around level 6.

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
| 💢 Empowered | Outgoing damage ×1.5 (enemy rage, frenzy, a boss's second phase) | 2 turns |

Older effect names used by early enemy templates and saved fights (`bleeding`, `stunned`, `weakened`, `frightened`, `blessed`) map onto the current ones, and every enemy ability carries a `target` (`player`, or `self` for buffs). Constructs are immune to bleed and poison; the undead are immune to poison. A stun on the player now costs them their next turn.

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

### Enemy Behavior

Each enemy plans its next move one turn ahead, shown on its card as **Next: …** (⚠ marks a big hit). It may change that plan in reaction to what the player just did, and the card updates before it acts (`frontend/src/utils/enemyAI.js`):

| Type | Behavior |
|------|----------|
| 👹 Brute | Winds up a ×1.75 blow every third turn. A stun cancels it; blocking or dodging halves it. |
| 🛡️ Soldier | Steady, precise attacks. Answers a player buff by weakening them; raises a guard when hurt. |
| 🗡️ Skirmisher | A flurry of two quick hits (60% each) and bleeding cuts. |
| 🐺 Beast | Pounces to stun (never twice in a row); frenzies once below half HP. |
| 🔮 Caster | Hexes (weaken, no damage) and blasts; once at ≤40% HP it shields itself, or heals if desperate. |
| 🤖 Construct | Charges up, then an overcharged ×2 strike. A stun drains the charge. |
| 💀 Undead | Drains life, healing half the damage it deals. |
| 👁️ Horror | Dread (weaken) and rend (bleed). |

Elites rally once at half HP (heal 20% and gain focus). Bosses hold their finisher back until half HP, then enter a second phase: a taunt, empowered for two turns, and the finisher every third turn. The server-side `CombatEngine` keeps its simpler AI; it isn't used in live play.

### Narration
Status effects are described narratively — never mechanically. "Blood trickles from the wound, refusing to clot" instead of "bleed for 3 turns (-2 HP/tick)".

The fight log reads like the story: a line that depends on the weapon, the enemy's type and the setting, followed by small numbers, e.g. "Sparks burst from the drone's chassis (−7)". A fight opens with the scene that led to it, the enemy's description and its taunt; enemies react again at half HP and when they fall, and no line repeats back to back. Only the story lines are sent to the server for the post-fight narration.

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
- [x] RL-based player personalization (contextual bandit + EMA)
- [x] Multi-page React Router with campaign persistence
- [x] Player profile page with engagement dimensions
- [x] Campaign history with turn-by-turn detail

---

## License

MIT

---

*Valence Mirage — Freedom is allowed but probability decides its cost.*
