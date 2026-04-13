"""Narrator — Generates narrative text based on action outcomes."""

import logging
from pathlib import Path

from openai import AsyncOpenAI

from models.action import ActionIntent
from models.game_state import PlayerState
import config

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "narrator.txt"


class Narrator:
    def __init__(self):
        self.client = AsyncOpenAI(
            base_url=config.NVIDIA_BASE_URL,
            api_key=config.NVIDIA_API_KEY,
        )
        self.system_prompt = PROMPT_PATH.read_text()

    async def narrate(
        self,
        intent: ActionIntent,
        outcome_result: str,
        roll: int,
        threshold: int,
        player: PlayerState,
        world_state: dict,
    ) -> str:
        user_message = (
            f"Player: {player.name}\n"
            f"Current situation: {world_state.get('situation', 'Unknown')}\n"
            f"Location: {world_state.get('location', 'Unknown')}\n"
            f"Player action: {intent.description}\n"
            f"Action type: {intent.action_type} (scale: {intent.scale}, risk: {intent.risk})\n"
            f"Outcome: {outcome_result}\n"
            f"Roll: {roll} (needed {threshold}+)\n"
            f"Player HP: {player.hp}/{player.max_hp}, Mana: {player.mana}/{player.max_mana}\n"
        )

        if intent.target:
            user_message += f"Target: {intent.target}\n"

        try:
            response = await self.client.chat.completions.create(
                model=config.NARRATOR_MODEL,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.8,
                max_tokens=500,
            )

            narration = response.choices[0].message.content.strip()
            logger.info(f"Narration generated: {len(narration)} chars")
            return narration

        except Exception as e:
            logger.error(f"Narration generation failed: {e}")
            fallback_map = {
                "critical_success": f"Against all odds, your {intent.action_type} succeeds brilliantly!",
                "success": f"Your {intent.action_type} works as intended.",
                "partial_success": f"Your {intent.action_type} partially succeeds, but with a cost.",
                "failure": f"Your {intent.action_type} fails. Things don't go as planned.",
                "critical_failure": f"Your {intent.action_type} goes catastrophically wrong!",
            }
            return fallback_map.get(outcome_result, "Something happens...")
