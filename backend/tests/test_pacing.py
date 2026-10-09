"""Turn-budget pacing: campaigns last their intended length and end on the boss fight.

Short 8-10 turns / 3 fights, Standard 13-15 / 5, Grand Saga 20-25 / 7. Story
beats finish when the player moves them on (inside their window) or are forced
to wrap up when they run out of turns. A fight is one turn. Surprise fights are
only allowed where they can't break the budget.
"""

import random

import pytest

from data.campaign_templates import CAMPAIGN_TEMPLATES
from engines import pacing
from engines.campaign_planner import CampaignPlanner
from engines.dice import DiceEngine
from helpers import (
    act,
    campaign_beats,
    create_session,
    get_session,
    make_intent,
    start_planned_fight,
    use_legacy_campaign,
    win_fight,
)

SIZES = {
    # size: (min_turns, max_turns, fights)
    "small": (8, 10, 3),
    "medium": (13, 15, 5),
    "large": (20, 25, 7),
}

ACTIONS = [
    "I search the area carefully",
    "I follow the trail ahead",
    "I study the old markings",
    "I press on toward the goal",
]


def _campaign(size: str | None) -> dict:
    """A fresh outline as a dict: shaped like the size's template, or the legacy 9-beat one."""
    template = CAMPAIGN_TEMPLATES[size] if size else None
    return CampaignPlanner._fallback_blueprint("Tester", template).model_dump()


def _at(campaign: dict, index: int) -> dict:
    act_data, beat = pacing.ordered_beats(campaign)[index]
    campaign["current_act"], campaign["current_beat"] = act_data["act_id"], beat["beat_id"]
    return campaign


# ─── Windows and budgets ───


def test_windows_add_up_the_beat_budgets():
    # Short: story, fight, story, elite fight, boss fight.
    assert pacing.beat_windows(_campaign("small")) == [(1, 2), (3, 4), (4, 6), (6, 8), (8, 10)]


@pytest.mark.parametrize("size", SIZES)
def test_turn_budget_matches_the_size(size):
    low, high, _ = SIZES[size]
    assert pacing.turn_budget(_campaign(size)) == (low, high)


def test_beats_saved_without_budgets_use_type_defaults():
    assert pacing._budget({"type": "combat"}) == (2, 2)
    assert pacing._budget({"type": "combat", "min_turns": 5, "max_turns": 9}) == (2, 2)
    assert pacing._budget({"type": "exploration"}) == (1, 2)
    assert pacing._budget({"type": "social", "min_turns": None, "max_turns": None}) == (1, 2)
    # The legacy outline: 7 story beats and 2 fights.
    assert pacing.turn_budget(_campaign(None)) == (11, 18)


STORY = {"type": "exploration", "min_turns": 1, "max_turns": 2}
SLOW_STORY = {"type": "social", "min_turns": 2, "max_turns": 3}


@pytest.mark.parametrize(
    ("beat", "window", "turn_after", "turns_in_beat_after", "moved_on", "expected"),
    [
        (STORY, (1, 2), 1, 1, True, pacing.COMPLETE),         # moved on, minimum met, window open
        (STORY, (3, 4), 2, 1, True, pacing.CONTINUE),         # window not open yet
        (SLOW_STORY, (2, 3), 2, 1, True, pacing.CONTINUE),    # beat's own minimum not met
        (STORY, (1, 2), 1, 1, False, pacing.CONTINUE),        # not moved on, turns left
        (STORY, (1, 2), 2, 2, False, pacing.FORCE),           # beat's maximum reached
        (STORY, (3, 4), 4, 1, False, pacing.FORCE),           # window closes this turn
        (STORY, (1, 2), 2, 2, True, pacing.COMPLETE),         # moving on beats forcing
    ],
    ids=["complete", "window-closed", "minimum-not-met", "continue", "beat-max", "window-end", "moved-at-max"],
)
def test_story_beat_decisions(beat, window, turn_after, turns_in_beat_after, moved_on, expected):
    assert pacing.decide_story_beat(beat, window, turn_after, turns_in_beat_after, moved_on) == expected


def test_story_progress_reports_the_chapter_and_whats_next():
    campaign = _campaign("medium")
    start = pacing.story_progress(campaign)
    assert (start["chapter"], start["total"], start["final"]) == (1, 8, False)
    assert start["next_beat_type"] == "combat"

    end = pacing.story_progress(_at(campaign, -1))
    assert (end["chapter"], end["final"], end["threat_hint"]) == (8, True, "boss")
    assert end["next_beat_title"] is None
    assert pacing.is_final_beat(campaign)
    assert pacing.next_beat(campaign) is None


def test_an_unknown_position_counts_as_the_first_beat():
    campaign = _campaign("small")
    campaign["current_act"], campaign["current_beat"] = 9, 9
    assert pacing.current_index(campaign) == 0


# ─── Surprise fights ───


def test_surprise_fight_fits_the_grand_saga_opening():
    assert pacing.surprise_fight_allowed(_campaign("large"), {}, turn_after=1, turns_in_beat_after=1)


