"""Narrator — AI-driven narrative generation with rule grounding."""

import logging
from pathlib import Path

from openai import AsyncOpenAI

import re

from models.action import ActionIntent
from models.game_state import PlayerState
from engines.campaign_planner import CampaignPlanner, CampaignBlueprint
from engines.pacing import (
    AFTER_FIGHT,
    DEVELOP,
    FIGHT_LEAD_IN,
    FINAL_FIGHT_LEAD_IN,
    RESOLVE,
    STORY_ENDS,
    SURPRISE_FIGHT,
    WRAP_UP,
)
from rag import RuleRetriever
import config
from engines.llm_utils import extract_message_text
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "narrator.txt"
EPILOGUE_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "epilogue.txt"


# ─── Story pacing (see engines/pacing.py) ───

# One instruction per kind of turn. The storyteller follows it so the story
# resolves when the turn budget says it should, not whenever the model feels like it.
PACING_DIRECTIVES = {
    DEVELOP: (
        "Develop the current beat: deepen it with a clue, a complication or a character moment. "
        "Do not resolve it yet."
    ),
    RESOLVE: (
        "The current beat resolves on this turn. Bring it to a satisfying close, "
        "then point the story toward the next beat."
    ),
    WRAP_UP: (
        "Time is short. Resolve the current beat NOW, even if it costs the player something "
        "or leaves a complication behind, then point the story toward the next beat."
    ),
    FIGHT_LEAD_IN: (
        "This chapter is a fight. Introduce the enemy now and end on the moment the battle begins."
    ),
    FINAL_FIGHT_LEAD_IN: (
        "FINAL CONFRONTATION. The campaign's central threat appears in person now. Make it feel like "
        "the climax of everything so far, and end on the moment the last battle begins."
    ),
    SURPRISE_FIGHT: (
        "Danger interrupts the current beat: an enemy appears before the beat can resolve."
    ),
    STORY_ENDS: (
        "THE STORY ENDS NOW. Resolve this action, then bring the campaign's central conflict to its "
        "conclusion and describe how the world is changed. Do not suggest any further actions."
    ),
    AFTER_FIGHT: (
        "The fight is over. Show its aftermath briefly, then point the story toward the next beat."
    ),
}


def pacing_section(brief: dict | None) -> str:
    """The STORY PACING block: where the player is in the story and what this turn must do.

    ``brief`` is ``pacing.story_progress(...)`` plus a ``moment`` key.
    """
    if not brief:
        return ""
    directive = PACING_DIRECTIVES.get(brief.get("moment"), PACING_DIRECTIVES[DEVELOP])
    lines = ["STORY PACING:"]
    act_title = brief.get("act_title")
    lines.append(
        f"- Chapter {brief.get('chapter')} of {brief.get('total')}"
        + (f" · Act {brief.get('act_id')}: {act_title}" if act_title else "")
    )
    lines.append(f"- Current beat: {brief.get('beat_title', '')} ({brief.get('beat_type', '')})")
    if brief.get("final"):
        lines.append("- This is the final chapter of the campaign.")
    elif brief.get("next_beat_title"):
        kind = "a fight" if brief.get("next_beat_type") == "combat" else brief.get("next_beat_type", "")
        lines.append(f"- Next beat: {brief['next_beat_title']} ({kind})")
    lines.append(f"- This turn: {directive}")
    return "\n".join(lines)


_CHOICE_LINE = re.compile(r"^\s*(?:→|->).*$", re.MULTILINE)


def strip_choice_lines(text: str) -> str:
    """Remove "→ action" suggestion lines (an ending offers no further actions)."""
    return re.sub(r"\n{3,}", "\n\n", _CHOICE_LINE.sub("", text or "")).strip()


