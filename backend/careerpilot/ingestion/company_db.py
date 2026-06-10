"""Ingest company profiles from data/companies.json into vector store."""
import asyncio
import json
from pathlib import Path
from careerpilot.agents.background.fact_checker import ingest_document

COLLECTION = "company_db"
_DATA_FILE = Path(__file__).parent.parent / "data" / "companies.json"


async def ingest_all_companies():
    companies = json.loads(_DATA_FILE.read_text())
    total = 0
    for company in companies:
        name = company["name"]
        chunks = []
        for signal in company.get("hiring_signals", []):
            chunks.append(f"{name} hiring signal: {signal}")
        for note in company.get("culture_notes", []):
            chunks.append(f"{name} culture: {note}")
        for step in company.get("interview_process", []):
            chunks.append(f"{name} interview process: {step}")
        stack = company.get("tech_stack", [])
        if stack:
            chunks.append(f"{name} tech stack: {', '.join(stack)}")
        roles = company.get("roles_commonly_open", [])
        if roles:
            chunks.append(f"{name} commonly hires: {', '.join(roles)}")

        result = await ingest_document(
            collection_name=COLLECTION,
            source_url=f"careerpilot://seed/company/{name.lower().replace(' ', '_')}",
            chunks=chunks,
            metadata={"company": name, "tier": company.get("tier", ""), "domain": "company_intel"},
        )
        total += result["ingested"]
    return {"ingested": total, "companies": len(companies)}


if __name__ == "__main__":
    asyncio.run(ingest_all_companies())
