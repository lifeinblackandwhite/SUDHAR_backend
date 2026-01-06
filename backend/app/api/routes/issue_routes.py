from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db.models import Issue, IssueMedia
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
import os

router = APIRouter(prefix="/issues", tags=["Issues"])

# 🔹 Absolute path INSIDE container
UPLOAD_DIR = "/code/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_issue(
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
    # 🔹 Create PostGIS point (lon, lat order is IMPORTANT)
    point = from_shape(Point(longitude, latitude), srid=4326)

    new_issue = Issue(
        description=description,
        category=category,
        state=state,
        city=city,
        area=area,
        pincode=pincode,
        location=point
    )

    db.add(new_issue)
    await db.flush()  # ensures new_issue.id exists

    # 🔹 Save images safely
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
    return {"status": "success", "issue_id": new_issue.id}
