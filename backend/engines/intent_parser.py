"""Intent Parser — Extracts structured ActionIntent from free-form player input."""

import json
import logging
from pathlib import Path

from openai import AsyncOpenAI
from pydantic import ValidationError

from models.action import ActionIntent
import config
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "intent_parse.txt"


class IntentParser:
    def __init__(self):
        self.client = AsyncOpenAI(
            base_url=config.NVIDIA_BASE_URL,
            api_key=config.NVIDIA_API_KEY,
            timeout=30.0,
            max_retries=1,
        )
        self.system_prompt = PROMPT_PATH.read_text()

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4))
    async def _safe_chat_completion(self, messages):
        return await self.client.chat.completions.create(
            model=config.INTENT_MODEL,
            messages=messages,
            temperature=0.1,
            max_tokens=300,
        )

    async def parse(self, player_input: str, world_context: str, stats_summary: str) -> ActionIntent:
        user_message = (
            f'Player action: "{player_input}"\n'
            f"Current context: {world_context}\n"
            f"Player stats: {stats_summary}"
        )

        try:
            response = await self._safe_chat_completion(
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message},
                ]
            )
            raw = response.choices[0].message.content.strip()
            logger.debug(f"Intent parser raw output: {raw}")
        except Exception as e:
            logger.error(f"Intent parsing API failure: {e}")
            raw = "{}"

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
