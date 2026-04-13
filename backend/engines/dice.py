"""Dice Engine — Rolls dice and classifies outcomes."""

import random
import logging

from models.outcome import Outcome, StateChanges

logger = logging.getLogger(__name__)

# Outcome classification thresholds
# Roll >= threshold + margin → better outcome
# Roll < threshold - margin → worse outcome
CRITICAL_MARGIN = 5  # How much better/worse than threshold for crits


class DiceEngine:
    """Handles dice rolling and outcome classification."""

    def resolve(
        self,
        roll: int | None,
        threshold: int,
        intent_type: str,
    ) -> str:
        """Classify the outcome based on roll vs threshold.

        Args:
            roll: The d20 roll. If None, generates a random one.
            threshold: Required roll to succeed.
            intent_type: Action type (used for state change logic).

        Returns:
            One of: critical_success, success, partial_success, failure, critical_failure
        """
        if roll is None:
            roll = random.randint(1, 20)

        if roll >= threshold + CRITICAL_MARGIN:
            result = "critical_success"
        elif roll >= threshold:
            result = "success"
        elif roll >= threshold - 2:
            # Near miss — partial success with consequence
            result = "partial_success"
        elif roll <= 2:
            # Natural low roll — critical failure
            result = "critical_failure"
        else:
            result = "failure"

        logger.info(f"Dice: roll={roll}, threshold={threshold} → {result}")
        return result

    @staticmethod
    def roll_d20() -> int:
        """Generate a random d20 roll."""
        return random.randint(1, 20)
