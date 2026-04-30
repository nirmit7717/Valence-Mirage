"""Valence Mirage — FastAPI Game Server (Phase 3.6: Combat Overhaul)"""

import logging
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from engines import IntentParser, ProbabilityEngine, DiceEngine, Narrator, StateManager
from engines.campaign_planner import CampaignPlanner, CampaignBlueprint
from engines.npc_engine import NPCEngine, NPCState, NPCPersonality
from engines.combat_engine import CombatEngine
from engines.deviation import evaluate_alignment, get_warning_message
from models.action import ActionIntent
from models.game_state import GameSession, Turn, Item
from models.outcome import Outcome, StateChanges, ProbabilityScore, ScoreBreakdown
from models.combat import CombatState, CombatAction, CombatActionType
from database import Database
from rag import RuleRetriever, VectorStore
import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("valence_mirage")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize engines
    app.state.intent_parser = IntentParser()
    app.state.probability = ProbabilityEngine()
    app.state.dice = DiceEngine()
    app.state.narrator = Narrator()
    app.state.state_manager = StateManager()
    app.state.campaign_planner = CampaignPlanner()
    app.state.npc_engine = NPCEngine()
    app.state.combat_engine = CombatEngine()

    # Initialize vector store + RAG
    app.state.vector_store = VectorStore()
    rule_retriever = RuleRetriever()
    await rule_retriever.initialize()
    app.state.rule_retriever = rule_retriever

    # Initialize database
    db = Database()
    await db.connect()
    app.state.db = db

    # Restore in-memory sessions from DB
    await _restore_sessions(app)

    logger.info("Valence Mirage v0.6.2 initialized — engines + DB + vector search + NPCs + local combat + context-aware combat")

    # Ensure admin user exists
    await _ensure_admin(db)

    yield

    # Persist all active sessions before shutdown
    sm: StateManager = app.state.state_manager
    for sid in sm.list_sessions():
        session = sm.get_session(sid)
        if session:
            await db.save_full_session(session)
    await db.close()
    logger.info("Valence Mirage server shutting down — sessions persisted")


async def _ensure_admin(db: Database):
    """Create default admin user if no users exist."""
    count = await db.count_users()
    if count == 0:
        admin_pass = os.getenv("ADMIN_PASSWORD", "admin123")
        await db.create_user("admin", hash_password(admin_pass), "admin")
        logger.info("Default admin user created")


async def _restore_sessions(app):
    db: Database = app.state.db
    sm: StateManager = app.state.state_manager
    sessions = await db.list_sessions()
    restored = 0
    for s in sessions:
        session = await db.load_session(s["session_id"])
        if session:
            sm._sessions[session.session_id] = session
            restored += 1
    logger.info(f"Restored {restored} sessions from database")


