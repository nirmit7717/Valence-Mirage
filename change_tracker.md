# Valence Mirage: Change Tracker

This document tracks all significant architectural improvements, feature additions, and bug fixes.

---

## v0.5.0 — React UI Overhaul & Immersion System (2026-04-27)

### 🏗️ Architecture: Vanilla JS → React SPA
- **Full React rewrite**: Converted the entire frontend from a single 1200-line HTML file to a modular React + Vite SPA
- **Component-based**: 9 components, 1 custom hook, 5 utility modules
- **Build system**: Vite builds to `backend/static/`, zero backend changes required
- **Old UI preserved**: `index.old.html` backed up in static directory

### 📜 NarrativeCard System (Feature #1, #2)
- **Modal overlay card** for narrations with fade/slide transitions
- **Escape/click-outside to dismiss**
- **TTS toggle button** in card header
- **Choices rendered as styled buttons** inside the card
- **Continue button** for non-choice narrations

### ⌨️ Typewriter Animation (Feature #9)
- **Character-by-character text reveal** (~20ms per char, configurable)
- **Click to skip** — instantly reveals full text
- **Auto-skip for long text** (>800 chars)
- **TTS starts immediately**, does not wait for typing
- **Speed adjustable** via Settings Panel (5–50ms)

### 📖 Smart Narration Chunking (Feature #11)
- **Splits long narrations** (>450 chars) into logical segments
- **Paragraph-first splitting**, sentence-level fallback
- **Sequential display**: chunk → Continue → next chunk → ... → choices
- **Chunk indicator** (e.g. "— 2 / 4 —")
- **Client-side only**, no backend changes

### 🔊 Text-to-Speech (Feature #3)
- **Browser SpeechSynthesis API** with HTML stripping
- **Chunked speaking** at sentence boundaries (200-char chunks)
- **Cancels previous speech** before new narration
- **Toggle from Settings Panel or NarrativeCard header**

### 🎨 Dynamic Background Theming (Feature #4, #12)
- **10 theme mappings**: fantasy, dark_fantasy, horror, sci_fi, desert, forest, ocean, underdark, mountain, ruins
- **Auto-detected** from campaign keywords, setting, title, premise
- **Smooth CSS transitions** (1.2s gradient fade)
- **Ambient animations**: subtle brightness/saturation pulses per theme

### ⏳ Loading Overlay (Feature #5)
- **Fullscreen semi-transparent overlay** with spinner
- **Randomized flavor text** ("The dice are rolling...", "Fate stirs...")
- **Blocks all clicks** during API calls

### ⚔️ Combat Cinematic Effects (Feature #10)
- **Screen flash**: white/yellow for crits, blue for misses, red for hits
- **Duration < 300ms** — subtle and fast
- **Detection from combat log** keywords
- **Toggle-able** via Settings Panel

### ⚙️ Settings Panel (Feature #13)
- **Fixed bottom-right gear icon**
- **Controls**: TTS on/off, Animations on/off, Text speed slider

### 🛡️ Performance Safeguards (Feature #14)
- **Typewriter cancels cleanly** on new narration
- **TTS cancels before new speech** — no queue buildup
- **No memory leaks**: all intervals/timeouts cleaned up

---

## 🛠️ Gameplay Mechanics & Pacing
- **Forced Pacing System**: Implemented `turns_since_roll` and `turns_in_beat` counters. The system now automatically forces an obstacle or combat encounter if the player avoids risky actions for more than 4 turns.
- **Narrative Beat Advance**: Standardized the progression of story beats based on turn thresholds and success outcomes to ensure the campaign follows the intended arc.
- **NPC Generation Cleanup**: Removed the "blind" generation of non-contextual NPCs at session start. Characters now emerge naturally through the story beats.
- **Campaign Conclusion Lifecycle**: Added a definitive end-state detection. When the final beat of the final act is cleared, the system signals completion.

## ⚔️ Combat UI Overhaul (Expedition 33 Style)
- **Three-Tier Menu System**: Replaced the flat list of combat abilities with a structured sub-menu layout:
  - **Attack**: Dynamically filters inventory for weapons.
  - **Skill**: Displays class-specific mana abilities.
  - **Items**: Lists consumables like health/mana potions.
