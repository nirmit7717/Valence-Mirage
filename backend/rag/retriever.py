"""Rule Retriever — Semantic search over game rules and trajectories.

Phase 3: Uses ChromaDB vector store with NVIDIA embeddings.
Falls back to keyword matching if vector store unavailable.
"""

import logging
from typing import Optional

from rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


class RuleRetriever:
    """Retrieves relevant game rules and narrative patterns using vector search."""

    def __init__(self):
        self.vector_store = VectorStore()
        self._keyword_rules: dict[str, str] = {}  # Fallback
        self._use_vector = False
        self._load_fallback_rules()

    async def initialize(self):
        """Initialize the vector store (call during app startup)."""
        try:
            await self.vector_store.initialize()
            self._use_vector = True
            logger.info("RuleRetriever: vector search enabled")
        except Exception as e:
            logger.warning(f"Vector store init failed, using keyword fallback: {e}")
            self._use_vector = False

    def _load_fallback_rules(self):
        """Load rules for keyword fallback."""
        from pathlib import Path
        rules_dir = Path(__file__).parent.parent / "data" / "rules"
        if not rules_dir.exists():
            return
        for rule_file in rules_dir.glob("*.md"):
            category = rule_file.stem
            self._keyword_rules[category] = rule_file.read_text()

    async def get_relevant_rules(self, action_type: str, context: str = "", top_k: int = 3) -> str:
        """Retrieve rules relevant to an action using semantic search."""
        query = f"{action_type} {context}".strip()

        if self._use_vector:
            try:
                hits = await self.vector_store.search_rules(query, top_k=top_k)
                if hits:
                    return "\n\n---\n\n".join(
                        f"[{h['category']} (sim: {h['similarity']})]\n{h['text']}"
                        for h in hits
                    )
            except Exception as e:
                logger.warning(f"Vector search failed, falling back: {e}")

        # Keyword fallback
        return self._keyword_fallback(query)

    async def get_narrative_similarity(self, action_description: str) -> float:
        """Get similarity score for an action against known trajectories."""
        if not self._use_vector:
            return 0.5  # Neutral when vector search unavailable

        try:
            return await self.vector_store.get_top_similarity(action_description)
        except Exception:
            return 0.5

    async def search_all(self, query: str, top_k: int = 3) -> dict:
        """Search both rules and trajectories. Returns combined results."""
        results = {"rules": [], "trajectories": [], "top_similarity": 0.5}

        if self._use_vector:
            try:
                results["rules"] = await self.vector_store.search_rules(query, top_k)
                results["trajectories"] = await self.vector_store.search_trajectories(query, top_k)
                all_sims = [r["similarity"] for r in results["rules"] + results["trajectories"]]
                if all_sims:
                    results["top_similarity"] = max(all_sims)
            except Exception as e:
                logger.warning(f"Vector search failed: {e}")

        return results

    def _keyword_fallback(self, query: str) -> str:
        """Keyword-based rule matching (Phase 2 fallback)."""
        query_lower = query.lower()
        relevant = []

        combat_keywords = {"attack", "cast_spell", "defend", "flee", "combat", "damage", "fight", "sword", "hit"}
        exploration_keywords = {"explore", "investigate", "observe", "interact", "search", "rest", "discover", "hidden"}
        progression_keywords = {"level", "xp", "progress", "experience"}

        if any(k in query_lower for k in combat_keywords) and "combat" in self._keyword_rules:
            relevant.append(self._keyword_rules["combat"])
        if any(k in query_lower for k in exploration_keywords) and "exploration" in self._keyword_rules:
            relevant.append(self._keyword_rules["exploration"])
        if any(k in query_lower for k in progression_keywords) and "progression" in self._keyword_rules:
            relevant.append(self._keyword_rules["progression"])

        if not relevant:
            relevant.append(self._keyword_rules.get("progression", ""))

        return "\n\n---\n\n".join(relevant)
