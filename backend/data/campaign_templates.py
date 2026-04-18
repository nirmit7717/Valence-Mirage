"""Campaign template definitions — structured beat requirements per campaign size."""

from pydantic import BaseModel


class BeatRequirement(BaseModel):
    beat_id: int
    beat_type: str  # "narrative_choice", "combat", "exploration", "social", "choice"
    enforcement: str  # "soft" or "hard"
    description: str = ""  # what this beat should accomplish


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
    description: str
    acts: list[ActTemplate]
    escalation_rule: str  # when to force a combat beat


# ─── Templates ───

SMALL_TEMPLATE = CampaignTemplate(
    name="Short Adventure",
    size="small",
    total_beats=6,
    estimated_turns="12-15",
    description="A focused adventure with tight pacing. Quick setup, rising tension, decisive climax.",
    escalation_rule="If no combat by beat 3, force combat at beat 4.",
    acts=[
        ActTemplate(
            act_id=1, title="Setup",
            description="Establish the world, introduce the threat",
            beats=[
                BeatRequirement(beat_id=1, beat_type="narrative_choice", enforcement="soft",
                                description="Opening hook — introduce threat/conflict"),
                BeatRequirement(beat_id=2, beat_type="combat", enforcement="hard",
                                description="First encounter — establish danger"),
                BeatRequirement(beat_id=3, beat_type="exploration", enforcement="soft",
                                description="Discover clues or lore about the threat"),
            ]
        ),
        ActTemplate(
            act_id=2, title="Climax",
            description="Final confrontation and resolution",
            beats=[
                BeatRequirement(beat_id=4, beat_type="social", enforcement="soft",
                                description="Meet a key NPC — gain alliance or information"),
                BeatRequirement(beat_id=5, beat_type="choice", enforcement="hard",
                                description="Critical decision — approach to the final challenge"),
                BeatRequirement(beat_id=6, beat_type="combat", enforcement="hard",
                                description="Boss encounter — final battle"),
            ]
        ),
    ]
)

MEDIUM_TEMPLATE = CampaignTemplate(
    name="Standard Quest",
    size="medium",
    total_beats=10,
    estimated_turns="20-25",
    description="A full adventure with character development, twists, and a satisfying arc.",
    escalation_rule="If no combat by beat 4, force combat at beat 5.",
    acts=[
        ActTemplate(
            act_id=1, title="Setup",
            description="Establish the world, meet allies, learn the threat",
            beats=[
                BeatRequirement(beat_id=1, beat_type="narrative_choice", enforcement="soft",
                                description="Opening hook — establish the world and hint at danger"),
                BeatRequirement(beat_id=2, beat_type="combat", enforcement="hard",
                                description="First blood — an early encounter that teaches mechanics"),
                BeatRequirement(beat_id=3, beat_type="social", enforcement="soft",
                                description="Key NPC alliance — build trust, gain information"),
            ]
        ),
        ActTemplate(
            act_id=2, title="Rising Action",
            description="Deepen the plot, raise stakes, test the player",
            beats=[
                BeatRequirement(beat_id=4, beat_type="exploration", enforcement="soft",
                                description="Investigation — discover hidden lore or a new location"),
                BeatRequirement(beat_id=5, beat_type="combat", enforcement="hard",
                                description="Ambush or crisis — stakes raised, resources tested"),
                BeatRequirement(beat_id=6, beat_type="choice", enforcement="hard",
                                description="Moral choice — decision with lasting consequences"),
                BeatRequirement(beat_id=7, beat_type="narrative_choice", enforcement="soft",
                                description="Revelation — major plot twist changes the objective"),
            ]
        ),
        ActTemplate(
            act_id=3, title="Climax",
            description="Final confrontation and resolution",
            beats=[
                BeatRequirement(beat_id=8, beat_type="exploration", enforcement="soft",
                                description="Final preparation — rest, loot, NPC farewells"),
                BeatRequirement(beat_id=9, beat_type="social", enforcement="soft",
                                description="Last alliance — a final conversation before the end"),
                BeatRequirement(beat_id=10, beat_type="combat", enforcement="hard",
                                description="Boss encounter — the ultimate challenge"),
            ]
        ),
    ]
)

LARGE_TEMPLATE = CampaignTemplate(
    name="Grand Saga",
    size="large",
    total_beats=16,
    estimated_turns="30-35",
    description="An epic narrative arc with deep lore, multiple twists, and complex character development.",
    escalation_rule="If no combat by beat 5, force combat at beat 6.",
    acts=[
        ActTemplate(
            act_id=1, title="The Call",
            description="The world is introduced, the player is drawn into the conflict",
            beats=[
                BeatRequirement(beat_id=1, beat_type="narrative_choice", enforcement="soft",
                                description="Opening scene — atmospheric world introduction"),
                BeatRequirement(beat_id=2, beat_type="exploration", enforcement="soft",
                                description="First steps — explore the starting area"),
                BeatRequirement(beat_id=3, beat_type="combat", enforcement="hard",
                                description="First encounter — the threat reveals itself"),
                BeatRequirement(beat_id=4, beat_type="social", enforcement="soft",
                                description="Meet a mentor or guide — gain purpose"),
            ]
        ),
        ActTemplate(
            act_id=2, title="The Journey",
            description="Travel, grow stronger, face challenges, uncover the truth",
            beats=[
                BeatRequirement(beat_id=5, beat_type="exploration", enforcement="soft",
                                description="New territory — discover a significant location"),
                BeatRequirement(beat_id=6, beat_type="combat", enforcement="hard",
                                description="Trial by fire — a challenging encounter"),
                BeatRequirement(beat_id=7, beat_type="choice", enforcement="hard",
                                description="The crossroads — a meaningful decision"),
                BeatRequirement(beat_id=8, beat_type="social", enforcement="soft",
                                description="An unlikely ally — new NPC relationship"),
            ]
        ),
        ActTemplate(
            act_id=3, title="The Reckoning",
            description="The stakes become personal, betrayal and revelation",
            beats=[
                BeatRequirement(beat_id=9, beat_type="narrative_choice", enforcement="soft",
                                description="The twist — a revelation changes everything"),
                BeatRequirement(beat_id=10, beat_type="combat", enforcement="hard",
                                description="Betrayal or ambush — fight a former ally or new threat"),
                BeatRequirement(beat_id=11, beat_type="choice", enforcement="hard",
                                description="Moral crucible — a decision that defines the character"),
                BeatRequirement(beat_id=12, beat_type="exploration", enforcement="soft",
                                description="The final path — discover the enemy's weakness"),
            ]
        ),
        ActTemplate(
            act_id=4, title="The End",
            description="The final confrontation, resolution, and aftermath",
            beats=[
                BeatRequirement(beat_id=13, beat_type="social", enforcement="soft",
                                description="Before the storm — last conversations"),
                BeatRequirement(beat_id=14, beat_type="exploration", enforcement="soft",
                                description="Final preparation — arm yourself"),
                BeatRequirement(beat_id=15, beat_type="combat", enforcement="hard",
                                description="Lieutenant encounter — the penultimate fight"),
                BeatRequirement(beat_id=16, beat_type="combat", enforcement="hard",
                                description="Final boss — the ultimate confrontation"),
            ]
        ),
    ]
)

CAMPAIGN_TEMPLATES = {
    "small": SMALL_TEMPLATE,
    "medium": MEDIUM_TEMPLATE,
    "large": LARGE_TEMPLATE,
}
