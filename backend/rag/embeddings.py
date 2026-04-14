"""Embedding generation via NVIDIA NIM API."""

import logging
from openai import AsyncOpenAI

import config

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "nvidia/nv-embedqa-e5-v5"
EMBEDDING_DIMENSIONS = 1024


class EmbeddingGenerator:
    """Generate embeddings using NVIDIA NIM API."""

    def __init__(self):
        self.client = AsyncOpenAI(
            base_url=config.NVIDIA_BASE_URL,
            api_key=config.NVIDIA_API_KEY,
        )

    async def embed_query(self, text: str) -> list[float]:
        """Generate embedding for a search query."""
        response = await self.client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=[text],
            extra_body={"input_type": "query", "truncate": "END"},
        )
        return response.data[0].embedding

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of documents."""
        if not texts:
            return []
        # Batch in groups of 20 to avoid API limits
        all_embeddings = []
        for i in range(0, len(texts), 20):
            batch = texts[i:i + 20]
            response = await self.client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=batch,
                extra_body={"input_type": "passage", "truncate": "END"},
            )
            all_embeddings.extend([d.embedding for d in response.data])
        return all_embeddings
