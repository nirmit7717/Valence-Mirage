"""Campaign template definitions — structured beats with per-beat turn budgets.

Every size follows the same shape: the story builds through a few fights, and
the last fight is the climax against the campaign's central threat.

Each beat has a turn budget (``min_turns``..``max_turns``). A combat beat always
takes 2 turns: a lead-in turn where the enemy appears, then the fight itself.
The template's ``min_turns``/``max_turns`` are the sums of its beats, which is
what bounds the campaign's length (see engines/pacing.py).
"""

from pydantic import BaseModel, model_validator


class BeatRequirement(BaseModel):
    beat_id: int
    beat_type: str  # "narrative_choice", "combat", "exploration", "social", "choice"
    enforcement: str  # "soft" or "hard"
    description: str = ""  # what this beat should accomplish
    min_turns: int = 1
    max_turns: int = 2
    threat_hint: str | None = None  # "elite" or "boss" for escalating fights

    @model_validator(mode="after")
    def _valid_budget(self):
        if self.beat_type == "combat" and (self.min_turns, self.max_turns) != (2, 2):
            raise ValueError("combat beats take exactly 2 turns (lead-in + fight)")
        if not 1 <= self.min_turns <= self.max_turns:
            raise ValueError(f"beat {self.beat_id}: invalid turn budget {self.min_turns}-{self.max_turns}")
        return self


class ActTemplate(BaseModel):
    act_id: int
    title: str
    description: str = ""
    beats: list[BeatRequirement]


class CampaignTemplate(BaseModel):
    name: str
    size: str  # "small", "medium", "large"
    total_beats: int
    estimated_turns: str
    min_turns: int
    max_turns: int
    description: str
    acts: list[ActTemplate]

    @model_validator(mode="after")
    def _totals_match_beats(self):
        beats = [beat for act in self.acts for beat in act.beats]
        if len(beats) != self.total_beats:
            raise ValueError(f"{self.size}: total_beats {self.total_beats} != {len(beats)} beats")
        if sum(b.min_turns for b in beats) != self.min_turns:
            raise ValueError(f"{self.size}: min_turns doesn't match the sum of beat minimums")
        if sum(b.max_turns for b in beats) != self.max_turns:
            raise ValueError(f"{self.size}: max_turns doesn't match the sum of beat maximums")
        if not beats or beats[-1].beat_type != "combat" or beats[-1].threat_hint != "boss":
            raise ValueError(f"{self.size}: the final beat must be the boss fight")
        return self

    @property
    def beats(self) -> list[BeatRequirement]:
        return [beat for act in self.acts for beat in act.beats]

    @property
    def fight_count(self) -> int:
        return sum(1 for beat in self.beats if beat.beat_type == "combat")


def _story(beat_id, beat_type, description, min_turns=1, max_turns=2):
    return BeatRequirement(beat_id=beat_id, beat_type=beat_type, enforcement="soft",
                           description=description, min_turns=min_turns, max_turns=max_turns)


def _fight(beat_id, description, threat_hint=None):
    return BeatRequirement(beat_id=beat_id, beat_type="combat", enforcement="hard",
                           description=description, min_turns=2, max_turns=2, threat_hint=threat_hint)


FINAL_FIGHT = "Final confrontation — face the campaign's central threat and decide the story's fate"


# ─── Templates ───

SMALL_TEMPLATE = CampaignTemplate(
    name="Short Adventure",
    size="small",
    total_beats=5,
    estimated_turns="8-10",
    min_turns=8,
    max_turns=10,
    description="A focused adventure with tight pacing: a quick hook, two escalating fights, and a decisive climax.",
    acts=[
        ActTemplate(
            act_id=1, title="Setup",
            description="Establish the world and the threat",
            beats=[
                _story(1, "narrative_choice", "Opening hook — introduce the threat and the player's stake in it"),
                _fight(2, "First encounter — the threat's servants show how dangerous it is"),
                _story(3, "exploration", "Discovery — uncover where the threat hides or how to reach it"),
            ],
        ),
        ActTemplate(
            act_id=2, title="Climax",
            description="Escalation and the final confrontation",
            beats=[
                _fight(4, "Escalation — the threat's strongest lieutenant blocks the way", threat_hint="elite"),
                _fight(5, FINAL_FIGHT, threat_hint="boss"),
            ],
        ),
    ],
)

