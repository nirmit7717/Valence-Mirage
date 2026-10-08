"""Bug: enemies must come from the campaign, with stats from how they are described.

Regression: in a cyberpunk campaign the narrator described corporate security,
but combat showed "A Giant Rat appears!" — substring matching found "rat" inside
"corporate" and "operative".
"""

import asyncio
from types import SimpleNamespace

import pytest

from data.enemies import ENEMY_TEMPLATES
from data.enemy_archetypes import build_enemy_template
from engines.enemy_designer import (
    EnemyDesigner,
    EnemySpec,
    design_enemy,
    extract_enemy_phrase,
    normalize_spec,
)
from engines.setting import FANTASY, POSTAPOC, SCIFI, detect_genre
from helpers import act, create_session, get_session, make_intent

CYBERPUNK_CAMPAIGN = {
    "title": "Neon Requiem",
    "premise": "A megacorp hunts the netrunner who stole its secrets.",
    "setting": "The neon-lit undercity of a cyberpunk megacity",
    "tone": "cyberpunk noir",
    "key_themes": ["corporate greed", "implants"],
    "acts": [],
    "current_act": 1,
    "current_beat": 1,
}
DRONE_SCENE = (
    "Rain hisses on the neon signs. Two corporate operatives step out of the van, "
    "and a corporate security drone drops from the smog and opens fire on you."
)
CLASSIC_NAMES = {template.name for template in ENEMY_TEMPLATES.values()}


def _world(campaign=None, **extra):
    world = {"campaign": dict(campaign or CYBERPUNK_CAMPAIGN), "location": "Undercity market"}
    world.update(extra)
    return world


# ─── Heuristic extraction ───


def test_cyberpunk_scene_yields_the_described_enemy_not_a_rat():
    phrase = extract_enemy_phrase(DRONE_SCENE)
    assert phrase is not None
    assert phrase.name == "Corporate Security Drone"
    assert phrase.archetype == "construct"


@pytest.mark.parametrize(
    "scene",
    [
        "Your corporate contact winces as the operative reviews the damage report.",
        "The narrator of the separate broadcast is accurate.",
    ],
)
def test_substrings_never_match_enemy_nouns(scene):
    phrase = extract_enemy_phrase(scene)
    assert phrase is None or ("Rat" not in phrase.name.split() and "Mage" not in phrase.name.split())


def test_compound_and_modifiers_are_kept():
    phrase = extract_enemy_phrase("From the ash steps a hulking cyborg enforcer, servos whining.")
    assert phrase.name == "Hulking Cyborg Enforcer"
    assert phrase.archetype == "construct"  # what it *is* beats its job title


def test_plural_and_possessive_nouns_are_singularized():
    assert extract_enemy_phrase("Feral wolves charge out of the treeline.").name == "Feral Wolf"
    phrase = extract_enemy_phrase("The mercenary's rifle swings toward you as she attacks.")
    assert phrase.name == "Mercenary"


def test_hostile_sentence_wins_over_earlier_mention():
    scene = "A guard nods at you from the gate. Suddenly a shadow assassin lunges from the rafters!"
    assert extract_enemy_phrase(scene).name == "Shadow Assassin"


def test_player_class_words_are_not_enemies():
    assert extract_enemy_phrase("You, a seasoned warrior, ready your blade.") is None


# ─── Genre detection ───


@pytest.mark.parametrize(
    ("text", "genre"),
    [
        ("A cyberpunk megacity ruled by megacorps", SCIFI),
        ("neon streets, corporate towers and chrome implants", SCIFI),
        ("A post-apocalyptic wasteland of raiders", POSTAPOC),
        ("A haunted castle besieged by the undead", FANTASY),
        ("", FANTASY),
    ],
)
def test_detect_genre(text, genre):
    assert detect_genre(text) == genre


# ─── Presets ───


def test_archetype_and_threat_shape_the_stats():
    def stats(archetype, threat="standard", tier=1):
        return build_enemy_template("X", archetype, threat, tier)

    assert stats("brute").hp > stats("skirmisher").hp
    assert stats("construct").armor > stats("beast").armor
    assert stats("caster").attack_bonus > stats("brute").attack_bonus
    assert stats("soldier", "boss").hp > stats("soldier", "elite").hp > stats("soldier").hp > stats("soldier", "minion").hp
    assert stats("soldier", "boss").xp_reward > stats("soldier").xp_reward
    assert stats("soldier", tier=4).hp > stats("soldier", tier=1).hp
    assert len(stats("soldier", "boss").abilities) == 3


