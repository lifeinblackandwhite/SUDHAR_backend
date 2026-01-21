from fastapi import APIRouter, Depends, UploadFile, File, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db.models import Issue, IssueMedia
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
import os

from app.core.issue_states import IssueState
from app.services.abuse_decision import abuse_decision
from app.services.audit_logger import log_event
from app.services.notification_service import notify_community
from app.services.issue_state_service import change_issue_state

router = APIRouter(prefix="/issues", tags=["Issues"])

UPLOAD_DIR = "/code/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_issue(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    state: str = Form(...),
    city: str = Form(...),
    area: str = Form(...),
    pincode: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    user_id: str = Form(None),  # Firebase UID from Flutter
    images: list[UploadFile] | None = File(None),
    db: AsyncSession = Depends(get_db)
):
    # --------------------------------------------------
    # 1️⃣ Create geometry
    # --------------------------------------------------
    point = from_shape(Point(longitude, latitude), srid=4326)

    # --------------------------------------------------
    # 2️⃣ Create Issue (SUBMITTED)
    # --------------------------------------------------
    issue = Issue(
        user_id=user_id,  # Link to reporter's Firebase UID
        title=title,
        description=description,
        category=category,
        state=state,
        city=city,
        area=area,
        pincode=pincode,
        location=point,
        status=IssueState.SUBMITTED.value,
        abuse_cleared=False
    )

    db.add(issue)
    await db.flush()  # ID guaranteed here

    # --------------------------------------------------
    # 3️⃣ Read image for abuse prevention
    # --------------------------------------------------
    image_bytes = None
    if images:
        image_bytes = await images[0].read()
        images[0].file.seek(0)

    # -------------------------------------------------- 
    # 4️⃣ Abuse prevention
    # --------------------------------------------------
    is_clean = await abuse_decision(issue, image_bytes, latitude=latitude, longitude=longitude)

    if not is_clean:
        change_issue_state(
            issue=issue,
            new_state=IssueState.AUTO_REJECTED
        )

        await log_event(
            db=db,
            issue_id=issue.id,
            actor_type="system",
            actor_id=None,
            action="AUTO_REJECTED",
            new_value={"reason": "abuse_prevention"},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        await db.commit()
        return {"status": "rejected", "reason": "abuse_detected"}

    # --------------------------------------------------
    # 5️⃣ Passed abuse prevention
    # --------------------------------------------------
    issue.abuse_cleared = True

    change_issue_state(
        issue=issue,
        new_state=IssueState.UNDER_VERIFICATION
    )

    await log_event(
        db=db,
        issue_id=issue.id,
        actor_type="system",
        actor_id=None,
        action="UNDER_VERIFICATION",
    )

    # --------------------------------------------------
    # 6️⃣ Save images
    # --------------------------------------------------
    if images:
        for img in images:
            path = os.path.join(UPLOAD_DIR, f"{issue.id}_{img.filename}")
            with open(path, "wb") as f:
                f.write(await img.read())

            db.add(IssueMedia(issue_id=issue.id, file_path=path))

    # --------------------------------------------------
    # 7️⃣ COMMIT (single source of truth)
    # --------------------------------------------------
    await db.commit()

    # --------------------------------------------------
    # 8️⃣ Notify AFTER commit
    # --------------------------------------------------
    await notify_community(issue)

    return {
        "status": "success",
        "issue_id": issue.id
    }


@router.get("/{issue_id}")
async def get_issue_by_id(
    issue_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get issue details by ID including images.
    """
    from sqlalchemy import select
    
    issue = await db.get(Issue, issue_id)
    
    if not issue:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Issue not found")
    
    # Get images for this issue
    media_result = await db.execute(
        select(IssueMedia).where(IssueMedia.issue_id == issue_id)
    )
    media_items = media_result.scalars().all()
    
    image_urls = []
    for media in media_items:
        filename = media.file_path.split("/")[-1]
        image_urls.append(f"/uploads/{filename}")
    
    return {
        "id": issue.id,
        "title": issue.title,
        "description": issue.description,
        "category": issue.category,
        "state": issue.state,
        "city": issue.city,
        "area": issue.area,
        "pincode": issue.pincode,
        "status": issue.status,
        "priority_score": round(issue.priority_score, 2) if issue.priority_score else 0,
        "created_at": issue.created_at.isoformat() if issue.created_at else None,
        "images": image_urls,
    }
