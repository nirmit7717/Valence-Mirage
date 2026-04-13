"""Campaign Planner — Generates narrative arc/blueprint at session start."""

import json
import logging
from pathlib import Path

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

import config

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "campaign_plan.txt"


class StoryBeat(BaseModel):
    """A single plot point in the campaign."""
    beat_id: int
    title: str
    description: str = ""
    type: str = "exploration"  # exploration, combat, social, choice, revelation, climax
    key_npcs: list[str] = []
    probability_modifier: float = 0.0  # Bonus/penalty for actions aligned with this beat


class CampaignAct(BaseModel):
    """An act containing multiple story beats."""
    act_id: int
    title: str
    description: str = ""
    beats: list[StoryBeat]


class CampaignBlueprint(BaseModel):
    """The full planned narrative arc for a campaign session."""
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
    """Generates and manages campaign narrative arcs."""

    def __init__(self):
        self.client = AsyncOpenAI(
            base_url=config.NVIDIA_BASE_URL,
            api_key=config.NVIDIA_API_KEY,
        )
        self.prompt = PROMPT_PATH.read_text()

    async def generate_blueprint(self, player_name: str = "Adventurer") -> CampaignBlueprint:
        """Generate a campaign blueprint with narrative arc."""
        user_msg = (
            f"Player character: {player_name}\n"
            f"Generate a complete campaign blueprint for a single-session dark fantasy adventure."
        )

        try:
            response = await self.client.chat.completions.create(
                model=config.INTENT_MODEL,  # Use fast model for planning
                messages=[
                    {"role": "system", "content": self.prompt},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.7,
                max_tokens=800,
            )

            raw = response.choices[0].message.content.strip()
            logger.info(f"Campaign blueprint raw: {raw[:200]}...")

            data = json.loads(raw)
            return CampaignBlueprint(**data)

        except Exception as e:
            logger.warning(f"Campaign blueprint generation failed, using fallback: {e}")
            return self._fallback_blueprint(player_name)

    def get_current_beat(self, blueprint: CampaignBlueprint) -> StoryBeat | None:
        """Get the current story beat the player should be in."""
        for act in blueprint.acts:
            if act.act_id == blueprint.current_act:
                for beat in act.beats:
                    if beat.beat_id == blueprint.current_beat:
                        return beat
        return None

    def advance_beat(self, blueprint: CampaignBlueprint) -> CampaignBlueprint:
        """Move to the next story beat."""
        current_act = None
        for act in blueprint.acts:
            if act.act_id == blueprint.current_act:
                current_act = act
                break

        if not current_act:
            return blueprint

        beat_ids = [b.beat_id for b in current_act.beats]
        if blueprint.current_beat < max(beat_ids):
            blueprint.current_beat += 1
        else:
            # Advance to next act
            act_ids = [a.act_id for a in blueprint.acts]
            if blueprint.current_act < max(act_ids):
                blueprint.current_act += 1
                blueprint.current_beat = 1

        return blueprint

    def get_narrative_relevance_bonus(self, blueprint: CampaignBlueprint, action_description: str) -> float:
        """Calculate how relevant an action is to the current story beat.
        
        Returns a bonus/penalty to probability.
        Actions aligned with the current beat get +0.1 to +0.2
        Actions tangential get 0.0
        Actions that derail the story get -0.1 to -0.2
        """
        beat = self.get_current_beat(blueprint)
        if not beat:
            return 0.0

        # Simple keyword overlap check
        # Phase 3: Replace with embedding-based similarity
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
        """Pre-defined blueprint if AI generation fails."""
        return CampaignBlueprint(
            title="The Dark Tower",
            premise="A mysterious tower has appeared in the northern mountains. "
                    "Strange disappearances and eerie lights plague the region.",
            setting="A frontier tavern on the edge of the kingdom, near the northern mountains",
            tone="dark fantasy",
            acts=[
                CampaignAct(
                    act_id=1,
                    title="The Tavern",
                    description="Gather information and meet potential allies",
                    beats=[
                        StoryBeat(beat_id=1, title="The Barkeep's Warning",
                                 description="Learn about the dark tower from the barkeep",
                                 type="social", key_npcs=["barkeep"]),
                        StoryBeat(beat_id=2, title="The Hooded Stranger",
                                 description="A mysterious figure offers information",
                                 type="social", key_npcs=["hooded stranger"]),
                        StoryBeat(beat_id=3, title="The Decision",
                                 description="Choose how to proceed: alone or with allies",
                                 type="choice"),
                    ],
                ),
                CampaignAct(
                    act_id=2,
                    title="The Road North",
                    description="Journey toward the tower, facing dangers along the way",
                    beats=[
                        StoryBeat(beat_id=1, title="Ambush on the Road",
                                 description="Bandits or creatures attack on the road",
                                 type="combat"),
                        StoryBeat(beat_id=2, title="The Abandoned Village",
                                 description="Discover what happened to the nearby village",
                                 type="exploration"),
                        StoryBeat(beat_id=3, title="The Tower's Shadow",
                                 description="First sight of the tower, choose approach",
                                 type="choice"),
                    ],
                ),
                CampaignAct(
                    act_id=3,
                    title="The Tower",
                    description="Enter the tower and face its master",
                    beats=[
                        StoryBeat(beat_id=1, title="The Tower's Defenses",
                                 description="Navigate the tower's magical defenses",
                                 type="combat"),
                        StoryBeat(beat_id=2, title="The Truth",
                                 description="Discover the true nature of the tower",
                                 type="revelation"),
                        StoryBeat(beat_id=3, title="The Final Confrontation",
                                 description="Face the tower's master",
                                 type="climax"),
                    ],
                ),
            ],
            current_act=1,
            current_beat=1,
            key_themes=["mystery", "courage", "sacrifice"],
            possible_endings=[
                "Destroy the tower and save the region",
                "Become the tower's new master",
                "Seal the tower at great personal cost",
            ],
        )
