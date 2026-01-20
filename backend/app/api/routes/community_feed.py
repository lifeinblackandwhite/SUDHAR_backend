from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.db.models import Issue, IssueMedia
from app.core.issue_states import IssueState

router = APIRouter(prefix="/community", tags=["Community"])


@router.get("/feed")
async def resident_issue_feed(
    state: str,
    city: str,
    pincode: str,
    category: str,  # REQUIRED
    db: AsyncSession = Depends(get_db)
):
    # Get issues
    query = (
        select(Issue)
        .where(Issue.status == IssueState.UNDER_VERIFICATION.value)
        .where(Issue.abuse_cleared.is_(True))
        .where(func.lower(Issue.city) == city.lower())
        .where(func.lower(Issue.state) == state.lower())
        .where(Issue.pincode == pincode)
        .where(func.lower(Issue.category) == category.lower())
        .order_by(Issue.created_at.desc())
    )

    result = await db.execute(query)
    issues = result.scalars().all()

    # Build response with images
    response = []
    for issue in issues:
        # Get images for this issue
        media_result = await db.execute(
            select(IssueMedia).where(IssueMedia.issue_id == issue.id)
        )
        media_items = media_result.scalars().all()
        
        # Convert file paths to URLs
        image_urls = []
        for media in media_items:
            # Extract filename from path like "/code/uploads/1_image.jpg"
            filename = media.file_path.split("/")[-1]
            image_urls.append(f"/uploads/{filename}")
        
        response.append({
            "id": issue.id,
            "title": issue.title,
            "description": issue.description,
            "category": issue.category,
            "state": issue.state,
            "city": issue.city,
            "area": issue.area,
            "pincode": issue.pincode,
            "status": issue.status,
            "created_at": issue.created_at,
            "images": image_urls,  # Added images
        })

    return response

