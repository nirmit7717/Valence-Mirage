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
    ) -> str:
        # Fetch relevant rules for grounding
        relevant_rules = self.rule_retriever.get_relevant_rules(
            intent.action_type, intent.description
        )

        # Truncate rules to avoid token bloat (max ~600 chars)
        rules_context = relevant_rules[:600] if relevant_rules else ""

        user_msg = (
            f"Action: {intent.description}\n"
            f"Type: {intent.action_type}\n"
            f"Outcome: {outcome_result}\n"
            f"Dice: rolled {roll} vs threshold {threshold}\n"
            f"Player: {player.name} (HP {player.hp}/{player.max_hp}, "
            f"Mana {player.mana}/{player.max_mana}, "
            f"Level {player.level})\n"
            f"Location: {world_state.get('location', 'unknown')}\n"
            f"Situation: {world_state.get('situation', '')[-300:]}\n"
        )

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
                max_tokens=400,
            )
            narration = response.choices[0].message.content.strip()
            logger.debug(f"Narration: {narration[:100]}...")
            return narration

        except Exception as e:
            logger.error(f"Narration API error: {e}")
            return f"Your {intent.action_type} results in {outcome_result}. The world shifts around you."