def test_preset_uses_canonical_status_effects_and_flavor_moves():
    template = build_enemy_template("Arc Sentinel", "construct", "standard", 2, ["Taser Burst", "Rail Slam"])
    assert [a["name"] for a in template.abilities] == ["Taser Burst", "Rail Slam"]
    canonical = {"bleed", "stun", "weaken", "focus", "poisoned", "burning"}
    for archetype in ("brute", "soldier", "skirmisher", "beast", "caster", "construct", "undead", "horror"):
        for ability in build_enemy_template("X", archetype).abilities:
            if "status_effect" in ability:
                assert ability["status_effect"] in canonical


def test_loot_names_follow_the_setting():
    names = {entry["name"] for entry in build_enemy_template("X", "soldier", "elite", genre=SCIFI).loot_table}
    assert "Med Injector" in names
    assert "Healing Draught" not in names


# ─── LLM spec validation ───


def test_normalize_spec_cleans_and_infers():
    spec = normalize_spec({"name": "  a chrome hunter drone. ", "archetype": "robotish", "threat": "huge",
                           "moves": ["Laser Sweep", 42, "x" * 80]})
    assert spec.name == "Chrome Hunter Drone"
    assert spec.archetype == "construct"
    assert spec.threat == "standard"
    assert spec.moves[0] == "Laser Sweep"
    assert all(len(m) <= 30 for m in spec.moves)


@pytest.mark.parametrize("data", [None, "drone", {}, {"name": ""}, {"name": "!!!"}])
def test_normalize_spec_rejects_unusable(data):
    assert normalize_spec(data) is None


class _Completions:
    def __init__(self, content):
        self.content = content
        self.requests = []

    async def create(self, **kwargs):
        self.requests.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))])


def _designer(content):
    designer = EnemyDesigner()
    completions = _Completions(content)
    designer.client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return designer, completions


def test_designer_parses_llm_json_and_sends_campaign_context():
    designer, completions = _designer(
        '{"name": "Arasaka Hunter-Killer", "archetype": "construct", "threat": "elite", '
        '"description": "A sleek kill-drone.", "moves": ["Micro-Missile Volley", "Mono-Wire Lash"]}'
    )
    spec = asyncio.run(designer.describe(narration=DRONE_SCENE, world_state=_world(), threat_hint=None))
    assert spec.name == "Arasaka Hunter-Killer"
    assert (spec.archetype, spec.threat) == ("construct", "elite")
    prompt = completions.requests[0]["messages"][1]["content"]
    assert "Neon Requiem" in prompt and "security drone" in prompt


def test_designer_returns_none_on_garbage():
    designer, _ = _designer("I cannot help with that")
    assert asyncio.run(designer.describe(narration=DRONE_SCENE, world_state=_world())) is None


# ─── Orchestration ───


class _StubDesigner:
    def __init__(self, spec):
        self.spec = spec
        self.hints = []

    async def describe(self, *, narration, world_state, threat_hint=None):
        self.hints.append(threat_hint)
        return self.spec


def test_llm_spec_drives_name_and_stats():
    spec = EnemySpec(name="Arasaka Hunter-Killer", archetype="construct", threat="elite", moves=["Volley"])
    enemy = asyncio.run(design_enemy(_StubDesigner(spec), narration=DRONE_SCENE, world_state=_world(), player_level=2))
    expected = build_enemy_template("Arasaka Hunter-Killer", "construct", "elite", 2, ["Volley"], SCIFI)
    assert enemy.source == "designed"
    assert enemy.template.name == "Arasaka Hunter-Killer"
    assert (enemy.template.hp, enemy.template.armor) == (expected.hp, expected.armor)
    assert enemy.template.abilities[0]["name"] == "Volley"


