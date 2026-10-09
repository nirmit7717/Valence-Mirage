"""Story-aware combat: the fight screen knows the scene, the enemy's kind and the setting.

The combat payload carries the scene that set up the fight (choice lines removed,
at most 400 characters), the enemy's archetype, the campaign's genre and the
player's class, so the browser can describe the fight in the story's terms.
"""

from helpers import get_session, start_planned_fight
from models.combat import CombatState

LONG_SCENE = (
    "Rain hammers the old watchtower as you climb the last of its broken stairs. " * 6
    + "At the top, a goblin scavenger lunges from the shadows, blade raised.\n"
    "→ Fight\n→ Dodge\n→ Shout"
)


def test_scene_text_is_trimmed_at_a_sentence_start():
    import main

    scene = main._combat_scene(LONG_SCENE)
    assert len(scene) <= 400
    assert scene.startswith("Rain hammers") or scene.startswith("At the top")
    assert main._combat_scene("") == ""
    assert main._combat_scene("Short.\n→ Go") == "Short."


def test_the_fight_keeps_the_end_of_the_scene_that_introduced_the_enemy(client, app_state):
    session_id, _, combat = start_planned_fight(client, app_state, narration=LONG_SCENE)

    scene = get_session(session_id).world_state["combat"]["scene"]

    assert "→" not in scene
    assert len(scene) <= 400
    assert scene.endswith("a goblin scavenger lunges from the shadows, blade raised.")
    assert not scene.startswith(" ")
    assert combat["scene"] == scene


def test_a_short_scene_is_kept_whole(client, app_state):
    _, _, combat = start_planned_fight(client, app_state)
    assert combat["scene"] == "A goblin scavenger lunges from the shadows, blade raised."


def test_the_payload_describes_the_enemy_the_setting_and_the_hero(client, app_state):
    _, _, combat = start_planned_fight(client, app_state, character_class="rogue")

    assert combat["enemy"]["archetype"] == "skirmisher"  # goblins are quick and sneaky
    assert combat["genre"] == "fantasy"
    assert combat["player"]["character_class"] == "rogue"


def test_hydrate_returns_the_same_presentation(client, app_state):
    session_id, headers, combat = start_planned_fight(client, app_state)
    hydrated = client.get(f"/session/{session_id}/hydrate", headers=headers).json()["combat_data"]
    for key in ("scene", "genre"):
        assert hydrated[key] == combat[key]
    assert hydrated["enemy"]["archetype"] == combat["enemy"]["archetype"]


def test_fights_saved_before_scenes_existed_still_load(client, app_state):
    session_id, headers, _ = start_planned_fight(client, app_state)
    stored = get_session(session_id).world_state["combat"]
    stored.pop("scene")
    stored["enemy_profile"] = {}

    assert CombatState(**stored).scene == ""
    hydrated = client.get(f"/session/{session_id}/hydrate", headers=headers).json()["combat_data"]
    assert hydrated["scene"] == ""
    assert hydrated["enemy"]["archetype"] == "soldier"  # a sensible default for the browser
