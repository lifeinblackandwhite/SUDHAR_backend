from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db.models import Issue, IssueMedia
from sqlalchemy import insert
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

router = APIRouter(prefix="/issues", tags=["Issues"])

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
    images: list[UploadFile] = File(default=None),
    db: AsyncSession = Depends(get_db)
):
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
    await db.flush()  # To get issue ID before commit

    if images:
        for img in images:
            filename = f"uploads/{new_issue.id}_{img.filename}"
            with open(filename, "wb") as buffer:
                buffer.write(await img.read())

            media = IssueMedia(issue_id=new_issue.id, file_path=filename)
            db.add(media)

    await db.commit()
    return {"status": "success", "issue_id": new_issue.id}
