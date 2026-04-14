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

    async def save_full_session(self, session: GameSession) -> None:
        await self.save_session(session)
        if session.turn_history:
            await self.save_turns_batch(session.session_id, session.turn_history)
        logger.info(f"Full session persisted: {session.session_id} ({len(session.turn_history)} turns)")
