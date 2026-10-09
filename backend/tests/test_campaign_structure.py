"""Campaign sizes: Short 8-10 turns / 3 fights, Standard 13-15 / 5, Grand Saga 20-25 / 7.

Every size ends with a boss fight, preceded by an elite fight, and the
generated outline always has exactly the template's structure.
"""

import pytest

from data.campaign_templates import (
    CAMPAIGN_TEMPLATES,
    ActTemplate,
    BeatRequirement,
    CampaignTemplate,
)
from engines.campaign_planner import (
    CampaignAct,
    CampaignBlueprint,
    CampaignPlanner,
    StoryBeat,
    conform_to_template,
)
from helpers import create_session, get_session, new_session

EXPECTED = {
    # size: (beats, acts, fights, min_turns, max_turns)
    "small": (5, 2, 3, 8, 10),
    "medium": (8, 3, 5, 13, 15),
    "large": (13, 4, 7, 20, 25),
}


# ─── Templates ───


@pytest.mark.parametrize("size", EXPECTED)
def test_template_shape(size):
    beats, acts, fights, min_turns, max_turns = EXPECTED[size]
    template = CAMPAIGN_TEMPLATES[size]

    assert len(template.beats) == beats
    assert len(template.acts) == acts
    assert template.fight_count == fights
    assert sum(b.min_turns for b in template.beats) == template.min_turns == min_turns
    assert sum(b.max_turns for b in template.beats) == template.max_turns == max_turns
    assert template.estimated_turns == f"{min_turns}-{max_turns}"
    assert [b.beat_id for b in template.beats] == list(range(1, beats + 1))


@pytest.mark.parametrize("size", EXPECTED)
def test_last_fight_is_the_boss_and_the_one_before_is_elite(size):
    fights = [b for b in CAMPAIGN_TEMPLATES[size].beats if b.beat_type == "combat"]
    assert CAMPAIGN_TEMPLATES[size].beats[-1] is fights[-1]
    assert fights[-1].threat_hint == "boss"
    assert fights[-2].threat_hint == "elite"
    assert all(f.threat_hint is None for f in fights[:-2])


@pytest.mark.parametrize("size", EXPECTED)
def test_every_fight_takes_exactly_two_turns(size):
    for beat in CAMPAIGN_TEMPLATES[size].beats:
        if beat.beat_type == "combat":
            assert (beat.min_turns, beat.max_turns) == (2, 2)


def _template(beats, min_turns, max_turns):
    return dict(name="T", size="x", total_beats=len(beats), estimated_turns="", description="",
                min_turns=min_turns, max_turns=max_turns, acts=[ActTemplate(act_id=1, title="A", beats=beats)])


def test_template_totals_must_match_the_beats():
    beats = [
        BeatRequirement(beat_id=1, beat_type="exploration", enforcement="soft", min_turns=1, max_turns=2),
        BeatRequirement(beat_id=2, beat_type="combat", enforcement="hard", min_turns=2, max_turns=2, threat_hint="boss"),
    ]
    CampaignTemplate(**_template(beats, 3, 4))  # valid
    with pytest.raises(ValueError):
        CampaignTemplate(**_template(beats, 5, 4))


def test_template_must_end_with_the_boss():
    beats = [
        BeatRequirement(beat_id=1, beat_type="combat", enforcement="hard", min_turns=2, max_turns=2, threat_hint="boss"),
        BeatRequirement(beat_id=2, beat_type="exploration", enforcement="soft", min_turns=1, max_turns=2),
    ]
    with pytest.raises(ValueError):
        CampaignTemplate(**_template(beats, 3, 4))


def test_combat_beats_must_take_two_turns():
    with pytest.raises(ValueError):
        BeatRequirement(beat_id=1, beat_type="combat", enforcement="hard", min_turns=1, max_turns=3)


# ─── Story beats ───


def test_story_beat_budgets_default_by_type():
    assert (StoryBeat(beat_id=1, title="x", type="combat").min_turns,
            StoryBeat(beat_id=1, title="x", type="combat").max_turns) == (2, 2)
    story = StoryBeat(beat_id=1, title="x", type="social")
    assert (story.min_turns, story.max_turns) == (1, 2)
    assert StoryBeat(beat_id=1, title="x", type="choice", min_turns=1, max_turns=1).max_turns == 1


# ─── Conforming model output to the template ───


