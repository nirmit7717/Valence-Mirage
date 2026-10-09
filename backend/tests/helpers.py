"""Test helpers and fakes shared across the offline suite."""

import main
from engines.campaign_planner import CampaignPlanner
from models.action import ActionIntent

DEFAULT_NARRATION = (
    "The torchlight gutters as you take stock of your surroundings.\n"
    "→ Search the room\n"
    "→ Listen at the door\n"
    "→ Move on"
)


def make_intent(**overrides) -> ActionIntent:
    """Build an ActionIntent with safe no-roll defaults."""
    data = {
        "action_type": "explore",
        "description": "look around",
        "scale": "minor",
        "risk": "low",
        "relevant_stat": "wisdom",
        "requires_roll": False,
    }
    data.update(overrides)
    return ActionIntent(**data)


# ─── Fakes for network-backed services ───


class FakeIntentParser:
    """Returns a configurable intent instead of calling the LLM."""

    def __init__(self):
        self.next_intent: ActionIntent | None = None
        self.queue: list[ActionIntent] = []
        self.calls: list[str] = []

    async def parse(self, player_input: str, world_context: str, stats_summary: str) -> ActionIntent:
        self.calls.append(player_input)
        if self.queue:
            intent = self.queue.pop(0)
        elif self.next_intent is not None:
            intent = self.next_intent
        else:
            intent = make_intent(description=player_input[:200])
        # main.py mutates the intent (forced rolls), so hand out copies.
        return intent.model_copy(deep=True)


class FakeNarrator:
    """Returns configurable narration and records every call."""

    def __init__(self):
        self.text = DEFAULT_NARRATION
        self.epilogue_text = "The last foe falls. Peace settles over the land, and the tale is told for years."
        self.calls: list[dict] = []
        self.epilogue_calls: list[dict] = []

    async def narrate(self, **kwargs) -> str:
        self.calls.append(kwargs)
        return self.text

    async def narrate_epilogue(self, **kwargs) -> str:
        self.epilogue_calls.append(kwargs)
        return self.epilogue_text

    async def narrate_opening(self, **kwargs) -> str:
        return DEFAULT_NARRATION

    async def narrate_combat_action(self, *args, **kwargs) -> str:
        return "Steel rings against steel."


class FakeRuleRetriever:
    _use_vector = False

    async def get_narrative_similarity(self, action_description: str) -> float:
        return 0.5

    async def get_relevant_rules(self, action_type: str, context: str = "", top_k: int = 3) -> str:
        return ""


class FakeEnemyDesigner:
    """Stands in for the LLM enemy reader. Returns `spec` (None = fall through to heuristics)."""

    def __init__(self):
        self.spec = None
        self.calls: list[dict] = []

    async def describe(self, *, narration, world_state, threat_hint=None):
        self.calls.append({"narration": narration, "threat_hint": threat_hint})
        return self.spec


class FakeNPCEngine:
    async def generate_dialogue(self, npc, player_action, player_name="Adventurer") -> dict:
        return {"dialogue": "...", "disposition_change": 0.0, "trust_change": 0.0, "wants_to_fight": False}


def make_planner() -> CampaignPlanner:
    """Real planner logic with the LLM blueprint call replaced by the fallback blueprint."""
    planner = CampaignPlanner()

    async def fake_generate_blueprint(player_name="Adventurer", keywords="", template=None, beat_weights=None):
        # Same structure guarantee as the real planner: shaped like the requested template.
        return CampaignPlanner._fallback_blueprint(player_name, template)

    planner.generate_blueprint = fake_generate_blueprint
    return planner


# ─── API helpers ───


def new_session(client, headers: dict | None = None, **body) -> tuple[dict, dict]:
    """POST /session/new and return (response_json, headers_for_follow_up_calls).

    Follow-up headers include the guest token when the server issues one.
    """
    payload = {"player_name": "Tester", "character_class": "warrior", "campaign_size": "medium"}
    payload.update(body)
    response = client.post("/session/new", json=payload, headers=headers or {})
    assert response.status_code == 200, response.text
    data = response.json()
    follow_up = dict(headers or {})
    if data.get("guest_token"):
        follow_up["X-Session-Token"] = data["guest_token"]
    return data, follow_up


