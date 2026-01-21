from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.database import get_db
from app.db.models import Issue, IssueVerification
from app.core.issue_states import IssueState
from app.services.audit_logger import log_event
from app.services.issue_state_service import change_issue_state
from dynamicranking.service import DynamicRankingService
import os

router = APIRouter(prefix="/community", tags=["Community"])

VERIFY_UPLOAD_DIR = "/code/uploads/verifications"
os.makedirs(VERIFY_UPLOAD_DIR, exist_ok=True)

# Community verification threshold - issue stays in feed until this many verifications
VERIFICATION_THRESHOLD = 10


@router.post("/verify/{issue_id}")
async def verify_issue(
    issue_id: int,
    verifier_id: str = Form(...),
    description: str | None = Form(None),
    image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    # --------------------------------------------------
    # 🔍 Fetch issue
    # --------------------------------------------------
    issue = await db.get(Issue, issue_id)

    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    # --------------------------------------------------
    # 🔒 State check (NO mutation)
    # --------------------------------------------------
    if IssueState(issue.status) != IssueState.UNDER_VERIFICATION:
        raise HTTPException(
            status_code=400,
            detail="Issue not open for community verification"
        )

    # --------------------------------------------------
    # 🚫 Prevent duplicate verification
    # --------------------------------------------------
    existing = await db.execute(
        select(IssueVerification)
        .where(IssueVerification.issue_id == issue_id)
        .where(IssueVerification.verifier_id == verifier_id)
    )

    if existing.scalar():
        raise HTTPException(
            status_code=400,
            detail="You have already verified this issue"
        )

    # --------------------------------------------------
    # 🖼 Save verification image
    # --------------------------------------------------
    filename = f"{issue_id}_{verifier_id}_{image.filename}"
    filepath = os.path.join(VERIFY_UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(await image.read())

    # --------------------------------------------------
    # 🧾 Store verification record
    # --------------------------------------------------
    verification = IssueVerification(
        issue_id=issue_id,
        verifier_id=verifier_id,
        description=description,
        image_path=filepath
    )

    db.add(verification)

    # --------------------------------------------------
    # 🧾 Audit log
    # --------------------------------------------------
    await log_event(
        db=db,
        issue_id=issue.id,
        actor_type="community",
        actor_id=verifier_id,
        action="VERIFICATION_SUBMITTED",
        new_value={
            "image_path": filepath,
            "description": description
        }
    )

    # --------------------------------------------------
    # ✅ Check verification threshold
    # --------------------------------------------------
    verification_count_result = await db.execute(
        select(func.count(IssueVerification.id))
        .where(IssueVerification.issue_id == issue_id)
    )
    # Add 1 because current verification isn't committed yet
    total_verifications = verification_count_result.scalar() + 1

    if total_verifications >= VERIFICATION_THRESHOLD:
        # Change status to VERIFIED
        change_issue_state(
            issue=issue,
            new_state=IssueState.VERIFIED
        )

        # Calculate priority score using dynamic ranking service
        ranking_service = DynamicRankingService()
        scores = ranking_service.calculate_priority_score(
            category=issue.category,
            verification_count=total_verifications,
            created_at=issue.created_at,
            status="Verified"
        )
        issue.priority_score = scores['priority_score']

        # Log state transition
        await log_event(
            db=db,
            issue_id=issue.id,
            actor_type="system",
            actor_id=None,
            action="COMMUNITY_VERIFIED",
            new_value={
                "verification_count": total_verifications,
                "priority_score": scores['priority_score']
            }
        )

    await db.commit()

    return {
        "status": "verification_submitted",
        "issue_id": issue_id,
        "verification_count": total_verifications,
        "community_verified": total_verifications >= VERIFICATION_THRESHOLD
    }
