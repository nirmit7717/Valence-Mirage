"""Outcome models — probability scoring and action resolution."""

from pydantic import BaseModel, Field


class ScoreBreakdown(BaseModel):
    """Individual component scores of the probability calculation."""

    similarity: float = 0.0        # RAG retrieval similarity (Phase 3)
    stat_bonus: float = 0.0        # Relevant stat modifier
    difficulty: float = 0.0        # Action difficulty penalty
    mana_penalty: float = 0.0      # Insufficient mana penalty
    saturation_penalty: float = 0.0  # Repeated action penalty
    novelty_bonus: float = 0.0     # Creative action bonus
    context_alignment: float = 0.0 # How well action aligns with current narrative context
    status_effect_modifier: float = 0.0  # Modifier from active status effects


class ProbabilityScore(BaseModel):
    """Full probability assessment for a player action."""

    raw_score: float = Field(..., description="Unweighted sum before sigmoid")
    probability: float = Field(..., description="sigmoid(raw_score), 0.0-1.0")
    dice_threshold: int = Field(..., description="Required d20 roll to succeed")
    breakdown: ScoreBreakdown = Field(
        default_factory=ScoreBreakdown,
        description="Individual component scores",
    )


class StateChanges(BaseModel):
    """Changes to apply to player/world state after action resolution."""

    hp_delta: int = 0
    mana_delta: int = 0
    items_used: list[str] = []
    items_gained: list[str] = []
    stat_changes: dict[str, int] = {}
    status_effects_added: list[str] = []
    status_effects_removed: list[str] = []


class Outcome(BaseModel):
    """Final result of a player action."""

    result: str = Field(
        ...,
        description="One of: critical_success, success, partial_success, "
                    "failure, critical_failure",
    )
    roll: int = Field(..., description="Actual d20 roll")
    threshold: int = Field(..., description="Required roll to succeed")
    narration: str = Field(..., description="LLM-generated story text")
    state_changes: StateChanges = Field(
        default_factory=StateChanges,
        description="State changes to apply",
    )
