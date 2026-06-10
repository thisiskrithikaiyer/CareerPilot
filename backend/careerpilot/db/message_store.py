"""Embeds and stores chat messages in ChromaDB for semantic skill scanning.

Only user messages are stored — assistant replies don't reveal user skills.
Collection: "conversations", filtered per-user by metadata at query time.
"""
import time
from careerpilot.db.vector_store import get_collection, embed_texts

COLLECTION = "conversations"


async def store_message(user_id: str, content: str, intent: str = "") -> None:
    """Embed and store a single user message in ChromaDB."""
    if not content.strip() or not user_id:
        return
    try:
        collection = get_collection(COLLECTION)
        embeddings = await embed_texts([content])
        doc_id = f"{user_id}_{int(time.time() * 1000)}"
        collection.add(
            documents=[content],
            embeddings=embeddings,
            metadatas=[{
                "user_id": user_id,
                "intent": intent,
                "timestamp": str(int(time.time())),
            }],
            ids=[doc_id],
        )
    except Exception as e:
        print(f"[MESSAGE_STORE] Failed to store message: {e}")


async def query_skill_signals(user_id: str, n_per_query: int = 5) -> list[str]:
    """
    Semantically search this user's conversation history for skill-revealing messages.
    Returns a deduplicated list of relevant message snippets.
    """
    _SKILL_QUERIES = [
        "technical skills programming languages frameworks tools",
        "system design architecture distributed systems scalability",
        "algorithms data structures dynamic programming graphs trees",
        "learned completed finished built implemented project",
        "interview asked technical round questions",
        "struggled with difficulty challenge blocked on",
        "practiced studied worked on coding problem",
    ]
    try:
        collection = get_collection(COLLECTION)
        embeddings = await embed_texts(_SKILL_QUERIES)

        seen: set[str] = set()
        results: list[str] = []

        for emb in embeddings:
            res = collection.query(
                query_embeddings=[emb],
                n_results=n_per_query,
                where={"user_id": user_id},
            )
            for doc in (res.get("documents") or [[]])[0]:
                if doc not in seen:
                    seen.add(doc)
                    results.append(doc)

        return results
    except Exception as e:
        print(f"[MESSAGE_STORE] Query failed: {e}")
        return []
