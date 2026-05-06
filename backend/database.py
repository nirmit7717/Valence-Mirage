"""Database layer — Async SQLite persistence for game sessions."""

import json
import logging
import aiosqlite
from datetime import datetime
from typing import Optional

from models.game_state import GameSession, PlayerState, PlayerStats, Turn, Item
from models.action import ActionIntent
from models.outcome import Outcome, StateChanges, ProbabilityScore, ScoreBreakdown

import config

logger = logging.getLogger(__name__)

DB_PATH = config.DATABASE_URL.split("///")[-1]

# ─── Schema ───────────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    player_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    player_json TEXT NOT NULL,
    world_state_json TEXT NOT NULL,
    turn_number INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    player_input TEXT NOT NULL,
    intent_json TEXT NOT NULL,
    score_json TEXT,
    roll INTEGER NOT NULL,
    outcome_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(session_id, turn_number),
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id, turn_number);

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'player',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tester_requests (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS campaign_history (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT,
    campaign_title TEXT,
    result TEXT,
    turns INTEGER,
    character_class TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS player_profiles (
    user_id TEXT PRIMARY KEY,
    combat_affinity REAL DEFAULT 0.0,
    exploration_affinity REAL DEFAULT 0.0,
    social_affinity REAL DEFAULT 0.0,
    narrative_depth_pref REAL DEFAULT 0.0,
    risk_tolerance REAL DEFAULT 0.0,
    pacing_pref REAL DEFAULT 0.0,
    sessions_played INTEGER DEFAULT 0,
    last_session_id TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""


class Database:
    """Async SQLite database for session persistence."""

    def __init__(self):
        self.db: Optional[aiosqlite.Connection] = None

    async def connect(self):
        self.db = await aiosqlite.connect(DB_PATH)
        self.db.row_factory = aiosqlite.Row
        await self.db.executescript(SCHEMA)
        await self.db.commit()
        logger.info(f"Database connected: {DB_PATH}")

    async def close(self):
        if self.db:
            await self.db.close()
            logger.info("Database connection closed")

    # ─── Session CRUD ──────────────────────────────────────────────────────

    async def save_session(self, session: GameSession) -> None:
        now = datetime.now().isoformat()
        player_json = session.player.model_dump_json()
        world_json = json.dumps(session.world_state)

        await self.db.execute(
            """INSERT INTO sessions (session_id, player_id, player_name, player_json, world_state_json, turn_number, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(session_id) DO UPDATE SET
                   player_json = excluded.player_json,
                   world_state_json = excluded.world_state_json,
                   turn_number = excluded.turn_number,
                   updated_at = excluded.updated_at
            """,
            (session.session_id, session.player.player_id, session.player.name,
             player_json, world_json, session.turn_number,
             session.created_at.isoformat(), now),
        )
        await self.db.commit()
        logger.debug(f"Session saved: {session.session_id} (turn {session.turn_number})")

    async def load_session(self, session_id: str) -> Optional[GameSession]:
        row = await self.db.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        )
        session_row = await row.fetchone()
        if not session_row:
            return None

        player = PlayerState.model_validate_json(session_row["player_json"])
        world_state = json.loads(session_row["world_state_json"])
        turns = await self._load_turns(session_id)

        return GameSession(
            session_id=session_row["session_id"],
            player=player,
            world_state=world_state,
            turn_history=turns,
            turn_number=session_row["turn_number"],
            created_at=datetime.fromisoformat(session_row["created_at"]),
        )

    async def list_sessions(self) -> list[dict]:
        rows = await self.db.execute(
            """SELECT session_id, player_name, turn_number, created_at, updated_at
               FROM sessions ORDER BY updated_at DESC"""
        )
        results = []
        async for row in rows:
            results.append({
                "session_id": row["session_id"],
                "player_name": row["player_name"],
                "turn_number": row["turn_number"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            })
        return results

    async def delete_session(self, session_id: str) -> bool:
        await self.db.execute("DELETE FROM turns WHERE session_id = ?", (session_id,))
        cursor = await self.db.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        await self.db.commit()
        deleted = cursor.rowcount > 0
        if deleted:
            logger.info(f"Session deleted: {session_id}")
        return deleted

    # ─── Turn Persistence ──────────────────────────────────────────────────

    async def save_turn(self, session_id: str, turn: Turn) -> None:
        intent_json = turn.intent.model_dump_json()
        score_json = turn.score.model_dump_json() if turn.score else None
        outcome_json = turn.outcome.model_dump_json()

        await self.db.execute(
            """INSERT INTO turns (session_id, turn_number, player_input, intent_json, score_json, roll, outcome_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(session_id, turn_number) DO NOTHING
            """,
            (session_id, turn.turn_number, turn.player_input,
             intent_json, score_json, turn.roll, outcome_json),
        )
        await self.db.commit()

    async def save_turns_batch(self, session_id: str, turns: list[Turn]) -> None:
        data = [
            (session_id, t.turn_number, t.player_input,
             t.intent.model_dump_json(),
             t.score.model_dump_json() if t.score else None,
             t.roll, t.outcome.model_dump_json())
            for t in turns
        ]
        await self.db.executemany(
            """INSERT INTO turns (session_id, turn_number, player_input, intent_json, score_json, roll, outcome_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(session_id, turn_number) DO NOTHING
            """,
            data,
        )
        await self.db.commit()

    async def _load_turns(self, session_id: str) -> list[Turn]:
        rows = await self.db.execute(
            "SELECT * FROM turns WHERE session_id = ? ORDER BY turn_number",
            (session_id,),
        )
        turns = []
        async for row in rows:
            intent = ActionIntent.model_validate_json(row["intent_json"])
            score = ProbabilityScore.model_validate_json(row["score_json"]) if row["score_json"] else None
            outcome = Outcome.model_validate_json(row["outcome_json"])
            turns.append(Turn(
                turn_number=row["turn_number"],
                player_input=row["player_input"],
                intent=intent,
                score=score,
                roll=row["roll"],
                outcome=outcome,
            ))
        return turns

    # ─── Full Session Save ────────────────────────────────────────────────

    # ─── User Management ────────────────────────────────────────────────

    async def create_user(self, username: str, password_hash: str, role: str = "player") -> dict:
        import uuid
        user_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        await self.db.execute(
            "INSERT INTO users (id, username, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, username, password_hash, role, now),
        )
        await self.db.commit()
        return {"id": user_id, "username": username, "role": role, "created_at": now}

    async def get_user_by_username(self, username: str) -> Optional[dict]:
        row = await self.db.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = await row.fetchone()
        if not user:
            return None
        return {"id": user["id"], "username": user["username"],
                "password_hash": user["password_hash"], "role": user["role"],
                "created_at": user["created_at"]}

    async def get_user_by_id(self, user_id: str) -> Optional[dict]:
        row = await self.db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = await row.fetchone()
        if not user:
            return None
        return {"id": user["id"], "username": user["username"],
                "password_hash": user["password_hash"], "role": user["role"],
                "created_at": user["created_at"]}

    async def count_users(self) -> int:
        row = await self.db.execute("SELECT COUNT(*) FROM users")
        result = await row.fetchone()
        return result[0]

    async def create_tester_request(self, email: str) -> dict:
        import uuid
        req_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        await self.db.execute(
            "INSERT INTO tester_requests (id, email, created_at) VALUES (?, ?, ?)",
            (req_id, email, now),
        )
        await self.db.commit()
        return {"id": req_id, "email": email, "created_at": now}

    async def save_campaign_history(self, user_id: str, session_id: str, title: str,
                                     result: str, turns: int, character_class: str) -> dict:
        import uuid
        h_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        await self.db.execute(
            """INSERT INTO campaign_history (id, user_id, session_id, campaign_title, result, turns, character_class, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (h_id, user_id, session_id, title, result, turns, character_class, now),
        )
        await self.db.commit()
        return {"id": h_id, "user_id": user_id, "session_id": session_id,
                "campaign_title": title, "result": result, "turns": turns,
                "character_class": character_class, "created_at": now}

    async def get_campaign_history(self, user_id: str) -> list[dict]:
        rows = await self.db.execute(
            "SELECT * FROM campaign_history WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        results = []
        async for row in rows:
            results.append({
                "id": row["id"], "session_id": row["session_id"],
                "campaign_title": row["campaign_title"], "result": row["result"],
                "turns": row["turns"], "character_class": row["character_class"],
                "created_at": row["created_at"],
            })
        return results

    async def get_user_stats(self, user_id: str) -> dict:
        rows = await self.db.execute(
            "SELECT result, turns, character_class FROM campaign_history WHERE user_id = ?",
            (user_id,),
        )
        total = 0
        wins = 0
        total_turns = 0
        class_counts: dict[str, int] = {}
        async for row in rows:
            total += 1
            if row["result"] == "victory":
                wins += 1
            total_turns += row["turns"] or 0
            cls = row["character_class"] or "unknown"
            class_counts[cls] = class_counts.get(cls, 0) + 1
        favorite_class = max(class_counts, key=class_counts.get) if class_counts else "none"
        return {
            "total_campaigns": total,
            "wins": wins,
            "avg_turns": round(total_turns / total, 1) if total > 0 else 0,
            "favorite_class": favorite_class,
        }

    # ─── Full Session Save ────────────────────────────────────────────────

    async def save_full_session(self, session: GameSession) -> None:
        await self.save_session(session)
        if session.turn_history:
            await self.save_turns_batch(session.session_id, session.turn_history)
        logger.info(f"Full session persisted: {session.session_id} ({len(session.turn_history)} turns)")

    # ─── Player Profile ────────────────────────────────────────────────

    async def load_profile(self, user_id: str):
        """Load player profile. Returns PlayerProfile or None."""
        from models.profile import PlayerProfile
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM player_profiles WHERE user_id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return PlayerProfile(
                user_id=row["user_id"],
                combat_affinity=row["combat_affinity"],
                exploration_affinity=row["exploration_affinity"],
                social_affinity=row["social_affinity"],
                narrative_depth_pref=row["narrative_depth_pref"],
                risk_tolerance=row["risk_tolerance"],
                pacing_pref=row["pacing_pref"],
                sessions_played=row["sessions_played"],
                last_session_id=row["last_session_id"],
            )

    async def save_profile(self, profile) -> None:
        """Save or update player profile (upsert)."""
        from datetime import datetime
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO player_profiles
                    (user_id, combat_affinity, exploration_affinity, social_affinity,
                     narrative_depth_pref, risk_tolerance, pacing_pref,
                     sessions_played, last_session_id, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    combat_affinity = excluded.combat_affinity,
                    exploration_affinity = excluded.exploration_affinity,
                    social_affinity = excluded.social_affinity,
                    narrative_depth_pref = excluded.narrative_depth_pref,
                    risk_tolerance = excluded.risk_tolerance,
                    pacing_pref = excluded.pacing_pref,
                    sessions_played = excluded.sessions_played,
                    last_session_id = excluded.last_session_id,
                    updated_at = excluded.updated_at
            """, (
                profile.user_id,
                profile.combat_affinity,
                profile.exploration_affinity,
                profile.social_affinity,
                profile.narrative_depth_pref,
                profile.risk_tolerance,
                profile.pacing_pref,
                profile.sessions_played,
                profile.last_session_id,
                datetime.now().isoformat(),
            ))
            await db.commit()
            logger.info(f"Profile saved for {profile.user_id} (sessions: {profile.sessions_played})")
