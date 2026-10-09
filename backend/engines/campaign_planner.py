"""Campaign Planner — Generates narrative arc/blueprint at session start."""

import json
import logging
import re
from pathlib import Path

from openai import AsyncOpenAI
from pydantic import BaseModel, Field, model_validator

import config
from engines.llm_utils import extract_message_text

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "campaign_plan.txt"

# Words too common to count as "the action relates to this beat".
_STOP_WORDS = {
    "the", "and", "for", "are", "but", "not", "you", "your", "all", "can", "her", "his", "was",
    "one", "our", "out", "had", "has", "how", "its", "may", "new", "now", "old", "see", "way",
    "who", "did", "get", "let", "say", "she", "too", "use", "from", "with", "this", "that",
    "into", "over", "they", "them", "then", "than", "what", "when", "where", "which", "while",
    "there", "their", "here", "have", "will", "would", "could", "should", "about", "after",
    "before", "around", "through", "toward", "towards", "just", "some", "more", "most", "very",
    "also", "only", "each", "other", "such", "like", "make", "take", "look", "find",
}


class StoryBeat(BaseModel):
    beat_id: int
    title: str
    description: str = ""
    type: str = "exploration"
    key_npcs: list[str] = []
    probability_modifier: float = 0.0
    # Turn budget for this beat (0 = default by type; sessions saved before budgets existed).
    min_turns: int = 0
    max_turns: int = 0
    threat_hint: str | None = None  # "elite" | "boss" for escalating fights

    @model_validator(mode="after")
    def _default_budget(self):
        if self.type == "combat":
            self.min_turns, self.max_turns = 2, 2
        else:
            self.min_turns = self.min_turns or 1
            self.max_turns = max(self.max_turns or 2, self.min_turns)
        return self


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
            timeout=30.0,
            max_retries=2,
        )
        self.prompt = PROMPT_PATH.read_text()

    async def generate_blueprint(self, player_name: str = "Adventurer", keywords: str = "", template=None, beat_weights: dict = None) -> CampaignBlueprint:
        if keywords.strip():
            user_msg = (
                f"Player character: {player_name}\n"
                f"Player wants this kind of adventure: {keywords.strip()}\n"
            )
        else:
            user_msg = (
                f"Player character: {player_name}\n"
            )

        # Add template structure to prompt
        if template:
            template_desc = f"\nCAMPAIGN STRUCTURE (you must follow this exactly):\n"
            template_desc += (
                f"Total beats: {template.total_beats} ({template.fight_count} of them fights), "
                f"campaign length: {template.estimated_turns} turns\n"
            )
            for act in template.acts:
                template_desc += f"\nAct {act.act_id}: {act.title} — {act.description}\n"
                for beat in act.beats:
                    escalation = f", threat={beat.threat_hint}" if beat.threat_hint else ""
                    template_desc += (
                        f"  Beat {beat.beat_id}: type={beat.beat_type}{escalation} — {beat.description}\n"
                    )
            user_msg += template_desc
            # Adaptive beat weighting from player profile
            if beat_weights:
                weight_desc = "\nPLAYER PREFERENCES (weight beat content accordingly):\n"
                for btype, weight in beat_weights.items():
                    weight_desc += f"  {btype}: {weight:.2f}\n"
                user_msg += weight_desc
            user_msg += "\nGenerate a campaign that fills this structure with creative content. Keep the beat types as specified.\n"
        else:
            user_msg += "Generate a complete campaign blueprint for a single-session dark fantasy adventure.\n"

        request_kwargs = {
            "model": config.INTENT_MODEL,
            "messages": [
                {"role": "system", "content": self.prompt},
                {"role": "user", "content": user_msg},
            ],
            "temperature": 0.7,
            "max_tokens": 1000,
        }

        try:
            try:
                response = await self.client.chat.completions.create(
                    **request_kwargs,
                    response_format={"type": "json_object"},
                )
            except Exception as e:
                logger.warning(f"JSON-mode blueprint request failed, retrying without JSON mode: {e}")
                response = await self.client.chat.completions.create(**request_kwargs)

            raw = extract_message_text(response)
            logger.info(f"Campaign blueprint raw: {raw[:200]}...")

            blueprint = None
            if not raw:
                logger.warning("Campaign blueprint response contained no text content; using fallback blueprint")
            else:
                data = self._parse_json_robust(raw)
                if data:
                    try:
                        blueprint = CampaignBlueprint(**data)
                    except Exception as e:
                        logger.warning(f"Campaign JSON didn't match the blueprint model: {e}")
                else:
                    logger.warning("Could not parse campaign JSON, using fallback")
        except Exception as e:
            logger.warning(f"Campaign blueprint generation failed: {e}")
            blueprint = None

        if blueprint is None:
            return self._fallback_blueprint(player_name, template)
        # The model's creative content is kept, but the structure always comes from the template.
        return conform_to_template(blueprint, template) if template else blueprint

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
            # Beat IDs are generated from the campaign template and may not be
            # contiguous within an act. Advance to the next actual beat ID.
            next_beat = next((beat_id for beat_id in sorted(beat_ids)
                              if beat_id > blueprint.current_beat), None)
            if next_beat is not None:
                blueprint.current_beat = next_beat
            else:
                blueprint.current_beat = max(beat_ids)
        else:
            act_ids = [a.act_id for a in blueprint.acts]
            if act_ids and blueprint.current_act < max(act_ids):
                blueprint.current_act += 1
                next_act = next((act for act in blueprint.acts if act.act_id == blueprint.current_act), None)
                blueprint.current_beat = min((beat.beat_id for beat in next_act.beats), default=1)

        return blueprint

    def get_narrative_relevance_bonus(self, blueprint: CampaignBlueprint, action_description: str) -> float:
        """Small bonus when the action shares meaningful words with the current beat.

        Only words of 4+ letters that aren't stop words count, so "the" or "a"
        no longer make every action look on-topic.
        """
        beat = self.get_current_beat(blueprint)
        if not beat:
            return 0.0

        overlap = len(_meaningful_words(f"{beat.title} {beat.description}") & _meaningful_words(action_description))
        if overlap >= 3:
            return 0.2
        elif overlap >= 1:
            return 0.1
        return 0.0

    @staticmethod
    def _fallback_blueprint(player_name: str, template=None) -> CampaignBlueprint:
        """Built-in campaign used when the model fails. Shaped like ``template`` when given."""
        if template is not None:
            return _themed_fallback(template)
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


