"""Action Intent model — structured output from intent parsing."""

from pydantic import BaseModel, Field
from typing import Optional


class ActionIntent(BaseModel):
    """Parsed representation of a player's free-form action."""

    action_type: str = Field(
        ...,
        description="Category: attack, cast_spell, persuade, deceive, explore, "
                    "investigate, steal, defend, heal, dominate, flee, interact, "
                    "dialogue, choice, observe, other",
    )
    description: str = Field(
        ...,
        description="Clean paraphrase of what the player intends to do",
    )
    scale: str = Field(
        default="moderate",
        description="Effect magnitude: minor, moderate, major, extreme, cosmic",
    )
    risk: str = Field(
        default="low",
        description="Consequence severity if it fails: low, medium, high, extreme",
    )
    target: Optional[str] = Field(
        None,
        description="Who or what is the target of this action",
    )
    relevant_stat: str = Field(
        default="wisdom",
        description="Primary player stat: strength, intelligence, dexterity, "
                    "control, charisma, wisdom",
    )
    uses_resource: bool = Field(
        False,
        description="Whether this action consumes mana or items",
    )
    resource_cost: int = Field(
        0,
        description="Mana cost if the action is magical, 0 otherwise",
    )
    requires_roll: bool = Field(
        True,
        description="Whether this action needs a dice roll. False for trivial "
                    "actions, narrative choices, information gathering, or routine "
                    "interactions where there's no meaningful risk.",
    )
    suggested_choices: list[str] = Field(
        default_factory=list,
        description="If this is a choice moment, list the options. Empty if free-form.",
    )
