"""Redis queue consumer — dequeues plan generation jobs and runs the Planner agent."""
import asyncio
import json
import logging

logger = logging.getLogger(__name__)


async def process_job(job: dict) -> None:
    user_id = job.get("user_id")
    if not user_id:
        logger.warning("plan_worker: job missing user_id, skipping")
        return
    try:
        from careerpilot.agents.background.daily_check import build_daily_plan
        result = await build_daily_plan(user_id)
        logger.info(f"plan_worker: plan generated for {user_id} — mode={result['plan'].get('priority_mode')}")
    except Exception as e:
        logger.error(f"plan_worker: failed for user {user_id}: {e}")


async def run_worker(poll_interval: float = 1.0) -> None:
    from careerpilot.db.redis import get_redis
    r = get_redis()
    logger.info("plan_worker: started, listening on plan_queue")
    while True:
        raw = r.blpop("plan_queue", timeout=int(poll_interval))
        if raw:
            _, payload = raw
            job = json.loads(payload)
            await process_job(job)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker())
