"""Player profile models — RL engagement tracking dimensions."""

from dataclasses import dataclass, field
from pydantic import BaseModel, Field
from typing import Optional


# ─── Per-Turn Signal ───

@dataclass
class TurnSignal:
    """Raw behavioral signal collected on every player turn."""
    turn_number: int
    action_type: str = ""             # From IntentParser (attack, explore, persuade, etc.)
    required_roll: bool = False       # Probabilistic outcome triggered
    dice_result: str = ""             # critical_success / success / failure / critical_failure
    time_spent_ms: int = 0           # Time between this action and previous action
    combat_action: bool = False       # Was this a combat turn?
    npc_interaction: bool = False     # Did player interact with an NPC?
    explored: bool = False            # Investigate / examine / search / look actions
    fled: bool = False                # Player attempted to flee
    resources_spent: float = 0.0      # Mana + items consumed this turn


# ─── Session Aggregation ───

@dataclass
class SessionMetrics:
    """Aggregated metrics from a completed session — used to update profile."""
    combat_ratio: float = 0.0         # combat turns / total turns
    exploration_ratio: float = 0.0    # exploration actions / total turns
    social_ratio: float = 0.0         # NPC interactions / total turns
    avg_time_between_actions_ms: float = 0.0  # pacing signal
    risk_score: float = 0.0           # aggressive actions + resource spending / total
    skip_rate: float = 0.0            # Not directly measurable server-side (future: frontend signal)
    session_duration_min: float = 0.0
    turns_played: int = 0


# ─── Player Profile (persisted) ───

class PlayerProfile(BaseModel):
    """Persistent player preference profile — updated via EMA after each session.

    All dimensions range from -1.0 to 1.0:
      0.0 = neutral (default / cold start)
      +1.0 = strong preference
      -1.0 = strong avoidance
    """
    user_id: str
    combat_affinity: float = 0.0          # More combat beats, harder enemies
    exploration_affinity: float = 0.0     # More discovery beats, richer environments
    social_affinity: float = 0.0          # More NPC beats, deeper dialogue
    narrative_depth_pref: float = 0.0     # Longer vs shorter narration
    risk_tolerance: float = 0.0           # Riskier encounters, better rewards
    pacing_pref: float = 0.0             # Fast/action vs slow/brooding
    sessions_played: int = 0
    last_session_id: Optional[str] = None

    def clamp(self) -> "PlayerProfile":
        """Clamp all dimensions to [-1.0, 1.0]."""
        for dim in ("combat_affinity", "exploration_affinity", "social_affinity",
                     "narrative_depth_pref", "risk_tolerance", "pacing_pref"):
            val = max(-1.0, min(1.0, getattr(self, dim)))
            setattr(self, dim, val)
        return self


# ─── EMA Helper ───

def ema(current: float, observation: float, alpha: float = 0.3) -> float:
    """Exponential moving average update.

    Args:
        current: Current profile dimension value
        observation: New session metric (0.0-1.0 range)
        alpha: Learning rate (0.3 = moderate, converges in 5-10 sessions)

    Returns:
        Updated value (unclamped — caller should clamp)
    """
    # Shift observation from [0,1] to [-1,1] centered at 0
    # For ratios: 0.5 = neutral, >0.5 = positive affinity, <0.5 = avoidance
    shifted = (observation * 2.0) - 1.0
    return (1.0 - alpha) * current + alpha * shifted


# ─── Profile Update ───

def update_profile(profile: PlayerProfile, metrics: SessionMetrics, alpha: float = 0.3) -> PlayerProfile:
    """Update profile dimensions from session metrics using EMA.

    Args:
        profile: Current player profile
        metrics: Aggregated session metrics
        alpha: EMA learning rate (default 0.3 = moderate adaptation)

    Returns:
        Updated profile (clamped to valid ranges)
    """
    if metrics.turns_played < 3:
        # Too few turns for reliable signal — skip update
        return profile

    profile.combat_affinity = ema(profile.combat_affinity, metrics.combat_ratio, alpha)
    profile.exploration_affinity = ema(profile.exploration_affinity, metrics.exploration_ratio, alpha)
    profile.social_affinity = ema(profile.social_affinity, metrics.social_ratio, alpha)
    profile.narrative_depth_pref = ema(profile.narrative_depth_pref, 1.0 - metrics.skip_rate, alpha)
    profile.risk_tolerance = ema(profile.risk_tolerance, metrics.risk_score, alpha)

    # Normalize pacing: fast = <5s avg, slow = >30s avg
    pacing_normalized = max(0.0, min(1.0, 1.0 - (metrics.avg_time_between_actions_ms / 30000.0)))
    profile.pacing_pref = ema(profile.pacing_pref, pacing_normalized, alpha)

    profile.sessions_played += 1
    profile.clamp()
    return profile


# ─── Campaign Beat Weights ───

def get_beat_weights(profile: Optional[PlayerProfile]) -> dict[str, float]:
    """Generate campaign beat type weights from player profile.

    Args:
        profile: Player profile (None = cold start defaults)

    Returns:
        Dict of beat_type → weight (all positive, sum varies)
    """
    if profile is None:
        return {
            "combat": 0.3,
            "exploration": 0.3,
            "social": 0.2,
            "choice": 0.2,
        }

    return {
        "combat": 0.3 + profile.combat_affinity * 0.25,
        "exploration": 0.3 + profile.exploration_affinity * 0.25,
        "social": 0.2 + profile.social_affinity * 0.25,
        "choice": 0.2,  # Always present — player agency
    }


# ─── Narration Parameters ───

def get_narration_params(profile: Optional[PlayerProfile]) -> dict:
    """Get narrator parameters adapted to player profile.

    Args:
        profile: Player profile (None = defaults)

    Returns:
        Dict with max_tokens and temperature
    """
    if profile is None:
        return {"max_tokens": 500, "temperature": 0.7}

    depth = profile.narrative_depth_pref
    return {
        "max_tokens": int(300 + depth * 200),   # 100-500 range
        "temperature": 0.6 + depth * 0.15,       # 0.45-0.75 range
    }
