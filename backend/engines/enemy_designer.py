"""Enemy Designer — turns the narrator's description of a foe into a combat enemy.

The name always comes from the campaign: the enemy the narrator just
described. Its stats come from a preset picked by how it was described
(archetype + threat), scaled by player level. See data/enemy_archetypes.py.

Resolution order:
1. LLM reads the scene and returns {name, archetype, threat, moves}.
2. If that fails, a heuristic finds the enemy noun phrase in the narration
   ("a corporate security drone" -> "Corporate Security Drone", construct).
3. If the narration names no enemy, a setting-appropriate fallback is used.
"""

import json
import logging
import random
import re
from dataclasses import dataclass, field

from openai import AsyncOpenAI
from pydantic import BaseModel

import config
from data.enemies import ENEMY_TEMPLATES
from data.enemy_archetypes import ARCHETYPES, THREATS, build_enemy_template
from engines.llm_utils import extract_message_text
from engines.setting import FANTASY, POSTAPOC, SCIFI, genre_of
from models.combat import EnemyTemplate

logger = logging.getLogger(__name__)

_THREAT_RANK = {threat: rank for rank, threat in enumerate(THREATS)}


class EnemySpec(BaseModel):
    name: str
    archetype: str = "soldier"
    threat: str = "standard"
    description: str = ""
    moves: list[str] = []


@dataclass
class DesignedEnemy:
    template: EnemyTemplate
    enemy_key: str  # ENEMY_TEMPLATES key when a hand-built template was used, else ""
    source: str     # "designed" (LLM) | "narrator" (heuristic) | "fallback"
    archetype: str
    threat: str
    description: str = ""
    profile: dict = field(default_factory=dict)


# ─── Vocabulary for the heuristic extractor ───

_ARCHETYPE_NOUNS = {
    "beast": (
        "wolf hound rat spider bear boar beast serpent snake scorpion bat crow raven panther jackal "
        "hyena vermin worm ape wyvern warg lizard crocodile shark hawk vulture mastiff dog tiger lion "
        "insect swarm leech mantis"
    ),
    "brute": (
        "ogre troll giant brute behemoth minotaur mutant juggernaut bruiser orc berserker hulk yeti "
        "cyclops titan bouncer"
    ),
    "soldier": (
        "soldier guard guardsman knight sentinel trooper enforcer mercenary merc warden legionnaire "
        "militiaman officer agent operative cop marine paladin captain commander gunman gunner fighter "
        "champion lieutenant sergeant templar crusader inquisitor peacekeeper patrolman bodyguard "
        "gladiator samurai duelist swordsman spearman"
    ),
    "skirmisher": (
        "bandit thug assassin thief raider scavenger cutthroat ganger gangster hitman ninja archer "
        "sniper hunter brigand pirate smuggler poacher goblin kobold imp stalker ruffian outlaw "
        "marauder highwayman scout infiltrator saboteur"
    ),
    "caster": (
        "mage sorcerer sorceress witch warlock cultist necromancer shaman priest priestess acolyte "
        "hacker netrunner technomancer psion psychic oracle conjurer enchanter druid magus hexer "
        "illusionist summoner mystic zealot"
    ),
    "construct": (
        "drone robot android cyborg mech automaton golem turret synth bot sentry machine droid "
        "exosuit construct gargoyle"
    ),
    "undead": (
        "skeleton zombie ghoul wraith ghost specter spectre lich vampire revenant mummy banshee "
        "phantom corpse spirit wight"
    ),
    "horror": (
        "horror abomination demon fiend devil aberration monster creature entity dragon drake wyrm "
        "elemental chimera hydra kraken nightmare succubus hag"
    ),
}
ENEMY_NOUNS: dict[str, str] = {
    noun: archetype for archetype, nouns in _ARCHETYPE_NOUNS.items() for noun in nouns.split()
}
# Archetypes that describe what the enemy *is* (beat role words like "enforcer").
_NATURE_ARCHETYPES = {"construct", "undead", "beast", "horror"}
_NATURE_ADJECTIVES = {
    "undead": "undead", "skeletal": "undead", "spectral": "undead", "ghostly": "undead", "rotting": "undead",
    "robotic": "construct", "mechanical": "construct", "cybernetic": "construct",
    "demonic": "horror", "eldritch": "horror", "feral": "beast", "rabid": "beast",
}