def create_session(client, headers: dict | None = None, **body) -> tuple[str, dict]:
    data, follow_up = new_session(client, headers=headers, **body)
    return data["session_id"], follow_up


def get_session(session_id: str):
    """Return the in-memory GameSession for direct state manipulation in tests."""
    return main.app.state.state_manager.get_session(session_id)


def act(client, session_id: str, headers: dict, action: str = "I look around"):
    return client.post(f"/session/{session_id}/action", json={"action": action}, headers=headers)


# ─── Campaign structure helpers ───


def campaign_beats(session_id: str) -> list[tuple[int, dict]]:
    """All beats of the session's campaign in story order, as (act_id, beat_dict)."""
    campaign = get_session(session_id).world_state["campaign"]
    acts = sorted(campaign["acts"], key=lambda a: a["act_id"])
    return [(act["act_id"], beat) for act in acts for beat in act["beats"]]


def move_to_beat(session_id: str, index: int) -> dict:
    """Jump the campaign to the beat at ``index`` in story order (negative = from the end)."""
    act_id, beat = campaign_beats(session_id)[index]
    world = get_session(session_id).world_state
    world["campaign"]["current_act"] = act_id
    world["campaign"]["current_beat"] = beat["beat_id"]
    world["turns_in_beat"] = 0
    return beat


def move_to_first_beat_of_type(session_id: str, beat_type: str) -> dict:
    index = next(i for i, (_, beat) in enumerate(campaign_beats(session_id)) if beat["type"] == beat_type)
    return move_to_beat(session_id, index)


def use_legacy_campaign(session_id: str) -> None:
    """Swap in the pre-template 9-beat campaign (sessions saved before turn budgets existed).

    Its last beat is a non-combat "climax", so a story action can end the campaign.
    """
    legacy = CampaignPlanner._fallback_blueprint("Tester").model_dump()
    for act in legacy["acts"]:
        for beat in act["beats"]:
            beat.pop("min_turns", None)
            beat.pop("max_turns", None)
            beat.pop("threat_hint", None)
    world = get_session(session_id).world_state
    world["campaign"] = legacy
    world["campaign_template"] = {}
    world["turns_in_beat"] = 0


def win_fight(client, session_id: str, headers: dict, combat_data: dict, turns_taken: int = 30, **overrides):
    """Resolve the active fight as a valid victory."""
    return resolve_fight(client, session_id, headers, combat_data, turns_taken=turns_taken, **overrides)


def lose_fight(client, session_id: str, headers: dict, combat_data: dict, turns_taken: int = 3):
    """Resolve the active fight as a defeat (player at 0 HP)."""
    return resolve_fight(client, session_id, headers, combat_data, turns_taken=turns_taken,
                         result="defeat", player_hp=0)


def resolve_fight(client, session_id: str, headers: dict, combat_data: dict, turns_taken: int = 30, **overrides):
    """POST /combat/resolve for the active fight; defaults describe a valid victory."""
    body = {
        "combat_id": combat_data["combat_id"],
        "result": "victory",
        "player_hp": combat_data["player"]["hp"],
        "player_mana": combat_data["player"]["mana"],
        "enemy_name": combat_data["enemy"]["name"],
        "items_used": [],
        "combat_log": [],
        "turns_taken": turns_taken,
    }
    body.update(overrides)
    return client.post(f"/session/{session_id}/combat/resolve", headers=headers, json=body)


GOBLIN_SCENE = "A goblin scavenger lunges from the shadows, blade raised."


def start_planned_fight(client, app_state, narration: str = GOBLIN_SCENE, **session_body):
    """New session moved to its first planned fight; one action starts it.

    Returns (session_id, headers, combat_data).
    """
    app_state.intent_parser.next_intent = make_intent(description="inspect stonework")
    app_state.narrator.text = narration
    session_id, headers = create_session(client, **session_body)
    move_to_first_beat_of_type(session_id, "combat")
    body = act(client, session_id, headers).json()
    assert body["combat_started"] is True, body
    return session_id, headers, body["combat_data"]
