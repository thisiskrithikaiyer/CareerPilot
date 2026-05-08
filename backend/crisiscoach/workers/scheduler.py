"""Cron job scheduler — finance checks, interview prep (APScheduler)."""
import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


async def _run_finance_checks() -> None:
    from crisiscoach.db.supabase import get_client
    from crisiscoach.agents.background.finance_check_agent import run_for_user

    sb = get_client()
    users = sb.table("users").select("id").eq("active", True).execute()
    for u in users.data:
        try:
            await run_for_user(u["id"])
        except Exception as e:
            logger.error(f"finance_check failed for {u['id']}: {e}")


async def _run_interview_prep() -> None:
    from crisiscoach.db.supabase import get_client
    from crisiscoach.agents.background.interview_prep import generate_prep_plan

    sb = get_client()
    users = sb.table("users").select("id").eq("active", True).execute()
    for u in users.data:
        try:
            await generate_prep_plan(u["id"])
        except Exception as e:
            logger.error(f"interview_prep failed for {u['id']}: {e}")


async def _run_target_recalibration() -> None:
    from crisiscoach.db.supabase import get_client
    from crisiscoach.agents.background.target_recalibrator import recalibrate_targets

    sb = get_client()
    # Only run for users who have committed to a goal plan (phase=active)
    users = sb.table("users").select("id").eq("phase", "active").execute()
    for u in users.data:
        try:
            await recalibrate_targets(u["id"])
        except Exception as e:
            logger.error(f"target_recalibration failed for {u['id']}: {e}")


def build_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    # Finance check — every Sunday at 9 AM
    scheduler.add_job(_run_finance_checks, CronTrigger(day_of_week="sun", hour=9), id="finance_check")

    # Interview prep — every Monday at 7 AM
    scheduler.add_job(_run_interview_prep, CronTrigger(day_of_week="mon", hour=7), id="interview_prep")

    # Target recalibration — every Sunday at 6 AM (before finance check)
    scheduler.add_job(_run_target_recalibration, CronTrigger(day_of_week="sun", hour=6), id="target_recalibration")

    return scheduler


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.get_event_loop()
    scheduler = build_scheduler()
    scheduler.start()
    logger.info("scheduler: started")
    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
