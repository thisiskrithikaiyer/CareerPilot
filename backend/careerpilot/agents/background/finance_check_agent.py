"""Finance check agent — weekly runway recalculation based on updated expenses."""


async def run_for_user(user_id: str) -> dict:
    """Recalculate runway weeks from latest expense and savings data."""
    from careerpilot.db.supabase import get_client
    sb = get_client()

    profile = (
        sb.table("users")
        .select("monthly_savings, monthly_expenses, severance_remaining")
        .eq("id", user_id)
        .single()
        .execute()
    )
    data = profile.data or {}

    savings = float(data.get("monthly_savings") or 0)
    expenses = float(data.get("monthly_expenses") or 1)  # avoid div/0
    severance = float(data.get("severance_remaining") or 0)
    total_available = savings + severance

    if expenses <= 0:
        return {"skipped": True, "reason": "no_expense_data"}

    runway_months = total_available / expenses
    runway_weeks = int(runway_months * 4.33)

    sb.table("users").update({"runway_weeks": runway_weeks}).eq("id", user_id).execute()

    alert = None
    if runway_weeks <= 8:
        alert = (
            f"Warning: You have approximately {runway_weeks} weeks of runway left. "
            "Consider reducing discretionary spending or exploring bridge income options."
        )
        sb.table("notifications").insert({
            "user_id": user_id,
            "type": "finance_alert",
            "body": alert,
        }).execute()

    return {"runway_weeks": runway_weeks, "alert": alert}
