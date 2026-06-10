"""Fact checker — pre-embeds source chunks into vector store on document ingestion."""
from careerpilot.db.vector_store import get_collection, embed_texts


async def ingest_document(
    collection_name: str,
    source_url: str,
    chunks: list[str],
    metadata: dict | None = None,
) -> dict:
    """
    Embed and store document chunks. Called during ingestion pipeline runs.
    Each chunk is stored with source URL for citation retrieval.
    """
    if not chunks:
        return {"ingested": 0}

    collection = get_collection(collection_name)
    base_meta = metadata or {}
    ids = [f"{source_url}::chunk_{i}" for i in range(len(chunks))]
    metadatas = [{**base_meta, "source": source_url, "chunk_index": i} for i in range(len(chunks))]

    embeddings = await embed_texts(chunks)
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )
    return {"ingested": len(chunks), "collection": collection_name}


async def verify_claim(claim: str, collection_name: str) -> dict:
    """Check if a claim is supported by stored sources."""
    from careerpilot.db.vector_store import query_collection

    results = query_collection(collection_name, claim, n_results=3)
    has_support = bool(results)
    return {
        "claim": claim,
        "supported": has_support,
        "sources": [r.get("source", "") for r in results],
    }