def test_no_surprise_fight_right_before_a_planned_fight():
    # Standard and Short open with a story beat followed by the first fight.
    assert not pacing.surprise_fight_allowed(_campaign("medium"), {}, 1, 1)
    assert not pacing.surprise_fight_allowed(_campaign("small"), {}, 1, 1)


def test_no_surprise_fight_on_a_combat_beat():
    assert not pacing.surprise_fight_allowed(_at(_campaign("large"), 2), {}, 3, 1)


def test_no_surprise_fight_in_the_final_act():
    # Legacy outline: "The Truth" is a story beat followed by a story beat, but in the final act.
    campaign = _at(_campaign(None), 7)
    assert pacing.ordered_beats(campaign)[8][1]["type"] == "climax"
    assert not pacing.surprise_fight_allowed(campaign, {}, 12, 1)
    # The same shape earlier in the story is allowed.
    assert pacing.surprise_fight_allowed(_at(_campaign(None), 0), {}, 1, 1)


def test_at_most_one_surprise_fight_per_act():
    campaign = _campaign("large")
    world = {}
    pacing.record_surprise_fight(campaign, world)
    assert world["surprise_fights"] == {"1": 1}
    assert not pacing.surprise_fight_allowed(campaign, world, 1, 1)


def test_no_surprise_fight_without_a_turn_to_spare():
    campaign = _campaign("large")  # opening beat: 1-2 turns, window (1, 2)
    assert not pacing.surprise_fight_allowed(campaign, {}, turn_after=2, turns_in_beat_after=2)
    assert not pacing.surprise_fight_allowed(campaign, {}, turn_after=2, turns_in_beat_after=1)


# ─── Play-throughs ───


def _success_intent(rng, step):
    # Alternate narrative and rolled actions, all on the story's path.
    return make_intent(description="press on", requires_roll=step % 2 == 1)


def _failure_intent(rng, step):
    # Failed rolls and side actions never move a beat on, so every beat runs to its maximum.
    if step % 2:
        return make_intent(description="press on", requires_roll=True)
    return make_intent(description="press on", relevance="tangential")


def _mixed_intent(rng, step):
    return make_intent(
        description="press on",
        requires_roll=rng.random() < 0.5,
        relevance="tangential" if rng.random() < 0.25 else "relevant",
        action_type="choice" if rng.random() < 0.15 else "explore",
    )


def play_campaign(client, app_state, intent_for_turn, *, seed=0, session_id=None, headers=None,
                  max_actions=80, **session_body):
    """Act and win every fight until the campaign ends. HP is topped up so nobody dies.

    Returns {"session_id", "turns", "fights" (threats in order), "result"}.
    """
    rng = random.Random(seed)
    if session_id is None:
        session_id, headers = create_session(client, **session_body)
    fights = []
    for step in range(max_actions):
        session = get_session(session_id)
        if session.world_state.get("campaign_ended"):
            break
        session.player.hp = session.player.max_hp
        app_state.intent_parser.next_intent = intent_for_turn(rng, step)
        response = act(client, session_id, headers, ACTIONS[step % len(ACTIONS)])
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["redo_turn"] is False, body
        if body["combat_started"]:
            fights.append(body["combat_data"]["enemy"]["threat"])
            resolved = win_fight(client, session_id, headers, body["combat_data"])
            assert resolved.status_code == 200, resolved.text
    else:
        pytest.fail(f"campaign didn't end within {max_actions} actions")
    session = get_session(session_id)
    return {
        "session_id": session_id,
        "turns": session.turn_number,
        "fights": fights,
        "result": session.world_state.get("campaign_result"),
    }


def _assert_full_campaign(run, size):
    low, high, fight_count = SIZES[size]
    assert run["result"] == "victory"
    assert low <= run["turns"] <= high, run
    assert len(run["fights"]) == fight_count, run
    assert run["fights"][-2:] == ["elite", "boss"], run  # the last fight is the climax


@pytest.mark.parametrize("size", SIZES)
def test_a_player_who_keeps_succeeding_finishes_at_the_minimum(client, app_state, fixed_roll, size):
    fixed_roll(15)
    run = play_campaign(client, app_state, _success_intent, campaign_size=size)
    _assert_full_campaign(run, size)
    assert run["turns"] == SIZES[size][0]


@pytest.mark.parametrize("size", SIZES)
def test_a_player_who_never_moves_on_is_carried_to_the_maximum(client, app_state, fixed_roll, size):
    fixed_roll(1)
    run = play_campaign(client, app_state, _failure_intent, campaign_size=size)
    _assert_full_campaign(run, size)
    assert run["turns"] == SIZES[size][1]


@pytest.mark.parametrize("seed", [1, 2])
@pytest.mark.parametrize("size", SIZES)
def test_mixed_play_stays_inside_the_budget(client, app_state, monkeypatch, size, seed):
    rolls = random.Random(seed * 101)
    monkeypatch.setattr(DiceEngine, "roll_d20", staticmethod(lambda: rolls.randint(1, 20)))
    run = play_campaign(client, app_state, _mixed_intent, seed=seed, campaign_size=size)
    _assert_full_campaign(run, size)


