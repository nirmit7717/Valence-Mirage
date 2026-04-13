"""State Manager — Manages game sessions in memory (Phase 1)."""

import logging
from datetime import datetime
from copy import deepcopy

from models.game_state import GameSession, PlayerState, Turn
from models.outcome import StateChanges
from models.action import ActionIntent
import config

logger = logging.getLogger(__name__)


class StateManager:
    """Creates, stores, and updates game sessions. Phase 1: in-memory."""

    def __init__(self):
        self._sessions: dict[str, GameSession] = {}

    def create_session(self, player_name: str = "Adventurer") -> GameSession:
        """Create a new game session with default starting state."""
        session = GameSession(
            player=PlayerState(
                name=player_name,
                hp=config.DEFAULT_HP,
                max_hp=config.DEFAULT_HP,
                mana=config.DEFAULT_MANA,
                max_mana=config.DEFAULT_MANA,
            ),
        )
        self._sessions[session.session_id] = session
        logger.info(f"Session created: {session.session_id} for '{player_name}'")
        return session

    def get_session(self, session_id: str) -> GameSession | None:
        """Retrieve a session by ID."""
        return self._sessions.get(session_id)

    def apply_changes(
        self,
        session: GameSession,
        intent: ActionIntent,
        state_changes: StateChanges,
    ) -> None:
        """Apply state changes after an action is resolved.

        Updates player state in-place within the session.
        """
        player = session.player

        # HP changes
        player.hp = max(0, min(player.max_hp, player.hp + state_changes.hp_delta))

        # Mana changes
        player.mana = max(0, min(player.max_mana, player.mana + state_changes.mana_delta))

        # Consume mana if action uses resource
        if intent.uses_resource and intent.resource_cost > 0:
            player.mana = max(0, player.mana - intent.resource_cost)

        # Items used
        for item_name in state_changes.items_used:
            player.inventory = [
                i for i in player.inventory
                if not (i.name.lower() == item_name.lower() and i.consumes_on_use)
            ]

        # Items gained
        # (Phase 2: actual Item objects. Phase 1: just track names)
        for item_name in state_changes.items_gained:
            from models.game_state import Item
            player.inventory.append(
                Item(name=item_name, description="A mysterious item.")
            )

        # Stat changes
        for stat, delta in state_changes.stat_changes.items():
            if hasattr(player.stats, stat):
                current = getattr(player.stats, stat)
                setattr(player.stats, stat, max(1, current + delta))

        # Status effects
        for effect in state_changes.status_effects_added:
            if effect not in player.status_effects:
                player.status_effects.append(effect)

        for effect in state_changes.status_effects_removed:
            if effect in player.status_effects:
                player.status_effects.remove(effect)

        # Track action history for saturation/novelty
        player.action_history.append(intent.action_type)
        # Keep only last 20 action types to prevent unbounded growth
        if len(player.action_history) > 20:
            player.action_history = player.action_history[-20:]

        logger.info(
            f"State updated: HP={player.hp}/{player.max_hp}, "
            f"Mana={player.mana}/{player.max_mana}"
        )

    def list_sessions(self) -> list[str]:
        """List all session IDs."""
        return list(self._sessions.keys())

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Session deleted: {session_id}")
            return True
        return False
