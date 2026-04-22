"""State Manager — Manages game sessions in memory (Phase 1)."""

import logging
from datetime import datetime
from copy import deepcopy

from models.game_state import GameSession, PlayerState, Turn, Item
from models.outcome import StateChanges
from models.action import ActionIntent
import config

logger = logging.getLogger(__name__)

# XP rewards by outcome
XP_REWARDS = {
    "critical_success": 30,
    "success": 20,
    "partial_success": 15,
    "failure": 10,
    "critical_failure": 5,
    "narrative_choice": 5,
}

# Starting baseline
def get_starter_items(char_class: str) -> list[Item]:
    items = [
        Item(name="Health Potion", description="Restores 15 HP when consumed.", item_type="consumable",
             hp_restore=15, usable=True, consumes_on_use=True),
        Item(name="Mana Potion", description="Restores 15 mana when consumed.", item_type="consumable",
             mana_restore=15, usable=True, consumes_on_use=True),
    ]
    
    c = char_class.lower()
    if c == "warrior":
        items.append(Item(name="Iron Longsword", description="A sturdy battle blade.", item_type="weapon", stat_bonus={"strength": 2}, usable=False))
    elif c == "rogue":
        items.append(Item(name="Twin Daggers", description="Sharp and perfectly balanced.", item_type="weapon", stat_bonus={"dexterity": 2}, usable=False))
    elif c == "wizard":
        items.append(Item(name="Oak Staff", description="Humming with latent arcane energy.", item_type="weapon", stat_bonus={"intelligence": 2}, usable=False))
    elif c == "cleric":
        items.append(Item(name="Holy Mace", description="Blessed by the light.", item_type="weapon", stat_bonus={"wisdom": 2}, usable=False))
    elif c == "bard":
        items.append(Item(name="Lute of Embers", description="A beautiful wooden instrument.", item_type="weapon", stat_bonus={"charisma": 2}, usable=False))
    else:
        items.append(Item(name="Traveler's Sickle", description="A simple tool for a long road.", item_type="weapon", stat_bonus={"strength": 1}, usable=False))
        
    return items


class StateManager:
    """Creates, stores, and updates game sessions."""

    def __init__(self):
        self._sessions: dict[str, GameSession] = {}

    def create_session(self, player_name: str = "Adventurer") -> GameSession:
        player = PlayerState(
            name=player_name,
            hp=config.DEFAULT_HP,
            max_hp=config.DEFAULT_HP,
            mana=config.DEFAULT_MANA,
            max_mana=config.DEFAULT_MANA,
            character_class=player_name.lower() if player_name.lower() in ["warrior", "rogue", "wizard", "cleric", "bard"] else "warrior",
            inventory=get_starter_items(player_name.lower() if player_name.lower() in ["warrior", "rogue", "wizard", "cleric", "bard"] else "warrior"),
        )
        session = GameSession(player=player)
        self._sessions[session.session_id] = session
        logger.info(f"Session created: {session.session_id} for '{player_name}'")
        return session

    def get_session(self, session_id: str) -> GameSession | None:
        return self._sessions.get(session_id)

    def apply_changes(
        self,
        session: GameSession,
        intent: ActionIntent,
        state_changes: StateChanges,
        outcome: str = "success",
    ) -> dict:
        """Apply state changes after an action is resolved.

        Returns dict with level_up info if applicable.
        """
        player = session.player
        level_up_info = {}

        # --- HP changes ---
        player.hp = max(0, min(player.max_hp, player.hp + state_changes.hp_delta))

        # --- Mana changes ---
        player.mana = max(0, min(player.max_mana, player.mana + state_changes.mana_delta))

        # Consume mana if action uses resource
        if intent.uses_resource and intent.resource_cost > 0:
            player.mana = max(0, player.mana - intent.resource_cost)

        # --- Items used ---
        for item_name in state_changes.items_used:
            player.inventory = [
                i for i in player.inventory
                if not (i.name.lower() == item_name.lower() and i.consumes_on_use)
            ]

        # --- Items gained ---
        for item_name in state_changes.items_gained:
            player.inventory.append(
                Item(name=item_name, description="A mysterious item.", item_type="misc")
            )

        # --- Stat changes ---
        for stat, delta in state_changes.stat_changes.items():
            if hasattr(player.stats, stat):
                current = getattr(player.stats, stat)
                setattr(player.stats, stat, max(1, current + delta))

        # --- Status effects ---
        for effect in state_changes.status_effects_added:
            if effect not in player.status_effects:
                player.status_effects.append(effect)
        for effect in state_changes.status_effects_removed:
            if effect in player.status_effects:
                player.status_effects.remove(effect)

        # --- Passive regen (small recovery each turn) ---
        if outcome not in ("critical_failure",):
            player.mana = min(player.max_mana, player.mana + 1)  # +1 mana per turn
            player.hp = min(player.max_hp, player.hp + 1)        # +1 HP per turn

        # --- XP gain ---
        xp_gain = XP_REWARDS.get(outcome, 10)
        leveled = player.gain_xp(xp_gain)
        if leveled:
            level_up_info = {
                "new_level": player.level,
                "max_hp": player.max_hp,
                "max_mana": player.max_mana,
                "stat_increased": "a core attribute",
            }
            logger.info(f"LEVEL UP! {player.name} is now level {player.level}")

        # --- Action history ---
        player.action_history.append(intent.action_type)
        if len(player.action_history) > 20:
            player.action_history = player.action_history[-20:]

        logger.info(
            f"State updated: HP={player.hp}/{player.max_hp}, "
            f"Mana={player.mana}/{player.max_mana}, "
            f"XP={player.xp}/{player.xp_to_next}, "
            f"Level={player.level}"
        )

        return level_up_info

    def list_sessions(self) -> list[str]:
        return list(self._sessions.keys())

    def delete_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Session deleted: {session_id}")
            return True
        return False
