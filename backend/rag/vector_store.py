"""ChromaDB vector store for rules and narrative trajectories."""

import json
import logging
from pathlib import Path
from typing import Optional

import chromadb

from rag.embeddings import EmbeddingGenerator, EMBEDDING_DIMENSIONS

logger = logging.getLogger(__name__)

CHROMA_DIR = Path(__file__).parent.parent / "data" / "chroma_db"
RULES_DIR = Path(__file__).parent.parent / "data" / "rules"
TRAJECTORIES_FILE = Path(__file__).parent.parent / "data" / "trajectories.json"

RULES_COLLECTION = "game_rules"
TRAJECTORIES_COLLECTION = "narrative_trajectories"


class VectorStore:
    """Manages ChromaDB collections for rules and narrative trajectories."""

    def __init__(self):
        self.client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self.embedder = EmbeddingGenerator()
        self.rules_collection = None
        self.trajectories_collection = None
        self._initialized = False

    async def initialize(self):
        """Create/load collections and index rules + trajectories."""
        if self._initialized:
            return

        # Rules collection — stores chunked rule documents
        self.rules_collection = self.client.get_or_create_collection(
            name=RULES_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )

        # Trajectories collection — stores narrative examples
        self.trajectories_collection = self.client.get_or_create_collection(
            name=TRAJECTORIES_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )

        # Index rules if collection is empty
        if self.rules_collection.count() == 0:
            await self._index_rules()

        # Index trajectories if available
        if self.trajectories_collection.count() == 0 and TRAJECTORIES_FILE.exists():
            await self._index_trajectories()

        self._initialized = True
        logger.info(
            f"VectorStore initialized: {self.rules_collection.count()} rules chunks, "
            f"{self.trajectories_collection.count()} trajectories"
        )

    async def _index_rules(self):
        """Load and chunk rule files into ChromaDB."""
        if not RULES_DIR.exists():
            logger.warning(f"Rules directory not found: {RULES_DIR}")
            return

        all_chunks = []
        all_ids = []
        all_metadata = []

        for rule_file in RULES_DIR.glob("*.md"):
            category = rule_file.stem
            content = rule_file.read_text()

            # Split into chunks by headers (##)
            sections = content.split("## ")
            for i, section in enumerate(sections):
                section = section.strip()
                if not section:
                    continue

                chunk_id = f"{category}_chunk_{i}"
                # Truncate to ~500 chars per chunk for better retrieval
                chunk_text = section[:500]
                all_chunks.append(chunk_text)
                all_ids.append(chunk_id)
                all_metadata.append({"category": category, "chunk_index": i})

        if all_chunks:
            embeddings = await self.embedder.embed_documents(all_chunks)
            self.rules_collection.add(
                ids=all_ids,
                documents=all_chunks,
                embeddings=embeddings,
                metadatas=all_metadata,
            )
            logger.info(f"Indexed {len(all_chunks)} rule chunks from {RULES_DIR}")

    async def _index_trajectories(self):
        """Load seed narrative trajectories into ChromaDB."""
        try:
            data = json.loads(TRAJECTORIES_FILE.read_text())
            trajectories = data if isinstance(data, list) else data.get("trajectories", [])
        except Exception as e:
            logger.warning(f"Failed to load trajectories: {e}")
            return

        if not trajectories:
            return

        chunks = []
        ids = []
        metas = []

        for i, traj in enumerate(trajectories):
            text = traj if isinstance(traj, str) else json.dumps(traj)
            chunks.append(text[:500])
            ids.append(f"traj_{i}")
            metas.append({"type": "trajectory", "index": i})

        if chunks:
            embeddings = await self.embedder.embed_documents(chunks)
            self.trajectories_collection.add(
                ids=ids,
                documents=chunks,
                embeddings=embeddings,
                metadatas=metas,
            )
            logger.info(f"Indexed {len(chunks)} narrative trajectories")

    async def search_rules(self, query: str, top_k: int = 3) -> list[dict]:
        """Search rules by semantic similarity."""
        await self.initialize()

        query_embedding = await self.embedder.embed_query(query)
        results = self.rules_collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self.rules_collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        hits = []
        if results and results["documents"]:
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                similarity = 1.0 - dist  # cosine distance → similarity
                hits.append({
                    "text": doc,
                    "category": meta.get("category", "unknown"),
                    "similarity": round(similarity, 4),
                })
        return hits

    async def search_trajectories(self, query: str, top_k: int = 3) -> list[dict]:
        """Search narrative trajectories by semantic similarity."""
        await self.initialize()

        if self.trajectories_collection.count() == 0:
            return []

        query_embedding = await self.embedder.embed_query(query)
        results = self.trajectories_collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self.trajectories_collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        hits = []
        if results and results["documents"]:
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                similarity = 1.0 - dist
                hits.append({
                    "text": doc,
                    "similarity": round(similarity, 4),
                })
        return hits

    async def add_trajectory(self, text: str, metadata: dict = None):
        """Add a new narrative trajectory (e.g., from completed sessions)."""
        await self.initialize()

        traj_id = f"traj_{self.trajectories_collection.count()}"
        embedding = await self.embedder.embed_documents([text])

        self.trajectories_collection.add(
            ids=[traj_id],
            documents=[text[:500]],
            embeddings=embedding,
            metadatas=[metadata or {"type": "player_generated"}],
        )
        logger.info(f"Added trajectory: {traj_id}")

    async def get_top_similarity(self, query: str) -> float:
        """Get the highest similarity score for a query across all collections."""
        rule_hits = await self.search_rules(query, top_k=1)
        traj_hits = await self.search_trajectories(query, top_k=1)

        scores = []
        if rule_hits:
            scores.append(rule_hits[0]["similarity"])
        if traj_hits:
            scores.append(traj_hits[0]["similarity"])

        return max(scores) if scores else 0.5  # Default to neutral
