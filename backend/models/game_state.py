"""Game state models — player, session, and turn tracking."""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field

from .action import ActionIntent
from .outcome import Outcome


class Item(BaseModel):
    """An item in the player's inventory."""

    name: str
    description: str = ""
    stat_bonus: dict[str, int] = {}    # e.g., {"strength": 2}
    usable: bool = True
    consumes_on_use: bool = False


class PlayerStats(BaseModel):
    """Player character ability scores."""

    strength: int = 10       # Physical actions, combat
    intelligence: int = 10   # Spells, knowledge, perception
    dexterity: int = 10      # Agility, stealth, reflexes
    control: int = 10        # Stability of complex/scale actions
    charisma: int = 10       # Social, persuasion, deception
    wisdom: int = 10         # Insight, willpower, awareness


class PlayerState(BaseModel):
    """Full player state at any point in the game."""

    player_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Adventurer"
    level: int = 1
    hp: int = 50
    max_hp: int = 50
    mana: int = 50
    max_mana: int = 50
    stats: PlayerStats = Field(default_factory=PlayerStats)
    inventory: list[Item] = []
    status_effects: list[str] = []
    action_history: list[str] = []  # Last N action_type strings (for saturation)


class Turn(BaseModel):
    """A single turn in the game."""

    turn_number: int
    player_input: str
    intent: ActionIntent
    score: "ProbabilityScore | None" = None
    roll: int
    outcome: Outcome


class GameSession(BaseModel):
    """A complete game session."""

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    player: PlayerState = Field(default_factory=PlayerState)
    world_state: dict = Field(default_factory=lambda: {
        "location": "a dimly lit tavern on the edge of the kingdom",
        "time": "evening",
        "situation": "You sit alone at a corner table. The barkeep eyes you "
                     "warily. Rumors speak of a dark tower rising in the northern mountains.",
        "npcs_present": ["barkeep"],
        "quests": ["Investigate the dark tower"],
    })
    turn_history: list[Turn] = []
    turn_number: int = 0
    created_at: datetime = Field(default_factory=datetime.now)


# Fix forward reference
from .outcome import ProbabilityScore  # noqa: E402
Turn.model_rebuild()
