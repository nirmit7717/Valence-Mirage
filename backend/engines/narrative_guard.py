"""Narrative Guard — Detects attempts to break story coherence or exploit the system."""

import logging
from openai import AsyncOpenAI

import config

logger = logging.getLogger(__name__)

GUARD_PROMPT = """You are a narrative coherence guardian for a fantasy RPG. Analyze the player's action and determine if it attempts to break the story.

RED FLAGS (return break_detected=true):
- Meta-gaming: referencing game mechanics ("I exploit the probability system")
- Reality breaking: attempting to be omnipotent or alter fundamental rules
- Refusal to engage: deliberately breaking immersion ("I do nothing forever")
- Inappropriate content: actions that don't fit a fantasy RPG setting
- Exploitation: trying to game the dice system with overly safe wording

LEGITIMATE ACTIONS (return break_detected=false):
- Creative problem solving, even if unconventional
- Bold/risky actions — these are encouraged
- Humorous actions that stay in character
- Actions that reference the game world naturally

Respond with JSON only:
{"break_detected": bool, "reason": "brief explanation", "suggested_redirect": "if break_detected, suggest an in-character alternative, else null"}"""


class NarrativeGuard:
    """Guards against narrative-breaking player actions."""

    def __init__(self):
        self.client = AsyncOpenAI(
            base_url=config.NVIDIA_BASE_URL,
            api_key=config.NVIDIA_API_KEY,
        )

    async def check_action(self, player_action: str, world_context: str = "") -> dict:
        """Check if an action tries to break narrative coherence.

        Returns: {"break_detected": bool, "reason": str, "suggested_redirect": str|None}
        """
        user_msg = (
            f"Player action: \"{player_action}\"\n"
            f"World context: {world_context[:200]}"
        )

        try:
            response = await self.client.chat.completions.create(
                model=config.INTENT_MODEL,  # Use fast 8b model for guard checks
                messages=[
                    {"role": "system", "content": GUARD_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.1,
                max_tokens=200,
            )

            import json
            raw = response.choices[0].message.content.strip()
            # Extract JSON from response
            if "```" in raw:
                raw = raw.split("```")[1].strip()
                if raw.startswith("json"):
                    raw = raw[4:].strip()

            result = json.loads(raw)
            logger.debug(f"Guard check: {result}")
            return result

        except Exception as e:
            logger.warning(f"Guard check failed: {e}")
            # On failure, allow the action (fail open)
            return {"break_detected": False, "reason": "guard_check_failed", "suggested_redirect": None}
