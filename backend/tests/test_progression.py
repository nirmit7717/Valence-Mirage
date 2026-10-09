"""Milestone leveling and story-scaled enemies.

XP comes from playing the story: a flat amount per turn (dice luck doesn't
matter), a bonus for each finished beat, and a fight reward set by the fight's
tier and threat. Enemy tier follows how far the story has come, so a campaign
size always ends around the same level: Short ~3, Standard ~4, Grand Saga ~6.
"""

import pytest

from engines import progression
from engines.campaign_planner import CampaignPlanner
from data.campaign_templates import CAMPAIGN_TEMPLATES
from data.enemy_archetypes import build_enemy_template
from engines.state_manager import StateManager
from helpers import (
    act,
    create_session,
    get_session,
    make_intent,
    move_to_beat,
    start_planned_fight,
    win_fight,
)
from models.game_state import PlayerState
from test_pacing import _failure_intent, _success_intent, play_campaign

TARGET_LEVEL = {"small": 3, "medium": 4, "large": 6}


def _campaign(size: str) -> dict:
    return CampaignPlanner._fallback_blueprint("Tester", CAMPAIGN_TEMPLATES[size]).model_dump()


def _at(campaign: dict, index: int) -> dict:
    from engines import pacing

    act_data, beat = pacing.ordered_beats(campaign)[index]
    campaign["current_act"], campaign["current_beat"] = act_data["act_id"], beat["beat_id"]
    return campaign


# ─── XP tables ───


def test_level_thresholds():
    totals, total = {}, 0
    for level in range(1, 8):
        total += progression.xp_for_next_level(level)
        totals[level + 1] = total
    assert totals == {2: 100, 3: 230, 4: 400, 5: 600, 6: 800, 7: 1050, 8: 1350}
    assert progression.xp_for_next_level(8) > progression.xp_for_next_level(7)  # keeps growing past the table


@pytest.mark.parametrize(
    ("tier", "threat", "xp"),
    [(1, "standard", 25), (2, "standard", 35), (3, "elite", 68), (4, "boss", 150), (5, "boss", 200),
     (1, "minion", 13), (9, "standard", 80), (0, "standard", 25)],
)
def test_fight_xp_follows_tier_and_threat(tier, threat, xp):
    assert progression.fight_xp(tier, threat) == xp


def test_beat_xp_grows_with_each_act():
    assert [progression.beat_xp(act_number) for act_number in (1, 2, 3, 4)] == [20, 25, 30, 35]


def test_every_story_turn_earns_the_same_xp_whatever_the_dice_say():
    for outcome in ("critical_success", "success", "failure", "critical_failure", "narrative_choice"):
        session = StateManager().create_session("Warrior")
        StateManager().apply_changes(session, make_intent(), _no_changes(), outcome)
        assert session.player.xp == progression.ACTION_XP == 5


def _no_changes():
    from models.outcome import StateChanges

    return StateChanges()


# ─── Level-ups ───


def test_a_level_up_is_predictable():
    player = StateManager().create_session("Warrior").player
    player.hp = 10
    stats_before = player.stats.model_copy()
    max_hp, max_mana = player.max_hp, player.max_mana

    (level_up,) = progression.award(player, 100, "fight")

    assert (player.level, player.xp, player.xp_to_next) == (2, 0, 130)
    assert player.max_hp == max_hp + 8 and player.max_mana == max_mana + 3
    assert player.stats.strength == stats_before.strength + 1  # primary every level
    assert player.stats.control == stats_before.control + 1    # secondary on even levels
    assert player.stats.dexterity == stats_before.dexterity
    assert player.hp == 10 + round(player.max_hp * 0.3)        # a partial heal, not a full one
    assert level_up == {
        "level": 2, "reason": "fight", "hp_gain": 8, "mana_gain": 3,
        "stats": {"strength": 1, "control": 1}, "max_hp": player.max_hp, "max_mana": player.max_mana,
    }


@pytest.mark.parametrize(
    ("character_class", "hp_gain", "mana_gain", "primary"),
    [("warrior", 8, 3, "strength"), ("cleric", 7, 7, "wisdom"), ("rogue", 6, 5, "dexterity"),
     ("bard", 6, 7, "charisma"), ("wizard", 5, 8, "intelligence")],
)
def test_class_growth(character_class, hp_gain, mana_gain, primary):
    player = PlayerState(character_class=character_class)
    before = getattr(player.stats, primary)
    (level_up,) = progression.award(player, 100, "beat")
    assert (level_up["hp_gain"], level_up["mana_gain"]) == (hp_gain, mana_gain)
    assert getattr(player.stats, primary) == before + 1


def test_odd_levels_only_raise_the_primary_stat():
    player = PlayerState(character_class="wizard")
    level_ups = progression.award(player, 230, "beat")
    assert [lu["level"] for lu in level_ups] == [2, 3]
    assert level_ups[1]["stats"] == {"intelligence": 1}


def test_a_big_award_can_cross_several_levels():
    player = PlayerState()
    level_ups = progression.award(player, 405, "fight")
    assert [lu["level"] for lu in level_ups] == [2, 3, 4]
    assert (player.level, player.xp, player.xp_to_next) == (4, 5, 200)
    assert progression.total_xp(player) == 405


def test_gain_xp_uses_the_milestone_rules():
    player = PlayerState()
    assert player.gain_xp(99) is False
    assert player.gain_xp(1) is True
    assert (player.level, player.xp_to_next) == (2, 130)


