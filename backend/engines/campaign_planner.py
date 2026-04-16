"""Campaign Planner — Generates narrative arc/blueprint at session start."""

import json
import logging
import re
from pathlib import Path

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

import config

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "campaign_plan.txt"


class StoryBeat(BaseModel):
    beat_id: int
    title: str
    description: str = ""
    type: str = "exploration"
    key_npcs: list[str] = []
    probability_modifier: float = 0.0


class CampaignAct(BaseModel):
    act_id: int
    title: str
    description: str = ""
    beats: list[StoryBeat]


class CampaignBlueprint(BaseModel):
    title: str
    premise: str
    setting: str
    tone: str = "dark fantasy"
    acts: list[CampaignAct] = []
    current_act: int = 1
    current_beat: int = 1
    key_themes: list[str] = []
    possible_endings: list[str] = []


class CampaignPlanner:

    def __init__(self):
        self.client = AsyncOpenAI(
            base_url=config.NVIDIA_BASE_URL,
            api_key=config.NVIDIA_API_KEY,
        )
        self.prompt = PROMPT_PATH.read_text()

    async def generate_blueprint(self, player_name: str = "Adventurer", keywords: str = "") -> CampaignBlueprint:
        if keywords.strip():
            user_msg = (
                f"Player character: {player_name}\n"
                f"Player wants this kind of adventure: {keywords.strip()}\n"
                f"Generate a matching campaign blueprint."
            )
        else:
            user_msg = (
                f"Player character: {player_name}\n"
                f"Generate a complete campaign blueprint for a single-session dark fantasy adventure."
            )

        try:
            response = await self.client.chat.completions.create(
                model=config.INTENT_MODEL,
                messages=[
                    {"role": "system", "content": self.prompt},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.7,
                max_tokens=1000,
            )

            raw = response.choices[0].message.content.strip()
            logger.info(f"Campaign blueprint raw: {raw[:200]}...")

            data = self._parse_json_robust(raw)
            if data:
                return CampaignBlueprint(**data)
            else:
                logger.warning("Could not parse campaign JSON, using fallback")
                return self._fallback_blueprint(player_name)

        except Exception as e:
            logger.warning(f"Campaign blueprint generation failed: {e}")
            return self._fallback_blueprint(player_name)

    def _parse_json_robust(self, raw: str) -> dict | None:
        """Try multiple strategies to parse potentially truncated JSON."""
        # Strategy 1: Direct parse
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # Strategy 2: Extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Strategy 3: Find the first { and last } and try
        start = raw.find('{')
        end = raw.rfind('}')
        if start != -1 and end > start:
            try:
                return json.loads(raw[start:end+1])
            except json.JSONDecodeError:
                pass

        # Strategy 4: Repair truncated JSON by closing open brackets
        substring = raw[start:end+1] if start != -1 else raw
        open_braces = substring.count('{') - substring.count('}')
        open_brackets = substring.count('[') - substring.count(']')
        repaired = substring + (']' * max(0, open_brackets)) + ('}' * max(0, open_braces))
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass

        # Strategy 5: Strip any trailing incomplete content after last complete value
        last_complete = max(substring.rfind('"],'), substring.rfind('"},'), substring.rfind('"],'))
        if last_complete > 0:
            truncated = substring[:last_complete+1]
            t_braces = truncated.count('{') - truncated.count('}')
            t_brackets = truncated.count('[') - truncated.count(']')
            truncated += (']' * max(0, t_brackets)) + ('}' * max(0, t_braces))
            try:
                return json.loads(truncated)
            except json.JSONDecodeError:
                pass

        logger.error(f"All JSON parse strategies failed for: {raw[:100]}...")
        return None

    def get_current_beat(self, blueprint: CampaignBlueprint) -> StoryBeat | None:
        for act in blueprint.acts:
            if act.act_id == blueprint.current_act:
                for beat in act.beats:
                    if beat.beat_id == blueprint.current_beat:
                        return beat
        return None

    def advance_beat(self, blueprint: CampaignBlueprint) -> CampaignBlueprint:
        current_act = None
        for act in blueprint.acts:
            if act.act_id == blueprint.current_act:
                current_act = act
                break

        if not current_act:
            return blueprint

        beat_ids = [b.beat_id for b in current_act.beats]
        if beat_ids and blueprint.current_beat < max(beat_ids):
            blueprint.current_beat += 1
        else:
            act_ids = [a.act_id for a in blueprint.acts]
            if act_ids and blueprint.current_act < max(act_ids):
                blueprint.current_act += 1
                blueprint.current_beat = 1

        return blueprint

    def get_narrative_relevance_bonus(self, blueprint: CampaignBlueprint, action_description: str) -> float:
        beat = self.get_current_beat(blueprint)
        if not beat:
            return 0.0

        beat_words = set(beat.title.lower().split() + beat.description.lower().split())
        action_words = set(action_description.lower().split())
        overlap = len(beat_words & action_words)

        if overlap >= 3:
            return 0.2
        elif overlap >= 1:
            return 0.1
        return 0.0

    @staticmethod
    def _fallback_blueprint(player_name: str) -> CampaignBlueprint:
        return CampaignBlueprint(
            title="The Dark Tower",
            premise="A mysterious tower has appeared in the northern mountains. "
                    "Strange disappearances and eerie lights plague the region.",
            setting="A frontier tavern on the edge of the kingdom, near the northern mountains",
            tone="dark fantasy",
            acts=[
                CampaignAct(
                    act_id=1, title="The Tavern",
                    description="Gather information and meet potential allies",
                    beats=[
                        StoryBeat(beat_id=1, title="The Barkeep's Warning", description="Learn about the dark tower from the barkeep", type="social", key_npcs=["barkeep"]),
                        StoryBeat(beat_id=2, title="The Hooded Stranger", description="A mysterious figure offers information", type="social", key_npcs=["hooded stranger"]),
                        StoryBeat(beat_id=3, title="The Decision", description="Choose how to proceed", type="choice"),
                    ],
                ),
                CampaignAct(
                    act_id=2, title="The Road North",
                    description="Journey toward the tower",
                    beats=[
                        StoryBeat(beat_id=1, title="Ambush on the Road", description="Bandits or creatures attack", type="combat"),
                        StoryBeat(beat_id=2, title="The Abandoned Village", description="Discover what happened nearby", type="exploration"),
                        StoryBeat(beat_id=3, title="The Tower's Shadow", description="First sight of the tower", type="choice"),
                    ],
                ),
                CampaignAct(
                    act_id=3, title="The Tower",
                    description="Enter the tower and face its master",
                    beats=[
                        StoryBeat(beat_id=1, title="The Tower's Defenses", description="Navigate magical defenses", type="combat"),
                        StoryBeat(beat_id=2, title="The Truth", description="Discover the tower's true nature", type="revelation"),
                        StoryBeat(beat_id=3, title="The Final Confrontation", description="Face the tower's master", type="climax"),
                    ],
                ),
            ],
            current_act=1, current_beat=1,
            key_themes=["mystery", "courage", "sacrifice"],
            possible_endings=[
                "Destroy the tower and save the region",
                "Become the tower's new master",
                "Seal the tower at great personal cost",
            ],
        )
