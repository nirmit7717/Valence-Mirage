"""Loot Engine — AI-driven reward generation based on action outcomes."""

import json
import logging
from pathlib import Path

from openai import AsyncOpenAI
from pydantic import ValidationError

from models.action import ActionIntent
from models.game_state import Item
import config

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "loot_generate.txt"


class LootEngine:
    """Generates contextual loot/rewards based on action outcomes."""

    def __init__(self):
        self.client = AsyncOpenAI(
            base_url=config.NVIDIA_BASE_URL,
            api_key=config.NVIDIA_API_KEY,
        )
        self.prompt = PROMPT_PATH.read_text()

    async def generate_loot(
        self,
        intent: ActionIntent,
        outcome: str,
        context: str,
    ) -> Item | None:
        """Generate a loot item based on the action outcome.

        Returns an Item if loot is warranted, or None if no loot.
        """
        # No loot on failures
        if outcome in ("failure", "critical_failure", "narrative_choice"):
            return None

        user_msg = (
            f"Player action: {intent.description}\n"
            f"Action type: {intent.action_type}\n"
            f"Outcome: {outcome}\n"
            f"Context: {context}\n"
            f"Generate an appropriate reward. Output null if no loot fits."
        )

        try:
            response = await self.client.chat.completions.create(
                model=config.INTENT_MODEL,
                messages=[
                    {"role": "system", "content": self.prompt},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.6,
                max_tokens=200,
            )

            raw = response.choices[0].message.content.strip()
            logger.debug(f"Loot raw: {raw}")

            # Handle null/no loot
            if raw.lower() in ("null", "none", "nil", ""):
                return None

            # Strip markdown if present
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            data = json.loads(raw)
            if data is None:
                return None

            return Item(**data)

        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning(f"Loot parse failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Loot generation error: {e}")
            return None
