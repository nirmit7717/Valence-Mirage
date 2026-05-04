"""Narrator — AI-driven narrative generation with rule grounding."""

import logging
from pathlib import Path

from openai import AsyncOpenAI

from models.action import ActionIntent
from models.game_state import PlayerState
from engines.campaign_planner import CampaignPlanner, CampaignBlueprint
from rag import RuleRetriever
import config
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "narrator.txt"


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
                temperature=0.85,
                max_tokens=500,
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
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Combat narration failed: {e}")
            return f"{action_description}. {result}."
