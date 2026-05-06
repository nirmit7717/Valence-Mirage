"""Engagement Tracker — per-turn signal collection, session aggregation, profile updates.

Collects implicit behavioral signals from every player turn, aggregates them
at session end, and updates the player profile via EMA (exponential moving average).
"""

import time
import logging
from typing import Optional

from models.profile import TurnSignal, SessionMetrics, PlayerProfile, update_profile

logger = logging.getLogger(__name__)

# Action type classifications for signal mapping
COMBAT_TYPES = {"attack", "defend", "flee", "ability", "combat"}
EXPLORATION_TYPES = {"explore", "investigate", "search", "examine", "look", "inspect", "discover"}
SOCIAL_TYPES = {"persuade", "intimidate", "deceive", "dialogue", "talk", "barter", "convince"}
RISKY_TYPES = {"attack", "charge", "rush", "assault", "ambush", "gamble", "reckless"}
CAUTIOUS_TYPES = {"defend", "flee", "retreat", "hide", "evade", "wait", "observe"}


class EngagementTracker:
    """Tracks player engagement signals across a session."""

    def __init__(self):
        self._signals: dict[str, list[TurnSignal]] = {}  # session_id → signals
        self._last_action_time: dict[str, float] = {}     # session_id → timestamp
        self._session_start: dict[str, float] = {}        # session_id → start time

    def start_session(self, session_id: str) -> None:
        """Mark session start for timing signals."""
        self._signals[session_id] = []
        self._last_action_time[session_id] = time.time()
        self._session_start[session_id] = time.time()

    def record_turn(
        self,
        session_id: str,
        turn_number: int,
        action_type: str = "",
        required_roll: bool = False,
        dice_result: str = "",
        combat_action: bool = False,
        npc_interaction: bool = False,
        mana_spent: float = 0.0,
        items_used: int = 0,
    ) -> TurnSignal:
        """Record a signal for a single turn.

        Args:
            session_id: Session identifier
            turn_number: Current turn number
            action_type: Classified action type from IntentParser
            required_roll: Whether a dice roll was triggered
            dice_result: Outcome of the roll
            combat_action: Whether this was a combat turn
            npc_interaction: Whether player interacted with an NPC
            mana_spent: Mana consumed this turn
            items_used: Number of items consumed this turn

        Returns:
            The recorded TurnSignal
        """
        now = time.time()
        last_time = self._last_action_time.get(session_id, now)
        time_spent_ms = int((now - last_time) * 1000)
        self._last_action_time[session_id] = now

        action_lower = action_type.lower()
        signal = TurnSignal(
            turn_number=turn_number,
            action_type=action_type,
            required_roll=required_roll,
            dice_result=dice_result,
            time_spent_ms=time_spent_ms,
            combat_action=combat_action,
            npc_interaction=npc_interaction,
            explored=action_lower in EXPLORATION_TYPES,
            fled=action_lower in {"flee", "retreat"},
            resources_spent=mana_spent + items_used * 5.0,  # Items weighted as 5 units
        )

        if session_id not in self._signals:
            self._signals[session_id] = []
        self._signals[session_id].append(signal)

        logger.debug(
            f"Turn signal: session={session_id} turn={turn_number} "
            f"type={action_type} combat={combat_action} npc={npc_interaction} "
            f"time={time_spent_ms}ms"
        )
        return signal

    def aggregate_session(self, session_id: str) -> Optional[SessionMetrics]:
        """Aggregate turn signals into session metrics.

        Call this when a session ends (campaign complete, game over, or abandoned).

        Args:
            session_id: Session to aggregate

        Returns:
            SessionMetrics or None if no signals collected
        """
        signals = self._signals.get(session_id, [])
        if not signals:
            logger.warning(f"No signals to aggregate for session {session_id}")
            return None

        total = len(signals)
        combat_turns = sum(1 for s in signals if s.combat_action)
        exploration_turns = sum(1 for s in signals if s.explored)
        social_turns = sum(1 for s in signals if s.npc_interaction)

        # Risk score: aggressive actions + resource spending normalized
        risky_actions = sum(1 for s in signals if s.action_type.lower() in RISKY_TYPES)
        cautious_actions = sum(1 for s in signals if s.action_type.lower() in CAUTIOUS_TYPES)
        total_resources = sum(s.resources_spent for s in signals)

        # Time calculations
        session_start = self._session_start.get(session_id, time.time())
        session_duration_min = (time.time() - session_start) / 60.0
        time_intervals = [s.time_spent_ms for s in signals if s.time_spent_ms > 0]
        avg_time_ms = sum(time_intervals) / len(time_intervals) if time_intervals else 0

        metrics = SessionMetrics(
            combat_ratio=combat_turns / total if total else 0,
            exploration_ratio=exploration_turns / total if total else 0,
            social_ratio=social_turns / total if total else 0,
            avg_time_between_actions_ms=avg_time_ms,
            risk_score=(
                (risky_actions - cautious_actions * 0.5) / total
                + min(total_resources / (total * 20.0), 0.3)  # Resource spending bonus, capped
            ) if total else 0,
            skip_rate=0.0,  # Not measurable server-side — future: frontend signal
            session_duration_min=session_duration_min,
            turns_played=total,
        )

        logger.info(
            f"Session metrics: {session_id} — "
            f"combat={metrics.combat_ratio:.2f} explore={metrics.exploration_ratio:.2f} "
            f"social={metrics.social_ratio:.2f} risk={metrics.risk_score:.2f} "
            f"pacing={metrics.avg_time_between_actions_ms:.0f}ms "
            f"turns={total} duration={metrics.session_duration_min:.1f}min"
        )
        return metrics

    def finalize_session(
        self, session_id: str, profile: Optional[PlayerProfile], user_id: str
    ) -> Optional[PlayerProfile]:
        """Aggregate session and update player profile.

        Args:
            session_id: Session to finalize
            profile: Current player profile (None = new player)
            user_id: User ID for profile creation

        Returns:
            Updated PlayerProfile, or None if insufficient data
        """
        metrics = self.aggregate_session(session_id)
        if metrics is None:
            return profile

        if profile is None:
            profile = PlayerProfile(user_id=user_id)

        profile = update_profile(profile, metrics)
        profile.last_session_id = session_id

        logger.info(
            f"Profile updated for {user_id}: "
            f"combat={profile.combat_affinity:.2f} explore={profile.exploration_affinity:.2f} "
            f"social={profile.social_affinity:.2f} depth={profile.narrative_depth_pref:.2f} "
            f"risk={profile.risk_tolerance:.2f} pacing={profile.pacing_pref:.2f} "
            f"(session #{profile.sessions_played})"
        )

        # Cleanup
        self._signals.pop(session_id, None)
        self._last_action_time.pop(session_id, None)
        self._session_start.pop(session_id, None)

        return profile