- **Improved UI Centering**: Moved the `#combatOverlay` from the nested grid to the root level of the DOM to ensure stable, absolute centering on all screen sizes.
- **Go Back Functionality**: Integrated navigation buttons for all combat sub-menus to allow fluid selection.
- **Concurrency Mutex**: Implemented a `busy` lock in Javascript to prevent players from double-clicking actions while the API is still processing the previous turn.

## 🏆 UI & Experience Enhancements
- **Campaign Concluded Modal**: Created a full-screen victory modal with a summary of the journey and a "Start New Adventure" reset button.
- **Inventory & Stats Integration**:
  - Removed "Rusty Sword" default to ensure inventory only contains relevant items.
  - Mapped items and weapons to the combat action endpoint so they correctly affect damage and healing.

## 🐛 Bug Fixes & Stability
- **ActionResponse Pydantic Validation**: Fixed a catastrophic 500 error where `campaign_ended` was being passed but was missing from the backend model schema.
- **Stat Attribute Typo**: Fixed a NameError where `stat_used` was incorrectly referenced instead of the valid `relevant_stat` field in the forced encounter logic.
- **Combat Data Payload Fix**: Resolved an issue where combat would "silently fail" because the `combat_data` JSON was not being assigned to the API response during automated ambushes.
- **Zombie Process Cleanup**: Resolved a port conflict where orphaned Python processes were holding Port 8000 hostage, preventing new server instances from binding.

---

## v0.4.1 — Combat System Overhaul & Pacing Fix (2026-04-25)

### 🔥 Local Combat Resolution (Client-Side Engine)
- **Complete JS Combat Engine**: All combat resolution now happens entirely in the browser:
  - d20 rolls, damage calculation (dice notation parser), status effects, enemy AI
  - Player actions (Attack/Skill/Item) resolve instantly with no API calls
  - Enemy turn executes locally after player action
  - Only the final result (victory/defeat) is sent to backend for narration + state sync
- **New Endpoint**: `POST /session/{id}/combat/resolve` — accepts final combat result, handles XP, loot, HP/mana sync, beat advancement, and post-combat narration
- **Removed**: Per-action `POST /session/{id}/combat/action` API calls (no longer needed)
- **Removed**: Flee button from combat UI (player must fight through encounters)
- **Expedition 33-Style Polish**:
  - Floating damage numbers with animations (color-coded: red for damage, green for healing, yellow for crits)
  - Hit flash + shake animations on entity cards
  - Smooth combat enter/exit transitions
  - Turn indicator (YOUR TURN / ENEMY TURN)
  - Combat log with color-coded entries and slide-in animation
  - Back buttons on all sub-menus for fluid navigation

### ⏱️ Separate Forced Encounter & Combat Timers
- **Forced Probabilistic Roll**: Triggers every **3 narrative turns** without a roll (`turns_since_roll >= 3`)
- **Forced Combat Encounter**: Triggers every **5 narrative turns** without combat (`turns_since_combat >= 5`)
- **Independent Counters**: Both timers run independently — a forced roll doesn't reset the combat timer and vice versa
- **Guaranteed Engagement**: Ensures both dice mechanics AND combat encounters happen regularly throughout any campaign size

### 📐 Campaign Size-Based Gameplay Loop
- **Strict Beat Completion**: Campaign ends only after ALL beats in the template are completed
- **Robust Completion Check**: `_is_campaign_complete()` detects both "past the end" and "on the final beat after advancing" cases
- **Beat Advancement Fix**: Uses "advance then check if position changed" pattern to correctly detect final beat completion
- **Campaign End Guard**: Actions are rejected after campaign ends (returns 400 error)
- **Pacing per Size**:
  - Small (6 beats): Forced roll every 3 turns, combat every 5 turns → ~2 combats in 15 turns
  - Medium (10 beats): Forced roll every 3 turns, combat every 5 turns → ~4 combats in 25 turns
  - Large (16 beats): Forced roll every 3 turns, combat every 5 turns → ~6 combats in 35 turns

