"""Probability Engine — Scores actions and converts to dice thresholds."""

import math
import logging

from models.action import ActionIntent
from models.game_state import PlayerState
from models.outcome import ProbabilityScore, ScoreBreakdown
import config

logger = logging.getLogger(__name__)


class ProbabilityEngine:
    """Computes action feasibility probability and dice thresholds."""

    def calculate(
        self,
        intent: ActionIntent,
        player: PlayerState,
        similarity: float = 0.5,  # Default mid-range when no RAG (Phase 1)
        context_alignment: float = 0.0,  # -1.0 to +1.0: how well action fits current narrative
        status_effects: list[str] | None = None,  # Active status effect names on player
    ) -> ProbabilityScore:
        """Calculate probability score for a player action.

        Args:
            intent: Parsed action intent.
            player: Current player state.
            similarity: RAG similarity score (0.0-1.0). Default 0.5 for Phase 1.

        Returns:
            ProbabilityScore with breakdown, probability, and dice threshold.
        """
        breakdown = ScoreBreakdown()

        # --- Similarity (RAG) ---
        breakdown.similarity = similarity

        # --- Stat bonus ---
        stat_value = getattr(player.stats, intent.relevant_stat, 10)
        # Centered on 10 (average). Range: -0.33 to +0.33 for stats 0-20
        breakdown.stat_bonus = (stat_value - 10) / 30

        # --- Difficulty ---
        breakdown.difficulty = config.DIFFICULTY_MAP.get(intent.scale, -0.2)

        # --- Mana penalty ---
        breakdown.mana_penalty = 0.0
        if intent.uses_resource and intent.resource_cost > 0:
            if player.mana < intent.resource_cost:
                # Can't afford it — heavy penalty but not impossible (desperation)
                breakdown.mana_penalty = -0.3
            elif player.mana < intent.resource_cost * 2:
                # Low on mana — slight penalty
                breakdown.mana_penalty = -0.1

        # --- Saturation penalty (repeated actions) ---
        recent = player.action_history[-config.SATURATION_WINDOW:]
        repeat_count = recent.count(intent.action_type)
        breakdown.saturation_penalty = config.SATURATION_PENALTY * repeat_count

        # --- Novelty bonus ---
        window = player.action_history[-config.NOVELTY_WINDOW:]
        if intent.action_type not in window:
            breakdown.novelty_bonus = config.NOVELTY_BONUS
        else:
            breakdown.novelty_bonus = 0.0

        # --- Context alignment ---
        breakdown.context_alignment = context_alignment

        # --- Status effect modifier ---
        se_mod = 0.0
        if status_effects:
            for eff in status_effects:
                name = eff.lower()
                if name == "focus":
                    se_mod += 0.15  # Focused → better outcomes
                elif name == "weaken":
                    se_mod -= 0.1   # Weakened → harder
                elif name in ("bleed", "poisoned", "burning"):
                    se_mod -= 0.05  # DoT effects → slight penalty
                elif name == "blocking":
                    if intent.action_type in ("defend", "block"):
                        se_mod += 0.1  # Blocking + defending = synergy
        breakdown.status_effect_modifier = se_mod

        # --- Weighted sum ---
        raw_score = (
            config.DEFAULT_WEIGHTS["similarity"] * breakdown.similarity
            + config.DEFAULT_WEIGHTS["stat_bonus"] * breakdown.stat_bonus
            + config.DEFAULT_WEIGHTS["difficulty"] * breakdown.difficulty
            + config.DEFAULT_WEIGHTS["mana_penalty"] * breakdown.mana_penalty
            + config.DEFAULT_WEIGHTS["saturation_penalty"] * breakdown.saturation_penalty
            + config.DEFAULT_WEIGHTS["novelty_bonus"] * breakdown.novelty_bonus
            + config.DEFAULT_WEIGHTS.get("context_alignment", 0.6) * breakdown.context_alignment
            + config.DEFAULT_WEIGHTS.get("status_effect_modifier", 0.4) * breakdown.status_effect_modifier
        )

        # --- Probability conversion ---
        probability = self._sigmoid(raw_score)

        # --- Dice threshold ---
        threshold = self._dice_threshold(probability)

        logger.info(
            f"Score: raw={raw_score:.3f}, prob={probability:.3f}, "
            f"threshold={threshold}, type={intent.action_type}"
        )

        return ProbabilityScore(
            raw_score=raw_score,
            probability=probability,
            dice_threshold=threshold,
            breakdown=breakdown,
        )

    @staticmethod
    def _sigmoid(x: float) -> float:
        """Scaled sigmoid for probability distribution."""
        return 1.0 / (1.0 + math.exp(-x * config.SIGMOID_SCALE))

    @staticmethod
    def _dice_threshold(probability: float) -> int:
        """Map probability to d20 required roll.

        Higher probability → lower threshold needed → easier to succeed.
        """
        raw = math.ceil((1.0 - probability) * config.DICE_SIDES)
        return max(config.MIN_THRESHOLD, min(config.MAX_THRESHOLD, raw))
