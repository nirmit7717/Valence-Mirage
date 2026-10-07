"""Campaign setting helpers — detect the genre a campaign is set in.

Used to keep generated content (enemy names, loot, relevance rules) consistent
with the campaign: a cyberpunk city should not spawn a "Giant Rat" from a
fantasy table, and a smartphone is fine there but off-topic in a medieval world.
"""

import re

FANTASY = "fantasy"
SCIFI = "scifi"
POSTAPOC = "postapoc"

# Single strong terms are enough to decide; weaker terms need two hits.
_STRONG = {
    SCIFI: ("cyberpunk", "sci-fi", "science fiction", "megacorp", "netrunner", "starship", "spaceship",
            "space station", "cyborg", "android", "hologram", "holographic", "neon-lit", "megacity"),
    POSTAPOC: ("post-apocalyptic", "postapocalyptic", "wasteland", "apocalypse", "nuclear winter", "fallout"),
}
_WEAK = {
    SCIFI: ("neon", "cyber", "corporate", "corporation", "hacker", "implant", "chrome", "synth", "laser",
            "plasma", "mech", "drone", "robot", "augmented", "dystopia", "dystopian", "futuristic",
            "orbital", "galactic", "circuit", "data", "neural", "server", "grid"),
    POSTAPOC: ("mutant", "raider", "bunker", "radiation", "irradiated", "scrap", "ruined city", "survivors"),
}


def _count_hits(text: str, terms: tuple[str, ...]) -> int:
    return sum(1 for term in terms if re.search(rf"\b{re.escape(term)}", text))


def campaign_text(world_state: dict) -> str:
    """All free text describing the campaign's setting, lowercased."""
    campaign = world_state.get("campaign") or {}
    parts = [
        campaign.get("title", ""),
        campaign.get("premise", ""),
        campaign.get("setting", ""),
        campaign.get("tone", ""),
        " ".join(campaign.get("key_themes", []) or []),
        world_state.get("location", ""),
        world_state.get("campaign_keywords", ""),
    ]
    return " ".join(str(p) for p in parts if p).lower()


def detect_genre(text: str) -> str:
    """Classify setting text as fantasy (default), scifi, or postapoc."""
    text = (text or "").lower()
    best, best_score = FANTASY, 0
    for genre in (SCIFI, POSTAPOC):
        score = 2 * _count_hits(text, _STRONG[genre]) + _count_hits(text, _WEAK[genre])
        if score >= 2 and score > best_score:
            best, best_score = genre, score
    return best


def genre_of(world_state: dict) -> str:
    return detect_genre(campaign_text(world_state))
