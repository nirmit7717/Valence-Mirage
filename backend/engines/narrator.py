"""Narrator — AI-driven narrative generation with rule grounding."""

import logging
from pathlib import Path

from openai import AsyncOpenAI

from models.action import ActionIntent
from models.game_state import PlayerState
from engines.campaign_planner import CampaignPlanner, CampaignBlueprint
from rag import RuleRetriever
import config

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "narrator.txt"


class Narrator:
    """Generates narrative descriptions of action outcomes."""

    def __init__(self):
        self.client = AsyncOpenAI(
            base_url=config.NVIDIA_BASE_URL,
            api_key=config.NVIDIA_API_KEY,
        )
        self.prompt = PROMPT_PATH.read_text()
        self.rule_retriever = RuleRetriever()

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

        user_msg = (
            f"Action: {intent.description}\n"
            f"Type: {intent.action_type}\n"
            f"Outcome: {outcome_result}\n"
            f"Dice: rolled {roll} vs threshold {threshold}\n"
            f"Player: {player.name} (HP {player.hp}/{player.max_hp}, "
            f"Mana {player.mana}/{player.max_mana}, "
            f"Level {player.level})\n"
            f"Inventory: {inv_names}\n"
            f"Location: {world_state.get('location', 'unknown')}\n"
            f"Situation: {world_state.get('situation', '')[-500:]}\n"
        )

        if campaign_title:
            user_msg += f"Campaign: {campaign_title} — {campaign_premise[:150]}\n"
        if beat_ctx:
            user_msg += f"Current Beat: {beat_ctx}\n"
        if npc_ctx:
            user_msg += f"NPCs Present: {npc_ctx}\n"
        if npc_dialogue:
            user_msg += f"NPC Interaction: {npc_dialogue.get('dialogue', '')[:200]}\n"
        if history_ctx:
            user_msg += f"\nRecent History:\n{history_ctx}"
        

        if rules_context:
            user_msg += f"\nRelevant Rules:\n{rules_context}\n"

        try:
            response = await self.client.chat.completions.create(
                model=config.NARRATOR_MODEL,
                messages=[
                    {"role": "system", "content": self.prompt},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.85,
                max_tokens=800,
            )
            narration = response.choices[0].message.content.strip()
            logger.debug(f"Narration: {narration[:100]}...")
            return narration

        except Exception as e:
            logger.error(f"Narration API error: {e}")
            return f"Your {intent.action_type} results in {outcome_result}. The world shifts around you."


    async def narrate_opening(self, title: str, premise: str, setting: str, player_name: str, tone: str = "", character_class: str = "") -> str:
        """Generate rich opening narration for a new campaign."""
        class_context = f"\nCharacter class: {character_class}" if character_class else ""
        user_msg = (
            f"Generate an atmospheric opening scene for a dark fantasy RPG.\n"
            f"Campaign: {title}\n"
            f"Premise: {premise}\n"
            f"Setting: {setting}\n"
            f"Player: {player_name}{class_context}\n"
            f"Tone: {tone or 'dark fantasy'}\n"
            f"3-4 paragraphs. Set the scene, introduce the atmosphere, reflect the character's nature, end with a call to action for {player_name}."
        )
        try:
            response = await self.client.chat.completions.create(
                model=config.INTENT_MODEL,  # cheap 8b for openings
                messages=[
                    {"role": "system", "content": "You are a dark fantasy RPG narrator. Write vivid, atmospheric prose. No JSON, no meta-commentary."},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.9,
                max_tokens=500,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Opening narration failed: {e}")
            return f"You find yourself in {setting}. {premise} The journey ahead is shrouded in mystery."