# ─── Template conformance ───

_FINAL_FIGHT_NOTE = "This is the final confrontation with the campaign's central threat."


def _meaningful_words(text: str) -> set[str]:
    words = re.findall(r"[a-z']+", (text or "").lower())
    return {w for w in words if len(w) >= 4 and w not in _STOP_WORDS}


def _title_from_description(description: str) -> str:
    """'Opening hook — introduce the threat' -> 'Opening Hook'."""
    head = re.split(r"\s+[—–-]\s+", description or "", maxsplit=1)[0].strip() or "Chapter"
    return " ".join(word[:1].upper() + word[1:] for word in head.split())


def conform_to_template(blueprint: CampaignBlueprint, template) -> CampaignBlueprint:
    """Return a blueprint with exactly the template's acts, beats, types and turn budgets.

    The model's creative content (titles, descriptions, NPCs) is kept where a beat
    of the same type exists: positionally first, otherwise the next unused beat of
    that type. Beats with no match get the template's own description.
    """
    source_acts = sorted(blueprint.acts, key=lambda a: a.act_id)
    source = [beat for act in source_acts for beat in act.beats]
    used: set[int] = set()

    acts: list[CampaignAct] = []
    position = 0
    for act_index, template_act in enumerate(template.acts):
        source_act = source_acts[act_index] if act_index < len(source_acts) else None
        beats: list[StoryBeat] = []
        for template_beat in template_act.beats:
            match = None
            if position < len(source) and position not in used and source[position].type == template_beat.beat_type:
                match = position
            else:
                match = next((i for i, b in enumerate(source) if i not in used and b.type == template_beat.beat_type), None)
            position += 1

            original = source[match] if match is not None else None
            if match is not None:
                used.add(match)
            description = (original.description if original and original.description else template_beat.description)
            if template_beat.threat_hint == "boss" and "final" not in description.lower():
                description = f"{description.rstrip('. ')}. {_FINAL_FIGHT_NOTE}"
            beats.append(StoryBeat(
                beat_id=template_beat.beat_id,
                title=(original.title if original and original.title else _title_from_description(template_beat.description)),
                description=description,
                type=template_beat.beat_type,
                key_npcs=original.key_npcs if original else [],
                probability_modifier=original.probability_modifier if original else 0.0,
                min_turns=template_beat.min_turns,
                max_turns=template_beat.max_turns,
                threat_hint=template_beat.threat_hint,
            ))
        acts.append(CampaignAct(
            act_id=template_act.act_id,
            title=(source_act.title if source_act and source_act.title else template_act.title),
            description=(source_act.description if source_act and source_act.description else template_act.description),
            beats=beats,
        ))

    if len(source) != len(template.beats) or len(used) != len(source):
        logger.info(f"Blueprint conformed to the {template.size} template "
                    f"({len(source)} model beats -> {len(template.beats)}, {len(used)} reused)")

    return CampaignBlueprint(
        title=blueprint.title,
        premise=blueprint.premise,
        setting=blueprint.setting,
        tone=blueprint.tone,
        acts=acts,
        current_act=acts[0].act_id,
        current_beat=acts[0].beats[0].beat_id,
        key_themes=blueprint.key_themes,
        possible_endings=blueprint.possible_endings,
    )