### 🔧 Backend Improvements
- **Combat Data Enrichment**: `combat_data` payload now includes `attack_bonus`, `armor`, `enemy_tier`, `abilities`, and full `inventory` for client-side resolution
- **Forced Combat Path**: When `turns_since_combat >= 5`, combat auto-initiates with a quick ambush narration regardless of beat type
- **Enemy Tier Scaling**: Enemy tier scales with player level (`min(5, max(1, player_level))`)
- **Version bumped**: v0.3.0 → v0.4.0

### 🐛 Post-Release Fix (2026-04-25)
- **Forced Combat Priority Fix**: When both forced roll (3 turns) and forced combat (5 turns) triggered simultaneously, the combat block would conditionally fall through to the roll path — causing the ambush narration to be overwritten and `combat_started` to be `False` despite combat being initialized in session state. Now forced combat always returns immediately with ambush narration + combat data regardless of `intent.requires_roll` state.
- **Campaign Completion Detection Fix**: `advance_beat()` doesn't increment past the final beat, so the old `_is_campaign_complete()` check (which only checked `> max_beat`) never triggered. Updated to use "advance then check if position changed" pattern — campaign ends correctly when the final beat is completed.

---

## v0.6.0 — Game Logic Fixes & Dice Animation System (2026-04-28)

### 💀 Player Death Detection (Issue #1)
- **Backend**: `_check_player_death()` helper — detects HP ≤ 0 after state changes and after combat resolve
- **Death path**: Sets `game_over=true`, `campaign_ended=true`, `status="failed"`, returns death narration
- **Frontend**: `gameOver` state blocks all further input, CampaignEndOverlay shows red "💀 Fallen" screen
- **Combat death**: If player HP = 0 after combat, triggers game over (not just "defeat")

### 🎯 Campaign Objective (Issue #2)
- **Objective derived** from `blueprint.possible_endings[0]` or `blueprint.premise` at session creation
- **Stored in** `session.world_state["campaign_objective"]`
- **Passed in** every `ActionResponse` and combat resolve response
- **Displayed in** FloatingHUD sidebar as "🎯 Objective" section

### 🎭 Narrator Immersion Rules (Issue #3)
- **HP/mana replaced** with descriptive terms in narrator prompts:
  - HP: healthy / bruised and battered / wounded, blood running freely / at death's door, barely conscious
  - Mana: brimming with energy / moderately taxed / running thin, nearly spent / dangerously low
- **5 new IMMERSION RULES** in narrator prompt:
  - Never mention exact HP/mana numbers
  - Never use meta-language about choices ("you have 3 options")
  - Use descriptive language for physical state
  - End with natural prompts ("What will you do?")
- **Debug logging** for stat changes (`hp_delta`, `mana_delta`, trigger)
- **Combat defeat narration** no longer leaks HP numbers to LLM

### 🎲 Dice Roll Animation System (New Feature)
- **Backend `dice_result` field** in action responses:
  ```json
  { "rolled": 14, "target": 10, "success": true, "critical": false, "type": "attack" }
  ```
- **Only populated when a roll actually occurs** — never faked
- **DiceRoll component**: Full-screen overlay animation triggered BEFORE narration card
  - 12-frame number cycling (~1s), landing on actual roll value
  - Shows roll type (⚔️ Attack / ✦ Skill / 🔍 Check)
  - Success/failure/critical color coding (green/red/gold)
- **useGame flow**: API response → `dice_result` → animation → `onDiceAnimationComplete()` → process narration

### 🏳️ Clean Response Structure
- Every response now includes: `game_over`, `victory`, `campaign_objective`, `dice_result` (optional)
- All 3 return paths in action handler updated with new fields
- Combat resolve endpoint returns `game_over`, `victory`, `campaign_objective`

---

## v0.6.1 — Combat Dice Animation & Post-Combat Narration Fix (2026-04-28)

### ⚔️ Combat Dice Animation
- **Inline CombatDice component** in the combat arena
- Shows for every player attack, player skill, and enemy action
- Number cycling (~0.5s) → final roll → HIT/MISS/CRIT with color coding
- **Action lock** (`actionLockRef`) prevents double-clicks during animation
- **combat.js updated**: `resolvePlayerAttack`, `resolvePlayerSkill`, `resolveEnemyTurn` return `diceInfo` metadata
- No dice shown for item uses or support abilities (no roll involved)

