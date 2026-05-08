from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from crisiscoach.api.routes.auth import get_current_user

router = APIRouter()


@router.post("/goal-plan/commit")
async def commit_goal_plan(user: dict = Depends(get_current_user)):
    """Mark the most recent goal plan as committed, transition user to active, fire background agents."""
    user_id = user.get("sub", "")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        from crisiscoach.db.supabase import get_client
        sb = get_client()

        latest = (
            sb.table("goal_plan")
            .select("id")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        ).data
        if not latest:
            raise HTTPException(status_code=404, detail="No goal plan to commit")

        plan_id = latest[0]["id"]
        today = date.today().isoformat()
        sb.table("goal_plan").update({
            "goal_committed_at": today,
            "next_revision_date": (date.today() + timedelta(days=10)).isoformat(),
        }).eq("id", plan_id).execute()
        sb.table("users").update({"phase": "active"}).eq("id", user_id).execute()

        # Fire recalibration non-blocking (daily plan is built synchronously by the frontend)
        import asyncio
        from crisiscoach.agents.background.target_recalibrator import recalibrate_targets
        loop = asyncio.get_event_loop()
        loop.create_task(recalibrate_targets(user_id))

        return {"plan_id": plan_id, "committed_at": today}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/goal-plan/recent")
async def get_latest_goal_plan(user: dict = Depends(get_current_user)):
    """Return the most recent goal plan for the authenticated user."""
    user_id = user.get("sub", "")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        from crisiscoach.db.supabase import get_client
        row = (
            get_client()
            .table("goal_plan")
            .select("id, date, goal_stratergy, revision_analytics, goal_committed_at, next_revision_date, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if not row.data:
            raise HTTPException(status_code=404, detail="No goal plan found")
        return row.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
