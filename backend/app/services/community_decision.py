from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.models import IssueVerification
from app.core.issue_states import IssueState

CONFIRM_THRESHOLD = 3
DENY_THRESHOLD = 2

async def community_decision(db: AsyncSession, issue_id: int):
    result = await db.execute(
        select(
            IssueVerification.vote,
            func.count(IssueVerification.vote)
        )
        .where(IssueVerification.issue_id == issue_id)
        .group_by(IssueVerification.vote)
    )

    counts = {row[0]: row[1] for row in result}

    if counts.get("DENY", 0) >= DENY_THRESHOLD:
        return IssueState.COMMUNITY_REJECTED

    if counts.get("CONFIRM", 0) >= CONFIRM_THRESHOLD:
        return IssueState.VERIFIED

    return None