# Fantasy nouns that have a hand-built template with curated abilities and loot.
CLASSIC_NOUNS = {
    "goblin": "goblin_scavenger", "skeleton": "skeleton_soldier", "rat": "giant_rat",
    "bandit": "bandit_thug", "thug": "bandit_thug", "brigand": "bandit_thug",
    "wolf": "corrupted_wolf", "warg": "corrupted_wolf", "knight": "dark_knight",
    "mage": "shadow_mage", "sorcerer": "shadow_mage", "witch": "shadow_mage",
    "dragon": "dragon_whelp", "drake": "dragon_whelp", "wyrm": "dragon_whelp",
    "vampire": "vampire_lord", "demon": "demon_guardian", "fiend": "demon_guardian",
    "lich": "lich_king", "necromancer": "lich_king",
}
CLASSIC_ARCHETYPES = {
    "goblin_scavenger": "skirmisher", "skeleton_soldier": "undead", "giant_rat": "beast",
    "bandit_thug": "skirmisher", "corrupted_wolf": "beast", "undead_archer": "undead",
    "dark_knight": "soldier", "shadow_mage": "caster", "crypt_horror": "horror",
    "dragon_whelp": "horror", "vampire_lord": "undead", "demon_guardian": "horror",
    "ancient_dragon": "horror", "lich_king": "undead", "demon_lord": "horror",
}

# Words that refer to the player or are too generic to be an enemy name.
_EXCLUDED = {"warrior", "wizard", "rogue", "cleric", "bard", "adventurer", "hero", "you"}
_STOP = set(
    "a an the this that these those its their his her your my our one two three four five six seven "
    "several many few some pair group pack squad band horde of from in on at with by to into toward "
    "towards behind through across over under and or but as is are was were be been you it they he "
    "she we there here then than when while now another other more all no not every each against "
    "like before after out up down around near".split()
)
_IRREGULAR = {"wolves": "wolf", "thieves": "thief", "mice": "rat", "men": "man"}
_HOSTILE = re.compile(
    r"\b(attack|lunge|charg|ambush|snarl|emerg|draw|strik|rush|block|fire|firing|aim|rais|advanc|"
    r"hostil|threat|blade|weapon|gun|growl|leap|pounce|swing|shriek|roar|hiss|surround|close in|"
    r"bear down|level|target|kill|menac|bar your|step forward|steps forward|confront|fight)",
    re.IGNORECASE,
)
_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9'\-]*")
_BREAK = re.compile(r"[.,;:!?()\"\u2014\u2013]")

_BOSS_WORDS = {"lord", "king", "queen", "overlord", "warlord", "emperor", "empress", "archon", "tyrant",
               "master", "matriarch", "patriarch", "boss", "kingpin", "ceo", "director", "prime"}
_ELITE_WORDS = {"captain", "commander", "champion", "chieftain", "alpha", "elite", "veteran", "elder",
                "ancient", "colossal", "massive", "towering", "hulking", "lieutenant", "sergeant", "heavy"}
_MINION_WORDS = {"small", "lone", "scrawny", "young", "lesser", "minor", "pup", "runt", "feeble",
                 "wounded", "weak", "tiny"}

# Fallback enemies when the narration names nobody, per setting genre.
_GENRE_FALLBACKS = {
    SCIFI: [("Corporate Enforcer", "soldier"), ("Security Drone", "construct"),
            ("Street Ganger", "skirmisher"), ("Rogue Combat Android", "construct")],
    POSTAPOC: [("Wasteland Raider", "skirmisher"), ("Irradiated Mutant", "brute"),
               ("Scrap Sentry", "construct")],
}


def _singular(word: str) -> str | None:
    word = word.lower().removesuffix("'s").rstrip("'")
    if word in ENEMY_NOUNS:
        return word
    if word in _IRREGULAR and _IRREGULAR[word] in ENEMY_NOUNS:
        return _IRREGULAR[word]
    for suffix, replacement in (("ves", "f"), ("ies", "y"), ("men", "man"), ("es", ""), ("s", "")):
        if word.endswith(suffix):
            candidate = word[: -len(suffix)] + replacement
            if candidate in ENEMY_NOUNS:
                return candidate
    return None


def _display(word: str) -> str:
    if any(ch.isdigit() for ch in word) or (word.isupper() and len(word) > 1):
        return word
    return word[:1].upper() + word[1:].lower()


@dataclass
class EnemyPhrase:
    name: str
    archetype: str
    classic_key: str | None
    words: list[str]


