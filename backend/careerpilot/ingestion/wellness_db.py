"""Ingest mental wellness and burnout recovery content."""
import asyncio
from careerpilot.agents.background.fact_checker import ingest_document

COLLECTION = "wellness_db"

SEED_CHUNKS = [
    "Job search is a marathon. Scheduling 2 'off' hours daily for exercise or hobbies reduces burnout and improves decision quality.",
    "Rejection is statistically expected: most candidates need 50-200 applications for one offer at senior levels.",
    "Daily structure (wake time, start time, end time) during unemployment reduces anxiety by maintaining a sense of control.",
    "Social isolation worsens job search outcomes. Maintain at least one social interaction per day.",
    "The 988 Suicide & Crisis Lifeline is available 24/7 by call or text for anyone in emotional crisis.",
]


async def ingest_seed_data():
    return await ingest_document(
        collection_name=COLLECTION,
        source_url="careerpilot://seed/wellness",
        chunks=SEED_CHUNKS,
        metadata={"domain": "wellness"},
    )


if __name__ == "__main__":
    asyncio.run(ingest_seed_data())