def test_the_campaign_never_ends_before_its_minimum(client, app_state, fixed_roll):
    # Every action moves the story on; the boss fight still can't come early.
    fixed_roll(20)
    run = play_campaign(client, app_state, lambda rng, step: make_intent(action_type="choice"),
                        campaign_size="small")
    _assert_full_campaign(run, "small")
    assert run["turns"] == 8


def test_a_legacy_session_plays_to_its_end(client, app_state, fixed_roll):
    fixed_roll(15)
    session_id, headers = create_session(client)
    use_legacy_campaign(session_id)

    run = play_campaign(client, app_state, _success_intent, session_id=session_id, headers=headers)

    assert run["result"] == "victory"
    assert 11 <= run["turns"] <= 18
    assert len(run["fights"]) == 2  # the old outline's two planned fights


# ─── Fights as turns ───


def test_a_planned_fight_is_one_turn_and_closes_its_beat(client, app_state):
    session_id, headers, combat = start_planned_fight(client, app_state)
    lead_in_turn = get_session(session_id).turn_number
    following = campaign_beats(session_id)[2][1]

    body = win_fight(client, session_id, headers, combat).json()

    assert body["turn_number"] == lead_in_turn + 1
    assert body["current_beat"] == following["title"]
    assert get_session(session_id).world_state["turns_in_beat"] == 0


def test_a_lost_fight_does_not_move_the_story_on(client, app_state):
    session_id, headers, combat = start_planned_fight(client, app_state)
    fight_beat = campaign_beats(session_id)[1][1]

    body = client.post(f"/session/{session_id}/combat/resolve", headers=headers, json={
        "combat_id": combat["combat_id"], "result": "defeat", "player_hp": 0,
        "player_mana": combat["player"]["mana"], "enemy_name": combat["enemy"]["name"], "turns_taken": 3,
    }).json()

    assert body["current_beat"] == fight_beat["title"]
    assert get_session(session_id).world_state["campaign_result"] == "defeat"


def test_a_fight_shows_up_in_history_and_the_story_log(client, app_state):
    session_id, headers, combat = start_planned_fight(client, app_state)
    app_state.narrator.text = "The goblin falls, and the path ahead is clear.\n→ Go on"
    win_fight(client, session_id, headers, combat)

    history = client.get(f"/session/{session_id}/history?limit=500", headers=headers).json()
    log = client.get(f"/session/{session_id}/hydrate", headers=headers).json()["story_log"]

    fight = history[-1]
    assert fight["player_input"] == f"Fought {combat['enemy']['name']}"
    assert fight["intent"]["action_type"] == "combat"
    assert fight["outcome"]["result"] == "combat_victory"
    assert log[-1] == {"turn": fight["turn_number"], "player_input": fight["player_input"],
                       "narration": "The goblin falls, and the path ahead is clear."}


# ─── Surprise fights through the API ───


def _prime_tension(session_id):
    get_session(session_id).world_state["combat_tension"] = 5  # threshold is 6


def test_tension_cannot_start_a_fight_right_before_a_planned_one(client, app_state, fixed_roll):
    fixed_roll(15)
    app_state.intent_parser.next_intent = make_intent(description="press on", relevance="tangential")
    session_id, headers = create_session(client)  # Standard: story beat, then the first fight
    _prime_tension(session_id)

    first = act(client, session_id, headers).json()
    second = act(client, session_id, headers).json()  # the beat runs out and wraps up
    lead_in = act(client, session_id, headers).json()

    assert (first["combat_started"], second["combat_started"]) == (False, False)
    assert lead_in["combat_started"] is True
    assert lead_in["current_beat"] == campaign_beats(session_id)[1][1]["title"]


def test_a_surprise_fight_fits_inside_the_grand_saga_budget(client, app_state, fixed_roll):
    fixed_roll(15)
    app_state.intent_parser.next_intent = make_intent(description="press on", relevance="tangential")
    session_id, headers = create_session(client, campaign_size="large")
    _prime_tension(session_id)

    started = act(client, session_id, headers).json()
    assert started["combat_started"] is True
    resolved = win_fight(client, session_id, headers, started["combat_data"]).json()

    # The fight used the opening beat's last turn, so the beat wrapped up.
    assert resolved["turn_number"] == 2
    assert resolved["current_beat"] == campaign_beats(session_id)[1][1]["title"]
    assert get_session(session_id).world_state["surprise_fights"] == {"1": 1}

    fixed_roll(1)
    run = play_campaign(client, app_state, _failure_intent, session_id=session_id, headers=headers)
    assert run["result"] == "victory"
    assert run["turns"] == 25  # every beat ran to its maximum, and the budget still held
    assert len(run["fights"]) == 7  # plus the surprise fight