def extract_enemy_phrase(narration: str) -> EnemyPhrase | None:
    """Find the enemy the narration describes, e.g. 'a corporate security drone opens fire'."""
    best: tuple[float, EnemyPhrase] | None = None
    sentences = list(re.finditer(r"[^.!?\n]+", narration or ""))
    for s_index, sentence in enumerate(sentences):
        text = sentence.group(0)
        tokens = list(_TOKEN.finditer(text))
        hostility = len(_HOSTILE.findall(text))
        i = 0
        while i < len(tokens):
            noun = _singular(tokens[i].group(0))
            if not noun or noun in _EXCLUDED:
                i += 1
                continue

            def _joined(a: int, b: int) -> bool:
                return not _BREAK.search(text[tokens[a].end():tokens[b].start()])

            nouns = [noun]
            j = i + 1
            while j < len(tokens) and len(nouns) < 3 and _joined(j - 1, j):
                next_noun = _singular(tokens[j].group(0))
                if not next_noun or next_noun in _EXCLUDED:
                    break
                nouns.append(next_noun)
                j += 1

            modifiers: list[str] = []
            k = i - 1
            while k >= 0 and len(modifiers) < 2 and _joined(k, k + 1):
                word = tokens[k].group(0)
                lowered = word.lower()
                if (lowered in _STOP or lowered in _EXCLUDED or lowered.endswith("ly")
                        or len(lowered) < 3 or _HOSTILE.match(lowered)):
                    break
                modifiers.insert(0, word)
                k -= 1

            archetype = ENEMY_NOUNS[nouns[-1]]
            for word in [m.lower() for m in modifiers] + nouns:
                nature = _NATURE_ADJECTIVES.get(word) or (
                    ENEMY_NOUNS.get(word) if ENEMY_NOUNS.get(word) in _NATURE_ARCHETYPES else None
                )
                if nature:
                    archetype = nature
                    break
            classic_key = next((CLASSIC_NOUNS[n] for n in nouns if n in CLASSIC_NOUNS), None)
            words = modifiers + nouns
            phrase = EnemyPhrase(
                name=" ".join(_display(w) for w in words),
                archetype=archetype,
                classic_key=classic_key,
                words=[w.lower() for w in words],
            )
            score = hostility * 10 + s_index + (i / max(1, len(tokens)))
            if best is None or score >= best[0]:
                best = (score, phrase)
            i = j
    return best[1] if best else None


def infer_threat(words: list[str]) -> str:
    lowered = {w.lower() for w in words}
    if lowered & _BOSS_WORDS:
        return "boss"
    if lowered & _ELITE_WORDS:
        return "elite"
    if lowered & _MINION_WORDS:
        return "minion"
    return "standard"


def infer_archetype(text: str) -> str:
    phrase = extract_enemy_phrase(text)
    return phrase.archetype if phrase else "soldier"


def beat_threat_hint(world_state: dict) -> str | None:
    """Combat during the campaign's final beat is a boss fight; leader beats are elite."""
    campaign = world_state.get("campaign") or {}
    acts = campaign.get("acts") or []
    if not acts:
        return None
    current_act, current_beat = campaign.get("current_act", 1), campaign.get("current_beat", 1)
    act = next((a for a in acts if a.get("act_id") == current_act), None)
    beat = next((b for b in (act or {}).get("beats", []) if b.get("beat_id") == current_beat), None)
    if not beat:
        return None
    last_act = max(acts, key=lambda a: a.get("act_id", 0))
    last_beat = max((b.get("beat_id", 0) for b in last_act.get("beats", [])), default=None)
    if current_act == last_act.get("act_id") and current_beat == last_beat:
        return "boss"
    text = f"{beat.get('title', '')} {beat.get('description', '')}".lower()
    if re.search(r"\b(boss|final|climax|showdown)\b", text):
        return "boss"
    if re.search(r"\b(lieutenant|champion|penultimate|elite|leader)\b", text):
        return "elite"
    return None


def _raise_threat(threat: str, hint: str | None) -> str:
    if hint and _THREAT_RANK[hint] > _THREAT_RANK.get(threat, 1):
        return hint
    return threat if threat in _THREAT_RANK else "standard"


