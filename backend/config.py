# config.py — Valence Mirage Configuration

import os
from dotenv import load_dotenv

load_dotenv()

# ─── LLM Configuration (NVIDIA NIM) ───
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")

# Intent parser model (fast, structured output)
INTENT_MODEL = os.getenv("INTENT_MODEL", "meta/llama-3.1-8b-instruct")

# Narrator model (more capable, creative)
NARRATOR_MODEL = os.getenv("NARRATOR_MODEL", "meta/llama-3.3-70b-instruct")

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

# ─── Storage (Phase 2+) ───
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./valence_mirage.db")
