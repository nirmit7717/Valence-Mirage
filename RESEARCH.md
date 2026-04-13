# LLM Game Master — Research Document
**Created:** 2026-04-12
**Project:** Online multiplayer chat-based D&D with RL-driven adaptive AI

---

## 1. Existing Similar Projects

### 1.1 Daicer (Most Relevant — Multiplayer AI DM)
- **GitHub:** https://github.com/lguibr/daicer
- **Language:** TypeScript
- **Status:** Active (updated Mar 2026), Phase 2 complete
- **What it does:** Multiplayer tabletop RPG powered by an AI Dungeon Master. Fuses deterministic dice mechanics with LangGraph orchestration and a React client. Faithful to D&D 5e.

**Architecture:**
```
┌─────────────────────────────────────────────┐
│               React Client                  │
│          (Multiplayer UI + Chat)             │
└──────────────────┬──────────────────────────┘
                   │ GraphQL Mutations
                   ▼
┌─────────────────────────────────────────────┐
│         Strapi Database (SSoT)              │
│         EntitySheet, TurnPipeline           │
└──────────────────┬──────────────────────────┘
                   │
    ┌──────────────┼──────────────┐
    ▼              ▼              ▼
┌────────┐  ┌───────────┐  ┌──────────┐
│ Intent │→│ Resolution│→│Persist   │
│(Input) │  │(Pure Logic│  │(Atomic   │
│        │  │ Engine)   │  │ Transact)│
└────────┘  └───────────┘  └──────────┘
                                │
                   ┌────────────┼────────────┐
                   ▼                         ▼
            ┌───────────┐           ┌───────────────┐
            │ Narration │           │ Memory (RAG)  │
            │ (LLM)     │           │ Embeddings    │
            └───────────┘           └───────────────┘
```

**Key Design Patterns:**
- **Turn Pipeline:** Intent -> Resolution -> Persistence -> Narration -> Memory (atomic transaction)
- **ActionEngine:** Pure deterministic logic (hit/miss, pathfinding) — LLM doesn't handle math
- **RAG Memory:** Turn summaries auto-embedded into KnowledgeSnippets for long-term recall
- **Fog of War:** Server-side visibility service prevents cheating
- **Deterministic World:** Seeded world generation
- **LangGraph:** Orchestration of multi-step LLM workflows

**Tech Stack:** Strapi, GraphQL, LangGraph, React, PostgreSQL

**What We Can Learn:**
- Separate deterministic game logic from LLM narration (critical for fairness)
- Turn-based pipeline is a solid pattern for multiplayer
- RAG memory gives the DM long-term campaign context
- **Missing:** No RL adaptation, no player behavior learning

---

### 1.2 Genesis Mnemosyne (Emergent Narrative with Memory)
- **GitHub:** https://github.com/genesismnemosyneengine-ai/genesis-mnemosyne
- **Language:** Python
- **Status:** Active (Sep 2025)
- **What it does:** Emergent narrative AI simulation where autonomous agents with persistent memories and evolving personalities create unpredictable stories.

**Architecture:**
```
main.py (CLI Entry)
    -> simulation.py (Game Loop)
        -> dungeon_master (Reality Check)
        -> agent.py (Agent Consciousness)
            -> memory.py (Vector experiences, 1536-dim embeddings)
            -> world.py (State)
```

**Key Features:**
- **Memory-Driven Identity:** Vector-based semantic memory (1536-dim embeddings) creates persistent character
- **Personality Evolution:** Dynamic traits based on trauma, bonding, power, madness
- **Reality Consensus:** Collective belief can solidify hallucinations into permanent features
- **Emergent Social Dynamics:** Agents form covenants, create laws, develop rituals
- **Player Avatar Mode:** Play as a character in the world

**Tech Stack:** Python 3.8+, OpenAI API, vector embeddings

**What We Can Learn:**
- Memory-driven personality evolution is directly relevant to our RL adaptation
- Vector memory for tracking player behavior patterns over time
- Personality trait dynamics could inform our RL reward signal design
- **Missing:** No multiplayer, no structured D&D rules, no RL

