"""Turn-budget pacing — decides when story beats finish and when fights happen.

Every beat has a turn budget (``min_turns``..``max_turns``). Adding the budgets
up gives each beat a *window* on the campaign's turn counter: the earliest and
latest turn on which it may finish. The rules:

- A story beat can't finish before its window opens, or before it has had its
  minimum turns. It finishes once the player's action moves it on.
- A story beat still open when it runs out of turns (its own maximum, or its
  window closing) is forced to wrap up on that turn.
- A combat beat takes exactly 2 turns: a lead-in turn where the enemy appears,
  then the fight itself (one turn). It finishes only when the fight is won.
- Surprise fights are allowed only where they can't break the budget.

Because a beat never finishes before ``sum(min)`` or after ``sum(max)`` turns,
a campaign always lasts between its template's ``min_turns`` and ``max_turns``.

Pure functions only — no app state, no I/O.
"""

from __future__ import annotations

CONTINUE = "continue"
COMPLETE = "complete"
FORCE = "force"


def _beat_dict(beat) -> dict:
    return beat if isinstance(beat, dict) else beat.model_dump()


def _budget(beat: dict) -> tuple[int, int]:
    """(min, max) turns, with type defaults for sessions saved before budgets existed."""
    if beat.get("type") == "combat":
        return 2, 2
    low = int(beat.get("min_turns") or 1)
    high = max(int(beat.get("max_turns") or 2), low)
    return low, high


def ordered_beats(campaign) -> list[tuple[dict, dict]]:
    """[(act, beat)] in story order. Accepts a blueprint model or its dict."""
    data = campaign if isinstance(campaign, dict) else campaign.model_dump()
    acts = sorted(data.get("acts") or [], key=lambda a: a.get("act_id", 0))
    return [(act, beat) for act in acts for beat in act.get("beats") or []]


def current_index(campaign) -> int:
    """Index of the current beat in story order (0 if the position is unknown)."""
    data = campaign if isinstance(campaign, dict) else campaign.model_dump()
    act_id, beat_id = data.get("current_act", 1), data.get("current_beat", 1)
    for index, (act, beat) in enumerate(ordered_beats(data)):
        if act.get("act_id") == act_id and beat.get("beat_id") == beat_id:
            return index
    return 0


def beat_windows(campaign) -> list[tuple[int, int]]:
    """For each beat, (earliest, latest) campaign turn on which it may finish."""
    windows, earliest, latest = [], 0, 0
    for _, beat in ordered_beats(campaign):
        low, high = _budget(beat)
        earliest += low
        latest += high
        windows.append((earliest, latest))
    return windows


def turn_budget(campaign) -> tuple[int, int]:
    """(min, max) turns for the whole campaign."""
    windows = beat_windows(campaign)
    return windows[-1] if windows else (0, 0)


def is_final_beat(campaign) -> bool:
    beats = ordered_beats(campaign)
    return bool(beats) and current_index(campaign) == len(beats) - 1


def current_beat(campaign) -> dict | None:
    beats = ordered_beats(campaign)
    return beats[current_index(campaign)][1] if beats else None


def next_beat(campaign) -> dict | None:
    beats = ordered_beats(campaign)
    index = current_index(campaign) + 1
    return beats[index][1] if index < len(beats) else None


def story_progress(campaign) -> dict | None:
    """Where the player is in the story, for the HUD and the storyteller."""
    beats = ordered_beats(campaign)
    if not beats:
        return None
    index = current_index(campaign)
    act, beat = beats[index]
    following = beats[index + 1][1] if index + 1 < len(beats) else None
    return {
        "chapter": index + 1,
        "total": len(beats),
        "act_id": act.get("act_id"),
        "act_title": act.get("title", ""),
        "beat_title": beat.get("title", ""),
        "beat_type": beat.get("type", ""),
        "threat_hint": beat.get("threat_hint"),
        "final": index == len(beats) - 1,
        "next_beat_title": following.get("title") if following else None,
        "next_beat_type": following.get("type") if following else None,
    }


def decide_story_beat(beat, window: tuple[int, int], turn_after: int, turns_in_beat_after: int,
                      moved_on: bool) -> str:
    """continue / complete / force for a non-combat beat, given the turn about to be played.

    ``turn_after`` and ``turns_in_beat_after`` count the current turn.
    """
    low, high = _budget(_beat_dict(beat))
    earliest, latest = window
    ready = turns_in_beat_after >= low and turn_after >= earliest
    if moved_on and ready:
        return COMPLETE
    if turns_in_beat_after >= high or turn_after >= latest:
        return FORCE
    return CONTINUE


# ─── What the storyteller does with a turn (directives live in engines/narrator.py) ───

DEVELOP = "develop"                          # story beat continues: deepen it, don't resolve it
RESOLVE = "resolve"                          # story beat finishes this turn
WRAP_UP = "wrap_up"                          # story beat is out of turns: resolve it now, even at a cost
FIGHT_LEAD_IN = "fight_lead_in"              # combat beat: introduce the enemy
FINAL_FIGHT_LEAD_IN = "final_fight_lead_in"  # the boss fight: the central threat appears
SURPRISE_FIGHT = "surprise_fight"            # tension fight interrupts a story beat
STORY_ENDS = "story_ends"                    # legacy outlines: the last (story) beat ends the campaign
AFTER_FIGHT = "after_fight"                  # post-fight narration once the fight closed its beat


def narration_moment(decision: str, fight: str | None, final: bool) -> str:
    """Which directive the storyteller gets for a planned turn."""
    if fight == "planned":
        return FINAL_FIGHT_LEAD_IN if final else FIGHT_LEAD_IN
    if fight == "surprise":
        return SURPRISE_FIGHT
    if decision in (COMPLETE, FORCE) and final:
        return STORY_ENDS
    if decision == COMPLETE:
        return RESOLVE
    if decision == FORCE:
        return WRAP_UP
    return DEVELOP


def surprise_fight_allowed(campaign, world_state: dict, turn_after: int, turns_in_beat_after: int) -> bool:
    """Can an unplanned (tension) fight start on this turn without breaking the budget?

    Rules: never on a combat beat, never on the beat right before a planned fight,
    never in the final act, at most one per act, and the fight turn must still fit
    inside this beat's budget and window.
    """
    beats = ordered_beats(campaign)
    if not beats:
        return False
    index = current_index(campaign)
    act, beat = beats[index]
    if beat.get("type") == "combat":
        return False
    if index + 1 < len(beats) and beats[index + 1][1].get("type") == "combat":
        return False
    final_act_id = beats[-1][0].get("act_id")
    if act.get("act_id") == final_act_id:
        return False
    counts = world_state.get("surprise_fights") or {}
    if counts.get(str(act.get("act_id")), 0) >= 1:
        return False
    _, high = _budget(beat)
    _, latest = beat_windows(campaign)[index]
    fight_turn = turn_after + 1
    return turns_in_beat_after + 1 <= high and fight_turn <= latest


def record_surprise_fight(campaign, world_state: dict) -> None:
    act, _ = ordered_beats(campaign)[current_index(campaign)]
    counts = dict(world_state.get("surprise_fights") or {})
    key = str(act.get("act_id"))
    counts[key] = counts.get(key, 0) + 1
    world_state["surprise_fights"] = counts
