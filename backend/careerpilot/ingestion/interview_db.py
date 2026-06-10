"""Ingest interview tips, question banks, and STAR frameworks into vector store."""
import asyncio
from careerpilot.agents.background.fact_checker import ingest_document

COLLECTION = "interview_db"

SEED_CHUNKS = [
    "Use the STAR method (Situation, Task, Action, Result) for behavioral questions to demonstrate concrete impact.",
    "Quantify results whenever possible: 'reduced load time by 40%' beats 'improved performance'.",
    "For system design rounds, clarify requirements first, then estimate scale, then propose architecture.",
    "The 'tell me about yourself' answer should be 90 seconds: past role → key achievement → why this role.",
    "Research the company's last two earnings calls and recent blog posts before any interview.",
]


async def ingest_seed_data():
    return await ingest_document(
        collection_name=COLLECTION,
        source_url="careerpilot://seed/interview",
        chunks=SEED_CHUNKS,
        metadata={"domain": "interview_prep"},
    )


async def ingest_from_file(filepath: str, source_url: str):
    with open(filepath) as f:
        text = f.read()
    chunks = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 50]
    return await ingest_document(COLLECTION, source_url, chunks, {"domain": "interview_prep"})


if __name__ == "__main__":
    asyncio.run(ingest_seed_data())
