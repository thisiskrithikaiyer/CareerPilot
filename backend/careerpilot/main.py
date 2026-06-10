from dotenv import load_dotenv
load_dotenv()

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from careerpilot.config import CORS_ORIGINS
from careerpilot.api.routes import chat, checkin, plan, auth, profile, goal_plan, daily_log, interviews, dashboard, intake

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from careerpilot.ingestion.curriculum_db import ingest_seed_data
    try:
        result = await ingest_seed_data()
        if not result.get("skipped"):
            logger.info(f"startup: ingested {result['ingested']} curriculum chunks")
    except Exception as e:
        logger.warning(f"startup: curriculum ingestion failed — {e}")
    yield


app = FastAPI(title="CrisisCoach AI", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(checkin.router, prefix="/api", tags=["checkin"])
app.include_router(plan.router, prefix="/api", tags=["plan"])
app.include_router(profile.router, prefix="/api/profile", tags=["profile"])
app.include_router(goal_plan.router, prefix="/api", tags=["goal-plan"])
app.include_router(daily_log.router, prefix="/api", tags=["daily-log"])
app.include_router(interviews.router, prefix="/api", tags=["interviews"])
app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
app.include_router(intake.router, prefix="/api", tags=["intake"])


@app.get("/health")
def health():
    return {"status": "ok"}
