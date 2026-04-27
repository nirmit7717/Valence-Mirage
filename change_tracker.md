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
*Status: All changes verified and server tested successfully.*
