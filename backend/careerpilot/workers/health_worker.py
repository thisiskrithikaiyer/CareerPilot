"""Nightly worker — runs PauseAgent and DailyCheck for all active users."""
import asyncio
import logging

logger = logging.getLogger(__name__)


async def run_nightly() -> None:
    from careerpilot.db.supabase import get_client
    from careerpilot.agents.background.pause_agent import run_for_user as pause_check
    from careerpilot.agents.background.daily_check import aggregate_for_user

    sb = get_client()
    users = sb.table("users").select("id").eq("active", True).execute()
    user_ids = [u["id"] for u in users.data]
    logger.info(f"health_worker: processing {len(user_ids)} users")

    for user_id in user_ids:
        try:
            agg = await aggregate_for_user(user_id)
            pause = await pause_check(user_id)
            logger.info(f"health_worker: {user_id} — agg={agg}, burnout={pause.get('burnout_flag')}")
        except Exception as e:
            logger.error(f"health_worker: error for {user_id}: {e}")

    logger.info("health_worker: nightly run complete")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_nightly())
