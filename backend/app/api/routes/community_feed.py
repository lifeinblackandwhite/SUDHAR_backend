from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import Issue
from app.core.issue_states import IssueState

router = APIRouter(prefix="/community", tags=["Community"])

@router.get("/feed")
async def resident_issue_feed(
    state: str,
    city: str,
    pincode: str,
    category: str,  # 🔒 REQUIRED now
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Issue)
        .where(Issue.status == IssueState.UNDER_VERIFICATION)
        .where(Issue.abuse_cleared == True)   # 🔒 abuse prevention enforced
        .where(Issue.state == state)
        .where(Issue.city == city)
        .where(Issue.pincode == pincode)
        .where(Issue.category == category)    # 🔒 mandatory category
        .order_by(Issue.created_at.desc())
    )

    result = await db.execute(query)
    issues = result.scalars().all()

    return [
        {
            "id": issue.id,
            "description": issue.description,
            "category": issue.category,
            "state": issue.state,
            "city": issue.city,
            "area": issue.area,
            "pincode": issue.pincode,
            "status": issue.status,
            "created_at": issue.created_at,
        }
        for issue in issues
    ]