app = FastAPI(
    title="Valence Mirage",
    description="AI-powered narrative engine with probabilistic dice mechanics",
    version="0.4.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
from auth import create_access_token, hash_password, verify_password, get_current_user, require_auth, require_admin
from config import JWT_SECRET as SECRET_KEY, JWT_ALGORITHM as ALGORITHM
from models.user import UserCreate, UserLogin, UserResponse, TokenResponse, TesterRequest
import os

def extract_choices(narration: str) -> list[str]:
    """Extract → prefixed suggestions from narration."""
    parts = re.split(r'→|->', narration)
    choices = []
    if len(parts) > 1:
        for part in parts[1:]:
            choice = part.split('\n')[0].strip()
            if choice:
                choices.append(choice)
    return choices

def clean_narration(narration: str) -> str:
    """Remove choice lines from narration for storage."""
    parts = re.split(r'→|->', narration)
    return parts[0].strip() if parts else narration.strip()



from pydantic import BaseModel, Field


class NewSessionRequest(BaseModel):
    player_name: str = Field(default="Adventurer", max_length=50)
    keywords: str = Field(default="", max_length=200, description="Keywords/themes for the adventure")
    character_class: str = Field(default="warrior", description="warrior, rogue, wizard, cleric, bard")
    campaign_size: str = Field(default="medium", description="small, medium, large")


class ActionRequest(BaseModel):
    action: str = Field(..., min_length=1, max_length=200, description="Free-form player action (max 200 chars)")

    def model_post_init(self, __context):
        self.action = self.action.strip()
        if not self.action:
            raise ValueError("Action cannot be empty")


class CombatResolveRequest(BaseModel):
    """Client sends final combat result after local resolution."""
    result: str = Field(..., description="victory or defeat")
    player_hp: int = Field(...)
    player_mana: int = Field(...)
    enemy_name: str = Field(...)
    combat_log: list[dict] = Field(default_factory=list, description="Full combat log entries")
    turns_taken: int = Field(default=1)


class ActionResponse(BaseModel):
    turn_number: int
    intent: ActionIntent
    requires_roll: bool
    probability: float | None = None
    dice_threshold: int | None = None
    roll: int | None = None
    outcome: str
    narration: str
    state_changes: StateChanges
    player_hp: int
    player_mana: int
    player_level: int = 1
    player_xp: int = 0
    player_xp_to_next: int = 100
    max_hp: int = 50
    max_mana: int = 50
    inventory: list[dict] = []
    level_up: dict = {}
    current_beat: str | None = None
    npc_dialogue: dict | None = None
    npcs: list[dict] = []
    choices: list[str] = []
    combat_started: bool = False
    combat_data: dict | None = None
    combat_beat_available: bool = False
    current_act: int | None = None
    campaign_ended: bool = False
    # ── New flags ──
    game_over: bool = False
    victory: bool = False
    campaign_objective: str | None = None
    dice_result: dict | None = None
    # ── Deviation tracking ──
    warning_count: int = 0
    warning_message: str | None = None
    game_over_reason: str | None = None
    # ── Dice debug ──
    dice_debug: dict | None = None


# SPA routing: static files served via spa_fallback route, no mount needed.


@app.get("/")
async def root():
    """Redirect to the SPA entry point."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/")


@app.get("/static/{path:path}")
async def spa_fallback(path: str):
    """Serve actual static files or index.html for SPA client-side routes."""
    import os
    if path == "" or path.endswith("/"):
        return FileResponse("static/index.html")
    file_path = os.path.join("static", path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    # SPA fallback — serve index.html for React Router paths
    return FileResponse("static/index.html")


@app.get("/health")
async def health():
    return {
        "name": "Valence Mirage",
        "version": "0.4.0",
        "status": "running",
        "active_sessions": len(app.state.state_manager._sessions),
        "db": "connected",
        "vector_search": "enabled" if app.state.rule_retriever._use_vector else "keyword_fallback",
    }


@app.post("/session/new", response_model=dict)
async def create_session(req: NewSessionRequest = NewSessionRequest(), authorization: str | None = None):
    sm: StateManager = app.state.state_manager
    planner: CampaignPlanner = app.state.campaign_planner
    npc_engine: NPCEngine = app.state.npc_engine
    db: Database = app.state.db

    # Create session
    session = sm.create_session(player_name=req.player_name)

    # Optionally associate with logged-in user
    if authorization and authorization.startswith("Bearer "):
        try:
            from jose import jwt as jose_jwt
            payload = jose_jwt.decode(authorization[7:], SECRET_KEY, algorithms=[ALGORITHM])
            session.world_state["user_id"] = payload.get("sub")
        except Exception:
            pass  # Auth optional

    # Apply character class
    from models.character import CharacterClass, CLASS_STATS, CLASS_ABILITIES, CLASS_STARTING_GEAR, CLASS_DESCRIPTIONS
    try:
        cls = CharacterClass(req.character_class.lower())
    except ValueError:
        cls = CharacterClass.WARRIOR

    class_stats = CLASS_STATS[cls]
    session.player.character_class = cls.value
    session.player.stats.strength = class_stats["strength"]
    session.player.stats.intelligence = class_stats["intelligence"]
    session.player.stats.dexterity = class_stats["dexterity"]
    session.player.stats.control = class_stats["control"]
    session.player.stats.charisma = class_stats["charisma"]
    session.player.stats.wisdom = class_stats["wisdom"]
    session.player.max_hp += class_stats["hp_bonus"]
    session.player.hp = session.player.max_hp
    session.player.max_mana += class_stats["mana_bonus"]
    session.player.mana = session.player.max_mana

    # Starting equipment
    from models.game_state import Item
    for gear in CLASS_STARTING_GEAR.get(cls, []):
        session.player.inventory.append(Item(
            name=gear["name"],
            item_type=gear["type"],
            description=f"Starting gear for {cls.value}",
        ))

    # Store abilities in world_state for combat use
    abilities = CLASS_ABILITIES.get(cls, [])
    session.world_state["abilities"] = [a.model_dump() for a in abilities]
    session.world_state["class_description"] = CLASS_DESCRIPTIONS.get(cls, "")

    # Generate campaign blueprint with template
    from data.campaign_templates import CAMPAIGN_TEMPLATES
    template = CAMPAIGN_TEMPLATES.get(req.campaign_size.lower(), CAMPAIGN_TEMPLATES["medium"])
    session.world_state["campaign_size"] = req.campaign_size.lower()
    session.world_state["campaign_template"] = template.model_dump()

    blueprint = await planner.generate_blueprint(req.player_name, keywords=req.keywords, template=template)
    session.world_state["campaign"] = blueprint.model_dump()
    session.world_state["location"] = blueprint.setting
    session.world_state["situation"] = blueprint.premise

    # Derive campaign objective from blueprint
    campaign_objective = blueprint.premise
    if blueprint.possible_endings:
        # Use the first possible ending as the objective text
        campaign_objective = blueprint.possible_endings[0]
    session.world_state["campaign_objective"] = campaign_objective

    # Track current beat for combat triggers
    if blueprint.acts and blueprint.acts[0].beats:
        session.world_state["current_act"] = blueprint.acts[0].act_id
        session.world_state["current_beat"] = blueprint.acts[0].beats[0].beat_id
    else:
        session.world_state["current_act"] = 1
        session.world_state["current_beat"] = 1

    # Removed raw NPC generation; NPCs will organically spawn via beats.
    session.world_state["npcs"] = {}

    # Initialize pacing counters
    session.world_state["turns_since_roll"] = 0
    session.world_state["turns_since_combat"] = 0
    session.world_state["combat_tension"] = 0
    session.world_state["turns_in_beat"] = 0

    # Generate opening narration
    narrator: Narrator = app.state.narrator
    opening_narration = ""
    try:
        opening_narration = await narrator.narrate_opening(
            title=blueprint.title,
            premise=blueprint.premise,
            setting=blueprint.setting,
            player_name=req.player_name,
            tone=blueprint.tone if hasattr(blueprint, "tone") else "",
            character_class=cls.value,
        )
        session.world_state["situation"] = opening_narration[-500:]
    except Exception as e:
        logger.warning(f"Opening narration failed: {e}")

    await db.save_session(session)

    logger.info(f"New session: {session.session_id} — '{req.player_name}' — Campaign: {blueprint.title}")

    return {
        "session_id": session.session_id,
        "player": session.player.model_dump(),
        "character_class": cls.value,
        "class_description": CLASS_DESCRIPTIONS.get(cls, ""),
        "abilities": [a.model_dump() for a in abilities],
        "campaign_size": req.campaign_size.lower(),
        "campaign": {
            "title": blueprint.title,
            "premise": blueprint.premise,
            "setting": blueprint.setting,
            "acts": [{"title": a.title, "beats": [{"title": b.title, "type": b.type} for b in a.beats]} for a in blueprint.acts],
            "possible_endings": blueprint.possible_endings,
        },
        "npcs": [],
        "world_state": {
            "location": session.world_state.get("location", ""),
            "situation": session.world_state.get("situation", ""),
            "campaign_objective": session.world_state.get("campaign_objective", ""),
        },
        "opening_narration": clean_narration(opening_narration),
        "choices": extract_choices(opening_narration),
    }


@app.get("/session/{session_id}", response_model=GameSession)
async def get_session(session_id: str):
    sm: StateManager = app.state.state_manager
    session = sm.get_session(session_id)
    if not session:
        db: Database = app.state.db
        session = await db.load_session(session_id)
        if session:
            sm._sessions[session_id] = session
        else:
            raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    sm: StateManager = app.state.state_manager
    db: Database = app.state.db
    deleted = await db.delete_session(session_id)
    sm.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"detail": f"Session {session_id} deleted"}


@app.get("/sessions", response_model=list[dict])
async def list_sessions():
    db: Database = app.state.db
    return await db.list_sessions()


def _is_campaign_complete(bp: CampaignBlueprint) -> bool:
    """Check if all beats in the campaign template have been completed.
    
    Returns True if we're at or past the last beat of the last act.
    Since advance_beat() won't increment past the final beat, we check
    if we're ON the final beat (the caller should advance first, then
    check — but if the final beat was just completed, we detect it here).
    """
    if not bp.acts:
        return True
    max_act = max(a.act_id for a in bp.acts)
    last_act = next((a for a in bp.acts if a.act_id == max_act), None)
    if not last_act or not last_act.beats:
        return True
    max_beat = max(b.beat_id for b in last_act.beats)
    # Past the end, or ON the final beat (advance won't go further)
    return bp.current_act > max_act or (bp.current_act == max_act and bp.current_beat >= max_beat)


def _get_total_beats(bp: CampaignBlueprint) -> int:
    """Count total beats in the blueprint."""
    return sum(len(a.beats) for a in bp.acts)


@app.post("/session/{session_id}/action", response_model=ActionResponse)
async def submit_action(session_id: str, req: ActionRequest):
    sm: StateManager = app.state.state_manager
    db: Database = app.state.db
    retriever: RuleRetriever = app.state.rule_retriever

    session = sm.get_session(session_id)
    if not session:
        session = await db.load_session(session_id)
        if session:
            sm._sessions[session_id] = session
        else:
            raise HTTPException(status_code=404, detail="Session not found")

    planner: CampaignPlanner = app.state.campaign_planner
    parser: IntentParser = app.state.intent_parser
    prob_engine: ProbabilityEngine = app.state.probability
    dice_engine: DiceEngine = app.state.dice
    narrator: Narrator = app.state.narrator
    npc_engine: NPCEngine = app.state.npc_engine

    # If campaign has ended, reject further actions
    if session.world_state.get("campaign_ended", False):
        raise HTTPException(status_code=400, detail="Campaign has ended. Start a new adventure.")

    # ── Combat Mode Guard ──
    # If combat is active, do NOT process as narrative.
    # Return current combat state so frontend shows combat UI.
    active_combat = session.world_state.get("combat")
    if active_combat and not active_combat.get("resolved", False):
        combat_engine_local: CombatEngine = app.state.combat_engine
        enemies = active_combat.get("enemies", [])
        enemy = enemies[0] if enemies else None
        if enemy:
            player_armor = combat_engine_local._calc_player_armor(session.player)
            attack_bonus = combat_engine_local._calc_attack_bonus(session.player)
            return ActionResponse(
                turn_number=session.turn_number,
                intent=ActionIntent(action="combat", action_type="attack", description="Combat in progress", relevant_stat="strength", risk="high", requires_roll=True),
                requires_roll=True,
                outcome="combat_active",
                narration=f"Combat continues! {enemy['name']} stands before you with {enemy['hp']}/{enemy['max_hp']} HP.",
                state_changes=StateChanges(),
                hp_change=0,
                mana_change=0,
                xp_change=0,
                player_hp=session.player.hp,
                player_mana=session.player.mana,
                player_xp=session.player.xp,
                player_xp_to_next=session.player.xp_to_next,
                player_level=session.player.level,
                max_hp=session.player.max_hp,
                max_mana=session.player.max_mana,
                choices=["Attack", "Use Ability", "Defend"],
                combat_started=True,
                combat_data={
                    "combat_id": active_combat.get("combat_id", ""),
                    "enemy": {"name": enemy["name"], "hp": enemy["hp"], "max_hp": enemy["max_hp"],
                              "armor": enemy.get("armor", 0), "attack_bonus": enemy.get("attack_bonus", 0),
                              "abilities": enemy.get("abilities", [])},
                    "player": {"name": session.player.name, "hp": session.player.hp, "max_hp": session.player.max_hp,
                               "mana": session.player.mana, "max_mana": session.player.max_mana,
                               "armor": player_armor, "attack_bonus": attack_bonus, "status_effects": []},
                    "abilities": session.world_state.get("abilities", []),
                    "inventory": [{"name": i.name, "type": i.item_type, "hp_restore": getattr(i, "hp_restore", 0), "mana_restore": getattr(i, "mana_restore", 0)} for i in session.player.inventory],
                    "enemy_tier": enemy.get("tier", 1),
                },
                dice_debug=None,
                warning_count=session.world_state.get("warning_count", 0),
                warning_message=None,
                game_over=False,
                game_over_reason=None,
                campaign_ended=False,
                victory=False,
            )
        else:
            # Combat data corrupt — clear it and continue as narrative
            session.world_state.pop("combat", None)
            logger.warning(f"Cleared corrupt combat state for session {session_id}")

    campaign_objective = session.world_state.get("campaign_objective", "")

    stats_summary = (
        f"STR={session.player.stats.strength} "
        f"INT={session.player.stats.intelligence} "
        f"DEX={session.player.stats.dexterity} "
        f"CON={session.player.stats.control} "
        f"CHA={session.player.stats.charisma} "
        f"WIS={session.player.stats.wisdom}"
    )
    world_context = (
        f"Location: {session.world_state.get('location', 'unknown')}. "
        f"{session.world_state.get('situation', '')}"
    )

    campaign_data = session.world_state.get("campaign")
    current_beat_title = None
    combat_beat_available = False
    if campaign_data:
        bp = CampaignBlueprint(**campaign_data)
        beat = planner.get_current_beat(bp)
        if beat:
            world_context += f" Current story beat: {beat.title} — {beat.description}"
            current_beat_title = beat.title
            if beat.type == "combat":
                combat_beat_available = True
        # Update current act/beat tracking
        session.world_state["current_act"] = bp.acts[0].act_id if bp.acts else 1
        session.world_state["current_beat"] = bp.acts[0].beats[0].beat_id if bp.acts and bp.acts[0].beats else 1

    # Track pacing — two independent counters
    turns_since_roll = session.world_state.get("turns_since_roll", 0)
    turns_since_combat = session.world_state.get("turns_since_combat", 0)
    turns_in_beat = session.world_state.get("turns_in_beat", 0)

    # 1. Intent Parsing
    try:
        intent = await parser.parse(req.action, world_context, stats_summary)
    except Exception as e:
        logger.error(f"Intent parsing API error: {e}")
        raise HTTPException(status_code=503, detail=f"AI service unavailable: {e}")

    # 1b. NPC interaction (runs before roll check)
    npc_dialogue = None
    npcs_data = session.world_state.get("npcs", {})
    if npcs_data:
        action_lower = req.action.lower()
        matched_npc = None
        for npc_id, npc_dict in npcs_data.items():
            npc_state = NPCState(**npc_dict)
            name_parts = npc_state.personality.name.lower().split()
            if (npc_state.personality.name.lower() in action_lower or
                any(p in action_lower for p in name_parts if len(p) >= 3) or
                npc_state.personality.role.lower() in action_lower):
                matched_npc = (npc_id, npc_state)
                break
        if not matched_npc and intent.target:
            for npc_id, npc_dict in npcs_data.items():
                npc_state = NPCState(**npc_dict)
                if npc_state.personality.name.lower() in (intent.target or "").lower():
                    matched_npc = (npc_id, npc_state)
                    break
        if not matched_npc and intent.action_type in ("persuade", "intimidate", "deceive", "dialogue"):
            best = None
            for npc_id, npc_dict in npcs_data.items():
                npc_state = NPCState(**npc_dict)
                if best is None or npc_state.disposition > best[1].disposition:
                    best = (npc_id, npc_state)
            if best:
                matched_npc = best
        if matched_npc:
            npc_id, npc_state = matched_npc
            try:
                dialogue_result = await npc_engine.generate_dialogue(
                    npc=npc_state, player_action=req.action, player_name=session.player.name,
                )
                npc_state.disposition = max(-1.0, min(1.0, npc_state.disposition + dialogue_result.get("disposition_change", 0.0)))
                npc_state.trust = max(0.0, min(1.0, npc_state.trust + dialogue_result.get("trust_change", 0.0)))
                npc_state.conversation_history.append({"player": req.action, "npc": dialogue_result.get("dialogue", "")})
                npc_state.interacted = True
                session.world_state["npcs"][npc_id] = npc_state.model_dump()
                npc_dialogue = dialogue_result
            except Exception as e:
                logger.warning(f"NPC dialogue failed: {e}")

    # ── Deviation Check ──
    warning_count = session.world_state.get("warning_count", 0)
    deviation_score = session.world_state.get("deviation_score", 0.0)
    warning_message_out = None
    game_over_reason = None

    # Get context for alignment evaluation
    npc_names = []
    npcs_data = session.world_state.get("npcs", {})
    if npcs_data:
        for npc_dict in npcs_data.values():
            name = npc_dict.get("personality", {}).get("name", "")
            if name:
                npc_names.append(name)

    recent_narration = session.world_state.get("situation", "")[-300:]
    location = session.world_state.get("location", "")

    classification, alignment = evaluate_alignment(
        action=req.action,
        current_beat=current_beat_title,
        recent_narration=recent_narration,
        campaign_objective=campaign_objective,
        location=location,
        npc_names=npc_names,
    )

    logger.info(f"Deviation: {classification} (alignment={alignment:.2f}, warnings={warning_count})")

    if classification == "major":
        warning_count += 1
        session.world_state["warning_count"] = warning_count
        deviation_score = max(-1.0, deviation_score - 0.3)
        session.world_state["deviation_score"] = deviation_score
        warning_message_out = get_warning_message(warning_count)

        if warning_count >= 3:
            game_over_reason = "lost_focus"
            # Build a game-over response
            session.world_state["campaign_ended"] = True
            await _record_campaign_end(db, session, "lost_focus")
            session.turn_number += 1
            final_msg = get_warning_message(3) or "You have strayed too far from your path. The journey collapses."
            return ActionResponse(
                turn_number=session.turn_number,
                intent=intent,
                requires_roll=False,
                outcome="critical_failure",
                narration=final_msg,
                state_changes=StateChanges(),
                player_hp=session.player.hp,
                player_mana=session.player.mana,
                player_level=session.player.level,
                player_xp=session.player.xp,
                player_xp_to_next=session.player.xp_to_next,
                max_hp=session.player.max_hp,
                max_mana=session.player.max_mana,
                inventory=[i.model_dump() for i in session.player.inventory],
                choices=[],
                game_over=True,
                victory=False,
                campaign_ended=True,
                campaign_objective=campaign_objective,
                warning_count=warning_count,
                warning_message=final_msg,
                game_over_reason=game_over_reason,
            )
    elif classification == "slight":
        deviation_score = max(-1.0, deviation_score - 0.1)
        session.world_state["deviation_score"] = deviation_score
        # No warning increment for slight deviation — just track the score
    else:
        # Relevant or creative_valid — reduce deviation score (forgive past)
        deviation_score = min(0.0, deviation_score + 0.1)
        session.world_state["deviation_score"] = deviation_score

    # 2. Check if roll is needed
    if not intent.requires_roll:
        turns_since_roll += 1
        turns_in_beat += 1
        
        # Force a probabilistic roll if 3 narrative turns have passed
        if turns_since_roll >= 3:
            intent.requires_roll = True
            intent.action_type = "Forced Encounter"
            intent.description = f"While attempting to {intent.description}, a sudden event disrupts the peace!"
            intent.relevant_stat = "dexterity"
            turns_since_roll = 0
            
    else:
        turns_since_roll = 0
        turns_in_beat += 1

    session.world_state["turns_since_roll"] = turns_since_roll
    session.world_state["turns_in_beat"] = turns_in_beat

    # ── Combat Tension Tracker ──
    # Accumulates tension each turn based on action risk and context.
    # Triggers combat when tension reaches threshold, ensuring reliable but contextual encounters.
    combat_tension = session.world_state.get("combat_tension", 0)
    combat_tension_threshold = 6  # Trigger combat at this level

    if session.world_state.get("combat"):
        # Already in combat — don't accumulate
        combat_tension = 0
    else:
        # Build tension based on action and context
        combat_tension += 1  # Base: +1 per turn

        # Risky actions increase tension faster
        if hasattr(intent, 'risk') and intent.risk in ("high", "extreme"):
            combat_tension += 2
        elif intent.action_type in ("attack", "cast_spell", "intimidate"):
            combat_tension += 2

        # Hostile context increases tension
        situation_lower = session.world_state.get("situation", "").lower()[-200:]
        hostile_words = ["enemy", "hostile", "threat", "undead", "skeleton", "bandit",
                         "guard", " patrol", "monster", "beast", "ambush", "attack",
                         "dark figure", "creature", "demon", "corrupt"]
        if any(w in situation_lower for w in hostile_words):
            combat_tension += 1

        # Combat beat available → increase tension faster
        if combat_beat_available:
            combat_tension += 1

    session.world_state["combat_tension"] = combat_tension
    logger.info(f"Combat tension: {combat_tension}/{combat_tension_threshold}")

    # ── Trigger combat when tension reaches threshold ──
    pending_combat = session.world_state.get("pending_combat", False)
    if combat_tension >= combat_tension_threshold and not session.world_state.get("combat"):
        session.world_state["combat_tension"] = 0
        session.world_state["pending_combat"] = True
        pending_combat = True
        logger.info(f"Combat triggered: tension {combat_tension} >= {combat_tension_threshold}, flagging narrator")

    # Build combat context for narrator if pending
    _combat_ctx = None
    if pending_combat:
        _combat_ctx = (
            "COMBAT_REQUIRED: True. A combat encounter must begin NOW. "
            "Naturally introduce a hostile enemy that fits the current story, location, and narrative. "
            "Name the enemy type explicitly (e.g., 'a skeleton soldier', 'a bandit thug', 'a corrupted wolf'). "
            "Describe the threat emerging and confronting the player. The combat will be resolved by the player."
        )

    if not intent.requires_roll:
        try:
            narration = await narrator.narrate(
                intent=intent,
                outcome_result="narrative_choice",
                roll=0,
                threshold=0,
                player=session.player,
                world_state=session.world_state,
                npc_dialogue=npc_dialogue,
                turn_history=session.turn_history,
                combat_context=_combat_ctx,
            )
        except Exception as e:
            logger.error(f"No-roll narration failed: {e}", exc_info=True)
            narration = f"You {intent.description}. The world shifts around you."

        session.world_state["situation"] = narration
        session.turn_number += 1
        level_up = sm.apply_changes(session, intent, StateChanges(), "narrative_choice")

        # If pending_combat was flagged, extract enemy from narration
        combat_started_no_roll = False
        combat_data_no_roll = None
        combat_source_no_roll = None
        if pending_combat and not session.world_state.get("combat"):
            enemy_name, enemy_key = _extract_enemy_from_narration(narration, session.player.level)
            if enemy_key:
                combat_engine_local: CombatEngine = app.state.combat_engine
                enemy_tier = min(5, max(1, session.player.level))
                combat = combat_engine_local.initiate_combat(
                    player_state=session.player,
                    narrative_context=narration[-200:],
                    enemy_key=enemy_key,
                    enemy_tier=enemy_tier,
                )
                session.world_state["combat"] = combat.model_dump()
                combat_started_no_roll = True
                enemy = combat.enemies[0]
                player_armor = combat_engine_local._calc_player_armor(session.player)
                attack_bonus = combat_engine_local._calc_attack_bonus(session.player)
                combat_data_no_roll = {
                    "combat_id": combat.combat_id,
                    "enemy": {
                        "name": enemy.name,
                        "hp": enemy.hp,
                        "max_hp": enemy.max_hp,
                        "armor": enemy.armor,
                        "attack_bonus": enemy.attack_bonus,
                        "abilities": enemy.abilities,
                    },
                    "player": {
                        "name": session.player.name,
                        "hp": session.player.hp,
                        "max_hp": session.player.max_hp,
                        "mana": session.player.mana,
                        "max_mana": session.player.max_mana,
                        "armor": player_armor,
                        "attack_bonus": attack_bonus,
                        "status_effects": [],
                    },
                    "abilities": session.world_state.get("abilities", []),
                    "inventory": [{"name": i.name, "type": i.item_type, "hp_restore": getattr(i, "hp_restore", 0), "mana_restore": getattr(i, "mana_restore", 0)} for i in session.player.inventory],
                    "enemy_tier": enemy_tier,
                }
                session.world_state["turns_since_combat"] = 0
                session.world_state["combat_tension"] = 0
                session.world_state["pending_combat"] = False
                combat_source_no_roll = "narrator"
                logger.info(f"Combat initiated from narration: {enemy_name} ({enemy_key})")
            else:
                logger.warning("pending_combat flagged but narrator didn't name a recognizable enemy — using fallback")
                enemy_key = _fallback_enemy(session.world_state, session.player.level)[0]
                if enemy_key:
                    combat_engine_local = app.state.combat_engine
                    enemy_tier = min(5, max(1, session.player.level))
                    combat = combat_engine_local.initiate_combat(
                        player_state=session.player,
                        narrative_context=narration[-200:],
                        enemy_key=enemy_key,
                        enemy_tier=enemy_tier,
                    )
                    session.world_state["combat"] = combat.model_dump()
                    combat_started_no_roll = True
                    enemy = combat.enemies[0]
                    player_armor = combat_engine_local._calc_player_armor(session.player)
                    attack_bonus = combat_engine_local._calc_attack_bonus(session.player)
                    combat_data_no_roll = {
                        "combat_id": combat.combat_id,
                        "enemy": {
                            "name": enemy.name,
                            "hp": enemy.hp,
                            "max_hp": enemy.max_hp,
                            "armor": enemy.armor,
                            "attack_bonus": enemy.attack_bonus,
                            "abilities": enemy.abilities,
                        },
                        "player": {
                            "name": session.player.name,
                            "hp": session.player.hp,
                            "max_hp": session.player.max_hp,
                            "mana": session.player.mana,
                            "max_mana": session.player.max_mana,
                            "armor": player_armor,
                            "attack_bonus": attack_bonus,
                            "status_effects": [],
                        },
                        "abilities": session.world_state.get("abilities", []),
                        "inventory": [{"name": i.name, "type": i.item_type, "hp_restore": getattr(i, "hp_restore", 0), "mana_restore": getattr(i, "mana_restore", 0)} for i in session.player.inventory],
                        "enemy_tier": enemy_tier,
                    }
                    session.world_state["turns_since_combat"] = 0
                    session.world_state["combat_tension"] = 0
                    combat_source_no_roll = "fallback"
                session.world_state["pending_combat"] = False

        if campaign_data:
            bp = CampaignBlueprint(**campaign_data)
            beat = planner.get_current_beat(bp)
            if beat:
                # Beat advancement for narrative choices
                if beat.type != "combat":
                    if intent.action_type == "choice" or intent.scale in ["moderate", "major", "extreme", "cosmic"] or turns_in_beat >= 4:
                        bp_adv = planner.advance_beat(bp)
                        if bp_adv.current_act == bp.current_act and bp_adv.current_beat == bp.current_beat and _is_campaign_complete(bp):
                            session.world_state["campaign_ended"] = True
                            await _record_campaign_end(db, session, "victory")
                        else:
                            bp = bp_adv
                            session.world_state["campaign"] = bp.model_dump()
                            beat = planner.get_current_beat(bp)
                            session.world_state["turns_in_beat"] = 0
                
                if beat:
                    current_beat_title = beat.title

        turn = Turn(
            turn_number=session.turn_number,
            player_input=req.action,
            intent=intent,
            score=None,
            roll=0,
            outcome=Outcome(
                result="narrative_choice",
                roll=0,
                threshold=0,
                narration=narration,
                state_changes=StateChanges(),
            ),
        )
        session.turn_history.append(turn)
        await db.save_turn(session_id, turn)
        await db.save_session(session)

        return ActionResponse(
            turn_number=session.turn_number,
            intent=intent,
            requires_roll=False,
            outcome="narrative_choice",
            narration=clean_narration(narration),
            state_changes=StateChanges(),
            player_hp=session.player.hp,
            player_mana=session.player.mana,
            player_level=session.player.level,
            player_xp=session.player.xp,
            player_xp_to_next=session.player.xp_to_next,
            max_hp=session.player.max_hp,
            max_mana=session.player.max_mana,
            inventory=[{"name": i.name, "type": i.item_type} for i in session.player.inventory],
            level_up=level_up,
            current_beat=current_beat_title,
            npc_dialogue=npc_dialogue,
            npcs=[{"name": n.get("personality",{}).get("name","?"), "role": n.get("personality",{}).get("role","?"), "disposition": n.get("disposition",0)} for n in session.world_state.get("npcs", {}).values()],
            choices=extract_choices(narration),
            combat_started=combat_started_no_roll,
            combat_data=combat_data_no_roll,
            campaign_ended=session.world_state.get("campaign_ended", False),
            game_over=False,
            victory=session.world_state.get("campaign_ended", False),
            campaign_objective=campaign_objective,
            dice_result=None,
            combat_source=combat_source_no_roll,
            warning_count=warning_count,
            warning_message=warning_message_out,
            dice_debug=None,
        )

    # 3. Vector similarity for probability scoring
    similarity = 0.5  # Default
    try:
        similarity = await retriever.get_narrative_similarity(intent.description)
        logger.debug(f"Vector similarity: {similarity}")
    except Exception as e:
        logger.warning(f"Similarity lookup failed: {e}")

    # Narrative relevance bonus from campaign
    narrative_bonus = 0.0
    if campaign_data:
        bp = CampaignBlueprint(**campaign_data)
        beat = planner.get_current_beat(bp)
        if beat:
            narrative_bonus = planner.get_narrative_relevance_bonus(bp, intent.description)

    # 4. Probability Calculation (with vector similarity + context alignment + status effects)
    # Normalize status effects: PlayerState uses list[str], combat uses list[dict]
    raw_effects = session.player.status_effects if hasattr(session.player, 'status_effects') and session.player.status_effects else []
    player_status_effects = []
    for se in raw_effects:
        if isinstance(se, dict):
            player_status_effects.append(se.get("name", ""))
        elif isinstance(se, str):
            player_status_effects.append(se)

    score = prob_engine.calculate(
        intent, session.player,
        similarity=0.5 + narrative_bonus + (similarity - 0.5),
        context_alignment=alignment,
        status_effects=player_status_effects,
    )

    # 5. Dice Roll & Outcome
    roll = dice_engine.roll_d20()
    outcome_result = dice_engine.resolve(roll, score.dice_threshold, intent.action_type)

    # 6. Narrative Generation
    try:
        narration = await narrator.narrate(
            intent=intent,
            outcome_result=outcome_result,
            roll=roll,
            threshold=score.dice_threshold,
            player=session.player,
            world_state=session.world_state,
            npc_dialogue=npc_dialogue,
            turn_history=session.turn_history,
            combat_context=_combat_ctx,
        )
    except Exception as e:
        narration = f"Your {intent.action_type} results in {outcome_result}."

    # 7. State changes
    state_changes = _compute_state_changes(intent, outcome_result, roll)
    level_up = sm.apply_changes(session, intent, state_changes, outcome_result)

    # 7b. Check for player death
    is_dead, death_message = _check_player_death(session)
    if is_dead:
        session.world_state["campaign_ended"] = True
        session.world_state["status"] = "failed"
        await _record_campaign_end(db, session, "defeat")
        session.turn_number += 1
        turn = Turn(
            turn_number=session.turn_number,
            player_input=req.action,
            intent=intent,
            score=score,
            roll=roll,
            outcome=Outcome(result="player_death", roll=roll, threshold=score.dice_threshold, narration=death_message, state_changes=state_changes),
        )
        session.turn_history.append(turn)
        await db.save_turn(session_id, turn)
        await db.save_session(session)

        logger.info(f"PLAYER DEATH: {session.player.name} at turn {session.turn_number}")

        return ActionResponse(
            turn_number=session.turn_number, intent=intent, requires_roll=True,
            probability=score.probability, dice_threshold=score.dice_threshold, roll=roll,
            outcome="player_death", narration=death_message, state_changes=state_changes,
            player_hp=0, player_mana=session.player.mana,
            player_level=session.player.level, player_xp=session.player.xp,
            player_xp_to_next=session.player.xp_to_next,
            max_hp=session.player.max_hp, max_mana=session.player.max_mana,
            inventory=[{"name": i.name, "type": i.item_type} for i in session.player.inventory],
            level_up={}, current_beat=current_beat_title, npc_dialogue=None, npcs=[],
            choices=[], combat_started=False, combat_data=None, campaign_ended=True,
            game_over=True, victory=False, campaign_objective=campaign_objective,
            dice_result={"rolled": roll, "target": score.dice_threshold,
                        "success": False, "critical": outcome_result == "critical_failure",
                        "type": "check"},
            combat_source=None,
            warning_count=warning_count,
            warning_message=None,
            game_over_reason="death",
        )

    # 7c. Build dice_result for frontend animation
    dice_result_payload = {
        "rolled": roll,
        "target": score.dice_threshold,
        "success": outcome_result in ("success", "critical_success", "partial_success"),
        "critical": outcome_result in ("critical_success", "critical_failure"),
        "type": "attack" if intent.action_type in ("attack", "cast_spell") else "skill" if intent.action_type in ("persuade", "intimidate", "deceive") else "check",
    }


    # 10. Update world state
    session.world_state["situation"] = narration
    session.turn_number += 1

    # 11. Advance story beat & check for combat triggers
    combat_started = False
    combat_data = None
    combat_source = None
    if campaign_data:
        bp = CampaignBlueprint(**campaign_data)
        beat = planner.get_current_beat(bp)
        
        if beat:
            if beat.type == "combat":
                # Beat requires combat — narrator already introduced it via pending_combat flag.
                # Extract enemy name from the narration and create combat_data.
                if not session.world_state.get("combat"):
                    enemy_name, enemy_key = _extract_enemy_from_narration(narration, session.player.level)
                    if enemy_key:
                        combat_engine_local: CombatEngine = app.state.combat_engine
                        enemy_tier = min(5, max(1, session.player.level))
                        combat = combat_engine_local.initiate_combat(
                            player_state=session.player,
                            narrative_context=narration[-200:],
                            enemy_key=enemy_key,
                            enemy_tier=enemy_tier,
                        )
                        session.world_state["combat"] = combat.model_dump()
                        combat_started = True
                        combat_beat_available = True
                        enemy = combat.enemies[0]
                        player_armor = combat_engine_local._calc_player_armor(session.player)
                        attack_bonus = combat_engine_local._calc_attack_bonus(session.player)
                        combat_data = {
                            "combat_id": combat.combat_id,
                            "enemy": {
                                "name": enemy.name,
                                "hp": enemy.hp,
                                "max_hp": enemy.max_hp,
                                "armor": enemy.armor,
                                "attack_bonus": enemy.attack_bonus,
                                "abilities": enemy.abilities,
                            },
                            "player": {
                                "name": session.player.name,
                                "hp": session.player.hp,
                                "max_hp": session.player.max_hp,
                                "mana": session.player.mana,
                                "max_mana": session.player.max_mana,
                                "armor": player_armor,
                                "attack_bonus": attack_bonus,
                                "status_effects": [],
                            },
                            "abilities": session.world_state.get("abilities", []),
                            "inventory": [{"name": i.name, "type": i.item_type, "hp_restore": getattr(i, "hp_restore", 0), "mana_restore": getattr(i, "mana_restore", 0)} for i in session.player.inventory],
                            "enemy_tier": enemy_tier,
                        }
                        session.world_state["turns_since_combat"] = 0
                        session.world_state["combat_tension"] = 0
                        session.world_state["pending_combat"] = False
                        combat_source = "beat"
                    else:
                        # Narrator didn't name a recognizable enemy — use fallback
                        logger.info("Beat type=combat but narrator didn't name enemy — using fallback")
                        fb_key, fb_name = _fallback_enemy(session.world_state, session.player.level)
                        if fb_key:
                            combat_engine_local = app.state.combat_engine
                            enemy_tier = min(5, max(1, session.player.level))
                            combat = combat_engine_local.initiate_combat(
                                player_state=session.player,
                                narrative_context=narration[-200:],
                                enemy_key=fb_key,
                                enemy_tier=enemy_tier,
                            )
                            session.world_state["combat"] = combat.model_dump()
                            combat_started = True
                            combat_beat_available = True
                            enemy = combat.enemies[0]
                            player_armor = combat_engine_local._calc_player_armor(session.player)
                            attack_bonus = combat_engine_local._calc_attack_bonus(session.player)
                            combat_data = {
                                "combat_id": combat.combat_id,
                                "enemy": {
                                    "name": enemy.name,
                                    "hp": enemy.hp,
                                    "max_hp": enemy.max_hp,
                                    "armor": enemy.armor,
                                    "attack_bonus": enemy.attack_bonus,
                                    "abilities": enemy.abilities,
                                },
                                "player": {
                                    "name": session.player.name,
                                    "hp": session.player.hp,
                                    "max_hp": session.player.max_hp,
                                    "mana": session.player.mana,
                                    "max_mana": session.player.max_mana,
                                    "armor": player_armor,
                                    "attack_bonus": attack_bonus,
                                    "status_effects": [],
                                },
                                "abilities": session.world_state.get("abilities", []),
                                "inventory": [{"name": i.name, "type": i.item_type, "hp_restore": getattr(i, "hp_restore", 0), "mana_restore": getattr(i, "mana_restore", 0)} for i in session.player.inventory],
                                "enemy_tier": enemy_tier,
                            }
                            session.world_state["turns_since_combat"] = 0
                            session.world_state["combat_tension"] = 0
                            combat_source = "fallback"
                        else:
                            # Even fallback failed — advance beat
                            bp_adv = planner.advance_beat(bp)
                            if bp_adv.current_act == bp.current_act and bp_adv.current_beat == bp.current_beat and _is_campaign_complete(bp):
                                session.world_state["campaign_ended"] = True
                            else:
                                bp = bp_adv
                                session.world_state["campaign"] = bp.model_dump()
                                beat = planner.get_current_beat(bp)
                                session.world_state["turns_in_beat"] = 0
            else:
                # Advance if successfully addressed or max pacing reached
                if outcome_result in ["success", "critical_success", "partial_success"] or narrative_bonus > 0.0 or turns_in_beat >= 4:
                    bp_adv = planner.advance_beat(bp)
                    if bp_adv.current_act == bp.current_act and bp_adv.current_beat == bp.current_beat and _is_campaign_complete(bp):
                        session.world_state["campaign_ended"] = True
                    else:
                        bp = bp_adv
                        session.world_state["campaign"] = bp.model_dump()
                        beat = planner.get_current_beat(bp)
                        session.world_state["turns_in_beat"] = 0

                # Handle pending_combat on a non-combat beat
                if pending_combat and not combat_started and not session.world_state.get("combat"):
                    enemy_name, enemy_key = _extract_enemy_from_narration(narration, session.player.level)
                    if enemy_key:
                        combat_engine_local = app.state.combat_engine
                        enemy_tier = min(5, max(1, session.player.level))
                        combat = combat_engine_local.initiate_combat(
                            player_state=session.player,
                            narrative_context=narration[-200:],
                            enemy_key=enemy_key,
                            enemy_tier=enemy_tier,
                        )
                        session.world_state["combat"] = combat.model_dump()
                        combat_started = True
                        enemy = combat.enemies[0]
                        player_armor = combat_engine_local._calc_player_armor(session.player)
                        attack_bonus = combat_engine_local._calc_attack_bonus(session.player)
                        combat_data = {
                            "combat_id": combat.combat_id,
                            "enemy": {
                                "name": enemy.name,
                                "hp": enemy.hp,
                                "max_hp": enemy.max_hp,
                                "armor": enemy.armor,
                                "attack_bonus": enemy.attack_bonus,
                                "abilities": enemy.abilities,
                            },
                            "player": {
                                "name": session.player.name,
                                "hp": session.player.hp,
                                "max_hp": session.player.max_hp,
                                "mana": session.player.mana,
                                "max_mana": session.player.max_mana,
                                "armor": player_armor,
                                "attack_bonus": attack_bonus,
                                "status_effects": [],
                            },
                            "abilities": session.world_state.get("abilities", []),
                            "inventory": [{"name": i.name, "type": i.item_type, "hp_restore": getattr(i, "hp_restore", 0), "mana_restore": getattr(i, "mana_restore", 0)} for i in session.player.inventory],
                            "enemy_tier": enemy_tier,
                        }
                        session.world_state["turns_since_combat"] = 0
                        session.world_state["combat_tension"] = 0
                        session.world_state["pending_combat"] = False
                        combat_source = "narrator"
                        logger.info(f"Combat initiated from narration (roll path): {enemy_name} ({enemy_key})")
                    else:
                        logger.warning("pending_combat flagged but narrator didn't name enemy (roll path) — using fallback")
                        fb_key, fb_name = _fallback_enemy(session.world_state, session.player.level)
                        if fb_key:
                            combat_engine_local_fb = app.state.combat_engine
                            enemy_tier = min(5, max(1, session.player.level))
                            combat = combat_engine_local_fb.initiate_combat(
                                player_state=session.player,
                                narrative_context=narration[-200:],
                                enemy_key=fb_key,
                                enemy_tier=enemy_tier,
                            )
                            session.world_state["combat"] = combat.model_dump()
                            combat_started = True
                            enemy = combat.enemies[0]
                            player_armor = combat_engine_local_fb._calc_player_armor(session.player)
                            attack_bonus = combat_engine_local_fb._calc_attack_bonus(session.player)
                            combat_data = {
                                "combat_id": combat.combat_id,
                                "enemy": {
                                    "name": enemy.name,
                                    "hp": enemy.hp,
                                    "max_hp": enemy.max_hp,
                                    "armor": enemy.armor,
                                    "attack_bonus": enemy.attack_bonus,
                                    "abilities": enemy.abilities,
                                },
                                "player": {
                                    "name": session.player.name,
                                    "hp": session.player.hp,
                                    "max_hp": session.player.max_hp,
                                    "mana": session.player.mana,
                                    "max_mana": session.player.max_mana,
                                    "armor": player_armor,
                                    "attack_bonus": attack_bonus,
                                    "status_effects": [],
                                },
                                "abilities": session.world_state.get("abilities", []),
                                "inventory": [{"name": i.name, "type": i.item_type, "hp_restore": getattr(i, "hp_restore", 0), "mana_restore": getattr(i, "mana_restore", 0)} for i in session.player.inventory],
                                "enemy_tier": enemy_tier,
                            }
                            session.world_state["turns_since_combat"] = 0
                            session.world_state["combat_tension"] = 0
                            combat_source = "fallback"
                        session.world_state["pending_combat"] = False
        
        if beat:
            current_beat_title = beat.title
    # 12. Record turn
    turn = Turn(
        turn_number=session.turn_number,
        player_input=req.action,
        intent=intent,
        score=score,
        roll=roll,
        outcome=Outcome(
            result=outcome_result,
            roll=roll,
            threshold=score.dice_threshold,
            narration=narration,
            state_changes=state_changes,
        ),
    )
    session.turn_history.append(turn)

    # 13. Persist
    await db.save_turn(session_id, turn)
    await db.save_session(session)

    logger.info(
        f"Turn {session.turn_number}: '{intent.action_type}' "
        f"→ {outcome_result} (roll={roll}, threshold={score.dice_threshold}, sim={similarity:.2f})"
    )

    return ActionResponse(
        turn_number=session.turn_number,
        intent=intent,
        requires_roll=True,
        probability=score.probability,
        dice_threshold=score.dice_threshold,
        roll=roll,
        outcome=outcome_result,
        narration=clean_narration(narration),
        state_changes=state_changes,
        player_hp=session.player.hp,
        player_mana=session.player.mana,
        player_level=session.player.level,
        player_xp=session.player.xp,
        player_xp_to_next=session.player.xp_to_next,
        max_hp=session.player.max_hp,
        max_mana=session.player.max_mana,
        inventory=[{"name": i.name, "type": i.item_type} for i in session.player.inventory],
        level_up=level_up,
        current_beat=current_beat_title,
        combat_source=combat_source,
        combat_beat_available=False,
        current_act=session.world_state.get("current_act", 1),
        npc_dialogue=npc_dialogue,
        npcs=[{"name": n.get("personality",{}).get("name","?"), "role": n.get("personality",{}).get("role","?"), "disposition": n.get("disposition",0)} for n in session.world_state.get("npcs", {}).values()],
        choices=extract_choices(narration),
        combat_started=combat_started,
        combat_data=combat_data,
        campaign_ended=session.world_state.get("campaign_ended", False),
        game_over=False,
        victory=session.world_state.get("campaign_ended", False),
        campaign_objective=campaign_objective,
        dice_result=dice_result_payload,
        warning_count=warning_count,
        warning_message=warning_message_out,
        dice_debug={
            "stat_bonus": round(score.breakdown.stat_bonus, 3),
            "difficulty": round(score.breakdown.difficulty, 3),
            "context_alignment": round(score.breakdown.context_alignment, 3),
            "status_effect_modifier": round(score.breakdown.status_effect_modifier, 3),
            "similarity": round(score.breakdown.similarity, 3),
            "novelty_bonus": round(score.breakdown.novelty_bonus, 3),
            "saturation_penalty": round(score.breakdown.saturation_penalty, 3),
            "final_target": score.dice_threshold,
        },
    )


# ─── Combat Endpoints (Client-Side Resolution) ───

@app.post("/session/{session_id}/combat/init")
async def init_combat(session_id: str, enemy_tier: int = 1, enemy_key: str | None = None):
    """Initiate a combat encounter. Returns all data for client-side resolution."""
    sm: StateManager = app.state.state_manager
    db: Database = app.state.db
    combat_engine: CombatEngine = app.state.combat_engine

    session = sm.get_session(session_id)
    if not session:
        session = await db.load_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

    context = session.world_state.get("situation", "")[:200]
    
    # Tier scales with player level
    effective_tier = min(5, max(1, enemy_tier))
    
    combat = combat_engine.initiate_combat(
        player_state=session.player,
        enemy_tier=effective_tier,
        enemy_key=enemy_key,
        narrative_context=context,
    )
    session.world_state["combat"] = combat.model_dump()
    session.world_state["turns_since_combat"] = 0
    session.world_state["combat_tension"] = 0
    
    await db.save_session(session)

    enemy = combat.enemies[0]
    player_armor = combat_engine._calc_player_armor(session.player)
    attack_bonus = combat_engine._calc_attack_bonus(session.player)

    return {
        "combat_id": combat.combat_id,
        "enemy": {
            "name": enemy.name,
            "hp": enemy.hp,
            "max_hp": enemy.max_hp,
            "armor": enemy.armor,
            "attack_bonus": enemy.attack_bonus,
            "abilities": enemy.abilities,
        },
        "player": {
            "name": session.player.name,
            "hp": combat.player.hp,
            "max_hp": combat.player.max_hp,
            "mana": combat.player.mana,
            "max_mana": combat.player.max_mana,
            "armor": player_armor,
            "attack_bonus": attack_bonus,
            "status_effects": [],
        },
        "abilities": session.world_state.get("abilities", []),
        "inventory": [{"name": i.name, "type": i.item_type, "hp_restore": getattr(i, "hp_restore", 0), "mana_restore": getattr(i, "mana_restore", 0)} for i in session.player.inventory],
        "enemy_tier": effective_tier,
        "message": f"A {enemy.name} appears! Prepare for battle!",
    }


@app.post("/session/{session_id}/combat/resolve")
async def resolve_combat(session_id: str, req: CombatResolveRequest):
    """Accept final combat result from client-side resolution.
    
    The client runs the entire combat locally (dice, damage, AI, effects).
    This endpoint handles: XP, loot, HP/mana sync, beat advancement, and narration.
    """
    sm: StateManager = app.state.state_manager
    db: Database = app.state.db
    narrator: Narrator = app.state.narrator
    combat_engine: CombatEngine = app.state.combat_engine

    session = sm.get_session(session_id)
    if not session:
        session = await db.load_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

    # Sync player HP/mana from combat
    session.player.hp = max(0, min(session.player.max_hp, req.player_hp))
    session.player.mana = max(0, min(session.player.max_mana, req.player_mana))

    rewards = {"xp": 0, "items": [], "loot_descriptions": []}
    narration = ""
    choices = []

    if req.result == "victory":
        # Calculate rewards using enemy name lookup
        from data.enemies import ENEMY_TEMPLATES, roll_loot
        enemy_key = next((k for k, v in ENEMY_TEMPLATES.items() if v.name == req.enemy_name), None)
        if enemy_key:
            template = ENEMY_TEMPLATES[enemy_key]
            rewards["xp"] = template.xp_reward
            loot = roll_loot(template)
            for entry in loot:
                item = Item(
                    name=entry["name"],
                    item_type=entry.get("type", "misc"),
                    description=f"Looted from {req.enemy_name}",
                    stat_bonus=entry.get("stat_bonus", {}),
                    hp_restore=entry.get("hp_restore", 0),
                    mana_restore=entry.get("mana_restore", 0),
                )
                rewards["items"].append(item)
                rewards["loot_descriptions"].append(f"Found: {entry['name']}")
            session.player.inventory.extend(rewards["items"])
        
        session.player.gain_xp(rewards["xp"])

        # Generate post-combat narration using the MAIN narrator (70B, full campaign context)
        log_summary = "; ".join([f"{e.get('actor','')}: {e.get('message','')}" for e in req.combat_log[-4:]])
        combat_intent = ActionIntent(
            action_type="explore",
            description=f"After defeating a {req.enemy_name} in combat ({req.turns_taken} turns, key moments: {log_summary}), survey the aftermath and continue the journey.",
            scale="moderate",
            risk="low",
            relevant_stat="wisdom",
            requires_roll=False,
        )
        try:
            narration = await narrator.narrate(
                intent=combat_intent,
                outcome_result="success",
                roll=0,
                threshold=0,
                player=session.player,
                world_state=session.world_state,
                turn_history=session.turn_history,
            )
        except Exception:
            narration = f"The {req.enemy_name} falls. The battle is won. What lies ahead?"
        
        choices = extract_choices(narration)
        session.world_state["situation"] = narration

        # Advance beat on victory
        campaign_data = session.world_state.get("campaign")
        if campaign_data:
            planner = app.state.campaign_planner
            bp = CampaignBlueprint(**campaign_data)
            bp_adv = planner.advance_beat(bp)
            if bp_adv.current_act == bp.current_act and bp_adv.current_beat == bp.current_beat and _is_campaign_complete(bp):
                session.world_state["campaign_ended"] = True
                await _record_campaign_end(db, session, "victory")
            else:
                bp = bp_adv
                session.world_state["campaign"] = bp.model_dump()

    elif req.result == "defeat":
        combat_intent = ActionIntent(
            action_type="explore",
            description=f"Recover from defeat by a {req.enemy_name}. The player barely survived.",
            scale="major",
            risk="high",
            relevant_stat="constitution",
            requires_roll=False,
        )
        try:
            narration = await narrator.narrate(
                intent=combat_intent,
                outcome_result="failure",
                roll=0,
                threshold=0,
                player=session.player,
                world_state=session.world_state,
                turn_history=session.turn_history,
            )
        except Exception:
            narration = f"The {req.enemy_name} overwhelms you. Darkness takes hold..."
        
        choices = extract_choices(narration)
        session.world_state["situation"] = narration

    # ── Check player death after combat ──
    is_dead, death_message = _check_player_death(session)
    game_over = False
    victory = False
    if is_dead:
        game_over = True
        session.world_state["campaign_ended"] = True
        session.world_state["status"] = "failed"
        await _record_campaign_end(db, session, "defeat")
        narration = death_message
        choices = []

    campaign_ended_flag = session.world_state.get("campaign_ended", False)
    if campaign_ended_flag and not is_dead:
        victory = True

    # Clean up combat state
    session.world_state.pop("combat", None)
    await db.save_session(session)

    # Check level up
    level_up = {}
    # XP was already applied via gain_xp, check if level changed
    # (gain_xp handles level ups internally)

    return {
        "result": req.result,
        "narration": narration,
        "rewards": rewards,
        "choices": choices,
        "player_hp": session.player.hp,
        "player_mana": session.player.mana,
        "player_level": session.player.level,
        "player_xp": session.player.xp,
        "player_xp_to_next": session.player.xp_to_next,
        "max_hp": session.player.max_hp,
        "max_mana": session.player.max_mana,
        "inventory": [{"name": i.name, "type": i.item_type} for i in session.player.inventory],
        "campaign_ended": campaign_ended_flag,
        "game_over": game_over,
        "victory": victory,
        "campaign_objective": session.world_state.get("campaign_objective", ""),
        "combat_source": None,
    }


@app.get("/session/{session_id}/combat")
async def get_combat_state(session_id: str):
    """Get current combat state."""
    sm: StateManager = app.state.state_manager
    session = sm.get_session(session_id)
    if not session:
        db: Database = app.state.db
        session = await db.load_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

    combat_data = session.world_state.get("combat")
    if not combat_data:
        return {"active": False}
    combat = CombatState(**combat_data)
    enemy = combat.enemies[0] if combat.enemies else None
    return {
        "active": True,
        "status": combat.status,
        "turn": combat.turn_number,
        "current_turn": combat.current_turn,
        "enemy": {"name": enemy.name, "hp": enemy.hp, "max_hp": enemy.max_hp} if enemy else None,
        "player": {"hp": combat.player.hp, "max_hp": combat.player.max_hp} if combat.player else None,
    }


@app.get("/session/{session_id}/history")
async def get_history(session_id: str, limit: int = 20):
    sm: StateManager = app.state.state_manager
    session = sm.get_session(session_id)
    if not session:
        db: Database = app.state.db
        session = await db.load_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    return session.turn_history[-limit:]


@app.get("/session/{session_id}/npcs")
async def get_session_npcs(session_id: str):
    """Get all NPCs in the current session."""
    sm: StateManager = app.state.state_manager
    session = sm.get_session(session_id)
    if not session:
        db: Database = app.state.db
        session = await db.load_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

    npcs_data = session.world_state.get("npcs", {})
    return [
        {
            "name": NPCState(**npc).personality.name,
            "role": NPCState(**npc).personality.role,
            "disposition": NPCState(**npc).disposition,
            "trust": NPCState(**npc).trust,
            "interacted": NPCState(**npc).interacted,
            "alive": NPCState(**npc).alive,
        }
        for npc in npcs_data.values()
    ]


def _compute_state_changes(intent: ActionIntent, outcome: str, roll: int) -> StateChanges:
    changes = StateChanges()

    if intent.uses_resource and intent.resource_cost > 0:
        changes.mana_delta = -intent.resource_cost

    if outcome == "critical_success":
        changes.mana_delta += 5
    elif outcome == "partial_success":
        if intent.risk in ("high", "extreme"):
            changes.hp_delta = -5
    elif outcome == "failure":
        if intent.risk in ("medium", "high", "extreme"):
            changes.hp_delta = -5
    elif outcome == "critical_failure":
        damage = 10 if intent.scale in ("minor", "moderate") else 20
        changes.hp_delta = -damage
        if intent.risk in ("high", "extreme"):
            changes.status_effects_added.append("stunned")

    # Debug logging for stat changes
    if changes.hp_delta != 0 or changes.mana_delta != 0:
        logger.info(f"State change: hp_delta={changes.hp_delta}, mana_delta={changes.mana_delta}, trigger={outcome}")

    return changes


# ─── Campaign history helper ───

async def _record_campaign_end(db: Database, session, result: str):
    """Save completed campaign to history. Called once per campaign end."""
    # Prevent duplicate saves
    if session.world_state.get("campaign_saved"):
        return
    session.world_state["campaign_saved"] = True

    campaign = session.world_state.get("campaign", {})
    title = campaign.get("title", "Unknown Campaign")
    cls = session.world_state.get("character_class", "unknown")
    user_id = session.world_state.get("user_id")

    # Fallback: if no user_id on session, try admin (default user)
    if not user_id:
        admin_user = await db.get_user_by_username("admin")
        if admin_user:
            user_id = admin_user["id"]
            logger.info(f"Campaign history: using admin fallback for session {session.session_id}")

    if user_id:
        try:
            await db.save_campaign_history(
                user_id=user_id,
                session_id=session.session_id,
                title=title,
                result=result,
                turns=session.turn_number,
                character_class=cls,
            )
            logger.info(f"\u2705 Campaign history saved: {title} ({result}, {session.turn_number} turns, user={user_id})")
        except Exception as e:
            logger.error(f"\u274c Failed to save campaign history: {e}", exc_info=True)
            session.world_state["campaign_saved"] = False  # Allow retry
    else:
        logger.warning(f"Campaign history skipped \u2014 no user_id for session {session.session_id}")


# ─── Enemy extraction from narration ───

def _extract_enemy_from_narration(narration: str, player_level: int) -> tuple[str | None, str | None]:
    """Extract enemy name from narrator output and match to an enemy template.
    
    The narrator writes the enemy naturally into the story. We parse the narration
    to find what enemy was mentioned and match it to the closest template.
    
    Returns (enemy_name, enemy_key).
    """
    from data.enemies import ENEMY_TEMPLATES, ENEMIES_BY_TIER
    import random
    rng = random.Random()
    narration_lower = narration.lower()
    enemy_tier = min(5, max(1, player_level))

    # Keyword → enemy_key mapping (same as before but now used only for matching)
    keyword_map = {
        "goblin": "goblin_scavenger", "scavenger": "goblin_scavenger",
        "skeleton": "skeleton_soldier", "bone": "skeleton_soldier", "undead": "skeleton_soldier", "zombie": "skeleton_soldier",
        "rat": "giant_rat", "vermin": "giant_rat",
        "bandit": "bandit_thug", "thug": "bandit_thug", "thief": "bandit_thug", "robber": "bandit_thug", "brigand": "bandit_thug",
        "wolf": "corrupted_wolf", "hound": "corrupted_wolf", "beast": "corrupted_wolf",
        "archer": "undead_archer",
        "knight": "dark_knight", "armored": "dark_knight", "warrior": "dark_knight", "soldier": "dark_knight",
        "mage": "shadow_mage", "sorcerer": "shadow_mage", "wizard": "shadow_mage", "witch": "shadow_mage",
        "horror": "crypt_horror", "abomination": "crypt_horror", "creature": "crypt_horror",
        "dragon": "dragon_whelp", "wyrm": "dragon_whelp", "drake": "dragon_whelp",
        "vampire": "vampire_lord", "blood": "vampire_lord",
        "demon": "demon_guardian", "fiend": "demon_guardian",
        "lich": "lich_king", "necromancer": "lich_king",
    }

    # Find all keyword matches with tier proximity
    matches = []
    for keyword, enemy_key in keyword_map.items():
        if keyword in narration_lower and enemy_key in ENEMY_TEMPLATES:
            tmpl = ENEMY_TEMPLATES[enemy_key]
            tier_diff = abs(tmpl.tier - enemy_tier)
            matches.append((tier_diff, enemy_key))

    if matches:
        matches.sort(key=lambda x: x[0])
        best_key = matches[0][1]
        return ENEMY_TEMPLATES[best_key].name, best_key

    # No match found — return None (narrator didn't name a recognized enemy)
    return None, None


def _fallback_enemy(world_state: dict, player_level: int) -> tuple[str, str]:
    """Fallback enemy selection when narrator extraction fails.
    
    Uses location/campaign context to pick a reasonable enemy.
    Guarantees combat happens when required.
    
    Returns (enemy_key, enemy_name).
    """
    from data.enemies import ENEMY_TEMPLATES, ENEMIES_BY_TIER
    import random
    rng = random.Random()
    enemy_tier = min(5, max(1, player_level))

    location = world_state.get("location", "").lower()
    situation = world_state.get("situation", "")[-300:].lower()
    campaign = world_state.get("campaign", {})
    themes = " ".join(campaign.get("key_themes", []))
    title = campaign.get("title", "").lower()
    premise = campaign.get("premise", "").lower()

    all_text = f"{location} {situation} {themes} {title} {premise}"

    # Location-aware fallback mapping
    location_map = {
        "crypt": ["skeleton_soldier", "undead_archer"],
        "grave": ["skeleton_soldier", "crypt_horror"],
        "dungeon": ["skeleton_soldier", "undead_archer", "giant_rat"],
        "cave": ["goblin_scavenger", "giant_rat", "corrupted_wolf"],
        "mine": ["goblin_scavenger", "bandit_thug"],
        "forest": ["corrupted_wolf", "giant_rat", "bandit_thug"],
        "swamp": ["giant_rat", "crypt_horror"],
        "ruin": ["skeleton_soldier", "goblin_scavenger", "undead_archer"],
        "castle": ["dark_knight", "shadow_mage"],
        "tower": ["shadow_mage", "dark_knight"],
        "city": ["bandit_thug", "dark_knight"],
        "town": ["bandit_thug"],
        "village": ["bandit_thug", "giant_rat"],
        "mountain": ["goblin_scavenger", "dark_knight"],
        "volcano": ["demon_guardian"],
    }

    # Try location match first
    for loc_keyword, candidates in location_map.items():
        if loc_keyword in all_text:
            # Filter by tier proximity
            valid = [c for c in candidates if c in ENEMY_TEMPLATES and abs(ENEMY_TEMPLATES[c].tier - enemy_tier) <= 2]
            if valid:
                chosen = rng.choice(valid)
                return chosen, ENEMY_TEMPLATES[chosen].name

    # Theme-based fallback
    theme_map = {
        "undead": "skeleton_soldier", "necro": "undead_archer", "death": "crypt_horror",
        "demon": "demon_guardian", "fire": "demon_guardian", "hell": "demon_guardian",
        "dragon": "dragon_whelp", "wyrm": "dragon_whelp",
        "bandit": "bandit_thug", "thief": "bandit_thug",
        "magic": "shadow_mage", "arcane": "shadow_mage",
        "wolf": "corrupted_wolf", "beast": "corrupted_wolf",
        "goblin": "goblin_scavenger",
    }
    for theme, enemy_key in theme_map.items():
        if theme in all_text and enemy_key in ENEMY_TEMPLATES:
            tmpl = ENEMY_TEMPLATES[enemy_key]
            if abs(tmpl.tier - enemy_tier) <= 2:
                return enemy_key, tmpl.name

    # Absolute fallback — tier-appropriate random
    keys = ENEMIES_BY_TIER.get(enemy_tier, [])
    if not keys:
        keys = ENEMIES_BY_TIER.get(max(1, enemy_tier - 1), [])
    if keys:
        chosen = rng.choice(keys)
        return chosen, ENEMY_TEMPLATES[chosen].name

    # Nuclear fallback
    return "bandit_thug", ENEMY_TEMPLATES["bandit_thug"].name


def _check_player_death(session) -> tuple[bool, str]:
    """Check if the player has died. Returns (is_dead, failure_message)."""
    if session.player.hp <= 0:
        return True, (
            f"The darkness closes in around {session.player.name}. "
            f"Your wounds are too grave. The adventure ends here, "
            f"fallen hero."
        )
    return False, ""


# ─── Auth Routes ──────────────────────────────────────────────────────────────

@app.post("/auth/login", response_model=TokenResponse)
async def login(req: UserLogin):
    db: Database = app.state.db
    user = await db.get_user_by_username(req.username)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user["id"], "username": user["username"], "role": user["role"]})
    return TokenResponse(access_token=token)


@app.post("/auth/tester-request")
async def tester_request(req: TesterRequest):
    import re
    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", req.email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    db: Database = app.state.db
    result = await db.create_tester_request(req.email)
    return {"detail": "Tester request submitted", "id": result["id"]}


@app.post("/auth/create-user", response_model=UserResponse)
async def create_user(req: UserCreate, admin: dict = Depends(require_admin)):
    db: Database = app.state.db
    existing = await db.get_user_by_username(req.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    user = await db.create_user(req.username, hash_password(req.password))
    return UserResponse(**user)


@app.get("/user/me", response_model=UserResponse)
async def get_me(user: dict = Depends(require_auth)):
    db: Database = app.state.db
    full_user = await db.get_user_by_id(user["id"])
    if not full_user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(id=full_user["id"], username=full_user["username"],
                        role=full_user["role"], created_at=full_user["created_at"])


@app.get("/user/dashboard")
async def get_dashboard(user: dict = Depends(require_auth)):
    db: Database = app.state.db
    history = await db.get_campaign_history(user["id"])
    stats = await db.get_user_stats(user["id"])
    return {"user": {"id": user["id"], "username": user["username"], "role": user["role"]},
            "campaigns": history, "stats": stats}


@app.post("/user/logout")
async def logout(user: dict = Depends(require_auth)):
    return {"detail": "Logged out"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=config.API_HOST, port=config.API_PORT, reload=True)