def classic_fallback_key(world_state: dict, player_level: int, rng: random.Random | None = None) -> str:
    """Pick a hand-built fantasy enemy that fits the location/themes (word-boundary matching)."""
    rng = rng or random.Random()
    tier = max(1, min(5, player_level))
    campaign = world_state.get("campaign") or {}
    text = " ".join([
        world_state.get("location", ""), (world_state.get("situation", "") or "")[-300:],
        " ".join(campaign.get("key_themes", []) or []), campaign.get("title", ""), campaign.get("premise", ""),
    ]).lower()

    location_map = {
        "crypt": ["skeleton_soldier", "undead_archer"], "grave": ["skeleton_soldier", "crypt_horror"],
        "dungeon": ["skeleton_soldier", "undead_archer", "giant_rat"],
        "cave": ["goblin_scavenger", "giant_rat", "corrupted_wolf"], "mine": ["goblin_scavenger", "bandit_thug"],
        "forest": ["corrupted_wolf", "giant_rat", "bandit_thug"], "swamp": ["giant_rat", "crypt_horror"],
        "ruin": ["skeleton_soldier", "goblin_scavenger", "undead_archer"],
        "castle": ["dark_knight", "shadow_mage"], "tower": ["shadow_mage", "dark_knight"],
        "city": ["bandit_thug", "dark_knight"], "town": ["bandit_thug"],
        "village": ["bandit_thug", "giant_rat"], "mountain": ["goblin_scavenger", "dark_knight"],
        "volcano": ["demon_guardian"],
    }
    for keyword, candidates in location_map.items():
        if re.search(rf"\b{keyword}", text):
            valid = [c for c in candidates if abs(ENEMY_TEMPLATES[c].tier - tier) <= 2]
            if valid:
                return rng.choice(valid)

    theme_map = {
        "undead": "skeleton_soldier", "necro": "undead_archer", "death": "crypt_horror",
        "demon": "demon_guardian", "hell": "demon_guardian", "dragon": "dragon_whelp",
        "bandit": "bandit_thug", "thief": "bandit_thug", "magic": "shadow_mage", "arcane": "shadow_mage",
        "wolf": "corrupted_wolf", "beast": "corrupted_wolf", "goblin": "goblin_scavenger",
    }
    for keyword, key in theme_map.items():
        if re.search(rf"\b{keyword}", text) and abs(ENEMY_TEMPLATES[key].tier - tier) <= 2:
            return key

    keys = [k for k, t in ENEMY_TEMPLATES.items() if t.tier == tier] or ["bandit_thug"]
    return rng.choice(keys)


def _sanitize_name(raw) -> str | None:
    if not isinstance(raw, str):
        return None
    name = re.sub(r"\s+", " ", raw).strip().strip("\"'`*[]()").strip()
    name = re.sub(r"^(a|an)\s+", "", name, flags=re.IGNORECASE).rstrip(".,;:!")
    words = name.split()
    if not words or not re.search(r"[A-Za-z]", name):
        return None
    name = " ".join(words[:5])[:40].strip()
    if name.islower():
        name = " ".join(_display(w) for w in name.split())
    return name or None


def normalize_spec(data) -> EnemySpec | None:
    """Validate an LLM enemy description; returns None if unusable."""
    if not isinstance(data, dict):
        return None
    name = _sanitize_name(data.get("name"))
    if not name:
        return None
    description = str(data.get("description") or "").strip()[:200]
    archetype = str(data.get("archetype") or "").strip().lower()
    if archetype not in ARCHETYPES:
        archetype = infer_archetype(f"{name}. {description}")
    threat = str(data.get("threat") or "").strip().lower()
    if threat not in THREATS:
        threat = infer_threat(name.split())
    moves = []
    for move in data.get("moves") or []:
        cleaned = _sanitize_name(move)
        if cleaned and cleaned.lower() != name.lower():
            moves.append(cleaned[:30])
    return EnemySpec(name=name, archetype=archetype, threat=threat, description=description, moves=moves[:3])


_DESIGN_PROMPT = """You design combat encounters for a narrative RPG. Read the scene and identify the single \
hostile enemy the player is about to fight. Output JSON only, no commentary.

JSON format:
{"name": "...", "archetype": "...", "threat": "...", "description": "...", "moves": ["...", "..."]}

Rules:
- name: the enemy exactly as the scene describes it, 1-4 words, Title Case, fitting the campaign's setting. \
Never use a fantasy creature in a sci-fi or modern setting unless the scene says so. If the scene names no \
enemy, invent one that fits the setting and the scene.
- archetype (choose one): brute = huge, heavily built or tanky; soldier = trained, armed fighter or guard; \
skirmisher = fast, sneaky, ranged or agile; beast = animal or feral creature; caster = magic, psionic or \
hacking user; construct = robot, drone, machine or golem; undead = dead or ghostly; horror = demon, \
abomination or monster.
- threat (choose one): boss = the main villain or a final confrontation; elite = a leader, champion or \
veteran; minion = a weak, lone foe; standard = everything else.
- description: one short sentence about how it looks and fights.
- moves: 2 short attack names (max 4 words each) that fit the enemy and the setting."""