### 📜 Post-Combat Narration Fix
- **Victory path**: Narration card now properly shows with choices extracted from arrow syntax (`→ ...`)
- **All paths** (victory/defeat/death) correctly set narration state for story continuation
- **Choices from backend** combat narration properly parsed and displayed as buttons

---
*Status: All changes verified, server tested, pushed to GitHub.*

---

## v0.7.0 — Combat Depth + Auth System + Stability (2026-04-28)

### ⚔️ Combat Depth System — Status Effects & Abilities

#### Status Effect Registry
- **Unified effect registry** (`STATUS_EFFECT_RULES`) in `models/combat.py` — defines behavior for every effect:
  - `bleed` — DoT: 2–4 damage/turn, 2–3 turns
  - `stun` — Skip next turn, 1 turn
  - `weaken` — Halve outgoing damage, 2 turns
  - `focus` — +5 to next d20 roll, 1 turn
  - Legacy effects preserved: poisoned, burning, blocking, healing, dodging, hidden
- **`StatusEffectType` enum** — canonical identifiers for all effects
- **`get_effect_rule()` lookup** — used by both engine and frontend
- **Non-stacking**: Reapplying refreshes duration (capped at `max_duration`), never stacks
- **Registry-driven frontend**: `combat.js` mirrors the backend registry identically

#### 6-Phase Turn Structure
Every combat turn now follows this formal order:
1. **Apply status effects** — DoT/HoT ticks, narrative log messages
2. **Can act?** — Stun check → skip turn if true
3. **Execute action** — attack/ability/flee
4. **Resolve dice roll** — d20 + roll modifiers (focus, stealth)
5. **Calculate damage** — base × damage modifier (weaken → ×0.5)
6. **Apply damage + update state** — dodge chance, HP update, effect application

#### Combat Engine Methods (New)
| Method | Purpose |
|--------|----------|
| `_apply_status_effects()` | Ticks all effects, returns narrative messages |
| `_can_act()` | Checks stun/skip-turn effects |
| `_get_damage_modifier()` | Multiplier from all effects on a combatant |
| `_get_roll_modifier()` | d20 bonus from all effects (focus, stealth) |
| `_get_armor_modifier()` | Armor bonus from effects (blocking) |
| `_get_dodge_chance()` | Dodge probability from effects (dodging) |
| `_apply_effect()` | Non-stacking effect application with duration cap |

#### Class Abilities (Refactored)
Each class now has **3 focused abilities** using the new effect types:
- **Warrior**: Power Strike (raw damage), Guard (blocking), Cleave (bleed)
- **Rogue**: Backstab (burst damage), Evade (dodging), Poison Blade (poisoned)
- **Wizard**: Arcane Bolt (mana damage), Focus Mind (focus buff), Lightning Bolt (stun)
- **Cleric**: Heal (HP restore), Smite (weaken), Holy Shield (blocking)
- **Bard**: Mock (weaken), Inspire (focus), Dissonance (raw damage)

#### Narration Constraints
- Added "STATUS EFFECTS IN NARRATION" section to `narrator.txt`
- Explicit prohibition against exposing mechanics ("applied bleed for 3 turns")
- Narrative description templates for each effect type

#### Frontend Display
- **Status pills** now show emoji icons per effect type: 🩸bleed, 💫stun, 📉weaken, 🎯focus, ☠️poison, 🔥burning, 🛡️blocking, 💨dodging
- **Color-coded pills** via CSS attribute selectors (bleed=red, stun=yellow, weaken=purple, focus=blue, etc.)
- **Effect tick messages** in combat log with icons
- **Dodge resolution** shown in combat log ("💨 You dodge Skeleton's Attack!")
- **Stun skip** shown when enemy or player is stunned ("💫 Skeleton is stunned and cannot act!")

### 🔐 Authentication & User Management