def test_final_beat_makes_it_a_boss_fight():
    campaign = dict(CYBERPUNK_CAMPAIGN, current_act=2, current_beat=2, acts=[
        {"act_id": 1, "beats": [{"beat_id": 1, "title": "Intro", "type": "social"}]},
        {"act_id": 2, "beats": [{"beat_id": 1, "title": "Chase", "type": "exploration"},
                                {"beat_id": 2, "title": "Tower Top", "type": "combat"}]},
    ])
    designer = _StubDesigner(EnemySpec(name="Director Kade", archetype="soldier", threat="standard"))
    enemy = asyncio.run(design_enemy(designer, narration="Kade attacks.", world_state=_world(campaign), player_level=1))
    assert designer.hints == ["boss"]
    assert enemy.threat == "boss"


def test_heuristic_used_when_llm_fails():
    enemy = asyncio.run(design_enemy(_StubDesigner(None), narration=DRONE_SCENE, world_state=_world(), player_level=1))
    assert enemy.source == "narrator"
    assert enemy.template.name == "Corporate Security Drone"
    assert enemy.archetype == "construct"


def test_scifi_fallback_when_no_enemy_is_named():
    enemy = asyncio.run(design_enemy(None, narration="The wind howls.", world_state=_world(), player_level=1))
    assert enemy.source == "fallback"
    assert enemy.template.name not in CLASSIC_NAMES


def test_fantasy_goblin_keeps_its_hand_built_template():
    fantasy = {"title": "The Dark Tower", "premise": "A tower in the mountains", "setting": "A frontier tavern"}
    enemy = asyncio.run(design_enemy(None, narration="A goblin scavenger lunges at you!",
                                     world_state=_world(fantasy), player_level=1))
    assert enemy.enemy_key == "goblin_scavenger"
    assert enemy.template.name == "Goblin Scavenger"
    assert enemy.template.hp == ENEMY_TEMPLATES["goblin_scavenger"].hp


def test_out_of_tier_classic_is_rebuilt_at_player_level():
    fantasy = {"title": "The Dark Tower", "premise": "A tower", "setting": "A tavern"}
    enemy = asyncio.run(design_enemy(None, narration="A lich rises and attacks!", world_state=_world(fantasy), player_level=1))
    assert enemy.template.name == "Lich"
    assert enemy.template.tier == 1
    assert enemy.template.hp < ENEMY_TEMPLATES["lich_king"].hp


# ─── API ───


def _cyberpunk_session(client, app_state):
    app_state.intent_parser.next_intent = make_intent(description="inspect stonework")
    session_id, headers = create_session(client)
    world = get_session(session_id).world_state
    world["campaign"].update({k: v for k, v in CYBERPUNK_CAMPAIGN.items() if k not in ("acts", "current_act", "current_beat")})
    world["combat_tension"] = 5
    app_state.narrator.text = DRONE_SCENE
    return session_id, headers


def test_combat_uses_the_campaign_enemy(client, app_state):
    session_id, headers = _cyberpunk_session(client, app_state)

    body = act(client, session_id, headers).json()

    enemy = body["combat_data"]["enemy"]
    assert enemy["name"] == "Corporate Security Drone"
    preset = build_enemy_template("Corporate Security Drone", "construct", "standard", 1, None, SCIFI)
    assert (enemy["max_hp"], enemy["armor"]) == (preset.hp, preset.armor)
    stored = get_session(session_id).world_state["combat"]
    assert stored["enemy_profile"]["archetype"] == "construct"
    assert stored["xp_reward"] == preset.xp_reward


def test_designed_enemy_victory_awards_server_side_rewards(client, app_state):
    session_id, headers = _cyberpunk_session(client, app_state)
    started = act(client, session_id, headers).json()
    xp_reward = get_session(session_id).world_state["combat"]["xp_reward"]
    combat = started["combat_data"]
    body = {
        "combat_id": combat["combat_id"], "result": "victory",
        "player_hp": combat["player"]["hp"], "player_mana": combat["player"]["mana"],
        "enemy_name": "Giant Rat", "combat_log": [], "turns_taken": 4,
    }

    # A forged enemy name is rejected outright...
    forged = client.post(f"/session/{session_id}/combat/resolve", headers=headers, json=body)
    assert forged.status_code == 400

    # ...and the real one earns the stored encounter's rewards.
    body["enemy_name"] = combat["enemy"]["name"]
    response = client.post(f"/session/{session_id}/combat/resolve", headers=headers, json=body)
    assert response.status_code == 200, response.text
    assert response.json()["rewards"]["xp"] == xp_reward > 0
    narrated = app_state.narrator.calls[-1]["intent"].description
    assert "Corporate Security Drone" in narrated