MEDIUM_TEMPLATE = CampaignTemplate(
    name="Standard Quest",
    size="medium",
    total_beats=8,
    estimated_turns="13-15",
    min_turns=13,
    max_turns=15,
    description="A full adventure with allies, a twist, rising stakes and a satisfying final battle.",
    acts=[
        ActTemplate(
            act_id=1, title="Setup",
            description="Establish the world, meet an ally, learn the threat",
            beats=[
                _story(1, "narrative_choice", "Opening hook — establish the world and hint at the danger"),
                _fight(2, "First blood — an early encounter that shows what the threat can do"),
                _story(3, "social", "Alliance — gain an ally's trust and learn about the threat"),
            ],
        ),
        ActTemplate(
            act_id=2, title="Rising Action",
            description="Raise the stakes and test the player",
            beats=[
                _fight(4, "Ambush — the enemy strikes back as the player gets closer"),
                _story(5, "choice", "Revelation and decision — a twist forces a hard choice", min_turns=1, max_turns=1),
                _fight(6, "Crisis — the consequences of the choice erupt into battle"),
            ],
        ),
        ActTemplate(
            act_id=3, title="Climax",
            description="The final battles and the resolution",
            beats=[
                _fight(7, "Lieutenant — the threat's right hand makes a last stand", threat_hint="elite"),
                _fight(8, FINAL_FIGHT, threat_hint="boss"),
            ],
        ),
    ],
)

LARGE_TEMPLATE = CampaignTemplate(
    name="Grand Saga",
    size="large",
    total_beats=13,
    estimated_turns="20-25",
    min_turns=20,
    max_turns=25,
    description="An epic arc with a mentor, a betrayal, many battles and a climactic showdown.",
    acts=[
        ActTemplate(
            act_id=1, title="The Call",
            description="The world is introduced and the player is drawn into the conflict",
            beats=[
                _story(1, "narrative_choice", "Opening hook — an atmospheric introduction and a call to act"),
                _story(2, "exploration", "First steps — explore the starting area and find the first trail"),
                _fight(3, "First encounter — the threat reveals itself"),
            ],
        ),
        ActTemplate(
            act_id=2, title="The Journey",
            description="Travel, grow stronger, face trials, uncover the truth",
            beats=[
                _story(4, "social", "Mentor — meet a guide who gives the journey purpose"),
                _fight(5, "Trial by fire — a hard battle on the road"),
                _story(6, "choice", "Crossroads — a meaningful decision about the path ahead"),
                _fight(7, "Ambush — the enemy strikes where the player is weakest"),
            ],
        ),
        ActTemplate(
            act_id=3, title="The Reckoning",
            description="Betrayal, revelation, and the path to the enemy",
            beats=[
                _story(8, "narrative_choice", "The twist — a revelation changes everything"),
                _fight(9, "Betrayal — fight a former ally or a hidden enemy"),
                _story(10, "exploration", "The enemy's weakness — discover how the threat can be beaten",
                       min_turns=1, max_turns=1),
                _fight(11, "Guardian — break through the defenses around the threat"),
            ],
        ),
        ActTemplate(
            act_id=4, title="The End",
            description="The final confrontation and its aftermath",
            beats=[
                _fight(12, "Lieutenant — the threat's champion makes a final stand", threat_hint="elite"),
                _fight(13, FINAL_FIGHT, threat_hint="boss"),
            ],
        ),
    ],
)

CAMPAIGN_TEMPLATES = {
    "small": SMALL_TEMPLATE,
    "medium": MEDIUM_TEMPLATE,
    "large": LARGE_TEMPLATE,
}