---

### 1.3 Claude-DnD (Solo D&D 5e via Claude Code)
- **GitHub:** https://github.com/SergeyKhval/claude-dnd (also forked by Tsikounet)
- **Language:** Python
- **What it does:** D&D 5e game engine plugin for Claude Code. Solo play with full rules, game state stored in editable markdown files.

**Architecture:** Simple — Claude Code + markdown state files + D&D 5e rules in system prompt

**What We Can Learn:**
- Markdown-based game state is lightweight and debuggable
- D&D 5e SRD rules can be embedded in system prompts
- **Missing:** No multiplayer, no RL, no persistent adaptation

---

### 1.4 AI Dungeon (Latitude Games — Commercial)
- **GitHub (original):** https://github.com/latitudegames/AIDungeon
- **What it does:** The original AI-powered text adventure. Uses GPT-2/3 for open-ended storytelling.
- **Relevance:** Pioneered the concept, but pure LLM story generator — no game rules, no multiplayer adaptation, no RL.

---

### 1.5 Other Notable Projects

| Project | URL | Notes |
|---------|-----|-------|
| Neuradventure | https://github.com/khajiitvaper2017/Neuradventure | LLM-driven adventure, TypeScript |
| TwitchAIDungeon | https://github.com/tomaarsen/TwitchAIDungeon | Twitch bot for collaborative AI Dungeon play (multiplayer via chat votes) |
| Inner-Self (AID mod) | https://github.com/LewdLeah/Inner-Self | Memory, goals, secrets, planning for AI Dungeon characters |

---

## 2. Architecture Analysis & Our Unique Position

### What exists in the landscape:
| Feature | Daicer | Genesis Mnemosyne | Claude-DnD | AI Dungeon |
|---------|--------|-------------------|------------|------------|
| Multiplayer | YES | NO | NO | NO |
| D&D 5e Rules | YES | NO | YES | NO |
| LLM Narration | YES | YES | YES | YES |
| RAG Memory | YES | YES (vector) | NO | NO |
| RL Adaptation | NO | NO | NO | NO |
| Player Behavior Learning | NO | NO | NO | NO |
| Adaptive Difficulty | NO | NO | NO | NO |

### Our Differentiator: RL-Driven Adaptive Game Master
No existing project combines LLM-based DM narration with RL that learns from player attack patterns, decision-making styles, and adapts encounters in real-time. This is genuinely novel.

### Recommended Architecture (Hybrid Approach)

Based on research, the optimal architecture combines the best patterns:

