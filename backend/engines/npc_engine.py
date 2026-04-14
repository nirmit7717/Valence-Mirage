"""NPC Engine — Dynamic NPC behavior with personality, memory, and disposition."""

import json
import logging
from datetime import datetime
from typing import Optional

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

import config

logger = logging.getLogger(__name__)


class NPCPersonality(BaseModel):
    """Core personality traits that drive NPC behavior."""
    name: str
    role: str = "commoner"  # merchant, guard, quest_giver, villain, ally, etc.
    traits: list[str] = Field(default_factory=lambda: ["neutral", "cautious"])
    speech_style: str = "casual"  # formal, casual, gruff, mysterious, hostile
    motivation: str = "self-interest"
    secrets: list[str] = Field(default_factory=list)
    knowledge: list[str] = Field(default_factory=list)


class NPCState(BaseModel):
    """Runtime state for an NPC in a session."""
    npc_id: str
    personality: NPCPersonality
    disposition: float = 0.0  # -1.0 (hostile) to 1.0 (friendly)
    trust: float = 0.0  # 0.0 to 1.0
    conversation_history: list[dict] = Field(default_factory=list)
    quest_given: bool = False
    quest_completed: bool = False
    interacted: bool = False
    alive: bool = True


NPC_DIALOGUE_PROMPT = """You are roleplaying as a fantasy RPG NPC. Stay in character at all times.

NPC PROFILE:
- Name: {name}
- Role: {role}
- Personality: {traits}
- Speech style: {speech_style}
- Motivation: {motivation}
- Disposition toward player: {disposition} (-1 hostile, 0 neutral, 1 friendly)
- Trust level: {trust}
- Secrets they know: {secrets}
- Knowledge they can share: {knowledge}
- Previous interactions: {history}

RULES:
- Disposition affects how helpful/hostile the NPC is
- If trust is low, NPC is evasive about secrets
- If disposition < -0.5, NPC may attack or refuse to talk
- If disposition > 0.5 and trust > 0.5, NPC may reveal secrets
- Keep dialogue concise (2-4 sentences)
- End with something that prompts the player to respond
- Never break character or reference game mechanics

Respond with JSON:
{{"dialogue": "what the NPC says", "disposition_change": float, "trust_change": float, "wants_to_fight": bool}}"""


class NPCEngine:
    """Generates dynamic NPC behavior and dialogue."""

    def __init__(self):
        self.client = AsyncOpenAI(
            base_url=config.NVIDIA_BASE_URL,
            api_key=config.NVIDIA_API_KEY,
        )

    async def generate_dialogue(
        self,
        npc: NPCState,
        player_action: str,
        player_name: str = "Adventurer",
    ) -> dict:
        """Generate NPC dialogue response to a player action."""
        history_str = ""
        if npc.conversation_history:
            recent = npc.conversation_history[-5:]
            history_str = "\n".join(
                f"  Player: {h.get('player', '')}\n  {npc.personality.name}: {h.get('npc', '')}"
                for h in recent
            )
        else:
            history_str = "No previous interactions."

        prompt = NPC_DIALOGUE_PROMPT.format(
            name=npc.personality.name,
            role=npc.personality.role,
            traits=", ".join(npc.personality.traits),
            speech_style=npc.personality.speech_style,
            motivation=npc.personality.motivation,
            disposition=round(npc.disposition, 2),
            trust=round(npc.trust, 2),
            secrets=", ".join(npc.personality.secrets) if npc.personality.secrets else "None",
            knowledge=", ".join(npc.personality.knowledge) if npc.personality.knowledge else "General world knowledge",
            history=history_str,
        )

        user_msg = f"Player ({player_name}) says/does: \"{player_action}\""

        try:
            response = await self.client.chat.completions.create(
                model=config.NARRATOR_MODEL,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.8,
                max_tokens=300,
            )

            raw = response.choices[0].message.content.strip()
            if "```" in raw:
                raw = raw.split("```")[1].strip()
                if raw.startswith("json"):
                    raw = raw[4:].strip()

            result = json.loads(raw)
            logger.debug(f"NPC dialogue for {npc.personality.name}: {result.get('dialogue', '')[:60]}...")
            return result

        except Exception as e:
            logger.error(f"NPC dialogue generation failed: {e}")
            return {
                "dialogue": f"*{npc.personality.name} eyes you warily but says nothing.*",
                "disposition_change": 0.0,
                "trust_change": 0.0,
                "wants_to_fight": npc.disposition < -0.5,
            }

    def create_npc(self, npc_id: str, personality: NPCPersonality, initial_disposition: float = 0.0) -> NPCState:
        """Create a new NPC with given personality."""
        return NPCState(
            npc_id=npc_id,
            personality=personality,
            disposition=initial_disposition,
        )

    async def generate_campaign_npcs(self, campaign_context: str, count: int = 3) -> list[NPCState]:
        """Generate NPCs appropriate for a campaign setting."""
        prompt = f"""Generate {count} unique NPCs for a fantasy RPG campaign.

Campaign context: {campaign_context}

For each NPC, respond with JSON array:
[{{"name": "NPC Name", "role": "their role", "traits": ["trait1", "trait2"], "speech_style": "formal|casual|gruff|mysterious|hostile", "motivation": "what drives them", "secrets": ["secret they know"], "knowledge": ["things they can tell the player"], "initial_disposition": float(-1 to 1)}}]

Keep names and roles varied. Make them memorable."""

        try:
            response = await self.client.chat.completions.create(
                model=config.INTENT_MODEL,
                messages=[
                    {"role": "system", "content": "You create compelling RPG NPCs. Output valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.9,
                max_tokens=800,
            )

            raw = response.choices[0].message.content.strip()
            if "```" in raw:
                raw = raw.split("```")[1].strip()
                if raw.startswith("json"):
                    raw = raw[4:].strip()

            npcs_data = json.loads(raw)
            npcs = []
            for i, npc_data in enumerate(npcs_data[:count]):
                personality = NPCPersonality(
                    name=npc_data.get("name", f"NPC_{i}"),
                    role=npc_data.get("role", "commoner"),
                    traits=npc_data.get("traits", ["neutral"]),
                    speech_style=npc_data.get("speech_style", "casual"),
                    motivation=npc_data.get("motivation", "self-interest"),
                    secrets=npc_data.get("secrets", []),
                    knowledge=npc_data.get("knowledge", []),
                )
                disposition = float(npc_data.get("initial_disposition", 0.0))
                npcs.append(self.create_npc(f"npc_{i}", personality, disposition))

            logger.info(f"Generated {len(npcs)} campaign NPCs")
            return npcs

        except Exception as e:
            logger.error(f"NPC generation failed: {e}")
            # Return a single default NPC
            return [self.create_npc("npc_0", NPCPersonality(
                name="Mysterious Stranger",
                role="wanderer",
                traits=["enigmatic", "helpful"],
                speech_style="mysterious",
                motivation="unknown purposes",
            ))]