def test_old_sessions_get_the_new_xp_requirements():
    # Saved under the old x1.5 curve: level 3 needed 225.
    player = PlayerState(level=3, xp=180, xp_to_next=225)
    progression.award(player, 5, "turn")
    assert (player.level, player.xp, player.xp_to_next) == (4, 15, 200)


def test_hydrate_recalculates_xp_to_next_for_old_sessions(client):
    session_id, headers = create_session(client)
    player = get_session(session_id).player
    player.level, player.xp, player.xp_to_next = 3, 50, 225

    hydrated = client.get(f"/session/{session_id}/hydrate", headers=headers).json()

    assert hydrated["player"]["xp_to_next"] == 170
    assert hydrated["player"]["xp"] == 50


# ─── Story-scaled enemies ───


@pytest.mark.parametrize(
    ("size", "index", "tier"),
    [("small", 0, 1), ("small", 1, 1), ("small", 3, 2), ("small", -1, 2),
     ("medium", 1, 1), ("medium", 3, 2), ("medium", 6, 3), ("medium", -1, 3),
     ("large", 2, 2), ("large", 6, 3), ("large", 10, 4), ("large", -1, 4)],
)
def test_enemy_tier_follows_story_progress(size, index, tier):
    assert progression.story_tier(_at(_campaign(size), index), size) == tier


def test_unknown_sizes_scale_like_a_standard_campaign():
    campaign = _at(_campaign("medium"), -1)
    assert progression.story_tier(campaign, None) == progression.story_tier(campaign, "medium")


def test_fight_threat_comes_from_the_story():
    campaign = _campaign("medium")
    assert progression.fight_threat(_at(campaign, 1)) == "standard"
    assert progression.fight_threat(_at(campaign, 6)) == "elite"
    assert progression.fight_threat(_at(campaign, 7)) == "boss"
    assert progression.fight_threat(_at(campaign, 7), surprise=True) == "standard"


def test_the_last_beat_of_an_outline_without_hints_is_the_boss():
    legacy = CampaignPlanner._fallback_blueprint("Tester").model_dump()
    assert progression.fight_threat(_at(legacy, -1)) == "boss"
    assert progression.fight_threat(_at(legacy, 3)) == "standard"


def test_every_designed_enemy_is_worth_its_fight_xp():
    for threat in ("minion", "standard", "elite", "boss"):
        for tier in (1, 3, 5):
            template = build_enemy_template("Foe", "soldier", threat, tier)
            assert template.xp_reward == progression.fight_xp(tier, threat)


def test_a_planned_fight_uses_the_story_tier_and_threat(client, app_state):
    session_id, _, combat = start_planned_fight(client, app_state)  # Standard, first fight
    stored = get_session(session_id).world_state["combat"]
    assert combat["enemy_tier"] == 1
    assert combat["enemy"]["threat"] == "standard"
    assert stored["xp_reward"] == progression.fight_xp(1, "standard")


def test_the_grand_saga_boss_is_tier_four_even_for_a_low_level_hero(client, app_state):
    app_state.intent_parser.next_intent = make_intent(description="press on")
    app_state.narrator.text = "The tyrant steps from the throne and attacks."
    session_id, headers = create_session(client, campaign_size="large")
    move_to_beat(session_id, -1)

    combat = act(client, session_id, headers).json()["combat_data"]

    assert (combat["enemy_tier"], combat["enemy"]["threat"]) == (4, "boss")
    assert get_session(session_id).world_state["combat"]["xp_reward"] == 150


# ─── XP in responses ───


def test_finishing_a_beat_reports_turn_and_beat_xp(client, app_state):
    app_state.intent_parser.next_intent = make_intent(description="press on")
    session_id, headers = create_session(client)

    body = act(client, session_id, headers).json()  # resolves the opening beat

    assert body["xp_gained"] == progression.ACTION_XP + progression.beat_xp(1)
    assert body["level_up"] == []
    assert body["player_xp"] == 25


def test_winning_a_fight_reports_fight_and_beat_xp(client, app_state):
    session_id, headers, combat = start_planned_fight(client, app_state)
    xp_before = progression.total_xp(get_session(session_id).player)

    body = win_fight(client, session_id, headers, combat).json()

    fight = progression.fight_xp(1, "standard")
    assert body["rewards"]["xp"] == fight
    assert body["xp_gained"] == fight + progression.beat_xp(1)
    assert progression.total_xp(get_session(session_id).player) == xp_before + body["xp_gained"]


def test_level_ups_are_listed_in_the_response(client, app_state):
    session_id, headers, combat = start_planned_fight(client, app_state)
    player = get_session(session_id).player
    player.xp = player.xp_to_next - 1

    body = win_fight(client, session_id, headers, combat).json()

    assert [lu["level"] for lu in body["level_up"]] == [2]
    assert body["player_level"] == 2


# ─── Balance: every size ends around its target level ───


@pytest.mark.parametrize("size", TARGET_LEVEL)
@pytest.mark.parametrize("mode", ["fastest", "slowest"])
def test_campaigns_end_near_their_target_level(client, app_state, fixed_roll, size, mode):
    fixed_roll(15 if mode == "fastest" else 1)
    intent = _success_intent if mode == "fastest" else _failure_intent

    run = play_campaign(client, app_state, intent, campaign_size=size)

    level = get_session(run["session_id"]).player.level
    assert run["result"] == "victory"
    assert abs(level - TARGET_LEVEL[size]) <= 1, (size, mode, level)