#### Backend
- **`auth.py`**: JWT authentication (python-jose), bcrypt password hashing (passlib)
- **`models/user.py`**: User + TesterRequest Pydantic models
- **`database.py`**: 3 new tables (users, tester_requests, campaign_history) + 8 new methods
- **`config.py`**: JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS (24h default)
- **Admin auto-creation** on startup: `admin`/`admin123` (override with `ADMIN_PASSWORD` env)
- **Auth routes**: `/auth/login`, `/auth/create-user` (admin), `/auth/tester-request`
- **User routes**: `/user/me`, `/user/dashboard`, `/user/logout`
- **Backward compatible**: Game routes accept JWT optionally — works with or without auth
- **`bcrypt==4.0.1`** pinned (passlib incompatibility with bcrypt 4.1+)

#### Frontend
- **`AppRouter.jsx`**: React Router with basename `/static`
- **`LoginPage.jsx`**: Dark fantasy split-layout login
- **`DashboardPage.jsx`**: User stats + campaign history
- **`GamePage.jsx`**: Game wrapper with optional auth check
- **`pages/auth.css`**: Dark fantasy themed auth pages
- **`api.js`**: `getAuthHeaders()`, new auth API functions, auth headers on all calls
- **`vite.config.js`**: Proxy `/auth` and `/user` routes
- **`react-router-dom`** added as dependency

### 🐛 Bug Fixes & Stability

| Issue | File | Fix |
|-------|------|-----|
| `NameError: 're' not defined` → 500 on session creation | `main.py` | Added `import re` |
| BrowserRouter missing `basename` → 404 on sub-routes | `AppRouter.jsx` | Added `basename="/static"` |
| Race condition: `busy` flag cleared during dice animation → duplicate actions | `useGame.js` | `busy` stays true until `onDiceAnimationComplete` |
| DiceRoll fires `onComplete` when `diceResult` is null → premature processing | `DiceRoll.jsx` | Guard: return early if no `diceResult`, removed from deps |
| `}}}` JSX syntax error in status effect rendering | `CombatOverlay.jsx` | Fixed double-closing brace |

### 📁 Files Changed

**New files:**
- `backend/auth.py`, `backend/models/user.py`
- `frontend/src/AppRouter.jsx`, `frontend/src/pages/LoginPage.jsx`, `frontend/src/pages/DashboardPage.jsx`, `frontend/src/pages/GamePage.jsx`, `frontend/src/pages/auth.css`

**Modified files:**
- `backend/models/combat.py` — StatusEffectType enum, STATUS_EFFECT_RULES registry, get_effect_rule()
- `backend/engines/combat_engine.py` — 7 new methods, 6-phase turn structure, removed _tick_effects
- `backend/models/character.py` — 3 abilities/class with new effect types
- `backend/main.py` — import re, auth routes, user routes
- `backend/database.py` — 3 tables, 8 methods for user management
- `backend/config.py` — JWT config fields
- `backend/prompts/narrator.txt` — Status effect narration constraints
- `frontend/src/utils/combat.js` — STATUS_RULES registry, 8 new exported functions, updated resolution functions
- `frontend/src/components/CombatOverlay.jsx` — Icon imports, status pill rendering with icons
- `frontend/src/index.css` — Per-effect color styling for status pills
- `frontend/src/api.js` — Auth headers, auth API functions
- `frontend/src/hooks/useGame.js` — Busy flag fix
- `frontend/src/components/DiceRoll.jsx` — Null guard fix
- `frontend/vite.config.js` — Auth proxy routes

---
*Status: All changes verified, server tested at http://localhost:8000.*

---

## v0.7.1 — Combat Enforcement + UI Polish + Campaign History (2026-04-30)

### ⚔️ Combat Mode Enforcement

#### Combat Tension Tracker
- Replaced flat `turns_since_combat >= 5` counter with context-aware `combat_tension` accumulator
- Tension accumulates based on action risk and story context:
  - +1 base per turn
  - +2 for risky actions (attack, cast_spell, intimidate)
  - +1 for hostile narration context (enemy, undead, ambush, etc.)
  - +1 when a combat beat is available
  - Threshold: 6 — triggers combat when reached
- Resets to 0 on combat start/resolution
- Enemy selection remains context-aware (narrator-driven + `_fallback_enemy()` guarantee chain)

