"""Valence Mirage — FastAPI Game Server (Phase 3: Intelligence)"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from engines import IntentParser, ProbabilityEngine, DiceEngine, Narrator, StateManager
from engines.campaign_planner import CampaignPlanner, CampaignBlueprint
from engines.loot_engine import LootEngine
from engines.narrative_guard import NarrativeGuard
from engines.npc_engine import NPCEngine, NPCState, NPCPersonality
from models.action import ActionIntent
from models.game_state import GameSession, Turn
from models.outcome import Outcome, StateChanges, ProbabilityScore, ScoreBreakdown
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
    app.state.loot_engine = LootEngine()
    app.state.narrative_guard = NarrativeGuard()
    app.state.npc_engine = NPCEngine()

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


from pydantic import BaseModel, Field


class NewSessionRequest(BaseModel):
    player_name: str = Field(default="Adventurer", max_length=50)
    keywords: str = Field(default="", max_length=200, description="Keywords/themes for the adventure")


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
    choices: list[str] = []
    npc_dialogue: dict | None = None
    guard_warning: str | None = None


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

    # Generate campaign blueprint
    blueprint = await planner.generate_blueprint(req.player_name, keywords=req.keywords)

    # Create session
    session = sm.create_session(player_name=req.player_name)
    session.world_state["campaign"] = blueprint.model_dump()
    session.world_state["location"] = blueprint.setting
    session.world_state["situation"] = blueprint.premise

    # Generate campaign NPCs
    try:
        npcs = await npc_engine.generate_campaign_npcs(blueprint.premise, count=3)
        session.world_state["npcs"] = {npc.npc_id: npc.model_dump() for npc in npcs}
    except Exception as e:
        logger.warning(f"NPC generation failed: {e}")
        session.world_state["npcs"] = {}

    await db.save_session(session)

    logger.info(f"New session: {session.session_id} — '{req.player_name}' — Campaign: {blueprint.title}")

    return {
        "session_id": session.session_id,
        "player": session.player.model_dump(),
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
    guard: NarrativeGuard = app.state.narrative_guard
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

    # 0. Narrative Guard — check for coherence breaking
    guard_warning = None
    try:
        world_ctx = session.world_state.get("situation", "")[:200]
        guard_result = await guard.check_action(req.action, world_ctx)
        if guard_result.get("break_detected"):
            redirect = guard_result.get("suggested_redirect", "Try a different approach.")
            guard_warning = f"The world resists your attempt to break its rules. {redirect}"
            logger.info(f"Guard blocked action: {guard_result.get('reason')}")
    except Exception as e:
        logger.warning(f"Guard check skipped: {e}")

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
    if campaign_data:
        bp = CampaignBlueprint(**campaign_data)
        beat = planner.get_current_beat(bp)
        if beat:
            world_context += f" Current story beat: {beat.title} — {beat.description}"
            current_beat_title = beat.title

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
            )
        except Exception as e:
            narration = f"You {intent.description}. The world shifts around you."

        session.world_state["situation"] = narration[-300:]
        session.turn_number += 1
        level_up = sm.apply_changes(session, intent, StateChanges(), "narrative_choice")

        if campaign_data:
            bp = planner.advance_beat(CampaignBlueprint(**campaign_data))
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
            narration=narration,
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
            guard_warning=guard_warning,
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
        )
    except Exception as e:
        narration = f"Your {intent.action_type} results in {outcome_result}."

    # 7. State changes
    state_changes = _compute_state_changes(intent, outcome_result, roll)
    level_up = sm.apply_changes(session, intent, state_changes, outcome_result)

    # 8. Loot generation
    if outcome_result in ("critical_success", "success", "partial_success"):
        loot: LootEngine = app.state.loot_engine
        loot_context = f"{intent.description} in {session.world_state.get('location', 'unknown')}"
        try:
            loot_item = await loot.generate_loot(intent, outcome_result, loot_context)
            if loot_item:
                session.player.inventory.append(loot_item)
                state_changes.items_gained.append(loot_item.name)
        except Exception as e:
            logger.warning(f"Loot generation failed: {e}")

    # 10. Update world state
    session.world_state["situation"] = narration[-300:]
    session.turn_number += 1

    # 11. Advance story beat
    if campaign_data:
        bp = CampaignBlueprint(**campaign_data)
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
        narration=narration,
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
        npc_dialogue=npc_dialogue,
        guard_warning=guard_warning,
    )


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
