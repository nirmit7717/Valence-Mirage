"""The storyteller knows where it is in the story, and campaigns end with a real ending.

Every narration gets a STORY PACING section (chapter N of M, act, beat, and one
directive for this turn). Winning the final fight produces an epilogue with no
further choices. Responses carry ``story_progress`` for the HUD.
"""

import asyncio
from types import SimpleNamespace

import pytest

from engines import pacing
from engines.narrator import PACING_DIRECTIVES, Narrator, pacing_section, strip_choice_lines
from engines.state_manager import StateManager
from helpers import (
    FakeRuleRetriever,
    act,
    campaign_beats,
    create_session,
    get_session,
    make_intent,
    move_to_beat,
    new_session,
    start_planned_fight,
    use_legacy_campaign,
    win_fight,
)

ENDING_WITH_CHOICES = "The tower crumbles into the sea.\n→ Walk away\n→ Look back\n→ Rest"


def _last_moment(app_state) -> str:
    return app_state.narrator.calls[-1]["pacing"]["moment"]


# ─── Directives ───


@pytest.mark.parametrize(
    ("decision", "fight", "final", "moment"),
    [
        (pacing.CONTINUE, None, False, pacing.DEVELOP),
        (pacing.COMPLETE, None, False, pacing.RESOLVE),
        (pacing.FORCE, None, False, pacing.WRAP_UP),
        (pacing.CONTINUE, "planned", False, pacing.FIGHT_LEAD_IN),
        (pacing.CONTINUE, "planned", True, pacing.FINAL_FIGHT_LEAD_IN),
        (pacing.CONTINUE, "surprise", False, pacing.SURPRISE_FIGHT),
        (pacing.COMPLETE, None, True, pacing.STORY_ENDS),
        (pacing.FORCE, None, True, pacing.STORY_ENDS),
    ],
)
def test_each_kind_of_turn_gets_its_directive(decision, fight, final, moment):
    assert pacing.narration_moment(decision, fight, final) == moment
    assert moment in PACING_DIRECTIVES


def _brief(**overrides):
    brief = {"chapter": 3, "total": 8, "act_id": 2, "act_title": "Rising Stakes", "beat_title": "The Ambush",
             "beat_type": "exploration", "final": False, "next_beat_title": "Crisis", "next_beat_type": "combat",
             "moment": pacing.DEVELOP}
    brief.update(overrides)
    return brief


def test_pacing_section_says_where_the_story_is_and_what_to_do():
    section = pacing_section(_brief())
    assert section.startswith("STORY PACING:")
    assert "Chapter 3 of 8 · Act 2: Rising Stakes" in section
    assert "Current beat: The Ambush (exploration)" in section
    assert "Next beat: Crisis (a fight)" in section
    assert f"This turn: {PACING_DIRECTIVES[pacing.DEVELOP]}" in section
    assert "Do not resolve it yet" in section


def test_pacing_section_for_the_final_confrontation():
    section = pacing_section(_brief(final=True, next_beat_title=None, moment=pacing.FINAL_FIGHT_LEAD_IN))
    assert "final chapter" in section
    assert "FINAL CONFRONTATION" in section
    assert "Next beat" not in section


def test_wrap_up_and_ending_directives():
    assert "Resolve the current beat NOW" in pacing_section(_brief(moment=pacing.WRAP_UP))
    ending = pacing_section(_brief(final=True, moment=pacing.STORY_ENDS))
    assert "THE STORY ENDS NOW" in ending
    assert "Do not suggest any further actions" in ending


def test_no_outline_means_no_pacing_section():
    assert pacing_section(None) == ""


def test_choice_lines_are_stripped_from_endings():
    assert strip_choice_lines(ENDING_WITH_CHOICES) == "The tower crumbles into the sea."
    assert strip_choice_lines("Done.\n-> Again") == "Done."


# ─── What the storyteller is told, turn by turn ───


def test_moving_the_opening_beat_on_resolves_it(client, app_state):
    app_state.intent_parser.next_intent = make_intent(description="press on")
    session_id, headers = create_session(client)

    act(client, session_id, headers)

    brief = app_state.narrator.calls[-1]["pacing"]
    assert brief["moment"] == pacing.RESOLVE
    assert (brief["chapter"], brief["total"]) == (1, 8)
    assert brief["next_beat_type"] == "combat"


def test_side_actions_develop_the_beat_until_time_runs_out(client, app_state):
    app_state.intent_parser.next_intent = make_intent(description="press on", relevance="tangential")
    session_id, headers = create_session(client)

    act(client, session_id, headers)
    assert _last_moment(app_state) == pacing.DEVELOP
    act(client, session_id, headers)
    assert _last_moment(app_state) == pacing.WRAP_UP


def test_a_combat_beat_turn_introduces_the_enemy(client, app_state):
    start_planned_fight(client, app_state)
    assert _last_moment(app_state) == pacing.FIGHT_LEAD_IN


def test_the_final_fight_lead_in_is_the_final_confrontation(client, app_state):
    app_state.intent_parser.next_intent = make_intent(description="press on")
    session_id, headers = create_session(client)
    move_to_beat(session_id, -1)

    assert act(client, session_id, headers).json()["combat_started"] is True
    brief = app_state.narrator.calls[-1]["pacing"]
    assert brief["moment"] == pacing.FINAL_FIGHT_LEAD_IN
    assert brief["final"] is True and brief["threat_hint"] == "boss"


def test_a_won_fight_points_the_story_at_the_next_beat(client, app_state):
    session_id, headers, combat = start_planned_fight(client, app_state)

    win_fight(client, session_id, headers, combat)

    brief = app_state.narrator.calls[-1]["pacing"]
    assert brief["moment"] == pacing.AFTER_FIGHT
    assert brief["next_beat_title"] == campaign_beats(session_id)[2][1]["title"]