class Narrator:
    """Generates narrative descriptions of action outcomes."""

    def __init__(self):
        self.client = AsyncOpenAI(
            base_url=config.NVIDIA_BASE_URL,
            api_key=config.NVIDIA_API_KEY,
            timeout=60.0,        # Fail fast instead of waiting 5min for 504
            max_retries=1,      # Reduce from default 2 retries
        )
        self.prompt = PROMPT_PATH.read_text()
        self.epilogue_prompt = EPILOGUE_PROMPT_PATH.read_text()
        combat_prompt_path = Path(__file__).parent.parent / "prompts" / "combat_narrator.txt"
        self.combat_prompt = combat_prompt_path.read_text()
        self.rule_retriever = RuleRetriever()

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4))
    async def _safe_chat_completion(self, messages, max_tokens):
        """Wrapper for OpenAI call with tenacity retry."""
        return await self.client.chat.completions.create(
            model=config.NARRATOR_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.8,
        )

    async def narrate(
        self,
        intent: ActionIntent,
        outcome_result: str,
        roll: int,
        threshold: int,
        player: PlayerState,
        world_state: dict,
        npc_dialogue: dict | None = None,
        turn_history: list | None = None,
        combat_context: str | None = None,
        narration_params: dict | None = None,
        pacing: dict | None = None,
    ) -> str:
        # Fetch relevant rules for grounding
        relevant_rules = await self.rule_retriever.get_relevant_rules(
            intent.action_type, intent.description
        )

        # Truncate rules to avoid token bloat (max ~600 chars)
        rules_context = relevant_rules[:600] if relevant_rules else ""

        # Campaign context
        campaign = world_state.get("campaign", {})
        campaign_title = campaign.get("title", "")
        campaign_premise = campaign.get("premise", "")
        beat_ctx = ""
        try:
            ca = campaign.get("current_act", 1)
            cb = campaign.get("current_beat", 1)
            for act in campaign.get("acts", []):
                if act.get("act_id") == ca:
                    for beat in act.get("beats", []):
                        if beat.get("beat_id") == cb:
                            beat_ctx = f"{beat.get('title', '')} — {beat.get('description', '')[:120]}"
                            break
                    break
        except Exception:
            beat_ctx = ""

        # NPC context
        npc_ctx = ""
        npcs = world_state.get("npcs", {})
        if npcs:
            npc_parts = []
            for nid, nd in npcs.items():
                p = nd.get("personality", {})
                interacted = nd.get("interacted", False)
                if interacted:
                    npc_parts.append(f"{p.get('name','?')} ({p.get('role','?')}, disposition={nd.get('disposition',0):.1f})")
            npc_ctx = "; ".join(npc_parts[:3])

        # Turn history summary (last 3 turns)
        history_ctx = ""
        if turn_history:
            for t in turn_history[-3:]:
                player_in = t.player_input if hasattr(t, 'player_input') else t.get('player_input', '')
                narr = t.outcome.narration if hasattr(t, 'outcome') else t.get('outcome', {}).get('narration', '')
                history_ctx += f"- Player: {player_in[:80]} → {narr[:100]}\n"

        # Player inventory
        inv_names = ", ".join(i.name for i in player.inventory[:8]) if player.inventory else "empty"

        # HP/mana descriptive state (never send raw numbers to LLM)
        hp_frac = player.hp / player.max_hp if player.max_hp > 0 else 1.0
        mana_frac = player.mana / player.max_mana if player.max_mana > 0 else 1.0
        if hp_frac > 0.8: hp_desc = "healthy"
        elif hp_frac > 0.5: hp_desc = "bruised and battered"
        elif hp_frac > 0.25: hp_desc = "wounded, blood running freely"
        else: hp_desc = "at death's door, barely conscious"
        if mana_frac > 0.8: mana_desc = "brimming with energy"
        elif mana_frac > 0.5: mana_desc = "moderately taxed"
        elif mana_frac > 0.25: mana_desc = "running thin, nearly spent"
        else: mana_desc = "dangerously low"

        user_msg = (
            f"Action: {intent.description}\n"
            f"Type: {intent.action_type}\n"
            f"Outcome: {outcome_result}\n"
            f"Dice: rolled {roll} vs threshold {threshold}\n"
            f"Player: {player.name} (Level {player.level}, physically {hp_desc}, arcane reserves {mana_desc})\n"
            f"Inventory: {inv_names}\n"
            f"Location: {world_state.get('location', 'unknown')}\n"
            f"Situation: {world_state.get('situation', '')[-500:]}\n"
        )

        if campaign_title:
            user_msg += f"Campaign: {campaign_title} — {campaign_premise[:150]}\n"
        if beat_ctx:
            user_msg += f"Current Beat: {beat_ctx}\n"
        story_pacing = pacing_section(pacing)
        if story_pacing:
            user_msg += f"\n{story_pacing}\n\n"
        if npc_ctx:
            user_msg += f"NPCs Present: {npc_ctx}\n"
        if npc_dialogue:
            user_msg += f"NPC Interaction: {npc_dialogue.get('dialogue', '')[:200]}\n"
        if history_ctx:
            user_msg += f"\nRecent History:\n{history_ctx}"

        if combat_context:
            user_msg += f"\n{combat_context}\n"

        if rules_context:
            user_msg += f"\nRelevant Rules:\n{rules_context}\n"

        try:
            response = await self.client.chat.completions.create(
                model=config.NARRATOR_MODEL,
                messages=[
                    {"role": "system", "content": self.prompt},
                    {"role": "user", "content": user_msg},
                ],
                temperature=narration_params.get("temperature", 0.85) if narration_params else 0.85,
                max_tokens=narration_params.get("max_tokens", 500) if narration_params else 500,
            )
            content = extract_message_text(response)
            if not content:
                logger.warning("Narrator: empty narration content returned from model")
                return f"Your {intent.action_type} results in {outcome_result}. The world shifts around you."

            narration = content.strip()
            logger.debug(f"Narration: {narration[:100]}...")
            return narration

        except Exception as e:
            logger.error(f"Narration API error: {e}")
            return f"Your {intent.action_type} results in {outcome_result}. The world shifts around you."


    async def narrate_epilogue(
        self,
        player: PlayerState,
        world_state: dict,
        final_enemy: str,
        fight_summary: str = "",
        turn_history: list | None = None,
        narration_params: dict | None = None,
    ) -> str:
        """The campaign's ending, written after the final fight is won. Never offers choices."""
        campaign = world_state.get("campaign", {}) or {}
        title = campaign.get("title", "") or "the journey"
        history_ctx = ""
        for t in (turn_history or [])[-4:]:
            player_in = t.player_input if hasattr(t, "player_input") else t.get("player_input", "")
            narr = t.outcome.narration if hasattr(t, "outcome") else t.get("outcome", {}).get("narration", "")
            history_ctx += f"- {player_in[:80]} → {strip_choice_lines(narr)[:120]}\n"

        user_msg = (
            f"Campaign: {title} — {campaign.get('premise', '')[:200]}\n"
            f"Setting: {campaign.get('setting', '')[:150]}\n"
            f"Tone: {campaign.get('tone', '') or 'dark fantasy'}\n"
            f"Objective: {world_state.get('campaign_objective', '')}\n"
            f"Hero: {player.name}, a level {player.level} {player.character_class}\n"
            f"Final battle: {player.name} has just defeated {final_enemy}"
            + (f" ({fight_summary})" if fight_summary else "")
            + "\n"
            f"Location: {world_state.get('location', 'unknown')}\n"
            f"Last scene: {strip_choice_lines(world_state.get('situation', ''))[-400:]}\n"
        )
        if history_ctx:
            user_msg += f"\nThe journey so far (most recent last):\n{history_ctx}"
        user_msg += "\nWrite the ending of this campaign now."

        fallback = (
            f"{final_enemy} falls, and with it the shadow that hung over {title} lifts at last. "
            f"{player.name} stands in the quiet that follows. The story will be told for a long time."
        )
        try:
            response = await self.client.chat.completions.create(
                model=config.NARRATOR_MODEL,
                messages=[
                    {"role": "system", "content": self.epilogue_prompt},
                    {"role": "user", "content": user_msg},
                ],
                temperature=narration_params.get("temperature", 0.85) if narration_params else 0.85,
                max_tokens=600,
            )
            content = strip_choice_lines(extract_message_text(response) or "")
            if not content:
                logger.warning("Narrator: empty epilogue returned from model")
                return fallback
            return content
        except Exception as e:
            logger.error(f"Epilogue narration failed: {e}")
            return fallback

    async def narrate_opening(self, title: str, premise: str, setting: str, player_name: str, tone: str = "", character_class: str = "") -> str:
        """Generate rich opening narration for a new campaign."""
        class_context = f"\nCharacter class: {character_class}" if character_class else ""
        user_msg = (
            f"Generate a highly structured and atmospheric opening scene for a dark fantasy RPG.\n"
            f"Campaign: {title}\n"
            f"Premise: {premise}\n"
            f"Setting: {setting}\n"
            f"Player: {player_name}{class_context}\n"
            f"Tone: {tone or 'dark fantasy'}\n"
            f"Instructions:\n"
            f"1. Properly define the vivid scene and the exact situation the player is currently in (avoid vague contexts).\n"
            f"2. Write 2-3 paragraphs establishing the world and the immediate hook.\n"
            f"3. End by providing EXACTLY 3 actionable choices for the player to begin their journey, using this exact format:\n"
            f"  → [action suggestion 1]\n"
            f"  → [action suggestion 2]\n"
            f"  → [action suggestion 3]\n"
            f"Make the choices under 100 characters each."
        )
        try:
            response = await self.client.chat.completions.create(
                model=config.INTENT_MODEL,  # cheap 8b for openings
                messages=[
                    {"role": "system", "content": "You are a dark fantasy RPG narrator. Write vivid atmospheric prose only. No JSON. No markdown. No reasoning blocks. No empty responses. No meta-commentary."},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.9,
                max_tokens=500,
            )
            content = extract_message_text(response)
            if not content:
                logger.warning("Narrator: empty opening narration content returned from model")
                return f"You find yourself in {setting}. {premise} The journey ahead is shrouded in mystery."
            return content.strip()
        except Exception as e:
            logger.warning(f"Opening narration failed: {e}")
            return f"You find yourself in {setting}. {premise} The journey ahead is shrouded in mystery."

    async def narrate_combat_action(self, action_description: str, result: str,
                                     character_class: str = "") -> str:
        """Short combat narration — 2-3 sentences, fast-paced."""
        class_ctx = f" Character class: {character_class}." if character_class else ""
        user_msg = (
            f"Action: {action_description}\n"
            f"Result: {result}{class_ctx}\n"
            f"Describe this combat action in 2-3 sentences. Focus on the impact."
        )
        try:
            response = await self.client.chat.completions.create(
                model=config.INTENT_MODEL,  # fast 8b for combat
                messages=[
                    {"role": "system", "content": self.combat_prompt},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.8,
                max_tokens=150,
            )
            content = extract_message_text(response)
            if not content:
                logger.warning("Narrator: empty combat narration content returned from model")
                return f"{action_description}. {result}."
            return content.strip()
        except Exception as e:
            logger.warning(f"Combat narration failed: {e}")
            return f"{action_description}. {result}."
