"""Valence Mirage — FastAPI Game Server (Phase 3: Intelligence)"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from engines import IntentParser, ProbabilityEngine, DiceEngine, Narrator, StateManager
from engines.campaign_planner import CampaignPlanner, CampaignBlueprint
from engines.npc_engine import NPCEngine, NPCState, NPCPersonality
from engines.combat_engine import CombatEngine
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

    logger.info("Valence Mirage v0.3.0 initialized — engines + DB + vector search + NPCs ready")
    yield

    # Persist all active sessions before shutdown
    sm: StateManager = app.state.state_manager
    for sid in sm.list_sessions():
        session = sm.get_session(sid)
        if session:
            await db.save_full_session(session)
    await db.close()
    logger.info("Valence Mirage server shutting down — sessions persisted")


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
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
import re

def extract_choices(narration: str) -> list[str]:
    """Extract → prefixed suggestions from narration."""
    import re
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
    import re
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


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/health")
async def health():
    return {
        "name": "Valence Mirage",
        "version": "0.3.0",
        "status": "running",
        "active_sessions": len(app.state.state_manager._sessions),
        "db": "connected",
        "vector_search": "enabled" if app.state.rule_retriever._use_vector else "keyword_fallback",
    }


@app.post("/session/new", response_model=dict)
async def create_session(req: NewSessionRequest = NewSessionRequest()):
    sm: StateManager = app.state.state_manager
    planner: CampaignPlanner = app.state.campaign_planner
    npc_engine: NPCEngine = app.state.npc_engine
    db: Database = app.state.db

    # Create session
    session = sm.create_session(player_name=req.player_name)

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

    # Track current beat for combat triggers
    if blueprint.acts and blueprint.acts[0].beats:
        session.world_state["current_act"] = blueprint.acts[0].act_id
        session.world_state["current_beat"] = blueprint.acts[0].beats[0].beat_id
    else:
        session.world_state["current_act"] = 1
        session.world_state["current_beat"] = 1

    # Generate campaign NPCs
    try:
        npcs = await npc_engine.generate_campaign_npcs(blueprint.premise, count=1)
        session.world_state["npcs"] = {npc.npc_id: npc.model_dump() for npc in npcs}
    except Exception as e:
        logger.warning(f"NPC generation failed: {e}")
        session.world_state["npcs"] = {}

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
        "npcs": [
            {"name": npc.personality.name, "role": npc.personality.role, "disposition": npc.disposition}
            for npc in npcs
        ] if session.world_state.get("npcs") else [],
        "world_state": {
            "location": session.world_state.get("location", ""),
            "situation": session.world_state.get("situation", ""),
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

    # 2. Check if roll is needed
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
                )
        except Exception as e:
            logger.error(f"No-roll narration failed: {e}", exc_info=True)
            narration = f"You {intent.description}. The world shifts around you."

        session.world_state["situation"] = narration
        session.turn_number += 1
        level_up = sm.apply_changes(session, intent, StateChanges(), "narrative_choice")

        if campaign_data:
            bp = CampaignBlueprint(**campaign_data)
            beat = planner.get_current_beat(bp)
            if beat:
                # Beat Lock Logic for narrative choices
                if beat.type != "combat":
                    if intent.action_type == "choice" or intent.scale in ["moderate", "major", "extreme", "cosmic"]:
                        bp = planner.advance_beat(bp)
                        session.world_state["campaign"] = bp.model_dump()
                        beat = planner.get_current_beat(bp)
                
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
        combat_started=False,
        combat_data=None,
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

    # 4. Probability Calculation (with vector similarity)
    score = prob_engine.calculate(intent, session.player, similarity=0.5 + narrative_bonus + (similarity - 0.5))

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
        )
    except Exception as e:
        narration = f"Your {intent.action_type} results in {outcome_result}."

    # 7. State changes
    state_changes = _compute_state_changes(intent, outcome_result, roll)
    level_up = sm.apply_changes(session, intent, state_changes, outcome_result)


    # 10. Update world state
    session.world_state["situation"] = narration
    session.turn_number += 1

    # 11. Advance story beat (CONDITIONAL)
    combat_started = False
    combat_data = None
    if campaign_data:
        bp = CampaignBlueprint(**campaign_data)
        beat = planner.get_current_beat(bp)
        
        if beat:
            if beat.type == "combat":
                # Auto-ambush
                if not session.world_state.get("combat"):
                    enemy_name = None
                    try:
                        resp = await app.state.intent_parser.client.chat.completions.create(
                            model=config.INTENT_MODEL,
                            messages=[
                                {"role": "system", "content": "Extract ONLY the name of the enemy or monster described in this text. Reply with just the noun phrase (e.g., 'Pale Woman', 'Skeleton Soldier')."},
                                {"role": "user", "content": narration[-300:]}
                            ],
                            temperature=0.1,
                            max_tokens=10
                        )
                        enemy_name = resp.choices[0].message.content.strip().replace('"', '')
                    except Exception as e:
                        logger.warning(f"Failed to extract enemy name: {e}")
                    
                    combat = app.state.combat_engine.initiate_combat(
                        player_state=session.player, 
                        narrative_context=narration[-200:],
                        enemy_name_override=enemy_name
                    )
                    session.world_state["combat"] = combat.model_dump()
                    combat_started = True
                    enemy = combat.enemies[0]
                    combat_data = {
                        "enemy": {"name": enemy.name, "hp": enemy.hp, "max_hp": enemy.max_hp, "armor": enemy.armor, "status_effects": []},
                        "player": {"hp": combat.player.hp, "max_hp": combat.player.max_hp, "mana": combat.player.mana, "max_mana": combat.player.max_mana, "status_effects": []},
                        "abilities": session.world_state.get("abilities", [])
                    }
                    narration += f"\n\n**⚔️ AMBUSH! A {enemy.name} attacks!**"
            else:
                # Advance if successfully addressed
                if outcome_result in ["success", "critical_success", "partial_success"] or narrative_bonus > 0.0:
                    bp = planner.advance_beat(bp)
                    session.world_state["campaign"] = bp.model_dump()
                    beat = planner.get_current_beat(bp)
            
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
        combat_beat_available=False,
        current_act=session.world_state.get("current_act", 1),
        npc_dialogue=npc_dialogue,
        npcs=[{"name": n.get("personality",{}).get("name","?"), "role": n.get("personality",{}).get("role","?"), "disposition": n.get("disposition",0)} for n in session.world_state.get("npcs", {}).values()],
        choices=extract_choices(narration),
        combat_started=combat_started,
        combat_data=combat_data
    )


# ─── Combat Endpoints ───

@app.post("/session/{session_id}/combat/start")
async def start_combat(session_id: str, enemy_tier: int = 1, enemy_key: str | None = None):
    """Initiate a combat encounter."""
    sm: StateManager = app.state.state_manager
    db: Database = app.state.db
    combat_engine: CombatEngine = app.state.combat_engine

    session = sm.get_session(session_id)
    if not session:
        session = await db.load_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

    context = session.world_state.get("situation", "")[:200]
    combat = combat_engine.initiate_combat(
        player_state=session.player,
        enemy_tier=enemy_tier,
        enemy_key=enemy_key,
        narrative_context=context,
    )
    session.world_state["combat"] = combat.model_dump()
    await db.save_session(session)

    enemy = combat.enemies[0]
    return {
        "combat_id": combat.combat_id,
        "enemy": {"name": enemy.name, "hp": enemy.hp, "max_hp": enemy.max_hp, "armor": enemy.armor},
        "player": {"hp": combat.player.hp, "max_hp": combat.player.max_hp, "mana": combat.player.mana, "max_mana": combat.player.max_mana},
        "turn": combat.turn_number,
        "status": combat.status,
        "message": f"A {enemy.name} appears! Prepare for battle!",
    }


@app.post("/session/{session_id}/combat/action")
async def combat_action(session_id: str, ability_name: str = "Attack", target: str = ""):
    """Execute a player combat action."""
    sm: StateManager = app.state.state_manager
    db: Database = app.state.db
    combat_engine: CombatEngine = app.state.combat_engine
    narrator: Narrator = app.state.narrator

    session = sm.get_session(session_id)
    if not session:
        session = await db.load_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

    combat_data = session.world_state.get("combat")
    if not combat_data:
        raise HTTPException(status_code=400, detail="No active combat")
    combat = CombatState(**combat_data)
    if combat.status != "active":
        raise HTTPException(status_code=400, detail=f"Combat is {combat.status}")

    # Find the ability
    abilities = session.world_state.get("abilities", [])
    chosen = None
    for a in abilities:
        if a["name"].lower() == ability_name.lower():
            chosen = a
            break

    # Determine action type
    if ability_name.lower() == "flee":
        action_type = CombatActionType.FLEE
    elif chosen:
        atype = chosen.get("ability_type", "attack")
        action_type = CombatActionType(atype) if atype in [e.value for e in CombatActionType] else CombatActionType.ATTACK
    else:
        action_type = CombatActionType.ATTACK

    action = CombatAction(
        actor="player",
        action_type=action_type,
        ability_name=ability_name,
        damage_dice=chosen.get("damage_dice", "1d6") if chosen else "1d6",
        mana_cost=chosen.get("mana_cost", 0) if chosen else 0,
        status_effect=chosen.get("status_effect") if chosen else None,
        status_duration=chosen.get("status_duration", 0) if chosen else 0,
        target=target or (combat.enemies[0].name if combat.enemies else ""),
    )

    # Tick player effects
    combat = combat_engine.tick_player_effects(combat)

    # Resolve player action
    combat = combat_engine.resolve_player_action(combat, action)
    player_log = combat.log[-1].message if combat.log else ""

    # Enemy turn if combat still active
    enemy_log = ""
    if combat.status == "active":
        combat = combat_engine.resolve_enemy_action(combat)
        enemy_log = combat.log[-1].message if combat.log else ""

    combat.turn_number += 1

    # Combat narration
    narration = ""
    full_action = f"{player_log} {enemy_log}".strip()
    
    if combat.status in ["victory", "defeat"]:
        try:
            narration = await narrator.narrate_combat_action(
                action_description=f"The battle against the enemy has ended in {combat.status}. {full_action}. Describe the immediate aftermath briefly and provide exactly 3 actionable exploration choices using the format:\n→ [action 1]\n→ [action 2]\n→ [action 3]",
                result=combat.status,
                character_class=session.player.character_class,
            )
        except Exception:
            narration = f"{full_action}\nThe battle is over. Describe your next action."
        # Push back to world state
        session.world_state["situation"] = narration
    else:
        # User requested no detailed generation during combat to reduce verbosity, UI logs handle the details.
        narration = ""

    # Handle combat end
    rewards = {"xp": 0, "items": [], "loot_descriptions": []}
    if combat.status in ("victory", "defeat"):
        if combat.status == "victory":
            rewards = combat_engine.get_combat_rewards(combat)
            session.player.gain_xp(rewards["xp"])
            for item in rewards["items"]:
                session.player.inventory.append(item)
            
            # ADVANCE BEAT ON VICTORY
            campaign_data = session.world_state.get("campaign")
            if campaign_data:
                planner = app.state.campaign_planner
                bp = CampaignBlueprint(**campaign_data)
                bp = planner.advance_beat(bp)
                session.world_state["campaign"] = bp.model_dump()
        # Sync combat HP back to player
        if combat.player:
            session.player.hp = combat.player.hp
            session.player.mana = combat.player.mana
        session.world_state.pop("combat", None)
    else:
        # Sync HP/mana mid-combat
        if combat.player:
            session.player.hp = combat.player.hp
            session.player.mana = combat.player.mana
        session.world_state["combat"] = combat.model_dump()

    await db.save_session(session)

    # Build enemy info
    enemy_info = None
    if combat.enemies:
        e = combat.enemies[0]
        enemy_info = {"name": e.name, "hp": e.hp, "max_hp": e.max_hp,
                      "armor": e.armor, "status_effects": [se.name for se in e.status_effects]}

    choices = []
    if narration and ("→" in narration or "-" in narration):
        choices = extract_choices(narration)

    return {
        "narration": narration,
        "player_log": player_log,
        "enemy_log": enemy_log,
        "combat_status": combat.status,
        "enemy": enemy_info,
        "player": {"hp": session.player.hp, "max_hp": session.player.max_hp,
                    "mana": session.player.mana, "max_mana": session.player.max_mana,
                    "status_effects": [se.name for se in combat.player.status_effects] if combat.player else []},
        "turn": combat.turn_number,
        "rewards": rewards,
        "abilities": abilities,
        "inventory": [{"name": i.name, "description": i.description, "type": i.item_type} for i in session.player.inventory],
        "choices": choices,
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

    return changes


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=config.API_HOST, port=config.API_PORT, reload=True)