#### Combat Auto-Activation (Frontend)
- **Root cause**: Combat data was stored in `narration.combatData` but `setCombat()` only fired on manual dismiss — if narration had choices (always does), combat never activated
- **Fix**: Auto-activate combat 2.5s after combat narration appears, regardless of choices
- `setCombat(createCombatState(combatData))` called from `_processResponse` directly

#### Combat Mode Guard (Backend)
- Added at top of `submit_action` — if combat is active, blocks all narrative processing
- Returns `outcome: "combat_active"` with full `combat_data` and combat choices `["Attack", "Use Ability", "Defend"]`
- Prevents combat from being bypassed by narrative actions

### 🎨 UI Polish

#### Sidebar Improvements
- Width increased from 160px → 220px for better readability
- Narrative card left-padding adjusted to match (80px → 120px)
- Turn counter added to HUD: `Level X · Turn Y`
- Removed `🎯 Objective` display from sidebar (breaks immersion — objective tracked internally only)

#### 4th Ability Per Class
- Added a 4th ability to every class for more tactical depth:
  - **Warrior**: War Cry (support, weaken 2 turns)
  - **Rogue**: Shadow Step (support, focus 1 turn)
  - **Wizard**: Arcane Shield (defend, blocking 1 turn)
  - **Cleric**: Purify (support, focus 1 turn)
  - **Bard**: Lullaby (support, stun 1 turn)
- Frontend maps all abilities dynamically (`state.abilities.map()`) — no hard limits

