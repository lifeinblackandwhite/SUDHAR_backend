from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db.models import Issue, IssueVerification
from app.services.community_decision import community_decision
from app.services.audit_logger import log_event

router = APIRouter(prefix="/community/verify", tags=["Community Verification"])

@router.post("/{issue_id}")
async def verify_issue(
    issue_id: int,
    vote: str,  # CONFIRM or DENY
    db: AsyncSession = Depends(get_db)
):
    verification = IssueVerification(
        issue_id=issue_id,
        verifier_id="mock_user",  # replace with Firebase UID later
        vote=vote
    )

    db.add(verification)
    await db.flush()

    new_state = await community_decision(db, issue_id)

    if new_state:
        issue = await db.get(Issue, issue_id)
        issue.status = new_state.value

        await log_event(
            db=db,
            issue_id=issue_id,
            actor_type="community",
            actor_id=None,
            action=new_state.value
        )

    await db.commit()
    return {"status": "vote recorded"}