# ─── Endings ───


def test_winning_the_final_fight_tells_the_ending(client, app_state):
    app_state.intent_parser.next_intent = make_intent(description="press on")
    session_id, headers = create_session(client)
    move_to_beat(session_id, -1)
    started = act(client, session_id, headers).json()
    story_calls = len(app_state.narrator.calls)

    body = win_fight(client, session_id, headers, started["combat_data"]).json()

    assert len(app_state.narrator.calls) == story_calls  # the epilogue replaces the usual narration
    (call,) = app_state.narrator.epilogue_calls
    assert call["final_enemy"] == started["combat_data"]["enemy"]["name"]
    assert body["narration"] == app_state.narrator.epilogue_text
    assert body["choices"] == []
    assert body["pending_outcome"] == {"type": "victory"}
    log = client.get(f"/session/{session_id}/hydrate", headers=headers).json()["story_log"]
    assert log[-1]["narration"] == app_state.narrator.epilogue_text


def test_an_earlier_fight_gets_no_epilogue(client, app_state):
    session_id, headers, combat = start_planned_fight(client, app_state)
    win_fight(client, session_id, headers, combat)
    assert app_state.narrator.epilogue_calls == []


def test_a_legacy_final_beat_ends_the_story_without_choices(client, app_state):
    app_state.intent_parser.next_intent = make_intent(action_type="choice", description="make the final choice")
    session_id, headers = create_session(client)
    use_legacy_campaign(session_id)
    move_to_beat(session_id, -1)
    session = get_session(session_id)
    session.turn_number = pacing.beat_windows(session.world_state["campaign"])[-1][0] - 1
    app_state.narrator.text = ENDING_WITH_CHOICES

    body = act(client, session_id, headers).json()

    assert _last_moment(app_state) == pacing.STORY_ENDS
    assert body["pending_outcome"] == {"type": "victory"}
    assert body["choices"] == []
    assert "→" not in body["narration"]
    history = client.get(f"/session/{session_id}/history", headers=headers).json()
    assert "→" not in history[-1]["outcome"]["narration"]


# ─── story_progress for the HUD ───


def test_new_sessions_start_at_chapter_one(client):
    data, _ = new_session(client, campaign_size="small")
    progress = data["story_progress"]
    assert (progress["chapter"], progress["total"], progress["act_id"]) == (1, 5, 1)
    assert progress["act_title"]


def test_actions_fights_and_hydrate_report_progress(client, app_state):
    app_state.intent_parser.next_intent = make_intent(description="press on")
    session_id, headers = create_session(client)

    after_action = act(client, session_id, headers).json()  # the opening beat resolves
    assert after_action["story_progress"]["chapter"] == 2
    lead_in = act(client, session_id, headers).json()
    assert lead_in["combat_started"] is True
    resolved = win_fight(client, session_id, headers, lead_in["combat_data"]).json()
    assert resolved["story_progress"]["chapter"] == 3

    hydrated = client.get(f"/session/{session_id}/hydrate", headers=headers).json()
    assert hydrated["story_progress"] == resolved["story_progress"]
    assert hydrated["story_progress"]["beat_title"] == hydrated["current_beat"]


def test_sessions_without_an_outline_have_no_progress(client):
    session_id, headers = create_session(client)
    get_session(session_id).world_state.pop("campaign")
    assert client.get(f"/session/{session_id}/hydrate", headers=headers).json()["story_progress"] is None


# ─── The real Narrator (model call replaced) ───


class _FakeCompletions:
    def __init__(self, text=None, error=None):
        self.text, self.error, self.messages = text, error, None

    async def create(self, **kwargs):
        self.messages = kwargs["messages"]
        if self.error:
            raise self.error
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.text))])


def _narrator(text=None, error=None):
    narrator = Narrator.__new__(Narrator)  # skip the network client and rule store
    completions = _FakeCompletions(text, error)
    narrator.client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    narrator.prompt = "narrator system prompt"
    narrator.epilogue_prompt = "epilogue system prompt"
    narrator.rule_retriever = FakeRuleRetriever()
    return narrator, completions


def _player():
    return StateManager().create_session("Hero").player


def test_narrate_sends_the_pacing_section_to_the_model():
    narrator, completions = _narrator(text="The road bends.\n→ Go on")
    asyncio.run(narrator.narrate(
        intent=make_intent(), outcome_result="success", roll=12, threshold=8, player=_player(),
        world_state={"campaign": {"title": "T"}}, pacing=_brief(moment=pacing.WRAP_UP),
    ))
    user_msg = completions.messages[1]["content"]
    assert "STORY PACING:" in user_msg
    assert PACING_DIRECTIVES[pacing.WRAP_UP] in user_msg


def test_epilogue_has_no_choices_and_uses_its_own_prompt():
    narrator, completions = _narrator(text=ENDING_WITH_CHOICES)
    world = {"campaign": {"title": "The Dark Tower", "premise": "A tower"}, "campaign_objective": "Stop it"}

    text = asyncio.run(narrator.narrate_epilogue(player=_player(), world_state=world, final_enemy="The Lich"))

    assert text == "The tower crumbles into the sea."
    assert completions.messages[0]["content"] == "epilogue system prompt"
    assert "The Lich" in completions.messages[1]["content"]


def test_epilogue_falls_back_when_the_model_fails():
    narrator, _ = _narrator(error=RuntimeError("model down"))
    world = {"campaign": {"title": "The Dark Tower"}}

    text = asyncio.run(narrator.narrate_epilogue(player=_player(), world_state=world, final_enemy="The Lich"))

    assert "The Lich falls" in text
    assert "→" not in text
