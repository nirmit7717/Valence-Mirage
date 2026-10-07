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
        self.calls: list[dict] = []

    async def narrate(self, **kwargs) -> str:
        self.calls.append(kwargs)
        return self.text

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
        return CampaignPlanner._fallback_blueprint(player_name)

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
