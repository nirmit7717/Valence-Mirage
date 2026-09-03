# config.py — Valence Mirage Configuration

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)

# ─── LLM Configuration (NVIDIA NIM) ───
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")                                                                                                                                                                                                                                   
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")

# Some NVIDIA models (notably gpt-oss reasoning variants and old Nemotron models)
# are slower or noisier for structured gameplay generation. Keep the app on a
# tested, stable 11B model that reliably returns clean chat output.
_BLOCKED_MODEL_HINTS = (
    "nv-embed-v1",
    "gpt-oss",
    "openai/gpt-oss",
    "nemotron-3.5-lightning",
    "nemotron",
    "deepseek-r1",
    "qwq",
    "reasoning",
)


def _safe_model_name(env_name: str, fallback: str) -> str:
    value = (os.getenv(env_name) or fallback).strip()
    lowered = value.lower()
    if any(hint in lowered for hint in _BLOCKED_MODEL_HINTS):
        return fallback
    return value


# Stable default for gameplay generation. These IDs have been verified against the
# current NVIDIA account and return usable text without the timeout/reasoning issues
# seen with the prior gpt-oss defaults.
INTENT_MODEL = _safe_model_name("INTENT_MODEL", "meta/llama-3.2-11b-vision-instruct")
NARRATOR_MODEL = _safe_model_name("NARRATOR_MODEL", "meta/llama-3.2-11b-vision-instruct")

# Embedding model for vector search; the old nv-embed-v1 was retired.
EMBEDDING_MODEL = _safe_model_name("EMBEDDING_MODEL", "nvidia/nemotron-3-embed-1b")

# ─── Probability Engine ───
SIGMOID_SCALE = 5.0

DIFFICULTY_MAP = {
    "minor": -0.1,
    "moderate": -0.2,
    "major": -0.35,
    "extreme": -0.55,
    "cosmic": -0.8,
}

# ─── Scoring Weights (Phase 1) ───
DEFAULT_WEIGHTS = {
    "similarity": 1.0,
    "stat_bonus": 0.8,
    "difficulty": 1.2,
    "mana_penalty": 0.6,
    "saturation_penalty": 0.4,
    "novelty_bonus": 0.3,
    "context_alignment": 0.6,
    "status_effect_modifier": 0.4,
}

# ─── Dice ───
DICE_SIDES = 20
MIN_THRESHOLD = 2
MAX_THRESHOLD = 20

# ─── Anti-Exploitation ───
SATURATION_WINDOW = 5
SATURATION_PENALTY = -0.1
NOVELTY_WINDOW = 10
NOVELTY_BONUS = 0.1

# ─── Game Defaults ───
DEFAULT_PLAYER_STATS = {
    "strength": 10,
    "intelligence": 10,
    "dexterity": 10,
    "control": 10,
    "charisma": 10,
    "wisdom": 10,
}
DEFAULT_HP = 50
DEFAULT_MANA = 50

# ─── API ───
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))

# ─── Auth ───
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# ─── Storage (Phase 2+) ───
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./valence_mirage.db")
