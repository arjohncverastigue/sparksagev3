from fastapi import APIRouter, Depends
from api.deps import get_current_user
import db

router = APIRouter()


@router.get("/summary")
async def analytics_summary(user: dict = Depends(get_current_user)):
    """Return summary counts of analytics events grouped by day and event_type.

    Rows now also include aggregated `tokens` and `cost` columns (Phase 5.4).
    """
    summary = await db.get_analytics_summary()
    return {"summary": summary}


@router.get("/history")
async def analytics_history(limit: int = 1000, user: dict = Depends(get_current_user)):
    """Return recent analytics events (most recent first)."""
    history = await db.get_analytics_history(limit=limit)
    return {"history": history}
