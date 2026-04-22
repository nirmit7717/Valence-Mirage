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
    item_type: str = "misc"           # weapon, armor, consumable, quest, misc
    stat_bonus: dict[str, int] = {}   # e.g., {"strength": 2}
    mana_restore: int = 0             # Consumables that restore mana
    hp_restore: int = 0               # Consumables that restore HP
    usable: bool = True
    consumes_on_use: bool = False


class PlayerStats(BaseModel):
    """Player character ability scores."""
    strength: int = 10
    intelligence: int = 10
    dexterity: int = 10
    control: int = 10
    charisma: int = 10
    wisdom: int = 10


class PlayerState(BaseModel):
    """Full player state at any point in the game."""
    player_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Adventurer"
    character_class: str = "warrior"  # warrior, rogue, wizard, cleric, bard
    level: int = 1
    xp: int = 0
    xp_to_next: int = 100            # XP needed for next level
    hp: int = 50
    max_hp: int = 50
    mana: int = 50
    max_mana: int = 50
    stats: PlayerStats = Field(default_factory=PlayerStats)
    inventory: list[Item] = []
    status_effects: list[str] = []
    action_history: list[str] = []

    def gain_xp(self, amount: int) -> bool:
        """Add XP and level up if threshold met. Returns True if leveled up."""
        self.xp += amount
        leveled = False
        while self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.level += 1
            self.xp_to_next = int(self.xp_to_next * 1.5)
            # Stat increase on level up
            self.max_hp += 10
            self.max_mana += 10
            self.hp = self.max_hp
            self.mana = self.max_mana
            
            # Universal +1 to all stats
            primary_stat = {
                "warrior": "strength", "rogue": "dexterity",
                "wizard": "intelligence", "cleric": "wisdom",
                "bard": "charisma"
            }.get(self.character_class.lower(), "strength")
            
            for s in ["strength", "intelligence", "dexterity", "control", "charisma", "wisdom"]:
                bonus = 2 if s == primary_stat else 1
                setattr(self.stats, s, getattr(self.stats, s) + bonus)
                
            leveled = True
        return leveled


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


from .outcome import ProbabilityScore  # noqa: E402
Turn.model_rebuild()