def _parse_json_object(raw: str):
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(raw[start:end + 1])
            except json.JSONDecodeError:
                return None
    return None


class EnemyDesigner:
    """LLM-backed reader that names the enemy from the scene and classifies it."""

    def __init__(self):
        self.client = AsyncOpenAI(
            base_url=config.NVIDIA_BASE_URL,
            api_key=config.NVIDIA_API_KEY,
            timeout=20.0,
            max_retries=1,
        )

    async def describe(self, *, narration: str, world_state: dict, threat_hint: str | None = None) -> EnemySpec | None:
        campaign = world_state.get("campaign") or {}
        user_msg = (
            f"Campaign: {campaign.get('title', '')} — {campaign.get('premise', '')}\n"
            f"Setting: {campaign.get('setting', '')} | Tone: {campaign.get('tone', '')}\n"
            f"Current location: {world_state.get('location', '')}\n"
        )
        if threat_hint == "boss":
            user_msg += "This fight is the campaign's final confrontation.\n"
        elif threat_hint == "elite":
            user_msg += "This foe is a leader or champion of the enemy forces.\n"
        user_msg += f'\nScene:\n"""\n{(narration or "")[-1500:]}\n"""'

        request = {
            "model": config.INTENT_MODEL,
            "messages": [{"role": "system", "content": _DESIGN_PROMPT}, {"role": "user", "content": user_msg}],
            "temperature": 0.4,
            "max_tokens": 250,
        }
        try:
            try:
                response = await self.client.chat.completions.create(**request, response_format={"type": "json_object"})
            except Exception as exc:
                logger.warning(f"JSON-mode enemy design failed, retrying without JSON mode: {exc}")
                response = await self.client.chat.completions.create(**request)
            spec = normalize_spec(_parse_json_object(extract_message_text(response)))
            if spec is None:
                logger.warning("Enemy designer returned no usable enemy; using heuristic")
            return spec
        except Exception as exc:
            logger.warning(f"Enemy design request failed; using heuristic: {exc}")
            return None


async def design_enemy(designer, *, narration: str, world_state: dict, player_level: int) -> DesignedEnemy:
    """Decide who the player fights. Always returns an enemy."""
    tier = max(1, min(5, player_level))
    genre = genre_of(world_state)
    hint = beat_threat_hint(world_state)

    spec = None
    if designer is not None:
        try:
            spec = await designer.describe(narration=narration, world_state=world_state, threat_hint=hint)
        except Exception as exc:
            logger.warning(f"Enemy designer crashed; using heuristic: {exc}")
    if spec is not None:
        threat = _raise_threat(spec.threat, hint)
        template = build_enemy_template(spec.name, spec.archetype, threat, tier, spec.moves, genre)
        return DesignedEnemy(template, "", "designed", spec.archetype, threat, spec.description)

    phrase = extract_enemy_phrase(narration)
    if phrase:
        threat = _raise_threat(infer_threat(phrase.words), hint)
        classic = ENEMY_TEMPLATES.get(phrase.classic_key) if phrase.classic_key else None
        if classic and genre == FANTASY and threat == "standard" and abs(classic.tier - tier) <= 1:
            template = classic.model_copy(deep=True, update={"name": phrase.name})
            return DesignedEnemy(template, phrase.classic_key, "narrator", CLASSIC_ARCHETYPES[phrase.classic_key], threat)
        template = build_enemy_template(phrase.name, phrase.archetype, threat, tier, None, genre)
        return DesignedEnemy(template, "", "narrator", phrase.archetype, threat)

    threat = _raise_threat("standard", hint)
    if genre in _GENRE_FALLBACKS:
        name, archetype = random.choice(_GENRE_FALLBACKS[genre])
        template = build_enemy_template(name, archetype, threat, tier, None, genre)
        return DesignedEnemy(template, "", "fallback", archetype, threat)

    key = classic_fallback_key(world_state, player_level)
    archetype = CLASSIC_ARCHETYPES.get(key, "soldier")
    if threat != "standard":
        template = build_enemy_template(ENEMY_TEMPLATES[key].name, archetype, threat, tier, None, genre)
        return DesignedEnemy(template, "", "fallback", archetype, threat)
    return DesignedEnemy(ENEMY_TEMPLATES[key].model_copy(deep=True), key, "fallback", archetype, threat)
