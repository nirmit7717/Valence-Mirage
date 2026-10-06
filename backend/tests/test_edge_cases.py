"""Edge-case tests for parsing, probability, dice, state changes, and API validation.

Converted from the old live-server script. Everything here runs offline:
LLM calls are faked and the database is a temporary SQLite file.
Live-model narration checks live in tests/live/ (opt-in).
"""

import asyncio
from types import SimpleNamespace

import pytest

import main
from engines.dice import DiceEngine
from engines.intent_parser import IntentParser
from engines.probability import ProbabilityEngine
from helpers import act, create_session, make_intent
from models.game_state import PlayerState

VALID_OUTCOMES = {"critical_success", "success", "partial_success", "failure", "critical_failure"}


# ─── Intent parsing ───


class _FakeCompletions:
    def __init__(self, content: str):
        self._content = content

    async def create(self, **kwargs):
        message = SimpleNamespace(content=self._content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def test_intent_parser_falls_back_on_invalid_json():
    parser = IntentParser()
    parser.client = SimpleNamespace(chat=SimpleNamespace(completions=_FakeCompletions("not json at all")))

    intent = asyncio.run(parser.parse("asdfghjkl qwertyuiop", "Location: nowhere.", "STR=10"))

    assert intent.action_type == "other"
    assert intent.description == "asdfghjkl qwertyuiop"
    assert intent.relevant_stat == "wisdom"


def test_intent_parser_accepts_valid_json():
    parser = IntentParser()
    payload = (
        '{"action_type": "attack", "description": "swing the sword", "scale": "moderate", '
        '"risk": "medium", "target": "goblin", "relevant_stat": "strength", '
        '"uses_resource": false, "resource_cost": 0, "requires_roll": true, "suggested_choices": []}'
    )
    parser.client = SimpleNamespace(chat=SimpleNamespace(completions=_FakeCompletions(payload)))

    intent = asyncio.run(parser.parse("I swing my sword", "Location: road.", "STR=14"))

    assert intent.action_type == "attack"
    assert intent.relevant_stat == "strength"
    assert intent.requires_roll is True


# ─── Probability engine ───


@pytest.mark.parametrize("scale", ["extreme", "cosmic"])
def test_huge_actions_get_hard_thresholds(scale):
    score = ProbabilityEngine().calculate(make_intent(scale=scale, requires_roll=True), PlayerState())
    assert score.dice_threshold >= 10
    assert score.probability < 0.5


def test_minor_actions_get_easy_thresholds():
    score = ProbabilityEngine().calculate(make_intent(scale="minor", requires_roll=True), PlayerState())
    assert score.dice_threshold <= 10


def test_repeated_actions_are_penalized():
    engine = ProbabilityEngine()
    intent = make_intent(action_type="attack", scale="moderate", requires_roll=True)
    fresh = engine.calculate(intent, PlayerState())
    repeated = engine.calculate(intent, PlayerState(action_history=["attack"] * 5))
    assert repeated.probability < fresh.probability
    assert repeated.breakdown.saturation_penalty < 0


# ─── Dice engine ───


@pytest.mark.parametrize("probability", [0.0, 0.01, 0.25, 0.5, 0.75, 0.99, 1.0])
def test_threshold_is_always_between_2_and_20(probability):
    assert 2 <= ProbabilityEngine._dice_threshold(probability) <= 20


def test_roll_is_always_between_1_and_20():
    rolls = {DiceEngine.roll_d20() for _ in range(500)}
    assert rolls <= set(range(1, 21))


@pytest.mark.parametrize("threshold", range(2, 21))
def test_outcome_is_always_valid(threshold):
    engine = DiceEngine()
    for roll in range(1, 21):
        assert engine.resolve(roll, threshold, "explore") in VALID_OUTCOMES


# ─── State changes ───


@pytest.mark.parametrize("outcome", ["failure", "critical_failure"])
def test_risky_failure_costs_hp(outcome):
    changes = main._compute_state_changes(make_intent(risk="high", requires_roll=True), outcome, 3)
    assert changes.hp_delta < 0


def test_safe_success_costs_no_hp():
    changes = main._compute_state_changes(make_intent(risk="low", requires_roll=True), "success", 15)
    assert changes.hp_delta == 0


# ─── API robustness ───


def test_unknown_session_returns_404(client):
    response = act(client, "nonexistent-id", {}, "test")
    assert response.status_code == 404


def test_missing_action_field_returns_422(client):
    session_id, headers = create_session(client)
    response = client.post(f"/session/{session_id}/action", json={}, headers=headers)
    assert response.status_code == 422


def test_whitespace_only_action_returns_422(client):
    session_id, headers = create_session(client)
    response = act(client, session_id, headers, "   ")
    assert response.status_code == 422


def test_action_at_length_limit_is_accepted(client):
    session_id, headers = create_session(client)
    action = ("I attack " * 30)[:200]
    assert len(action) == 200
    response = act(client, session_id, headers, action)
    assert response.status_code == 200, response.text


def test_action_over_length_limit_is_rejected(client):
    session_id, headers = create_session(client)
    response = act(client, session_id, headers, "x" * 201)
    assert response.status_code == 422


@pytest.mark.parametrize(
    "action",
    [
        "Run",
        "asdfghjkl qwertyuiop zxcvbnm",
        "I summon the power of ★☆★ and cast 召唤术 🔥",
        "I sit and cry about my lost homeland",
        "I want to check my inventory and see what items I have",
        "I draw my sword, kick down the door, and scream a battle cry",
    ],
)
def test_unusual_inputs_are_accepted(client, action):
    session_id, headers = create_session(client)
    response = act(client, session_id, headers, action)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["intent"]["action_type"]
    assert body["intent"]["relevant_stat"]
