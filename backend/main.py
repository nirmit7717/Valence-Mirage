"""Valence Mirage — FastAPI Game Server (Phase 1 with improvements)"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from engines import IntentParser, ProbabilityEngine, DiceEngine, Narrator, StateManager
from engines.campaign_planner import CampaignPlanner, CampaignBlueprint
from models.action import ActionIntent
from models.game_state import GameSession, Turn
from models.outcome import Outcome, StateChanges, ProbabilityScore, ScoreBreakdown
import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("valence_mirage")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.intent_parser = IntentParser()
    app.state.probability = ProbabilityEngine()
    app.state.dice = DiceEngine()
    app.state.narrator = Narrator()
    app.state.state_manager = StateManager()
    app.state.campaign_planner = CampaignPlanner()
    logger.info("Valence Mirage server initialized — all engines ready")
    yield
    logger.info("Valence Mirage server shutting down")


app = FastAPI(
    title="Valence Mirage",
    description="AI-powered narrative engine with probabilistic dice mechanics",
    version="0.2.0",
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
    current_beat: str | None = None  # Current story beat title
    choices: list[str] = []  # Available choices if DM presents them


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/health")
async def health():
    return {
        "name": "Valence Mirage",
        "version": "0.2.0",
        "status": "running",
        "active_sessions": len(app.state.state_manager._sessions),
    }


@app.post("/session/new", response_model=dict)
async def create_session(req: NewSessionRequest = NewSessionRequest()):
    sm: StateManager = app.state.state_manager
    planner: CampaignPlanner = app.state.campaign_planner

    # Generate campaign blueprint
    blueprint = await planner.generate_blueprint(req.player_name)

    # Create session with blueprint context
    session = sm.create_session(player_name=req.player_name)
    session.world_state["campaign"] = blueprint.model_dump()
    session.world_state["location"] = blueprint.setting
    session.world_state["situation"] = blueprint.premise

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
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.post("/session/{session_id}/action", response_model=ActionResponse)
async def submit_action(session_id: str, req: ActionRequest):
    sm: StateManager = app.state.state_manager
    session = sm.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    planner: CampaignPlanner = app.state.campaign_planner
    parser: IntentParser = app.state.intent_parser
    prob_engine: ProbabilityEngine = app.state.probability
    dice_engine: DiceEngine = app.state.dice
    narrator: Narrator = app.state.narrator

    stats_summary = (
        f"STR={session.player.stats.strength} "
        f"INT={session.player.stats.intelligence} "
        f"DEX={session.player.stats.dexterity} "
        f"CON={session.player.stats.control} "
        f"CHA={session.player.stats.charisma} "
        f"WIS={session.player.stats.wisdom}"
    )
    world_context = (
        f"Location: {session.player.name} is at {session.world_state.get('location', 'unknown')}. "
        f"{session.world_state.get('situation', '')}"
    )

    # Add campaign context for the intent parser
    campaign_data = session.world_state.get("campaign")
    if campaign_data:
        bp = CampaignBlueprint(**campaign_data)
        beat = planner.get_current_beat(bp)
        if beat:
            world_context += f" Current story beat: {beat.title} — {beat.description}"

    # 1. Intent Parsing
    try:
        intent = await parser.parse(req.action, world_context, stats_summary)
    except Exception as e:
        logger.error(f"Intent parsing API error: {e}")
        raise HTTPException(status_code=503, detail=f"AI service unavailable: {e}")

    # 2. Check if roll is needed
    if not intent.requires_roll:
        # No-roll path: narrate directly without dice
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
            logger.error(f"Narration error: {e}")
            narration = f"You {intent.description}. The world shifts around you."

        session.world_state["situation"] = narration[-300:]
        session.turn_number += 1
        session.player.action_history.append(intent.action_type)

        # Check if we should advance the story beat
        choices = []
        current_beat_title = None
        if campaign_data:
            bp = planner.advance_beat(CampaignBlueprint(**campaign_data))
            session.world_state["campaign"] = bp.model_dump()
            beat = planner.get_current_beat(bp)
            if beat:
                current_beat_title = beat.title
                # If the beat is a choice type, present options
                if beat.type == "choice":
                    choices = [f"Option {i+1}: {b.title}" for i, b in enumerate(
                        [b for a in bp.acts if a.act_id == bp.current_act for b in a.beats if b.beat_id == bp.current_beat]
                    )]

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

        return ActionResponse(
            turn_number=session.turn_number,
            intent=intent,
            requires_roll=False,
            outcome="narrative_choice",
            narration=narration,
            state_changes=StateChanges(),
            player_hp=session.player.hp,
            player_mana=session.player.mana,
            current_beat=current_beat_title,
            choices=choices,
        )

    # 3. Probability Calculation (with narrative relevance)
    narrative_bonus = 0.0
    current_beat_title = None
    if campaign_data:
        bp = CampaignBlueprint(**campaign_data)
        beat = planner.get_current_beat(bp)
        if beat:
            current_beat_title = beat.title
            narrative_bonus = planner.get_narrative_relevance_bonus(bp, intent.description)

    score = prob_engine.calculate(intent, session.player, similarity=0.5 + narrative_bonus)

    # 4. Dice Roll & Outcome
    roll = dice_engine.roll_d20()
    outcome_result = dice_engine.resolve(roll, score.dice_threshold, intent.action_type)

    # 5. Narrative Generation
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
        logger.error(f"Narration API error: {e}")
        narration = f"Your {intent.action_type} results in {outcome_result}."

    # 6. State changes
    state_changes = _compute_state_changes(intent, outcome_result, roll)
    sm.apply_changes(session, intent, state_changes)

    # 7. Update world state
    session.world_state["situation"] = narration[-300:]
    session.turn_number += 1

    # 8. Advance story beat if appropriate
    choices = []
    if campaign_data:
        bp = CampaignBlueprint(**campaign_data)
        bp = planner.advance_beat(bp)
        session.world_state["campaign"] = bp.model_dump()
        beat = planner.get_current_beat(bp)
        if beat:
            current_beat_title = beat.title

    # 9. Record turn
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

    logger.info(
        f"Turn {session.turn_number}: '{intent.action_type}' roll={intent.requires_roll} "
        f"→ {outcome_result} (roll={roll}, threshold={score.dice_threshold})"
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
        current_beat=current_beat_title,
        choices=choices,
    )


@app.get("/session/{session_id}/history")
async def get_history(session_id: str, limit: int = 20):
    sm: StateManager = app.state.state_manager
    session = sm.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.turn_history[-limit:]


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
