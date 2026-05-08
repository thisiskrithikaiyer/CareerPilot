"""ChromaDB-backed vector store using local sentence-transformer embeddings."""
from functools import lru_cache
from typing import Any
import chromadb
from chromadb.config import Settings
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from crisiscoach.config import CHROMA_PERSIST_DIR

_ef = DefaultEmbeddingFunction()


@lru_cache(maxsize=1)
def _get_chroma() -> chromadb.Client:
    return chromadb.PersistentClient(
        path=CHROMA_PERSIST_DIR,
        settings=Settings(anonymized_telemetry=False),
    )


def get_collection(name: str) -> chromadb.Collection:
    return _get_chroma().get_or_create_collection(name, embedding_function=_ef)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    return _ef(texts)


def query_collection(name: str, query_text: str, n_results: int = 4) -> list[dict[str, Any]]:
    """Returns list of metadata dicts with 'document' and 'source' keys."""
    collection = get_collection(name)
    results = collection.query(query_texts=[query_text], n_results=n_results)
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    return [{"document": d, **m} for d, m in zip(docs, metas)]
