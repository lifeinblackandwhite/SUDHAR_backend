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

from app.core.issue_states import IssueState
from app.services.notification_service import notify_community


router = APIRouter(prefix="/issues", tags=["Issues"])

# 🔹 Absolute path INSIDE container
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
    images: list[UploadFile] | None = File(None),
    db: AsyncSession = Depends(get_db)
):
    point = from_shape(Point(longitude, latitude), srid=4326)

    # 1️⃣ Create issue (initial state)
    new_issue = Issue(
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

    db.add(new_issue)
    await db.flush()  # ensures ID exists

    # 2️⃣ Run abuse prevention (Java service)
    is_clean = await abuse_decision(new_issue)

    if not is_clean:
        # ❌ Auto reject
        new_issue.status = IssueState.AUTO_REJECTED.value

        await log_event(
            db=db,
            issue_id=new_issue.id,
            actor_type="system",
            actor_id=None,
            action="AUTO_REJECTED",
            new_value={"reason": "abuse_detection"},
        )

        await db.commit()
        return {
            "status": "rejected",
            "reason": "abuse_detected"
        }

    # 3️⃣ Abuse PASSED → mark cleared
    new_issue.abuse_cleared = True
    new_issue.status = IssueState.UNDER_VERIFICATION.value

    # 4️⃣ Audit log
    await log_event(
        db=db,
        issue_id=new_issue.id,
        actor_type="system",
        actor_id=None,
        action="UNDER_VERIFICATION",
    )

    # 5️⃣ Notify community (NOW it is allowed)
    await notify_community(new_issue)

    # 6️⃣ Save images
    if images:
        for img in images:
            safe_filename = f"{new_issue.id}_{img.filename}"
            filepath = os.path.join(UPLOAD_DIR, safe_filename)

            with open(filepath, "wb") as buffer:
                buffer.write(await img.read())

            db.add(
                IssueMedia(
                    issue_id=new_issue.id,
                    file_path=filepath
                )
            )

    await db.commit()

    return {
        "status": "success",
        "issue_id": new_issue.id
    }