# Content for the built-in campaign, picked by beat type so any template can use it.
_FALLBACK_BEATS = {
    "narrative_choice": [
        ("The Barkeep's Warning", "Learn about the dark tower and the disappearances from the barkeep"),
        ("The Truth Revealed", "Discover the tower's master is someone the region once trusted"),
    ],
    "exploration": [
        ("The Abandoned Village", "Search the emptied village for signs of what took its people"),
        ("Secrets of the Tower", "Find the hidden path and the tower's weakness"),
    ],
    "social": [
        ("The Hooded Stranger", "A mysterious figure offers help — at a price"),
        ("The Old Hermit", "A hermit who once served the tower shares what he knows"),
    ],
    "choice": [
        ("The Decision", "Choose how to approach the tower and who to trust"),
        ("The Crossroads", "Save the captured villagers or press on toward the tower"),
    ],
    "combat": [
        ("Ambush on the Road", "The tower's raiders strike on the road north"),
        ("The Tower's Hounds", "Creatures from the tower hunt the player through the hills"),
        ("Night Raid", "The raiders attack the camp under cover of darkness"),
        ("The Traitor's Blade", "A trusted ally reveals their loyalty to the tower"),
        ("The Gatekeeper", "The tower's guardian bars the entrance"),
    ],
}
_FALLBACK_ELITE = ("The Tower's Champion", "The master's sworn champion makes a last stand on the stairs")
_FALLBACK_BOSS = ("The Master of the Tower", "Face the tower's master and end the darkness over the region")


def _themed_fallback(template) -> CampaignBlueprint:
    """The built-in Dark Tower campaign, shaped exactly like ``template``."""
    counters: dict[str, int] = {}
    beats_by_act: list[CampaignAct] = []
    for template_act in template.acts:
        beats = []
        for template_beat in template_act.beats:
            if template_beat.threat_hint == "boss":
                title, description = _FALLBACK_BOSS
            elif template_beat.threat_hint == "elite":
                title, description = _FALLBACK_ELITE
            else:
                pool = _FALLBACK_BEATS.get(template_beat.beat_type) or [(_title_from_description(template_beat.description), template_beat.description)]
                index = counters.get(template_beat.beat_type, 0)
                counters[template_beat.beat_type] = index + 1
                title, description = pool[index % len(pool)]
            beats.append(StoryBeat(beat_id=template_beat.beat_id, title=title, description=description,
                                   type=template_beat.beat_type))
        beats_by_act.append(CampaignAct(act_id=template_act.act_id, title=template_act.title,
                                        description=template_act.description, beats=beats))
    legacy = CampaignPlanner._fallback_blueprint("Adventurer")
    themed = legacy.model_copy(update={"acts": beats_by_act})
    return conform_to_template(themed, template)
