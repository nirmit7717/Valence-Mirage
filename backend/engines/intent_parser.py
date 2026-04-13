"""Intent Parser — Extracts structured ActionIntent from free-form player input."""

import json
import logging
from pathlib import Path

from openai import AsyncOpenAI
from pydantic import ValidationError

from models.action import ActionIntent
import config

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "intent_parse.txt"


class IntentParser:
    def __init__(self):
        self.client = AsyncOpenAI(
            base_url=config.NVIDIA_BASE_URL,
            api_key=config.NVIDIA_API_KEY,
        )
        self.system_prompt = PROMPT_PATH.read_text()

    async def parse(self, player_input: str, world_context: str, stats_summary: str) -> ActionIntent:
        user_message = (
            f'Player action: "{player_input}"\n'
            f"Current context: {world_context}\n"
            f"Player stats: {stats_summary}"
        )

        response = await self.client.chat.completions.create(
            model=config.INTENT_MODEL,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.1,
            max_tokens=300,
        )

        raw = response.choices[0].message.content.strip()
        logger.debug(f"Intent parser raw output: {raw}")

        try:
            data = json.loads(raw)
            return ActionIntent(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Failed to parse intent: {e}\nRaw: {raw}")
            return ActionIntent(
                action_type="other",
                description=player_input[:200],
                scale="moderate",
                risk="medium",
                target=None,
                relevant_stat="wisdom",
                uses_resource=False,
                resource_cost=0,
            )
