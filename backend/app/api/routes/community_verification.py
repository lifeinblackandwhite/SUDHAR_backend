from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.db.models import Issue, IssueVerification
from app.core.issue_states import IssueState
from app.services.audit_logger import log_event
import os

router = APIRouter(prefix="/community", tags=["Community"])

VERIFY_UPLOAD_DIR = "/code/uploads/verifications"
os.makedirs(VERIFY_UPLOAD_DIR, exist_ok=True)


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

    await db.commit()

    # ❗ STATE CHANGE IS DELIBERATELY NOT DONE HERE
    # Similarity + threshold logic will decide later

    return {
        "status": "verification_submitted",
        "issue_id": issue_id
    }