#### Navigation Fix
- Added "← Back to Dashboard" button to `ConnectOverlay` (new game screen)
- Uses `window.history.back()` for clean SPA navigation
- Styled as ghost button (doesn't compete with CTA)

### 💾 Campaign History Persistence

- **Root cause**: `save_campaign_history()` existed in database.py but was never called from main.py
- Added `_record_campaign_end()` helper with:
  - **Duplicate guard**: `campaign_saved` flag prevents double-saves
  - **Admin user fallback**: Sessions without auth use admin user for history
  - **Error recovery**: Clears `campaign_saved` on failure to allow retry
  - **Debug logging**: ✅/❌ prefixed messages
- Called at all 5 campaign-ending endpoints:
  - Deviation game-over (`lost_focus`)
  - Campaign victory — no-roll path (`victory`)
  - Player death — roll path (`defeat`)
  - Campaign victory — combat resolve (`victory`)
  - Player death — combat resolve (`defeat`)
- Session creation now extracts `user_id` from optional JWT
- Dashboard fetches and displays campaign history + stats

### 🐛 Bug Fixes

| Issue | File | Fix |
|-------|------|-----|
| Status effect crash: `se.get("name")` on `list[str]` | `main.py` | Safe `isinstance(se, dict)` check, handles str/dict/mixed/None |
| Combat never activated despite `combat_started=True` | `useGame.js` | Auto-activate combat from `combatData` with 2.5s delay |
| Narrative actions during combat | `main.py` | Combat Mode Guard returns `combat_active` with combat data |
| Campaign history never saved | `main.py` | `_record_campaign_end()` + calls at all 5 end points |
| No back button from new game screen | `ConnectOverlay.jsx` | Added cancel button with `onCancel` prop |
| SPA 404s on direct URL access | `main.py` | Replaced `StaticFiles` mount with SPA fallback route |

### 📁 Files Changed

**Modified files:**
- `backend/main.py` — Combat tension tracker, combat mode guard, status effect normalization, SPA fallback routing, `_record_campaign_end()`, user_id extraction, campaign history recording
- `backend/models/character.py` — 4 abilities/class (was 3)
- `backend/engines/probability.py` — `context_alignment` + `status_effect_modifier` params
- `backend/engines/deviation.py` — Campaign deviation evaluator
- `backend/models/outcome.py` — New ScoreBreakdown fields
- `backend/config.py` — New probability weights
- `frontend/src/hooks/useGame.js` — Auto-activate combat, turn counter, warning display
- `frontend/src/components/FloatingHUD.jsx` — Turn counter, removed objective
- `frontend/src/components/ConnectOverlay.jsx` — Back button
- `frontend/src/App.jsx` — `onCancel` prop for ConnectOverlay
- `frontend/src/index.css` — Sidebar width, padding, cancel button styles

**New files:**
- `backend/engines/deviation.py` — Campaign deviation tracking

---
*Status: All changes verified, server tested at http://localhost:8000.*

---

## v0.7.2 — System Coherence + Reliability Fixes (2026-05-04)

### 🎨 Dynamic Background Theming
- **`ui_context` field** added to `ActionResponse` — provides environment, tone, and enemy name per turn
- **Backend**: `_extract_ui_context()` extracts environment (forest/dungeon/city/ruins/mountain/ocean/desert/underdark/horror) and tone (calm/tense/combat/mystery) from narration keywords
- **Frontend**: Maps `ui_context.environment` → theme, updates body gradient dynamically every turn
- **Combat tone**: Auto-switches to horror/dark_fantasy themes during combat
- Background transitions smoothly (1.2s CSS transition already in place)

### ⚔️ Enemy Name Consistency
- **All 6 combat initiation points** now store `last_enemy_name` in `world_state`
- **`ui_context.enemy_name`** carries the tracked name in every response
- **Single source of truth**: narrator describes → `_extract_enemy_from_narration()` matches → stored in `world_state` → used in UI context

### 🔒 Input Validation Pipeline (redo_turn)
- **Major deviation** returns immediately with `redo_turn=True` — **does NOT call narrator** (saves API call)
- Frontend shows warning message, does NOT advance turn or change state
- Player can retry with a relevant action
- 3rd major deviation still triggers game over via `pending_outcome`
- **Kill switch**: `VALIDATION_ENABLED = True` flag — set to `False` to bypass all validation
- **Safe fallback**: `try/except` around evaluator — if it crashes, action is allowed through

### 🧠 Context Memory for Evaluation
- **Deviation evaluator** now accepts `turn_history` parameter
- Checks last 3 turns: player input overlap + narration overlap for richer alignment scoring
- `connection_found` flag aggregates from beat, narration, objectives, NPCs, AND turn history

### 🐛 Validation False Positive Fix
- **Root cause**: `always_valid` verb set was missing common combat verbs ("draw", "battle", "charge", "strike") and movement verbs ("run", "swim", "climb", "jump") — valid actions like "I draw my sword" were classified as `major` and blocked
- **Fix**: Expanded `always_valid` with combat verbs (draw, strike, slash, battle, engage, charge, retreat) and movement verbs (grab, open, push, pull, climb, jump, swim, run, walk)
- **Off-topic phrase detector**: Overrides verb matches for clearly modern/real-world inputs ("phone", "netflix", "pizza delivery", "income tax", etc.)
- Verified: combat actions → relevant, off-topic → major

### ⏱️ API Reliability Fixes
- **Explicit timeouts** on all OpenAI clients: narrator=60s, others=30s
- **Reduced retries**: max 2 attempts (was 3), max 4s backoff (was 8s)
- **Narrator `max_tokens`**: 500 (was 800) — reduces latency on slow responses
- **Worst case**: ~2 min total (was ~5 min on 504 timeout)

### 🎭 UI: Character Class in Sidebar
- FloatingHUD now shows class in header: `Warrior · Level 1 · Turn 3`

### 📁 Files Changed

**Modified files:**
- `backend/main.py` — `ui_context`, `VALIDATION_ENABLED` kill switch, try/except on evaluator, `redo_turn` response, enemy name tracking at all 6 combat init points
- `backend/engines/deviation.py` — Expanded `always_valid` verbs, off-topic phrase detector, `turn_history` parameter
- `backend/engines/narrator.py` — 60s timeout, max_retries=1, max_tokens=500, reduced tenacity retries
- `backend/engines/intent_parser.py` — 30s timeout, max_retries=1, reduced retries
- `backend/engines/campaign_planner.py` — 30s timeout, max_retries=1
- `backend/engines/npc_engine.py` — 30s timeout, max_retries=1
- `frontend/src/hooks/useGame.js` — `redo_turn` handling, `ui_context` → dynamic theme, `characterClass` in sidebar
- `frontend/src/components/FloatingHUD.jsx` — Class name in HUD header

---
*Status: All changes verified, tested with live game sessions.*