def _blueprint(beat_types: list[str], acts: int = 1) -> CampaignBlueprint:
    """Model output: titles are numbered across the whole story; beat ids restart per act."""
    per_act = max(1, len(beat_types) // acts)
    built, index = [], 0
    for act_id in range(1, acts + 1):
        chunk = beat_types[index:index + per_act] if act_id < acts else beat_types[index:]
        built.append(CampaignAct(act_id=act_id, title=f"Model Act {act_id}", beats=[
            StoryBeat(beat_id=i + 1, title=f"Model {t} {index + i}", description=f"model {t} {index + i}", type=t)
            for i, t in enumerate(chunk)
        ]))
        index += len(chunk)
    return CampaignBlueprint(title="Neon Requiem", premise="A megacorp hunts you.", setting="Undercity", acts=built,
                             current_act=2, current_beat=3)


def _assert_matches(blueprint, template):
    beats = [beat for act in blueprint.acts for beat in act.beats]
    assert [b.type for b in beats] == [t.beat_type for t in template.beats]
    assert [b.beat_id for b in beats] == [t.beat_id for t in template.beats]
    assert [(b.min_turns, b.max_turns) for b in beats] == [(t.min_turns, t.max_turns) for t in template.beats]
    assert [b.threat_hint for b in beats] == [t.threat_hint for t in template.beats]
    assert [a.act_id for a in blueprint.acts] == [a.act_id for a in template.acts]
    first_act, first_beat = blueprint.acts[0].act_id, blueprint.acts[0].beats[0].beat_id
    assert (blueprint.current_act, blueprint.current_beat) == (first_act, first_beat)


def test_conform_keeps_model_content_where_types_match():
    template = CAMPAIGN_TEMPLATES["small"]
    model = _blueprint(["narrative_choice", "combat", "exploration", "combat", "combat"], acts=2)

    result = conform_to_template(model, template)

    _assert_matches(result, template)
    titles = [b.title for a in result.acts for b in a.beats]
    assert titles[:3] == ["Model narrative_choice 0", "Model combat 1", "Model exploration 2"]
    assert result.title == "Neon Requiem" and result.premise == "A megacorp hunts you."
    assert result.acts[0].title == "Model Act 1"


def test_conform_fills_missing_beats_from_the_template():
    template = CAMPAIGN_TEMPLATES["medium"]
    result = conform_to_template(_blueprint(["narrative_choice", "combat"]), template)

    _assert_matches(result, template)
    final = result.acts[-1].beats[-1]
    assert final.title  # every beat has a title
    assert "final" in final.description.lower() or "central threat" in final.description.lower()


def test_conform_drops_extra_beats():
    template = CAMPAIGN_TEMPLATES["small"]
    model = _blueprint(["narrative_choice", "combat", "exploration"] * 6, acts=3)
    _assert_matches(conform_to_template(model, template), template)


def test_conform_reuses_mistyped_beats_by_type():
    template = CAMPAIGN_TEMPLATES["small"]
    # Model put everything out of order: combat, combat, exploration, narrative_choice, social
    model = _blueprint(["combat", "combat", "exploration", "narrative_choice", "social"])

    result = conform_to_template(model, template)

    _assert_matches(result, template)
    beats = [b for a in result.acts for b in a.beats]
    assert beats[0].title == "Model narrative_choice 3"  # found by type, not position
    assert beats[1].title == "Model combat 1"  # same type at the same position
    assert beats[2].title == "Model exploration 2"


def test_final_fight_is_framed_as_the_climax():
    template = CAMPAIGN_TEMPLATES["small"]
    model = _blueprint(["narrative_choice", "combat", "exploration", "combat", "combat"])
    final = conform_to_template(model, template).acts[-1].beats[-1]
    assert "final confrontation" in final.description.lower()


# ─── Fallback outline ───


@pytest.mark.parametrize("size", EXPECTED)
def test_fallback_outline_matches_each_template(size):
    template = CAMPAIGN_TEMPLATES[size]
    fallback = CampaignPlanner._fallback_blueprint("Tester", template)
    _assert_matches(fallback, template)
    titles = [b.title for a in fallback.acts for b in a.beats]
    assert len(set(titles)) == len(titles), "fallback beats should not repeat titles"


def test_legacy_fallback_without_a_template_is_unchanged():
    legacy = CampaignPlanner._fallback_blueprint("Tester")
    assert sum(len(a.beats) for a in legacy.acts) == 9


# ─── Beat relevance no longer matches on common words ───


def test_relevance_bonus_ignores_common_words():
    planner = CampaignPlanner()
    blueprint = conform_to_template(_blueprint(["narrative_choice"]), CAMPAIGN_TEMPLATES["small"])
    blueprint.acts[0].beats[0].title = "The Barkeep's Warning"
    blueprint.acts[0].beats[0].description = "Learn about the tower from the barkeep"

    assert planner.get_narrative_relevance_bonus(blueprint, "I look at the door and the floor") == 0.0
    assert planner.get_narrative_relevance_bonus(blueprint, "I question the barkeep") == 0.1
    assert planner.get_narrative_relevance_bonus(blueprint, "I ask the barkeep about the tower to learn more") == 0.2


# ─── API ───


@pytest.mark.parametrize("size", EXPECTED)
def test_new_sessions_get_the_full_structure(client, size):
    beats, acts, fights, _, _ = EXPECTED[size]
    data, _ = new_session(client, campaign_size=size)

    assert len(data["campaign"]["acts"]) == acts
    returned = [b for act in data["campaign"]["acts"] for b in act["beats"]]
    assert len(returned) == beats
    assert sum(1 for b in returned if b["type"] == "combat") == fights


def test_stored_campaign_keeps_turn_budgets(client):
    session_id, _ = create_session(client, campaign_size="small")
    beats = [b for act in get_session(session_id).world_state["campaign"]["acts"] for b in act["beats"]]
    assert sum(b["min_turns"] for b in beats) == 8
    assert sum(b["max_turns"] for b in beats) == 10
    assert beats[-1]["threat_hint"] == "boss"