```
┌─────────────────────────────────────────────────┐
│              Multiplayer Chat Client             │
│         (WebSocket-based, Web/Mobile)            │
└───────────────────────┬─────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│              Game Server (Python)                │
│                                                  │
│  ┌─────────────┐  ┌──────────────────────────┐  │
│  │ Game Engine │  │   LLM Game Master Layer   │  │
│  │ (Determin-  │  │   (Narration + RAG)       │  │
│  │ istic Rules)│  │                            │  │
│  │ - Dice      │  │   - Campaign narration     │  │
│  │ - Combat    │  │   - NPC dialogue           │  │
│  │ - Pathfind  │  │   - Encounter generation   │  │
│  │ - Stats     │  │   - Quest hooks            │  │
│  └──────┬──────┘  └────────────┬───────────────┘  │
│         │                      │                   │
│         ▼                      ▼                   │
│  ┌─────────────────────────────────────────────┐  │
│  │         RL Adaptation Layer (NOVEL)          │  │
│  │                                              │  │
│  │  Player Behavior Tracker                     │  │
│  │  ├── Attack pattern analysis                 │  │
│  │  ├── Decision tree logging                   │  │
│  │  ├── Risk tolerance scoring                  │  │
│  │  └── Strategy classification                 │  │
│  │                                              │  │
│  │  Adaptive Encounter Generator                │  │
│  │  ├── Difficulty adjustment (PPO/DQN)         │  │
│  │  ├── Enemy composition optimization          │  │
│  │  ├── Narrative pacing control                │  │
│  │  └── Reward shaping based on engagement      │  │
│  └─────────────────────────────────────────────┘  │
│                        │                           │
│                        ▼                           │
│  ┌─────────────────────────────────────────────┐  │
│  │         Database + Vector Store              │  │
│  │  PostgreSQL (game state) +                   │  │
│  │  Vector DB (RAG memory, player profiles)     │  │
│  └─────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### Key Architecture Decisions:
1. **Separate Game Logic from LLM** (learned from Daicer) — deterministic rules engine for fairness
2. **Turn-based Pipeline** — Intent -> Resolve -> Persist -> Narrate -> Adapt
3. **RL Agent per Player** — each player gets a behavioral profile that evolves
4. **Global Campaign RL** — meta-level RL adjusts overall difficulty and pacing
5. **RAG for Campaign Memory** — long-term context for the DM's storytelling

---

## 3. Dataset Research

### 3.1 Datasets for DM Role-Playing / Character Training

| Dataset | HuggingFace ID | Size | Description | Relevance |
|---------|---------------|------|-------------|-----------|
| **Internal Knowledge Map - StoryWriter/RolePlaying** | `Severian/Internal-Knowledge-Map-StoryWriter-RolePlaying` | 2K samples (1K-10K) | Detailed story writing & RP examples, well-formatted | HIGH — Direct RP quality training |
| **Combined Roleplay** | `agentlans/combined-roleplay` | 1M-10M rows | Multi-turn RP conversations, creative writing, character interactions | HIGH — Scale + diversity |
| **Roleplay TTL** | `hieunguyenminh/roleplay` | 1K-10K | Trains AI to embody characters with unique personas, backgrounds, traits | HIGH — Character embodiment |
| **GPT Role-play Realm** | `IlyaGusev/gpt_roleplay_realm` | ~4K dialogues (219 chars x 20 topics) | GPT-4 generated character dialogues. English + Russian | HIGH — Structured character dialogues |
| **Sonnet3.5 Charcard Roleplay** | `Gryphe/Sonnet3.5-Charcard-Roleplay` | ~10K dialogues | Character card-based RP via Sonnet 3.5, simulated user personalities | MEDIUM — Quality interactions |
| **OpenHermesPreferences-roleplay** | `vicgalle/OpenHermesPreferences-roleplay` | 1K-10K | DPO preference dataset with chosen/rejected pairs for RLHF | HIGH — Directly usable for RLHF/DPO |
| **MiniMax Role-play Benchmark** | `MiniMaxAI/role-play-bench` | 1K-10K | Benchmark for evaluating RP agents. Chinese + English | MEDIUM — Evaluation, not training |
| **Bluemoon RP Chat 300K** | `rickRossie/bluemoon_roleplay_chat_data_300k_messages` | 100K-1M messages | Large-scale RP chat data | MEDIUM — Scale but quality varies |

### 3.2 Datasets for Text Adventure / Interactive Fiction

| Dataset | HuggingFace ID | Size | Description | Relevance |
|---------|---------------|------|-------------|-----------|
| **Choose-Your-Story** | `PocketDoc/Choose-Your-Story-Long-Text-Adventures` | Large | Text adventure from choose-your-story sites, chat format | HIGH — Direct text adventure training |
| **AI Dungeon Text Adventures** | `SicariusSicariiStuff/text_adventures` | 100K-1M | Scraped from AI Dungeon, Apache 2.0 license | HIGH — Massive scale adventure data |
| **Floyd Text Adventures** | `PocketDoc/Floyd-Text-Adventures` | Moderate | Text adventure dataset in chat format | MEDIUM |
| **Skein Text Adventures** | `ToastyPigeon/skein-text-adventures` | Moderate | Multi-source text adventure collection | MEDIUM |

### 3.3 Datasets for NPC Dialogue / Game Quests

| Dataset | HuggingFace ID | Size | Description | Relevance |
|---------|---------------|------|-------------|-----------|
| **NPC Quest Dialogue** | `chimbiwide/NPC-Quest-Dialogue` | ~2K quests | High-quality NPC quest conversations for RPGs. Apache 2.0 | HIGH — Quest dialogue patterns |
| **NPC Dialogue v2** | `chimbiwide/NPC-Dialogue_v2` | 1K-10K | Improved NPC dialogue for video games | HIGH — General NPC behavior |
| **NPC Dialogue** | `amaydle/npc-dialogue` | 1K-10K | NPC dialogue dataset | MEDIUM |
| **RPG Quest NPC Dialogue** | `dprashar/npc_dialogue_rpg_quests` | 10K-100K | RPG quest-focused NPC interactions | HIGH — Quest-specific patterns |
| **MMORPG NPC Quest Dialogue** | `5z3f/mmorpg_npc_quest_dialogue` | Small | MMORPG-style quest dialogues | MEDIUM |

### 3.4 Datasets for Story Generation / Narrative

| Dataset | HuggingFace ID | Size | Description | Relevance |
|---------|---------------|------|-------------|-----------|
| **Story Generation Collection** | `RUCAIBox/Story-Generation` | Multiple datasets | ROCStories, WritingPrompts, Hippocorpus, WikiPlots | MEDIUM — Narrative quality |
| **Roleplay Forums Raw** | `lemonilia/roleplaying-forums-raw` | 100K-1M | Raw roleplaying forum scrapes, real human RP data | MEDIUM — Real RP patterns, needs cleaning |

### 3.5 Datasets for RL Training (Combat/Strategy Adaptation)

**No existing dataset directly covers this.** We need to generate our own through:
1. **Self-play logs** — Record all player sessions as training data
2. **D&D 5e SRD combat simulations** — Generate combat scenarios programmatically
3. **Player behavior clustering** — Build player archetypes from session data for RL reward shaping

**Related resources for combat RL:**
- D&D 5e SRD (Systems Reference Document): https://dnd.wizards.com/resources/systems-reference-document
- Open5e API (programmatic 5e rules): https://open5e.com/
- `dnd-5e-srd` npm package (used by Daicer) — structured 5e data

---

## 4. Recommended Training Strategy

### Phase 1: Base DM Model
Fine-tune a base LLM on:
- `agentlans/combined-roleplay` (general RP ability)
- `IlyaGusev/gpt_roleplay_realm` (character embodiment)
- `chimbiwide/NPC-Quest-Dialogue` + `dprashar/npc_dialogue_rpg_quests` (quest/NPC behavior)
- `SicariusSicariiStuff/text_adventures` (adventure narration)
- D&D 5e SRD rules (structured game knowledge)

### Phase 2: DPO/RLHF Alignment
Use:
- `vicgalle/OpenHermesPreferences-roleplay` (chosen/rejected for DM quality)
- Custom preference pairs from playtest sessions

### Phase 3: RL Adaptation (Our Novel Contribution)
Generate custom training data:
- Record all multiplayer sessions
- Extract: attack patterns, decision sequences, risk profiles, strategy shifts
- Train a secondary RL agent (PPO recommended) that:
  - Observes player behavior vectors
  - Adjusts encounter parameters (enemy stats, composition, narrative tension)
  - Reward signal: player engagement (session length, return rate, combat satisfaction surveys)

---

## 5. Key Takeaways

1. **No one has done RL + LLM DM** — our concept is genuinely novel
2. **Daicer's architecture is the best reference** for multiplayer game mechanics
3. **Genesis Mnemosyne's memory system** is relevant for player behavior tracking
4. **Plenty of RP/NPC datasets exist** for base model training
5. **Combat RL data must be self-generated** — no existing dataset covers adaptive difficulty in TTRPGs
6. **D&D 5e SRD is free** and gives us structured rules to embed in the system

---

*Next steps: Define architecture document, set up project structure, choose base model for fine-tuning.*
