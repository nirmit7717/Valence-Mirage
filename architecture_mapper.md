# Valence Mirage — Architecture & Codebase Map

This document serves as a comprehensive developer map for the Valence Mirage codebase. It outlines the responsibilities of each module in both the frontend and backend, explains how they interface, and catalogs the active bugs and architectural issues currently present in the system.

---

## 1. System Overview

Valence Mirage is an AI-powered role-playing game built on a decoupled Client-Server architecture:
- **Backend**: A Python **FastAPI** application serving as the gameplay engine, implementing RAG (Retrieval-Augmented Generation) rule grounding, state persistence (SQLite), dynamic NPC dialogue, mathematical success calculations, and turn-based combat.
- **Frontend**: A **React + Vite** single-page application (SPA) styled with custom CSS and featuring an interactive interface for custom character setups, real-time dice rolls, dynamic HUD bars, and a multi-tiered menu-driven combat screen.

---

## 2. Backend Architecture (`/backend`)

The backend codebase is modularized into data models, operational engines, data loaders, and routing files.

### 2.1 Core API & Server Integration
- **[main.py](file:///w:/Projects%20Antigravity/Valence%20Mirage/backend/main.py)**: The central application entrypoint.
  - Configures FastAPI app lifespan, CORS middlewares, and mounts the compiled frontend at `/static`.
  - Exposes authentication endpoints (`/auth/register`, `/auth/login`, `/auth/tester-request`).
  - Implements the core gameplay routing loop (`/session/new`, `/session/{id}/action`, `/session/{id}/combat/resolve`).
  - Manages database lifecycle connections and loads/persists sessions on startup and shutdown.
- **[auth.py](file:///w:/Projects%20Antigravity/Valence%20Mirage/backend/auth.py)**: Cryptographic and security operations.
  - Implements password hashing and verification using `cryptcontext` (bcrypt).
  - Handles JWT creation, signature decoding, and validation using `python-jose`.
  - Establishes dependency functions for route protection (`require_auth`, `require_admin`).
- **[config.py](file:///w:/Projects%20Antigravity/Valence%20Mirage/backend/config.py)**: Global configurations and constants.
  - Environment variable loaders (NVIDIA NIM APIs, database URLs).
  - Configures game rules, weights for success checks, dice mechanics, and JWT parameters.
- **[database.py](file:///w:/Projects%20Antigravity/Valence%20Mirage/backend/database.py)**: SQLite persistence layer using `aiosqlite`.
  - Manages schemas for `sessions`, `turns`, `users`, `tester_requests`, `campaign_history`, and `player_profiles`.
  - Implements CRUD actions to read and write active game sessions, history logs, and profile records.

### 2.2 Game Models (`/backend/models`)
Represent raw structured data and enforce Pydantic type validation.
- **[action.py](file:///w:/Projects%20Antigravity/Valence%20Mirage/backend/models/action.py)**: Structured schema for player action intents (`ActionIntent`) parsed by the LLM.
- **[character.py](file:///w:/Projects%20Antigravity/Valence%20Mirage/backend/models/character.py)**: Game definition templates for Warrior, Rogue, Wizard, Cleric, and Bard classes, including starting items and class skills.
- **[combat.py](file:///w:/Projects%20Antigravity/Valence%20Mirage/backend/models/combat.py)**: Core state structures representing the combat log, active combatants (players and enemies), and ongoing status effects.
- **[game_state.py](file:///w:/Projects%20Antigravity/Valence%20Mirage/backend/models/game_state.py)**: The structural representation of a single active game session (`GameSession`, `PlayerState`, `Item`, `Turn`).
- **[outcome.py](file:///w:/Projects%20Antigravity/Valence%20Mirage/backend/models/outcome.py)**: Structures parsing action success probabilities, stat changes, and dice modifier breakdowns.
- **[profile.py](file:///w:/Projects%20Antigravity/Valence%20Mirage/backend/models/profile.py)**: RL (Reinforcement Learning) profiling metrics tracking player affinity values (combat, exploration, social, risk, pacing) and adjusting campaign planners dynamically.
- **[user.py](file:///w:/Projects%20Antigravity/Valence%20Mirage/backend/models/user.py)**: Schemas validating auth request payloads.

### 2.3 Gameplay Engines (`/backend/engines`)
Responsible for game state state transitions, algorithmic computations, and AI integrations.
- **[campaign_planner.py](file:///w:/Projects%20Antigravity/Valence%20Mirage/backend/engines/campaign_planner.py)**: AI-driven campaign generation. Organizes story flows into Acts and Beats based on size templates, generating narrative content for each beat.
- **[combat_engine.py](file:///w:/Projects%20Antigravity/Valence%20Mirage/backend/engines/combat_engine.py)**: The turn-by-turn combat controller. Resolves damage math, resource costs, status ticks, and victory rewards (loot, XP, levels).
- **[deviation.py](file:///w:/Projects%20Antigravity/Valence%20Mirage/backend/engines/deviation.py)**: Computes semantic distance between player actions and current story beats. Triggers warning overlays if a player attempts irrelevant actions.
- **[dice.py](file:///w:/Projects%20Antigravity/Valence%20Mirage/backend/engines/dice.py)**: Simulates physical $d20$ rolls and matches outcomes to D&D thresholds (Crit Success, Success, Partial, Failure, Crit Failure).
- **[encounter_tuner.py](file:///w:/Projects%20Antigravity/Valence%20Mirage/backend/engines/encounter_tuner.py)**: Automatically scales enemy stats and sizes to fit player levels and combat capabilities.
- **[engagement_tracker.py](file:///w:/Projects%20Antigravity/Valence%20Mirage/backend/engines/engagement_tracker.py)**: Updates player profile metrics after sessions using Exponential Moving Averages (EMA).
- **[intent_parser.py](file:///w:/Projects%20Antigravity/Valence%20Mirage/backend/engines/intent_parser.py)**: High-speed LLM interface that parses player chat text into structured `ActionIntent` classes.
- **[narrator.py](file:///w:/Projects%20Antigravity/Valence%20Mirage/backend/engines/narrator.py)**: Creative LLM interface that generates immersive descriptions of action outcomes, using retrieved D&D rules as groundings.
- **[npc_engine.py](file:///w:/Projects%20Antigravity/Valence%20Mirage/backend/engines/npc_engine.py)**: Handles social mechanics. Simulates NPC dialog based on disposition states, trust levels, and player negotiation tactics.
- **[probability.py](file:///w:/Projects%20Antigravity/Valence%20Mirage/backend/engines/probability.py)**: Computes odds of action success based on stats, difficulty ratings, resource usage, and narrative similarity bonuses.
- **[state_manager.py](file:///w:/Projects%20Antigravity/Valence%20Mirage/backend/engines/state_manager.py)**: Core controller applying health/mana updates, leveling metrics, and inventory additions to the memory-persisted `GameSession` structures.

### 2.4 Retrieval-Augmented Generation (`/backend/rag`)
- **[vector_store.py](file:///w:/Projects%20Antigravity/Valence%20Mirage/backend/rag/vector_store.py)**: Embeds game rules and stores them locally inside collections managed by **ChromaDB**.
- **[retriever.py](file:///w:/Projects%20Antigravity/Valence%20Mirage/backend/rag/retriever.py)**: Fetches contextual game rule chunks from ChromaDB matching player action strings.
- **[embeddings.py](file:///w:/Projects%20Antigravity/Valence%20Mirage/backend/rag/embeddings.py)**: Accesses Nvidia embedding models to translate text blocks into vector matrices.

---

## 3. Frontend Architecture (`/frontend`)

The frontend is a React Single Page Application utilizing a declarative router, contextual global states, and modular layouts.

### 3.1 Routing & Global States
- **[main.jsx](file:///w:/Projects%20Antigravity/Valence%20Mirage/frontend/src/main.jsx)**: Entrypoint initializing the React DOM tree.
- **[AppRouter.jsx](file:///w:/Projects%20Antigravity/Valence%20Mirage/frontend/src/AppRouter.jsx)**:
  - Manages browser pathways (`/login`, `/dashboard`, `/new`, `/campaign/:id`, etc.).
  - Binds the app to `/static` base paths.
  - Implements the React `AuthContext` protecting user routes.
- **[api.js](file:///w:/Projects%20Antigravity/Valence%20Mirage/frontend/src/api.js)**: A structured utility layer containing all outbound backend HTTP requests (`fetch` wrappers forwarding authorization headers).
- **[hooks/useGame.js](file:///w:/Projects%20Antigravity/Valence%20Mirage/frontend/src/hooks/useGame.js)**: The core game client state machine.
  - Manages session ids, sidebar statistics, chat messaging logs, loading states, and theme modifiers.
  - Orchestrates dice roll animations and processes action outcomes, loot, level-ups, and combat transitions.

### 3.2 UI Components (`/frontend/src/components`)
- **CombatOverlay.jsx**: Highly interactive combat screen. Controls HP/Mana meters, action queues, class skill lists, inventory selection menus, and turn confirmations.
- **DiceRoll.jsx**: Controls custom animations showing visual dice physics during roll checks.
- **FloatingHUD.jsx**: An overlay showing character specs, active stats, and current level details.
- **NarrativeCard.jsx**: Renders narration output, choices, and formats dialogue bubbles.
- **Navbar.jsx**: Top navigation bar displaying profile links, routes, and logout actions.
- **Sidebar.jsx**: The left sidebar rendering the player character's inventory and active status effects.
- **ConnectOverlay.jsx**: Overlay displaying class selectors and keyword configuration menus.
- **CampaignEndOverlay.jsx**: Victory or loss displays triggered upon campaign resolution.

### 3.3 Layout Views (`/frontend/src/pages`)
- **LoginPage.jsx**: Contains fields for login and request-invite submissions.
- **DashboardPage.jsx**: Core panel to resume active sessions, create new games, or review campaign history.
- **CampaignHistoryPage.jsx**: Lists completed campaigns and classes played.
- **ProfilePage.jsx**: Renders stats and RL-derived affinity metrics (combat vs social ratio).
- **RolePage.jsx**: Renders descriptions and lore for selectable character classes.

---

## 4. Issues Discovered in Codebase

During analysis, the following codebase issues were identified. Note that these have **not** been modified or fixed, per instruction:

### Issue A: Missing Core Backend Dependencies
In **`backend/requirements.txt`**, several external libraries imported by `auth.py` and the engine layers are not declared:
1. **`python-jose`**: Imported via `from jose import JWTError, jwt` inside `backend/auth.py`. Since it is not in the requirements file and is not installed in the virtual environment, the server immediately crashes with a `ModuleNotFoundError: No module named 'jose'` on startup.
2. **`passlib`**: Imported via `from passlib.context import CryptContext` inside `backend/auth.py`. 
3. **`bcrypt`**: Required as an underlying hashing algorithm driver for `passlib` to support `"bcrypt"` hashing schemes. Without it, `passlib` will throw a runtime scheme configuration error.

### Issue B: Undefined Database Attribute in `database.py`
In **`backend/database.py`**, both the `load_profile` (Line 348) and `save_profile` (Line 371) methods attempt to open direct database connections using:
```python
async with aiosqlite.connect(self.db_path) as db:
```
- **Error**: The `Database` class has no member attribute named `self.db_path`. The local database path is configured in a global module constant named `DB_PATH`. 
- **Consequence**: Calling either method immediately results in a runtime crash: `AttributeError: 'Database' object has no attribute 'db_path'`.
- **Architectural Discrepancy**: All other database CRUD functions in `database.py` run queries directly on `self.db` (the shared class connection pool). `load_profile` and `save_profile` should also leverage `self.db` instead of trying to open concurrent database connections.

### Issue C: Missing Production Frontend Asset Files
In **`backend/static/index.html`** (Lines 7 and 8), the pre-compiled file references static javascript and css assets directly:
```html
<script type="module" crossorigin src="/static/assets/index-DbiugjHi.js"></script>
<link rel="stylesheet" crossorigin href="/static/assets/index-Bhv05D0p.css">
```
- **Error**: The `backend/static/` directory does not contain an `assets/` folder, and the referenced compiled assets `index-DbiugjHi.js` and `index-Bhv05D0p.css` are completely missing from the directory.
- **Consequence**: If a developer launches the backend server and navigates to the default URL, they will receive a blank screen with a 404 response on the javascript and css sources. The frontend must be built (via `npm run build` in the `frontend` directory) to populate the `backend/static` directory.
